# 05 — Transformers y clasificación NLP (implementación real)

## Archivo

- `Transformer_optimo.py`

## Modelos usados

- Zero-shot NLI: `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
- Sentimiento: `finiteautomata/beto-sentiment-analysis`
- NER: `dccuchile/bert-base-spanish-wwm-cased-finetuned-ner`

Selección de dispositivo:

- GPU si `torch.cuda.is_available()`
- CPU en caso contrario

## Estructura de señales

El pipeline define cuatro grupos de señales semánticas:

- `temas` (5 claves)
- `eventos` (8 claves)
- `posturas` (7 claves)
- `indicadores` (10 claves)

También define 6 grupos de referencia para entidades:

- `grupos_etnicos_entidades`
- `grupos_armados_entidades`
- `organizaciones_entidades`
- `lideres_entidades`
- `instituciones_entidades`
- `actores_economicos_entidades`

## Lógica de clasificación

- `temas`: zero-shot sobre etiquetas descriptivas con `multi_label=False`
- `eventos`, `posturas`, `indicadores`: puntaje de entailment por NLI par premisa/hipótesis
- `sentimiento`: etiqueta `positivo/negativo/neutral` y confianza
- `entidades`: matching por texto y refuerzo opcional por salida NER

## Cálculo de dimensiones por artículo

`_crear_scores_dimension()` produce:

- `score_dim1_gobernanza`
- `score_dim2_capacidad_institucional`
- `score_dim3_vulneracion_socioeconomica`
- `score_dim4_vulnerabilidad_territorial`
- `score_dim5_derechos_humanos_conflicto`

Cada score es promedio de subconjuntos de variables del artículo.

## Carga de corpus

`CargadorCorpus.cargar()`:

- lee `df_corpus_*.pkl`
- valida columnas requeridas: `periodico, titulo, fecha, texto, url, departamento`
- elimina duplicados por `url`
- descarta artículos sin texto

## Salida de procesamiento

- `resultados_pipeline/df_procesado.pkl`
- `resultados_pipeline/df_procesado.csv`
