# Radar de riesgo territorial — rama `radar-max_Septiembre`

Pipeline que calcula un radar de riesgo por departamento de Colombia a partir de prensa
regional. **Radar alto = zona difícil o inviable para implementar proyectos.**

Esta rama usa agregación **MAX** en vez de P75 (requisito de negocio) y está podada de
experimentos y scripts legacy para que sea más fácil de clonar y correr. Ver
`explicacion_alexa.md` para una guía completa en lenguaje llano.

Para el contexto completo, ver `CLAUDE.md` y la carpeta `contexto/`.

## Estructura

```
radar-max_Septiembre/
├── CLAUDE.md             se carga solo en cada conversacion; reglas duras
├── explicacion_alexa.md  guia de esta rama para un lector humano
├── contexto/             documentacion bajo demanda (00 a 10)
├── src/                  pipeline de produccion — ejecutar DESDE LA RAIZ
├── datos/
│   ├── corpus/           texto crudo de noticias (fuera de git, ver abajo)
│   ├── referencia/       radar oficial DANE
│   └── scores/           matrices ya calculadas (fuera de git, ver abajo)
└── resultados/           salidas (fuera de git)
```

## Requisitos

Python con PyTorch + CUDA (probado en RTX 4050), `transformers`, `pandas`, `openpyxl`,
`scikit-learn`, `matplotlib`, `seaborn`. Para scraping: `playwright`, `aiohttp`,
`nest_asyncio`. Ver `requirements.txt`.

El modelo NLI se descarga a `~/.cache/huggingface/hub` la primera vez.

`datos/corpus/` y `datos/scores/` no van en git (pesan ~107 MB y se regeneran o se
distribuyen aparte): se reciben en un `.zip` y se descomprimen dentro de `datos/`, de modo
que queden `datos/corpus/*.pkl` y `datos/scores/*.pkl`.

## Uso

### Scraping

```bash
python src/correr_grupo.py --listar     # ver la composicion de los 11 grupos
python src/correr_grupo.py 5            # un grupo
python src/correr_grupo.py --todos      # los 11, en secuencia
python src/monitor.py                   # que departamentos ya tienen pkl
```

Los grupos están armados para que dos departamentos que usan el mismo periódico no compitan
por el servidor. Leer el comentario de `GRUPOS_DEPARTAMENTOS` en `src/config_pipeline.py`
antes de reordenarlos.

**Trampa importante (histórica, corregida 2026-08-30):** el filtro de relevancia usaba solo
la **primera palabra** del término de búsqueda; hoy usa el `territorio` completo salvo que
no se le pase (fallback retrocompatible). Igual no pasar `"Vereda Paraguachón"` — nunca
pasar prefijos. Ver `contexto/05_scraping.md`.

### Pipeline completo

```bash
python src/orquestador_pipeline.py --skip-scraping
```

### Lugares sub-departamentales (veredas, municipios)

```bash
python src/scrape_lugares.py            # edita LUGARES dentro del script
python src/pipeline_lugares.py          # corpus -> indicadores -> excels
```

El radar de un lugar sub-departamental se calcula igual que el de un departamento: mismas
26 hipótesis V2, mismo sesgo descontado, **MAX** por indicador y los mismos cortes fijos.

### Tablas por departamento

```bash
python src/generar_max_articulos_por_departamento.py   # sin GPU, desde el pkl
```

### Tests

```bash
python src/test_integracion.py
```

Corpus sintético, sin cargar modelos. Es la única red de seguridad del repositorio: correrlo
tras cualquier cambio en el núcleo.

## Cómo se calcula el radar

1. Cada artículo se evalúa contra las **26 hipótesis V2** con el modelo NLI, dando una
   probabilidad de entailment (`ent_`) y de neutralidad (`neu_`) por hipótesis.
2. Se descuenta el sesgo "sí-decidor" por artículo y se calcula el score corregido:
   `clip(clip(ent − sesgo, 0) * (1 − neu), 0, 1)`.
3. Por departamento y por indicador, se toma el **MAX** entre todos los artículos de ese
   departamento (`exportar_indicadores_transformers_por_departamento` en
   `src/Transformer_optimo.py`; agregación de esta rama, requisito de negocio — la decisión
   técnica del historial del proyecto era P75, ver `contexto/08_log_decisiones.md`).
4. El radar final es el **promedio simple de los 26 indicadores** (sin pesos, sin z-score,
   sin terciles).
5. Se clasifica con **cortes fijos** `Bajo < 0.766 <= Medio < 0.9233 <= Alto`
   (`CORTE_BAJO_MEDIO_RADAR`/`CORTE_MEDIO_ALTO_RADAR` en `src/config_pipeline.py`,
   recalibrados para la escala MAX — ver `explicacion_alexa.md`).

## Notas de rendimiento

- 11.439 artículos × 26 hipótesis ≈ 125 min de GPU.
- El pre-filtro social fue **rechazado** (2026-08-31) y ya no corre: los 26 indicadores se
  puntúan sobre todos los artículos.
- `datos/scores/scores_v2.pkl` (5 lugares) y `scores_v2_32deptos.pkl` (nacional) permiten
  recalcular correcciones, umbrales y agregaciones **sin GPU**. Mirar ahí antes de puntuar
  nada de nuevo.
- Los scripts que escriben `.xlsx` fallan con `PermissionError` si el archivo está abierto en
  Excel. Los que corren GPU guardan el `.pkl` antes de escribir los Excel, así que una
  interrupción no obliga a repetir la corrida.
