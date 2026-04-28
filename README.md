# Webscrapping Transformers — Corpus de Noticias Regionales Colombia

Sistema de scraping de noticias para los **32 departamentos de Colombia**, orientado a la construcción de un corpus de texto para análisis con modelos Transformer (dimensiones de gobernanza, conflicto, capacidad institucional, etc.).

---

## Estructura del proyecto

```
scrappers.py              # Motor principal: 27 scrapers + funciones de orquestación
grupo_01.py … grupo_11.py # Scripts de ejecución por grupos de departamentos
monitor.py                # Monitor de progreso (departamentos completados/pendientes)
colab_carga_corpus.py     # Celda de carga del corpus consolidado en Google Colab
requirements.txt          # Dependencias Python
resultados/               # Carpeta de salida — archivos .pkl por departamento (no versionada)
```

---

## Requisitos

- Python 3.11–3.14
- Chromium instalado vía Playwright (solo para scrapers de Santander, Norte de Santander y Cundinamarca)

---

## Instalación

> **Nota para Python 3.14**: `newspaper4k` requiere `lxml < 6.0` pero solo existe wheel precompilado de `lxml 6.x` para Python 3.14. La instalación en dos pasos resuelve el conflicto:

```bash
# Paso 1: instalar todas las dependencias (incluye lxml 6.x)
pip install -r requirements.txt

# Paso 2: instalar newspaper4k sin sus dependencias declaradas
pip install newspaper4k==0.9.5 --no-deps

# Paso 3: instalar navegador Chromium para Playwright
python -m playwright install chromium
```

---

## Configuración

Editar la sección **CONFIG** al inicio de `scrappers.py`:

```python
# Rango de fechas
FECHA_DESDE = "2023-01-01"
FECHA_HASTA = "2023-12-31"

# Palabras clave — se combinan con el nombre del departamento
# Ejemplo: "Antioquia conflicto", "Antioquia comunidades", etc.
TEMAS_BUSQUEDA = [
    "conflicto",       # DIM5: derechos humanos, grupos armados
    "comunidades",     # DIM3: grupos étnicos, vulneración socioeconómica
    "institucional",   # DIM1/DIM2: gobernanza, capacidad institucional
    "derechos",        # DIM5/DIM1: DDHH, gobernanza
    "social",          # DIM3: protesta, movimientos sociales
]
```

Para personalizar los términos de **un solo grupo** sin tocar el global, editar `TEMAS` al inicio del `grupo_XX.py` correspondiente:

```python
# grupo_06.py
TEMAS = ["conflicto", "social"]   # reemplazar None con una lista propia
```

---

## Ejecución

### Opción A — Por grupos (recomendado para el corpus completo)

```bash
# Crear carpeta de salida
mkdir resultados

# Correr cada grupo (pueden lanzarse en ventanas separadas en paralelo)
python grupo_01.py   # Antioquia · Chocó · Vichada
python grupo_02.py   # Valle del Cauca · Arauca · Atlántico
python grupo_03.py   # Caldas · Meta · Bolívar
python grupo_04.py   # Risaralda · Caquetá · Putumayo
python grupo_05.py   # Quindío · Guaviare · Amazonas
python grupo_06.py   # Santander · Cesar · Boyacá
python grupo_07.py   # Norte de Santander · Magdalena · Guainía
python grupo_08.py   # Cundinamarca · La Guajira · Cauca
python grupo_09.py   # Córdoba · Nariño · Vaupés
python grupo_10.py   # Sucre · Huila · San Andrés y Providencia
python grupo_11.py   # Casanare · Tolima
```

Cada script guarda un `.pkl` por departamento en `resultados/` tan pronto termina, sin esperar a los demás del grupo.

### Opción B — Departamento individual (desarrollo / pruebas)

```python
from scrappers import *

df = scrape_departamento('Antioquia', '2023-01-01', '2023-12-31')
print(df[['periodico', 'titulo', 'fecha']].head())
```

### Ver progreso

```bash
python monitor.py
```

Muestra el estado de cada departamento (✓ completado / ▶ en curso / ○ pendiente) con tamaño del `.pkl` y hora de última modificación.

---

## Grupos de departamentos

| Grupo | Departamentos | Scrapers principales |
|-------|---------------|----------------------|
| G1  | Antioquia · Chocó · Vichada | elcolombiano · choco7dias *(lento)* · El Tiempo |
| G2  | Valle del Cauca · Arauca · Atlántico | elpais · lavozdelcinaruco *(lento)* · El Tiempo |
| G3  | Caldas · Meta · Bolívar | bcnoticias · llanoalmundo · El Tiempo |
| G4  | Risaralda · Caquetá · Putumayo | eldiario · llanoalmundo · El Tiempo |
| G5  | Quindío · Guaviare · Amazonas | elquindiano · llanoalmundo · El Tiempo |
| G6  | Santander · Cesar · Boyacá | enlacetelevision · corrillos · El Tiempo · elpilon |
| G7  | Norte de Santander · Magdalena · Guainía | enlacetelevision · corrillos · El Tiempo · elpilon |
| G8  | Cundinamarca · La Guajira · Cauca | El Tiempo · portafolio · publimetro · elpilon · diariodelcauca |
| G9  | Córdoba · Nariño · Vaupés | elmeridiano · diariodelsur · El Tiempo |
| G10 | Sucre · Huila · San Andrés y Providencia | elmeridiano · diariodelcauca · diariodelsur · El Tiempo |
| G11 | Casanare · Tolima | diariodecasanare · bcnoticias · El Tiempo |

---

## Cargar el corpus en Google Colab

Copiar el contenido de `colab_carga_corpus.py` en una celda de Colab. El script ofrece dos opciones:
- **Opción A**: montar Google Drive y leer los `.pkl` desde `resultados/`
- **Opción B**: subir los archivos manualmente

Columnas del DataFrame consolidado: `periodico`, `titulo`, `fecha`, `texto`, `url`, `departamento`, `terminos_encontrado`.

---

## Notas técnicas

| Tema | Detalle |
|------|---------|
| **TimeoutError masivos** (>200) | LlanoAlMundo, LaVozDelCinaruco, ElQuindiano, DiarioDelCauca tienen throttling severo. Son normales — los artículos que sí pasan son válidos. |
| **Python 3.14 + lxml** | Requiere instalación en dos pasos (ver arriba). En Python ≤ 3.13 basta `pip install -r requirements.txt`. |
| **Playwright serializado** | Todos los scrapers Playwright comparten un lock global (`_playwright_lock`) — nunca hay dos navegadores simultáneos aunque varios grupos estén corriendo a la vez. |
| **Respaldo automático** | Si un departamento obtiene menos de 50 artículos de sus scrapers locales, activa búsqueda de respaldo en El Tiempo automáticamente. |
| **Archivos de salida** | Nombrados `df_corpus_<departamento>.pkl` en `resultados/`. No se versionan en git (pueden superar 100 MB). |
