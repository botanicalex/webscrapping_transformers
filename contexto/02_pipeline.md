# 02 — Pipeline

*Actualizado 2026-09-01: refleja la promoción de V2 a `src/` (2026-08-31).*

## Flujo

```
scraping          scrappers.py            -> datos/corpus/df_corpus_<depto>.pkl
   |                                         (periodico, titulo, fecha, texto, url, departamento)
   v
transformers      Transformer_optimo.py   -> df_procesado (+26 indicadores, sesgo, dims)
   |                                         PipelineTransformers.procesar()
   v
radar             radar.py                -> radar por departamento
   |                                         CalculadorRadar
   v
metricas          metricas_y_calculo_...  -> accuracy (cortes fijos) vs oficial DANE
```

`orquestador_pipeline.py` encadena las cuatro etapas con validación de precondiciones y
criterio de parada (accuracy ≥ 0.70).

**Los scripts de `src/` se ejecutan desde la raíz del proyecto:** `python src/<script>.py`.
Las rutas de `config_pipeline.py` son relativas a esa raíz.

## Etapa 1 — Scraping

`scrappers.py` (285 KB) contiene ~30 clases `ScraperPeriodico` y el `GestorScraping`. La
entrada de alto nivel es `scrape_multiples_departamentos()`.

Se corre por grupos de 3 departamentos:

```bash
python src/correr_grupo.py 5        # un grupo
python src/correr_grupo.py --todos  # los 11
python src/correr_grupo.py --listar # ver composición sin correr
python src/monitor.py               # qué departamentos ya tienen pkl
```

La composición de los grupos no es arbitraria — ver el comentario extenso en
`config_pipeline.GRUPOS_DEPARTAMENTOS`. Detalles y trampas en `05_scraping.md`.

## Etapa 2 — Transformers

`PipelineTransformers.procesar(df)` en `Transformer_optimo.py`:

1. **26 hipótesis NLI (V2)** sobre todos los artículos, **sin pre-filtro social** (rechazado
   el 2026-08-31: costaba AUC; ver `08_log_decisiones.md`).
2. **Sesgo por artículo descontado**: media de P(entailment) contra 4 hipótesis nulas de
   calibración (`NULAS_CALIBRACION`, nunca la nula reservada).
3. **Score corregido**: `clip(clip(ent − sesgo, 0) * (1 − neu), 0, 1)`.
4. **Scores por dimensión** (`score_dim1..5`), agrupaciones temáticas de los 26.

NER y análisis de sentimiento están **comentados**, no borrados. No reactivarlos: no
alimentaban ningún indicador y solo consumían GPU.

`scrappers` se importa de forma **diferida**, dentro de `correr_scraping()`. Así los
procesos que solo puntúan con GPU no arrastran playwright/aiohttp.

**Referencia de tiempo:** 11.439 artículos × 26 hipótesis ≈ 125 min en la GPU local.

## Etapa 3 — Radar

`CalculadorRadar` en `radar.py`. `COLUMNAS_BINARIAS` es la **definición canónica de los 26
indicadores** y la consumen casi todos los scripts: no duplicar esa lista en otro sitio.

Producción agrega con **P75 por rango más cercano** (promovido 2026-08-31; antes MAX). La
revisión de agosto demostró que el MAX está dominado por el tamaño del corpus — ver
`04_hallazgos_revision_nli.md` y `08_log_decisiones.md` [2026-08-27].

## Etapa 4 — Métricas

`metricas_y_calculo_de_error.py` clasifica el radar propio con **cortes fijos**
(`Bajo < 0.2969 <= Medio < 0.3527 <= Alto`) y lee la clasificación oficial de su columna
(`Clasificacion_radar_oficial_promedio`, sin re-tercilar), y calcula accuracy,
precision/recall/F1 macro, Cohen-kappa y la matriz de confusión 3×3. Ver
`01_objetivo_y_radar.md`.

## Runners de tareas concretas

| Script | Para qué |
|---|---|
| `src/scrape_lugares.py` | Scraping de veredas/municipios (sub-departamental) |
| `src/pipeline_lugares.py` | Corpus de lugares → indicadores → excels + resumen |
| `src/generar_tablas_por_departamento.py` | Pipeline sobre los 32 → una tabla por departamento |
| `src/generar_max_articulos_por_departamento.py` | Resumen MAX + artículo de origen (sin GPU) |
| `src/combinar_corpus.py` | Actualizar el corpus nacional reemplazando departamentos |
| `src/test_integracion.py` | Test de integración con corpus sintético, sin cargar modelos |

`test_integracion.py` es la única red de seguridad del repositorio. Correrlo tras cambios en
el núcleo.

## Experimentos

`experimentos/` es un entorno aparte que **no toca `src/`**. Sus scripts se ejecutan **desde
`experimentos/`**, no desde la raíz. `nli_core.py` reproduce el scoring de producción bit a
bit sin importar `scrappers`, lo que permite iterar sin cargar el pipeline completo.
