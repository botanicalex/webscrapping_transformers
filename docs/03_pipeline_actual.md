# 03 — Pipeline actual (según código)

## Flujo implementado

1. Scraping por departamento y términos en `scrappers.py`
2. Guardado incremental por departamento en `resultados/df_corpus_<departamento>.pkl`
3. Carga consolidada de corpus (`CargadorCorpus`) en `Transformer_optimo.py`
4. Procesamiento NLP por artículo (`PipelineTransformers`)
5. Agregación por departamento y cálculo de radar (`CalculadorRadar`)
6. Exportación de salidas de pipeline a `resultados_pipeline/`
7. Evaluación separada de métricas en `metricas_y_calculo_de_error.py`

## Etapa de scraping

En `scrappers.py`:

- Fecha por defecto: 2023-01-01 a 2023-12-31
- Temas por defecto: conflicto, comunidades, institucional, derechos, social
- Grupos: 11 grupos (`GRUPOS_DEPARTAMENTOS`)
- Dos fases de ejecución por término:
  - Fase paralela para scrapers rápidos y rate-limited
  - Fase secuencial para scrapers Playwright con lock global
- Deduplicación por URL entre scrapers para un mismo término
- Unión multi-término con columna `terminos_encontrado`
- Respaldo automático con El Tiempo cuando el total por departamento queda por debajo del umbral

## Etapa NLP

En `Transformer_optimo.py`:

- Zero-shot: `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
- Sentimiento: `finiteautomata/beto-sentiment-analysis`
- NER: `dccuchile/bert-base-spanish-wwm-cased-finetuned-ner`
- Clasificación de temas con `multi_label=False`
- Detección de eventos/posturas/indicadores por entailment NLI
- Señales de entidades por matching textual y NER
- Cálculo de 5 scores por dimensión en artículo

## Etapa radar departamental

`CalculadorRadar.calcular()`:

- Convierte señales a tasas por departamento (`groupby.mean`)
- Invierte variables definidas en `VARS_INVERTIR`
- Construye bloques `bloque_A ... bloque_E` con PCA (o media si no aplica)
- Escala bloques a 0–100
- Calcula:
  - `corrupcion_score = minmax(0.80*B + 0.35*A - 0.15*C)`
  - `vulneracion_score = minmax(0.50*D + 0.50*E)`
  - `radar_propio = minmax(0.60*corrupcion_score + 0.40*vulneracion_score)`
- Etiqueta `categoria_riesgo` por cuantiles (bajo/medio/alto)

## Archivos de salida del pipeline

- `resultados_pipeline/df_procesado.pkl`
- `resultados_pipeline/df_procesado.csv`
- `resultados_pipeline/radar_departamentos.pkl`
- `resultados_pipeline/radar_departamentos.csv`
