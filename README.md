# Radar de riesgo territorial — Colombia

Sistema que clasifica los 32 departamentos de Colombia (y, en principio, lugares más
pequeños como veredas o municipios) en riesgo **Bajo / Medio / Alto** a partir de prensa
regional. **Radar alto significa zona difícil o inviable para implementar un proyecto**
—conflicto activo, presencia de grupos armados, ausencia de Estado—, no "cuánto pasa" en
la zona sino "cuánto estorba" a una intervención.

El pipeline scrapea periódicos regionales para el territorio pedido, evalúa cada artículo
contra 18 hipótesis con un modelo de lenguaje (NLI, `mDeBERTa-v3`), agrega esos puntajes
por departamento o lugar, y clasifica con cortes fijos. Hay una API (FastAPI) que expone
todo esto por HTTP y un front estático (HTML/JS sin build) que consulta esa API y muestra
el resultado en un dashboard. El sistema es un proxy construido y validado contra el radar
oficial del DANE donde existe (los 32 departamentos), pensado para poder aplicarse después
donde el DANE no llega.

## Organización del repo

```
├── src/                    Código de producción. Se corre desde la raíz: python src/x.py
│   ├── api.py                 API FastAPI — el servidor real
│   ├── radar.py                CalculadorRadar: bloques, cortes, clasificación
│   ├── Transformer_optimo.py   Las 18 hipótesis NLI
│   ├── config_pipeline.py      Cortes, grupos de scraping, rutas
│   ├── scrappers.py            Scraping por periódico (uno por clase)
│   ├── validacion_territorial.py  FILTRO 1: valida el territorio contra la tabla DANE
│   ├── municipios_colombia.py     Tabla DANE congelada (32 deptos, 1121 municipios)
│   └── ...                     scripts de scraping por lotes, reportes y tests offline
├── docs/                   Front (GitHub Pages lo publica desde acá)
│   ├── busqueda_pipeline.html   Formulario de consulta
│   ├── visualizacion_riesgo.html  Dashboard del resultado
│   └── README.md                Cómo levantar API + front paso a paso
├── contexto/               Documentación de investigación, numerada 00–10, a demanda
├── datos/referencia/       Radar oficial DANE (`comparacion_radares_V3.xlsx`)
├── colab_setup.ipynb       Notebook para levantar la API en Colab desde cero
└── CLAUDE.md               Reglas e historial del proyecto para quien programe
```

`datos/corpus/` y `datos/scores/` (texto scrapeado y matrices de scores ya calculadas) no
van en git por tamaño — se distribuyen aparte.

## Cómo levantarlo

El modelo NLI necesita GPU, así que la API corre en Google Colab y se expone a internet
con un túnel; el front es estático y vive en GitHub Pages.

1. **API en Colab (con GPU):** abrir [`colab_setup.ipynb`](colab_setup.ipynb) —clona el
   repo, instala dependencias y pre-descarga el modelo— y correr sus celdas en orden. La
   celda 4 levanta `uvicorn api:app --host 0.0.0.0 --port 8000` **desde dentro de `src/`**
   (no `uvicorn src.api:app` desde la raíz) y espera a que `/health` responda; puede tardar
   varios minutos porque ahí se carga el modelo NLI.
2. **Túnel:** la celda 5 expone esa API con **ngrok** (`pyngrok`, requiere un token gratis
   de ngrok pegado en la celda) y arma directamente el link del front con el parámetro
   `?api=` ya puesto — no hace falta armarlo a mano. Las URLs son del estilo
   `https://....ngrok-free.dev` (no `.trycloudflare.com`).
3. **Front:** si no se usa el link que imprime la celda 5, abrir
   `busqueda_pipeline.html` (o la copia publicada en GitHub Pages) con esa URL como
   parámetro `?api=`:
   ```
   https://botanicalex.github.io/webscrapping_transformers/busqueda_pipeline.html?api=https://....ngrok-free.dev
   ```

[`docs/README.md`](docs/README.md) describe un túnel con **cloudflared** en vez de ngrok —
quedó desactualizado frente a `colab_setup.ipynb`, que es lo que se usa hoy. Seguir el
notebook, no esa guía, hasta que se actualice.

## Los 18 indicadores, en 4 bloques (5-5-4-4)

Cada artículo se evalúa contra 18 hipótesis NLI (`src/Transformer_optimo.py`). El score de
cada una se corrige descontando el sesgo "sí-decidor" propio del artículo:
`clip(clip(ent − sesgo, 0) · (1 − neu), 0, 1)`. Por departamento o lugar se agrega por el
**máximo** entre sus artículos, y el radar final es el **promedio simple de los 18**
—los bloques son descriptivos (para el dashboard), no entran en la clasificación
(`src/radar.py`, `CalculadorRadar.BLOQUES`). Los bloques ya no son todos del mismo tamaño:
dos indicadores (`movimientos_sociales`, `exclusion_servicios_derechos`) se retiraron el
2026-10-06, y eso dejó dos bloques en 4 en vez de 5:

| Bloque | Indicadores |
|---|---|
| Conflicto armado y derechos | presencia de grupos armados, amenaza a líderes, amenaza e intimidación, desplazamiento forzado, violación de derechos humanos |
| Territorio y ambiente | conflicto territorial, conflictos socioambientales, daños ambientales, daño a territorios, resistencia territorial |
| Gobernanza y participación | irregularidad contractual, debilidad institucional, déficit de participación comunitaria, protesta social |
| Población y condiciones de vida | población afectada, grupos étnicos existentes, zonas de protección alimentaria, reasentamiento |

**Tres hipótesis se reescribieron** (texto vigente en `src/Transformer_optimo.py`):
`conflicto_territorial` → *"Hay una invasión de predios."*; `resistencia_territorial` →
*"Los habitantes rechazan una hidroeléctrica o un megaproyecto."*; `zonas_proteccion_alimentaria`
→ *"El territorio tiene una figura de protección especial para la producción de alimentos."*
Esta última es un cambio de concepto, no solo de redacción: antes medía actividad agrícola
observable, ahora una figura legal específica, mucho más rara. Las dos primeras se
reescribieron porque la frase anterior saturaba el control absurdo (casi cualquier artículo
"activaba" el indicador); las nuevas pasan el control mejor, pero **miden con menos
precisión que la versión anterior (V2)** según el juicio de jueces ciegos —una decisión
consciente, aceptando ese costo, no un defecto sin medir. Detalle completo en
`contexto/08_log_decisiones.md` [2026-10-07].

La clasificación usa cortes fijos recalibrados para estos 18 indicadores bajo agregación
MAX: `Bajo < 0.6559 ≤ Medio < 0.8839 ≤ Alto` (`CORTE_BAJO_MEDIO_RADAR` /
`CORTE_MEDIO_ALTO_RADAR` en `src/config_pipeline.py`). Son específicos de esta
configuración — no reusar con otra cantidad de indicadores o agregación sin recalibrar.

## Cómo se leen los resultados

Cada consulta devuelve un índice global 0–100 con su categoría (Bajo/Medio/Alto), el
puntaje de cada uno de los 4 bloques, y el detalle de los 18 indicadores con su puntaje
individual.

**El puntaje de un indicador es el MAX entre los artículos del período, con el sesgo del
modelo ya descontado** — no un promedio ni una proporción de artículos. Un valor alto
significa que *al menos un artículo* registró ese fenómeno con intensidad; no que sea una
condición generalizada en el territorio. Con poca prensa (un lugar con pocos artículos en
el período —ver el punto del rango de fechas por defecto, arriba—) un solo artículo puede
llevar un indicador al tope sin que eso refleje nada sistemático: el MAX es frágil cuando
el corpus es chico.

- **Puntaje muy bajo (1, 2, 6 sobre 100):** hay un artículo detrás, pero su score no llega
  al umbral de relevancia (`UMBRAL_INDICADOR_ACTIVO = 0.10` en `src/config_pipeline.py`).
  Es ruido del modelo —el NLI le asigna algo de probabilidad a casi cualquier hipótesis—,
  no evidencia de que el fenómeno ocurra.
- **Puntaje 0:** ningún artículo activó ese indicador en absoluto. En los Excel (el que
  descarga el dashboard, y los de `generar_max_articulos_por_departamento.py` /
  `pipeline_lugares.py`) la celda de título y de url muestra el texto *"No se activó este
  indicador"* en vez de un enlace vacío.

**Todo puntaje mayor a 0 es trazable al artículo que lo produjo**, tanto en el dashboard
como en los dos Excel de `src/`. Una diferencia a tener presente: el **modal** del
dashboard (clic en un indicador) solo muestra el artículo cuando superó el umbral de 0.10
—si no lo superó, dice honestamente que no hay un artículo que active ese indicador—,
mientras que los **Excel** van más allá: muestran el artículo de mayor puntaje aunque esté
por debajo del umbral, justamente para poder verificar de dónde sale un número bajo.

**Orden de las salidas:** el dashboard y su Excel descargado ordenan los 18 indicadores de
mayor a menor puntaje, cruzando los 4 bloques (no agrupados por bloque). Los Excel que
muestran varios territorios a la vez (`generar_max_articulos_por_departamento.py`: 32
departamentos; `pipeline_lugares.py`: lugares) no pueden tener un orden de filas distinto
por columna, así que ordenan por el **promedio** del valor de cada indicador entre todos
los territorios —no por su pico máximo—, para que un indicador que se dispara en un solo
lugar y está en cero en el resto no suba al tope del ranking.

## Validación territorial, sin dependencia de red

Antes de scrapear nada, `src/validacion_territorial.py` valida que el territorio escrito
por el usuario sea real para el departamento elegido, contra una tabla local congelada en
el repo (`src/municipios_colombia.py`: 32 departamentos, 1121 municipios, dataset DANE). Si
el texto no coincide, se corta ahí —con sugerencias si hay candidatos parecidos (fuzzy
match), o un rechazo si no hay ninguno.

Esto reemplazó una versión anterior que consultaba la API pública de DIVIPOLA en vivo: si
esa API se caía, se caían el autocompletado y la validación con ella. Al congelar la tabla
en el repo, `/lugares` (autocompletado) y la validación no dependen de ninguna red externa
— solo el scraping de noticias en sí la necesita.

## Qué NO hace

- **No hay filtro temático/social.** Un pre-filtro que descartaba artículos no relevantes
  antes de puntuarlos se probó y se **rechazó**: medido por indicador, costaba AUC de forma
  clara en los dos indicadores con estándar de plata (ver `contexto/08_log_decisiones.md`
  [2026-08-31]). Los 18 indicadores se puntúan sobre todos los artículos que el scraping
  trae.
- **La validación territorial no valida que los artículos hablen del territorio.** El
  FILTRO 1 solo confirma que el *nombre* del territorio escrito por el usuario es real; no
  hay una segunda pasada que verifique que cada artículo scrapeado trata efectivamente
  sobre ese lugar más allá de que el término de búsqueda aparezca mencionado.
- **El rango de fechas por defecto del front no es el que se usó para validar el sistema.**
  `busqueda_pipeline.html` arranca con fin = hoy, inicio = hace un mes; las corridas de
  referencia para los 4 lugares (Maicao, Oicatá, etc.) scrapearon del 2025-08-01 al
  2026-08-17 (`src/scrape_lugares.py`, más de un año). Con el rango por defecto, una
  consulta real va a traer muchos menos artículos que esas corridas de referencia — y con
  pocos artículos el MAX es más ruidoso (ver el punto de abajo).
- **La agregación es por máximo (MAX), no por percentil 75 (P75).** Es un requisito de
  negocio de esta rama, no la recomendación técnica del historial del proyecto: el MAX está
  medidamente más dominado por el tamaño del corpus que por la señal real entre lugares
  (razón artefacto/señal 0.91, contra 49.0 de P75) — un departamento con más artículos
  scrapeados tiene más chances de que algo puntúe alto, con independencia del riesgo real.

## Limitaciones conocidas

- **La accuracy contra el radar oficial del DANE no supera de forma concluyente las líneas
  base.** Con los 32 departamentos (n=32, error estándar ~8 pp), ni la configuración en
  producción ni ninguna variante medida se distinguen claramente de "siempre Bajo" (34.4%)
  o azar (33.3%). **El indicador de trabajo es el Spearman contra el oficial, no la
  accuracy** — +0.38/+0.42 según la variante exacta, arriba del +0.067 (prácticamente cero)
  del radar anterior a la revisión NLI de agosto, pero lejos de ser una correlación fuerte.
  Esa medición es de antes del retiro a 18 indicadores y de las frases nuevas de
  `conflicto_territorial`/`resistencia_territorial`: no se ha vuelto a correr a escala
  nacional con la configuración vigente —no medido.
- **El estándar de plata cubre solo 2 de los 18 indicadores.** Todas las conclusiones sobre
  qué tan bien discrimina cada indicador descansan, en última instancia, en esos dos.
- **La cobertura de prensa va en contra del objetivo.** Los departamentos que el DANE marca
  como más vulnerables son sistemáticamente los que menos prensa regional tienen —la
  correlación entre cantidad de artículos y clasificación oficial es negativa.
- **La procedencia exacta de la columna de referencia del DANE no está confirmada.** El
  Excel oficial (`datos/referencia/comparacion_radares_V3.xlsx`) se armó a mano desde una
  página del DANE cuya URL se perdió; se sabe que es del DANE, no con certeza cuál de sus
  índices es.
- **Un indicador queda en cero a escala nacional:** `danos_ambientales` no se activa en
  ningún departamento con la agregación P75 (la que corre en `master`/`pruebas`). Esta
  rama usa MAX con 18 indicadores y nunca se volvió a puntuar a escala nacional con esa
  combinación exacta —no medido, ver `contexto/07_backlog.md`.
- Detalle completo de todo lo anterior, con la evidencia y los experimentos que lo miden,
  en `contexto/09_riesgos_y_limites.md` y `contexto/08_log_decisiones.md`.

## Para trabajar en el código

Ver [`CLAUDE.md`](CLAUDE.md) (reglas duras del proyecto e historial reciente) y la carpeta
`contexto/` (documentación numerada, a demanda — empezar por `00_estado_actual.md`).
Validar cualquier cambio con `python src/test_integracion.py` (16 tests, sin GPU).

