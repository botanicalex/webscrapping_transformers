Retomamos el proyecto del radar de riesgo territorial. Trabajo en la rama `pruebas`
(carpeta pruebas/, no desarrollo/).

Antes de proponer o ejecutar nada, lee en este orden:

  contexto/10_combinaciones_y_rumbo.md  <- EMPIEZA AQUÍ. Qué combinación funciona
                                           mejor, qué se probó ya, cómo se calcula el
                                           radar hoy, y qué está roto en src/.
  contexto/00_estado_actual.md
  contexto/08_log_decisiones.md         <- lo que ya está cerrado, no relitigar
  contexto/07_backlog.md
  contexto/09_riesgos_y_limites.md      <- el techo estructural, antes de optimizar

## El estado en una línea, sin maquillaje

Producción corre V2 desde el 2026-08-31. **Su accuracy contra el DANE es 0.250: está por
debajo de las cinco líneas base** (azar 0.333, "siempre Bajo" 0.344, modelo nulo 0.281).
La mejor accuracy medida de todas las combinaciones es 0.406, pero usa terciles, que no son
desplegables en una vereda sola. Lo que sí mejoró es la **validez del instrumento**: el
radar V0 era indistinguible de uno hecho con hipótesis absurdas, y el V2 no.
Ver `contexto/10_combinaciones_y_rumbo.md` sección 1 para la comparación completa.

## Qué cambió el 2026-08-31 (tres commits + correcciones posteriores)

1. **Se rechazó el pre-filtro social** (`bb3e961`), umbral 0.85: cuesta AUC en los dos
   indicadores con estándar de plata (−0.053 y −0.027, IC95% excluye cero). Alcance: solo
   ese umbral, solo esos 2 indicadores.

2. **Se corrigieron 4 fallas de scraper** (`2552567`) y se re-scrapearon 3 departamentos:
   La Guajira 11→1.553, Norte de Santander 36→352, Valle del Cauca 117→145. **El corpus NO
   se fusionó** a `datos/corpus/`. San Andrés y Providencia **tiene 79 artículos en el
   corpus**; el 0 fue solo el resultado de esa corrida, con El Tiempo caído.

3. **Se promovió V2 a producción** (`331f033`): hipótesis nuevas, sin pre-filtro, sesgo
   descontado, P75 por rango más cercano, cortes fijos, clasificación oficial real del DANE.
   Verificado sin GPU y con GPU (max|dif| ~5e-7 contra `nli_core`).

4. **Una revisión posterior encontró errores en esa promoción**, ya corregidos:
   los cortes se habían calibrado sobre la distribución equivocada (P75 interpolado en vez
   de rango cercano) → recalibrados a **0.2969 / 0.3527**; el camino legado de métricas
   aplicaba los cortes V2 a columnas en escala 0–100; el comando por defecto reventaba
   *después* de las 4 h de GPU por colisión de `EXPERIMENTO_1`; `pipeline_lugares.py`
   reventaba por la columna `score_social` retirada; y la rama de scraping del orquestador
   era código muerto.

## Preferencias del usuario, ya expresadas

- **Evitar re-scraping.** Consume demasiado tiempo. El foco está en radar, transformers e
  indicadores.
- **La GPU sí se puede usar para transformers.** Se corren por separado del scraping.
- **No ir tan rápido:** explicar antes de avanzar y preguntar cuando haya una decisión de
  diseño de por medio.

## Arranque propuesto — elegir uno, no varios

1. **Ampliar el estándar de plata** (backlog punto 4). Cubre **2 de 26** indicadores y todas
   las conclusiones de calidad descansan en dos. No depende de nada. Conviene además
   reservar un tercio de los positivos como conjunto de validación
   (`09_riesgos_y_limites.md`). Usar el skill `experimento-hipotesis` si toca redacción.

2. **Los indicadores débiles** (backlog punto 5). Ojo: la etiqueta "tres indicadores
   muertos" del backlog es **inexacta a escala nacional** — ver el aviso al final de
   `contexto/10_combinaciones_y_rumbo.md`. El que está realmente en cero es
   `danos_ambientales`. Va mejor después del punto 1, porque ninguno tiene con qué medirse.

3. **Decidir si se fusiona el corpus re-scrapeado** de los 3 departamentos. `datos/corpus/`
   está enlazada por junction con `desarrollo/`, así que afecta a los dos worktrees.
   **Esta decisión va ANTES de re-puntuar**, no después: al revés obliga a repetir las 4 h
   de GPU (regla 8).

4. **Re-puntuar los 32 departamentos con el código de `src/`** (~4 h GPU). **Antes de
   lanzarlo, resolver el problema del cargador de corpus** (ver abajo): tal como está
   produce 35 filas de radar, no 32.

Lo que **no** conviene arrancar sin el usuario: la tarea 0 (identificar qué índice del DANE
es), que la trae él, y la decisión entre los tres caminos de `09_riesgos_y_limites.md`.

## Roto o pendiente en `src/` — leer antes de una corrida larga

- **`CargadorCorpus` carga TODOS los `df_corpus_*.pkl`**: una corrida real levanta 12.592
  artículos y 35 valores de `departamento` (incluye "Municipio Maicao", "Vereda
  Paraguachón", "Antioquia (2023)"), no 11.439 / 32.
- **`src/pipeline_lugares.py` y `src/generar_max_articulos_por_departamento.py`** siguen con
  cortes 1/3–2/3 y agregación MAX (rechazada). No están en el camino por defecto.
- **`experimentos_radar.jsonl` registra metadatos falsos** para la operación "bloques"
  ("36 indicadores", "zscore"): son 26 y no hay z-score.
- **El camino legado de pesos aleatorios** (`--operaciones-radar indicadores_transformers`)
  sigue invocable y poda al top-N por accuracy contra el propio DANE — riesgo de
  sobreajuste documentado. **No usarlo.** El default sin flags es el único validado.

## Recordatorios que ya costaron tiempo

- **Ninguna variante se adopta sin pasar el control absurdo.** El AUC solo no decide.
- **AUC y accuracy son ejes distintos.** El AUC mide discriminación del indicador contra el
  estándar de plata; la accuracy mide acuerdo del radar con el DANE. No mezclarlos ni usar
  uno para anular al otro "por potencia estadística".
- **Optimizar mirando Spearman, reportar la accuracy.** Pero el Spearman es **invariante a
  los cortes**: no sirve para justificar un juego de cortes sobre otro.
- **Con n=32, diferencias menores a ~15 pp son ruido — y la regla aplica en las dos
  direcciones**, también cuando el número que sale perjudica la decisión ya tomada.
- **Si cambias lo que se mide, recalibra el umbral.** Ya falló tres veces; la última, hoy:
  los cortes se calibraron sobre P75 interpolado y producción usa rango más cercano.
- **No optimizar los cortes contra la accuracy.** Se leen de la distribución y se verifican
  contra las anclas.
- **Antes de cualquier experimento**, `nli_core.verificar_contra_produccion_v2()` contra
  `datos/scores/df_procesado_baseline_v2.pkl` debe dar OK. La función sin sufijo es legado.
- Este entorno tiene un **MITM SSL local (Norton)**: cualquier scraper nuevo necesita
  `verify=False` (requests) o `TCPConnector(ssl=False)` (aiohttp); `newspaper.Article` usa
  su **propia** sesión y necesita su propio `Config` — ya está en `_NEWSPAPER_CONFIG`.
- Los scripts de `src/` se corren **desde la raíz**; los de `experimentos/`, **desde
  `experimentos/`**.

## Pendiente de entregable

`ESTADO_DEL_PROYECTO.md` existe también en `pruebas` (sincronizado por DSH el 2026-09-01;
antes describía el estado del 2026-08-30 con V0 en producción). Actualizarlo en `master`
es parte de fusionar `pruebas` a `master` (regla 13), que no se ha hecho.
