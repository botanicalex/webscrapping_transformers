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

---

## Estrategia de Expansión de Keywords para Departamentos Periféricos

Esta sección define la estrategia prioritaria de la semana para reducir el error en departamentos con baja cobertura mediática.

### Problema identificado

Los departamentos con menor desarrollo o acceso a comunicación generan pocos artículos con los términos genéricos actuales (`conflicto`, `comunidades`, etc.), lo que produce un radar de prensa poco representativo y un error alto frente al radar oficial.

### Departamentos críticos y keywords sugeridas

| Departamento | Keywords genéricas actuales (resultado pobre) | Keywords específicas sugeridas |
|---|---|---|
| Amazonas | conflicto, social | resguardo indígena, minería ilegal, frontera amazónica, defensoría, río Amazonas |
| Vaupés | conflicto, social | comunidades indígenas, aislamiento, selva, frontera Brasil, economía ilegal |
| Guainía | conflicto, social | minería ilegal, río Inírida, resguardo, frontera Venezuela, grupos armados |
| Putumayo | conflicto, derechos | sustitución de cultivos, erradicación, disidencias FARC, restitución de tierras, coca |
| Caquetá | conflicto, derechos | disidencias, restitución, colonización, deforestación, ganadería ilegal |
| La Guajira | comunidades, social | desnutrición, corrupción agua, crisis humanitaria, wayuu, regalías |
| Chocó | comunidades, derechos | confinamiento, minería ilegal, desplazamiento, comunidades afro, ríos |
| Vichada | institucional, social | colonización, frontera Venezuela, grupos armados, tierras baldías |

### Criterio de calidad por keyword

Una keyword es útil si:
- Genera artículos con **score de clasificación > 0.6** en el transformer
- Aporta al menos **20 artículos únicos** por departamento
- No genera ruido temático (artículos de otros departamentos o temas irrelevantes)

### Proceso de prueba recomendado

1. Tomar un departamento crítico (ej. Amazonas o Vaupés)
2. Correr `scrape_departamento(departamento, FECHA_DESDE, FECHA_HASTA)` con el set de keywords actual
3. Anotar número de artículos obtenidos
4. Reemplazar `TEMAS_BUSQUEDA` con las keywords específicas de la tabla anterior
5. Correr de nuevo y comparar volumen y calidad
6. Registrar resultado en `experimentos.md`

### Señal de alerta

Si `monitor.py` reporta < 100 artículos para un departamento después de la expansión de keywords, se debe:
- Buscar periódicos regionales digitales adicionales no incluidos en los 27 scrapers actuales
- Considerar ampliar el rango de fechas temporalmente para validar que el scraper funciona