Retomamos el proyecto del radar de riesgo territorial. Trabajo en la rama `pruebas`
(carpeta pruebas/, no desarrollo/).

Antes de proponer o ejecutar nada, lee en este orden:
  contexto/00_estado_actual.md
  contexto/08_log_decisiones.md   <- lo que ya está cerrado, no relitigar
  contexto/07_backlog.md
  contexto/09_riesgos_y_limites.md

## Qué cambió desde el arranque anterior (2026-08-30, misma sesión larga)

Se cerraron, en este orden: 0b (líneas base en el script de métricas), 1 (scoring V2
sobre los 32 departamentos, `datos/scores/scores_v2_32deptos.pkl`), y se midió lo más
importante del proyecto — **el radar V2 sí correlaciona con el oficial**:
`Spearman +0.384` (p=0.030, n=32) contra `+0.067` del V0, sin romper ninguna ancla de
validez aparente y con la nula reservada dando ~0.0000 a escala nacional. Con eso se
cerró también el punto 2 (cortes fijos `Bajo < 0.30 <= Medio < 0.35 <= Alto`). Detalle
completo, con toda la evidencia, en `08_log_decisiones.md` — leerlo antes de remedir
nada de esto.

**Nada de V2 está en `src/` todavía** (ni hipótesis, ni agregación P75, ni estos
cortes). Producción sigue con V0. Promoverlo es un paso aparte (regla 9), no hecho.

De paso, probando la tarea 3b, se encontraron y corrigieron **dos bugs reales de
producción** en `src/scrappers.py` (no hipótesis, bugs de scraping): el filtro de
relevancia ignoraba el nombre completo de los departamentos compuestos (La Guajira,
Norte de Santander, San Andrés y Providencia, Valle del Cauca), y ~20 de ~29 clases de
scraper no tenían el workaround SSL/MITM (antivirus Norton local) que `ElTiempo` ya
traía. Ambos corregidos y verificados contra red real — pero **quedaron 3 fallas de
scraper sin resolver** (El Tiempo con 502 en el momento, parser de El País sin extraer
resultados, timeouts en Corrillos/Enlace Televisión), así que el corpus de esos 4
departamentos sigue con los conteos viejos (11/36/79/117). Ver backlog punto 1b.

Sobre la tarea 0 del backlog (identificar cuál es el índice del DANE de referencia):
sigue PENDIENTE, la trae el usuario.

**Cambios sin commitear** al cerrar esta sesión (confirmar con el usuario si
commitear antes de seguir, o seguir encima de lo no commiteado):
`git status` muestra 5 docs de `contexto/` modificados, `src/metricas_y_calculo_de_error.py`
y `src/scrappers.py` modificados, y nuevos en `experimentos/`:
`exp_terminos_deficit.py`, `exp_terminos_deficit_choco.py`,
`exp_rescrape_fix_relevancia.py`, `exp_correlacion_v2_nacional.py`,
`exp_cortes_fijos_v2.py`, más sus resultados en `experimentos/resultados/`.

## Arranque propuesto

1. **Tarea 3 del backlog** (lo que pidió el usuario para esta sesión): A/B del
   pre-filtro social, pero con **AUC y control absurdo por indicador** — no la
   correlación agregada del radar completo, que ya se midió (+0.384 con vs +0.376 sin
   pre-filtro) y la propia entrada del log dice que no alcanza para decidir. Usa el
   skill `experimento-hipotesis` si aplica; no vuelve a tocar la GPU (los scores están
   en `datos/scores/scores_v2_32deptos.pkl` sin enmascarar).
2. En paralelo o después, según decida el usuario: tarea 1b (arreglar los 3 scrapers
   que quedaron rotos, para poder limpiar el corpus de los 4 departamentos y retomar
   3b/3c con datos confiables). No depende de nada técnico, se frenó por prioridad.
3. Backlog libre para lo que siga: 3b/3c (repetir con corpus limpio una vez resuelto
   1b), 4 (ampliar estándar de plata — no depende de nada), 5 (tres indicadores
   muertos), 7 (cobertura de prensa desbalanceada).

## Recordatorios que ya costaron tiempo

- Ninguna variante se adopta sin pasar el control absurdo. El AUC solo, no decide.
- Optimiza mirando Spearman contra radar_oficial_promedio; reporta la accuracy.
- Con n=32 no persigas mejoras menores a ~15 pp: son ruido.
- Si cambias lo que se mide, recalibra el umbral que lo corta.
- Este entorno tiene un MITM SSL local (antivirus Norton) que rompe cualquier request
  HTTPS sin workaround. Cualquier scraper NUEVO que se agregue necesita
  `verify=False` (requests) o `TCPConnector(ssl=False)` (aiohttp) — si no, falla con
  `CERTIFICATE_VERIFY_FAILED`. Ver `08_log_decisiones.md` [2026-08-30].
- El Bash tool a veces no conserva el cwd esperado entre llamadas (sobre todo después
  de un comando en background que falla al arrancar) — usar rutas absolutas en
  operaciones de scraping/GPU largas evita corridas fallidas por directorio equivocado.
