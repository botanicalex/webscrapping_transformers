# Radar de riesgo territorial — Colombia

Sistema que clasifica los 32 departamentos de Colombia (y, en principio, lugares más
pequeños como veredas o municipios) en riesgo **Bajo / Medio / Alto** a partir de prensa
regional. **Radar alto significa zona difícil o inviable para implementar un proyecto**
—conflicto activo, presencia de grupos armados, ausencia de Estado—, no "cuánto pasa" en
la zona sino "cuánto estorba" a una intervención.

El pipeline scrapea periódicos regionales para el territorio pedido, evalúa cada artículo
contra 20 hipótesis con un modelo de lenguaje (NLI, `mDeBERTa-v3`), agrega esos puntajes
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
│   ├── Transformer_optimo.py   Las 20 hipótesis NLI
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

1. **API en Colab (con GPU):** clonar el repo, `pip install -r requirements.txt`,
   `playwright install chromium`, y levantar `uvicorn src.api:app --host 0.0.0.0 --port
   8000`. Uvicorn carga el modelo NLI al arrancar — puede tardar varios minutos.
2. **Túnel:** hoy se usa **cloudflared** (`cloudflared tunnel --url http://localhost:8000`,
   sin cuenta) en vez de ngrok — el código conserva nombres y headers de la época de ngrok
   (`ngrok-skip-browser-warning`) aunque el mecanismo actual sea otro. El túnel imprime una
   URL pública `https://....trycloudflare.com`; verificar con `/health` antes de usar el
   front.
3. **Front:** abrir `busqueda_pipeline.html` (o la copia publicada en GitHub Pages) con esa
   URL como parámetro `?api=`:
   ```
   https://botanicalex.github.io/webscrapping_transformers/busqueda_pipeline.html?api=https://....trycloudflare.com
   ```

Guía completa, con los comandos exactos y las trampas conocidas (URL del túnel que cambia
cada vez, mixed content HTTPS→HTTP), en [`docs/README.md`](docs/README.md).

## Los 20 indicadores, en 4 bloques

Cada artículo se evalúa contra 20 hipótesis NLI (`src/Transformer_optimo.py`). El score de
cada una se corrige descontando el sesgo "sí-decidor" propio del artículo:
`clip(clip(ent − sesgo, 0) · (1 − neu), 0, 1)`. Por departamento o lugar se agrega por el
**máximo** entre sus artículos, y el radar final es el **promedio simple de los 20**
—los bloques son descriptivos (para el dashboard), no entran en la clasificación
(`src/radar.py`, `CalculadorRadar.BLOQUES`):

| Bloque | Indicadores |
|---|---|
| Conflicto armado y derechos | presencia de grupos armados, amenaza a líderes, amenaza e intimidación, desplazamiento forzado, violación de derechos humanos |
| Territorio y ambiente | conflicto territorial, conflictos socioambientales, daños ambientales, daño a territorios, resistencia territorial |
| Gobernanza y participación | irregularidad contractual, debilidad institucional, déficit de participación comunitaria, protesta social, movimientos sociales |
| Población y condiciones de vida | exclusión de servicios y derechos, población afectada, grupos étnicos existentes, zonas de protección alimentaria, reasentamiento |

La clasificación usa cortes fijos recalibrados para estos 20 indicadores bajo agregación
MAX: `Bajo < 0.7138 ≤ Medio < 0.905 ≤ Alto` (`CORTE_BAJO_MEDIO_RADAR` /
`CORTE_MEDIO_ALTO_RADAR` en `src/config_pipeline.py`). Son específicos de esta
configuración — no reusar con otra cantidad de indicadores o agregación sin recalibrar.

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
  [2026-08-31]). Los 20 indicadores se puntúan sobre todos los artículos que el scraping
  trae.
- **La validación territorial no valida que los artículos hablen del territorio.** El
  FILTRO 1 solo confirma que el *nombre* del territorio escrito por el usuario es real; no
  hay una segunda pasada que verifique que cada artículo scrapeado trata efectivamente
  sobre ese lugar más allá de que el término de búsqueda aparezca mencionado.
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
  accuracy** — hoy en +0.38/+0.42 según la variante exacta, arriba del +0.067 (prácticamente
  cero) del radar anterior a la revisión NLI de agosto, pero lejos de ser una correlación
  fuerte.
- **El estándar de plata cubre solo 2 de los 20 indicadores.** Todas las conclusiones sobre
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
  rama usa MAX con 20 indicadores y nunca se volvió a puntuar a escala nacional con esa
  combinación exacta —no medido, ver `contexto/07_backlog.md`.
- Detalle completo de todo lo anterior, con la evidencia y los experimentos que lo miden,
  en `contexto/09_riesgos_y_limites.md` y `contexto/08_log_decisiones.md`.

## Para trabajar en el código

Ver [`CLAUDE.md`](CLAUDE.md) (reglas duras del proyecto e historial reciente) y la carpeta
`contexto/` (documentación numerada, a demanda — empezar por `00_estado_actual.md`).
Validar cualquier cambio con `python src/test_integracion.py` (16 tests, sin GPU).
