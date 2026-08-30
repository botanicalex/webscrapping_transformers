# 05 — Scraping

## Cómo funciona la búsqueda

Para cada territorio se buscan **5 términos** (`cfg.TEMAS_BUSQUEDA`: conflicto, comunidades,
institucional, derechos, social), formando la consulta `"{territorio} {tema}"`. Los 5 corren
en paralelo y el resultado se deduplica por URL, añadiendo la columna
`terminos_encontrado`.

## ⚠️ La trampa que hay que conocer

El filtro de relevancia de `scrappers.py` (`GestorScraping._es_relevante`) usa **SOLO LA
PRIMERA PALABRA** del término de búsqueda:

```python
territorio = self.termino.split()[0].lower()
menciones_texto = texto_lower.count(territorio)
bonus_titulo    = 2 if territorio in titulo_lower else 0
return (menciones_texto + bonus_titulo) >= min_menciones
```

Buscar `"Vereda Paraguachón"` hace que el filtro cuente menciones de la palabra
**"vereda"** → devuelve artículos irrelevantes y descarta los buenos, **sin lanzar ningún
error**.

**Nunca pasar prefijos.** `scrape_lugares.py` separa `nombre` (el término real de búsqueda,
`"Paraguachón"`) de `etiqueta` (el nombre para reportar, `"Vereda Paraguachón"`).

Corolarios:
- El matcheo es **literal y sensible a tildes**. Si los artículos escriben "Guintiva" u
  "Oicata" sin tilde, no hay match. Si un lugar da 0 artículos, probar la variante sin tilde
  antes de concluir que no hay cobertura.
- Para nombres compuestos ("Valle del Cauca") el filtro solo mira "valle".

## Umbrales de relevancia

`min_menciones` por defecto es 3, calibrado para departamentos.

- **Departamentos:** `DEPARTAMENTO_MIN_MENCIONES` asigna 3 a los grandes y 2 a los pequeños.
- **Veredas y municipios:** usar **1**. Un lugar pequeño rara vez se nombra 3 veces.
- Los periódicos nacionales (`eltiempo`, `las2orillas`) fuerzan umbral 1 internamente: la
  consulta ya garantiza pertinencia.

## Asignación de periódicos

`DEPARTAMENTO_PERIODICOS` mapea cada departamento a sus scrapers. Si un departamento no
tiene scraper local (lista vacía), cae directo al respaldo (El Tiempo). Si el corpus queda
por debajo de `MIN_ARTICULOS_RESPALDO` (50), se activa el respaldo automáticamente.

**`scrape_departamento` consulta ese mapeo; `scrape_municipio` NO.** Para lugares
sub-departamentales hay que pasar `periodicos` explícito, o recorrerá *todos* los scrapers.
Convención: heredar los del departamento que contiene el lugar.

## Scrapers rotos o problemáticos

| Scraper | Estado |
|---|---|
| `elheraldo` | Cambió la estructura del buscador (abril 2026) → Atlántico va a respaldo |
| `eluniversal` | API Queryly devuelve HTTP 403 → Bolívar va a respaldo |
| `vanguardia` | API Queryly 403 → Boyacá usa El Tiempo |
| `elmorichal` | Sitio caído permanentemente → Vichada y Guainía a respaldo |
| `miputumayo` | 100% TimeoutError → Putumayo, Amazonas, Caquetá y Guaviare afectados |
| `choco7dias` | Funciona pero LENTO: ~35% de éxito, timeout 600 s |
| `lavozdelcinaruco` | Lento, timeout 600 s |
| `las2orillas` | Rate-limiting severo; excluido del respaldo por defecto |

## Concurrencia

- Scrapers rápidos (requests/aiohttp): concurrencia total.
- Playwright: serializado con un lock global — nunca dos Chromium a la vez.
- El Tiempo: semáforo global de 2; se satura con más.
- Los grupos de `GRUPOS_DEPARTAMENTOS` están armados para que dos departamentos que
  dependen del mismo periódico no caigan en la misma tanda. Ver el comentario en
  `config_pipeline.py` antes de reordenarlos.

## Cobertura resultante y su sesgo

El corpus nacional está muy desbalanceado, y **en contra de lo que necesitaríamos**:

```
Magdalena 1538 · Atlántico 1114 · Cesar 1075 · Córdoba 913 · Nariño 659 · Meta 613
...
Huila 86 · San Andrés 79 · Vichada 62 · Sucre 41 · Norte de Santander 36 ·
Vaupés 32 · La Guajira 11 · Guainía 6
```

**Norte de Santander (Catatumbo) tiene 36 artículos** siendo de los territorios más
afectados del país; Atlántico tiene 1.114 siendo de los más tranquilos. De los 11
departamentos que el índice oficial clasifica como Alto, 5 tienen menos de 100 artículos.

Reforzar `DEPARTAMENTO_PERIODICOS` para Norte de Santander, Chocó, La Guajira y Arauca
mejoraría el resultado más que cualquier ajuste de hipótesis. Ver `01_objetivo_y_radar.md`.

## Nombres de archivo

`_nombre_archivo()` normaliza a `df_corpus_<depto_sin_tildes_con_guiones>.pkl`. Cada
departamento guarda su pkl apenas termina, sin esperar a los demás: si la corrida se
interrumpe, lo ya scrapeado se conserva.
