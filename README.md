# Radar de prensa por departamento (versión actual basada en código)

Este repositorio ejecuta un pipeline de 3 etapas:

1. Scraping por departamento con scrapers de periódicos (`scrappers.py`)
2. Procesamiento NLP con Transformers y cálculo de radar (`Transformer_optimo.py`)
3. Evaluación de métricas frente a radar oficial cargado desde Excel (`metricas_y_calculo_de_error.py`)

## Estructura real del proyecto

- `scrappers.py`: motor principal de scraping
- `grupo_01.py` ... `grupo_11.py`: ejecución por grupos de departamentos
- `monitor.py`: monitor de avance de archivos `df_corpus_*.pkl`
- `colab_carga_corpus.py`: carga y validación de corpus en Colab
- `Transformer_optimo.py`: pipeline NLP + cálculo de radar departamental
- `metricas_y_calculo_de_error.py`: cálculo de métricas y gráficas desde `comparacion_radares.xlsx`
- `prueba_rapida.py`: prueba de scraping de un departamento
- `docs/*.md`: documentación técnica de esta versión
- `resultados/`: salida de scraping (`df_corpus_*.pkl`)
- `resultados_pipeline/`: salida de pipeline NLP/radar
- `graficos_metricas/`: salida de gráficas de métricas

## Requisitos

- Python 3.10+
- Dependencias en `requirements.txt`
- Para scrapers Playwright: instalar Chromium

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Configuración de scraping

En `scrappers.py` se define:

- `FECHA_DESDE = "2023-01-01"`
- `FECHA_HASTA = "2023-12-31"`
- `TEMAS_BUSQUEDA = ["conflicto", "comunidades", "institucional", "derechos", "social"]`
- `GRUPOS_DEPARTAMENTOS` con 11 grupos

La búsqueda se arma con `"{departamento} {tema}"` para todos los scrapers dentro del flujo principal.

## Ejecución

### 1) Scraping por grupos

```bash
python grupo_01.py
python grupo_02.py
python grupo_03.py
python grupo_04.py
python grupo_05.py
python grupo_06.py
python grupo_07.py
python grupo_08.py
python grupo_09.py
python grupo_10.py
python grupo_11.py
```

### 2) Monitorear avance

```bash
python monitor.py
```

### 3) Pipeline completo (opcionalmente saltando scraping)

```bash
python Transformer_optimo.py
python Transformer_optimo.py --skip-scraping --ruta-pkl resultados --salida resultados_pipeline
```

### 4) Métricas contra radar oficial

```bash
python metricas_y_calculo_de_error.py
```

## Archivos de salida

- Scraping: `resultados/df_corpus_<departamento>.pkl`
- NLP: `resultados_pipeline/df_procesado.pkl` y `.csv`
- Radar: `resultados_pipeline/radar_departamentos.pkl` y `.csv`
- Métricas: `resultado_comparacion_radares_<timestamp>.xlsx`
- Gráficas: `graficos_metricas/corrida_<timestamp>/`

## Notas operativas reales

- `scrappers.py` usa dos fases: paralelo (requests/aiohttp/rate-limited) y secuencial para Playwright.
- Lock global `_playwright_lock` serializa scrapers Playwright.
- Semáforos globales para `eltiempo` y `las2orillas`.
- Si un departamento queda con pocos artículos, se activa respaldo con El Tiempo (`min_articulos`, por defecto 50 en `scrape_departamento`).
- La columna de términos en el corpus se llama `terminos_encontrado`.
