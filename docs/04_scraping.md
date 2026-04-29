# 04 — Scraping (estado real del código)

## Script principal

- Archivo: `scrappers.py`
- Clase base: `ScraperPeriodico`
- Orquestador: `GestorScraping`

## Configuración central

Variables globales principales:

- `FECHA_DESDE = "2023-01-01"`
- `FECHA_HASTA = "2023-12-31"`
- `TEMAS_BUSQUEDA = ["conflicto", "comunidades", "institucional", "derechos", "social"]`
- `GRUPOS_DEPARTAMENTOS` con 11 grupos de ejecución

## Estrategia de ejecución por término

Para cada término de búsqueda, `GestorScraping.scrape_multiples()` separa scrapers en tres grupos:

- rápidos (paralelo)
- rate-limited (paralelo con pool limitado)
- Playwright (secuencial)

Controles globales:

- `_playwright_lock`: evita múltiples Chromium simultáneos
- `_eltiempo_semaphore`: limita concurrencia para El Tiempo
- `_las2orillas_semaphore`: limita concurrencia para Las2Orillas

## Flujo por departamento

Funciones públicas principales:

- `scrape_departamento(...)`
- `scrape_multiples_departamentos(...)`

Comportamiento:

- arma términos como `f"{departamento} {tema}"`
- ejecuta búsqueda multi-término en paralelo
- deduplica por `url`
- agrega columna `terminos_encontrado`
- asigna columna `departamento`
- guarda resultado por departamento en `resultados/df_corpus_<departamento>.pkl`

## Respaldo automático

En `scrape_departamento`, si el total de artículos es menor a `min_articulos` (default 50), intenta complementar con `eltiempo` usando términos faltantes.

## Columnas del corpus

Columnas esperadas/normalizadas en salidas de scraping:

- `periodico`
- `titulo`
- `fecha`
- `texto`
- `url`
- `departamento`
- `terminos_encontrado`

## Ejecución práctica

- por grupo: `python grupo_0X.py`
- por departamento: usar `scrape_departamento(...)`
- monitoreo de archivos: `python monitor.py`
