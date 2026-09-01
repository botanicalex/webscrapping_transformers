# Guía de esta rama para Alexa

Esta rama (`radar-max_Septiembre`) es una copia podada del proyecto, lista para clonar y
correr sin el historial de experimentos. Si algo de lo de abajo no cuadra con lo que ves en
el código, el código manda — pero repórtalo, porque significa que esta guía quedó
desactualizada.

## Qué es el proyecto

Un radar que clasifica los 32 departamentos de Colombia en riesgo **Bajo / Medio / Alto**
a partir de prensa regional, donde **Alto no significa "pasan muchas cosas"**: significa
**zona difícil o inviable para implementar un proyecto** (conflicto activo, presencia de
grupos armados, ausencia de Estado). Medio y Bajo son, en ese orden, menos difíciles.

## Qué contiene esta rama

### `src/` — el pipeline de producción (ejecutar siempre desde la raíz del repo)

| Script | Qué hace |
|---|---|
| `scrappers.py` | Scraping de los periódicos regionales por departamento. |
| `correr_grupo.py` | Corre el scraping de uno o varios de los 11 grupos de departamentos (`--listar` para verlos, `N` para correr uno, `--todos` para los 11). |
| `monitor.py` | Muestra qué departamentos ya tienen corpus (`.pkl`) y cuáles faltan. |
| `Transformer_optimo.py` | Corre el modelo NLI sobre el corpus: las 26 hipótesis por artículo, el descuento de sesgo, el score corregido, y la agregación por departamento (MAX en esta rama). |
| `radar.py` | Combina los 26 indicadores agregados en un único radar por departamento y lo clasifica en Bajo/Medio/Alto con los cortes fijos. |
| `config_pipeline.py` | Configuración central: rutas, grupos de scraping, los cortes Bajo/Medio/Alto. |
| `orquestador_pipeline.py` | Corre el pipeline completo (scraping opcional → indicadores → radar → comparación con el DANE). Uso típico: `--skip-scraping`, reusando el corpus ya scrapeado. |
| `metricas_y_calculo_de_error.py` | Compara el radar propio contra el oficial del DANE y calcula accuracy y métricas de error. |
| `test_integracion.py` | Suite de 10 tests con un corpus sintético (sin cargar el modelo NLI). Es la única red de seguridad del repo. |

### `contexto/` — documentación bajo demanda

Once documentos (`00` a `10`) pensados para leerse solo el que haga falta, no todos de
una sentada. Empezar por `contexto/00_estado_actual.md` (qué corre hoy) y
`contexto/10_combinaciones_y_rumbo.md` (comparación de configuraciones medidas, incluida
P75 vs MAX). `contexto/08_log_decisiones.md` tiene el detalle de por qué el historial
técnico del proyecto eligió P75 sobre MAX.

### `datos/referencia/` — la referencia oficial

Dos archivos `.xlsx` con el radar de riesgo publicado por el DANE para los 32
departamentos, contra el que se mide la accuracy del radar propio.
`comparacion_radares_V3.xlsx` es la versión vigente.

## Correr sobre veredas y municipios

El mismo pipeline se puede correr sobre un lugar más chico que un departamento (una
vereda, un municipio), para cuando no hay estadística oficial a esa escala:

1. Editar la lista `LUGARES` dentro de `src/scrape_lugares.py` (nombre de búsqueda,
   etiqueta descriptiva, periódicos a usar).
2. `python src/scrape_lugares.py` — scrapea cada lugar y guarda un `.pkl` por lugar en
   `datos/corpus/`.
3. `python src/pipeline_lugares.py` — combina esos `.pkl` (más el corpus de Antioquia
   2023 ya scrapeado), corre las 26 hipótesis NLI, y escribe una tabla de indicadores por
   artículo y un Excel resumen (MAX + artículo de origen) por lugar.

Un lugar se puntúa **exactamente igual que un departamento**: las mismas 26 hipótesis V2,
el mismo sesgo descontado, el mismo MAX por indicador, y los mismos cortes fijos
(`CORTE_BAJO_MEDIO_RADAR`/`CORTE_MEDIO_ALTO_RADAR` de `src/config_pipeline.py`) para
clasificar en Bajo/Medio/Alto — no hay una receta distinta para escalas sub-departamentales.

## Herramientas

- **`src/combinar_corpus.py`** — fusiona un departamento re-scrapeado (por ejemplo tras
  corregir un bug del scraper) al corpus nacional: reemplaza las filas viejas de ese
  departamento por las nuevas, deduplica por URL y descarta filas sin texto. No corre el
  modelo NLI.
- **`src/generar_max_articulos_por_departamento.py`** — sin GPU: lee un `df_procesado` ya
  calculado y genera un Excel con, por cada indicador y departamento, el valor MÁXIMO y el
  artículo que lo produjo. Útil para verificar manualmente que un indicador alto refleja
  algo real en el artículo de origen.

## Cómo ejecutarlo

**Requisitos:** Python con PyTorch + CUDA (el modelo NLI corre mucho más rápido con GPU),
`transformers`, `pandas`, `openpyxl`, `scikit-learn`. Para scraping: `playwright`,
`aiohttp`, `nest_asyncio`. Todo en `requirements.txt`. El modelo NLI
(`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`) se descarga solo, a
`~/.cache/huggingface`, la primera vez que se usa.

**Los datos no van en git.** `datos/corpus/` (texto crudo scrapeado) y `datos/scores/`
(matrices de scores ya calculadas, para no tener que volver a usar la GPU) pesan decenas
de MB y se reciben aparte, en un `.zip`. Descomprimirlo dentro de la carpeta `datos/`, de
modo que queden `datos/corpus/*.pkl` y `datos/scores/*.pkl`.

Comandos:

```bash
python src/correr_grupo.py --listar               # ver los 11 grupos de scraping
python src/correr_grupo.py N                       # scrapear el grupo N
python src/orquestador_pipeline.py --skip-scraping  # pipeline completo, sin scrapear de nuevo
python src/test_integracion.py                      # verificar que todo sigue funcionando
```

## Cómo se calcula el radar en esta rama

1. Cada artículo se evalúa contra **26 hipótesis** ("hay presencia de grupos armados en
   este territorio", etc.) con el modelo NLI, que da una probabilidad de que el texto
   respalde cada una (`ent_`) y una probabilidad de neutralidad (`neu_`).
2. Se descuenta un sesgo "sí-decidor" estimado con 4 hipótesis nulas de calibración, y se
   calcula el score corregido: `clip(clip(ent − sesgo, 0) * (1 − neu), 0, 1)`.
3. Por departamento y por cada uno de los 26 indicadores, se toma el valor **MÁXIMO** entre
   todos los artículos de ese departamento (`grupo[c].max()`).
4. El radar final es el **promedio simple de los 26 indicadores** — sin pesos, sin
   z-score, sin terciles.
5. Se clasifica con **cortes fijos**: `Bajo < 0.766 <= Medio < 0.9233 <= Alto`. Estos
   cortes se recalibraron específicamente para la escala MAX (los que traía la rama
   `pruebas`, 0.2969/0.3527, estaban calibrados para P75 y no significan nada aquí — un
   umbral solo tiene sentido para la distribución con la que se calibró). Se leyeron de
   huecos naturales en la distribución de los 32 departamentos, sin mirar la clasificación
   oficial del DANE, y se verificaron después contra un conjunto de departamentos que "no
   deberían" salir Alto o Bajo por juicio externo (ninguno se rompió). Con esos cortes: 6
   departamentos Bajo, 19 Medio, 7 Alto; accuracy contra el DANE 34.4%; Spearman contra el
   valor oficial continuo −0.1653 (calculado offline desde
   `datos/scores/scores_v2_32deptos.pkl`, sin usar GPU).

## La decisión de MAX

**Usar MAX en vez de P75 es un requisito de negocio del jefe, no una recomendación
técnica del proyecto.** Nota honesta y breve sobre la limitación conocida: el MAX está
dominado por el tamaño del corpus — un departamento con más artículos scrapeados tiene más
oportunidades de que algo puntúe alto, con independencia de si el riesgo real es mayor.
La revisión técnica del historial del proyecto midió esto (razón señal/artefacto 0.91 para
MAX contra 49.0 para P75) y por eso recomendaba P75, que además correlacionaba
positivamente con el radar oficial (Spearman +0.42) mientras que MAX no (−0.1653 en esta
rama, −0.18 en la medición histórica equivalente). El detalle completo está en
`contexto/08_log_decisiones.md`.

## Qué se eliminó y por qué

Para que esta rama sea fácil de clonar y no parezca un proyecto a medio hacer, se quitó
todo lo que era parte del *proceso* de llegar hasta acá, no del resultado:

- **`experimentos/` completo** (motor NLI de pruebas, hipótesis V0 y V2 originales,
  estándar de plata, y ~15 scripts de experimentos con sus resultados). Las 26 hipótesis
  V2 ya están incorporadas directamente en `src/Transformer_optimo.py`; `src/` nunca
  importó nada de `experimentos/`, así que el pipeline no pierde nada.
- **`src/generar_tablas_por_departamento.py`** — usaba el pre-filtro social, que se
  retiró de producción (rechazado, ver `contexto/08_log_decisiones.md`); queda fuera de
  esta rama.
- **Artefactos internos**: `PROMPT_ARRANQUE.md`, `AUDITORIA_2026-09-01.md` y
  `referencia_radar_simple.py` — notas y borradores de trabajo interno del equipo, no
  necesarios para correr o entender el pipeline.
- **El skill de Claude Code `experimento-hipotesis`**, porque dependía por completo de
  `experimentos/`.

Nada de esto se perdió: sigue existiendo en la rama `pruebas` del repositorio original.
