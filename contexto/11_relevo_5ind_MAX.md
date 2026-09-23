# 11 — Relevo: plan 5 indicadores bajo MAX (estado al 2026-09-23, ronda 2 cerrada)

Documento de traspaso entre conversaciones. **Leerlo entero antes de actuar.** Resume lo que
una conversación nueva necesita para seguir sin redescubrir nada; el detalle y la evidencia
están en los archivos que cita.

## 1. Dónde estamos

- Worktree `C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\pruebas`, rama
  `hipotesis-5ind-max` (desde `radar-max_Septiembre` = 71072a1, lo desplegado). Todo commiteado
  en local; **sin push ni merge**. `Presentacion/` (sin trackear) es del usuario: no tocarlo ni
  añadirlo.
- Ronda 1 (fases 0–8 de `experimentos/PLAN_5ind_MAX.md`) cerrada. **La F8 se revirtió el
  2026-09-23** (commit e1546fb) por la regla 15: `src/` es idéntico a `radar-max_Septiembre`,
  cortes `Bajo < 0.766 <= Medio < 0.9233 <= Alto`, `test_integracion` 10/10, clases 6/19/7.
  Radar con 26. Informe `informes/03_informe_reversion_f8.md`.
- **Ronda 2: pre-registro `experimentos/PREREG_5ind_MAX_r2.md` CONGELADO** (revisado por
  `orquesta-lead`, 12 correcciones adoptadas). **Fase A HECHA (2026-09-23):** ninguna de las 25
  candidatas pasa los criterios 1–5 (ninguna llega a M2 0.60; la mejor es P2 de grupos armados,
  0.38). 0 finalistas. Exclusión: 0 SÍ/SÍ en 940 juzgados, «no medible». Tabla en
  `experimentos/RESULTADOS_5ind_MAX_r2.md`; log [2026-09-23] «2a ronda, fase A» (tres entradas).
  **Fase A aprobada por el usuario; ronda 2 CERRADA:** los 5 conservan su hipótesis vigente, la
  fase B no se ejecuta y `src/` no cambia. Revisión final de `orquesta-lead`: APROBADO, 0
  bloqueantes, 7 menores adoptados. Informe `informes/04_informe_ronda2_solo_hipotesis.md`.
- Etiquetas locales: `base-26ind-radar-max` (71072a1), `base-26ind-f5` (cb336fa),
  `base-26ind-f7` (705a557), `base-26ind-f8-compuerta` (85db4e1, versión con la compuerta,
  revertida).
- Informes para el jefe/profesora: **`informes/`** (01 a 05; índice en `informes/README.md`;
  el 05 es el consolidado del plan). El siguiente es el 06.

## 2. Innegociables (del usuario)

- Agregación del radar = **MAX**. No se cambia ni se cuestiona.
- **Regla 15 (2026-09-23): de cada indicador solo se cambia la hipótesis.** Nada de compuertas
  de palabras clave, `min`, restas de confusores ni columnas nuevas. Sustituye al «NLI + reglas
  de palabras clave» del plan. Producción = solo el NLI; el LLM solo juzga, en local.
- Sin humano en el lazo: referencia = SÍ de `juez-a` (sonnet) **y** `juez-b` (opus), ciegos.
- **No se retira ningún indicador**: el radar sigue con 26.
- Sin push ni merge sin aprobación explícita. Toda decisión (adopciones y rechazos) a
  `contexto/08_log_decisiones.md`.
- Economía de tokens: el orquestador escribe los scripts; subagentes solo `orquesta-lead` (una
  vez por pre-registro y una al final) y los jueces. Nada de Explore ni general-purpose.
  Resúmenes ≤ 40 líneas; no volcar dataframes. GPU una sola vez por corpus.
- Si el contexto se llena: parar en un punto limpio (todo commiteado) y entregar un prompt de
  relevo (actualizar este documento).

## 3. Decisiones cerradas (no relitigar)

En `contexto/08_log_decisiones.md`, entradas [2026-09-22] y [2026-09-23]:
- Ronda 1: pre-registro congelado; premisa = solo `texto`, truncada como el NLI. Rechazadas las
  variantes de conflicto, desplazamiento, rechazo y exclusión. La V08 de grupos armados pasó los
  6 criterios, pero **no es promovible** por la regla 15.
- Hallazgo de método: el NLI confirma la forma de la frase, no su objeto. La vigente de
  rechazo, desplazamiento y conflicto suspende su propio control de objeto absurdo.
- F8 revertida (regla 15). La propuesta de compuertas del relevo anterior y las 4
  recomendaciones asociadas quedan sin efecto.
- Ronda 2 = solo hipótesis (F1), 5 indicadores, criterios de la ronda 1. Pre-registro congelado.
- **Ronda 2 cerrada con 0 finalistas:** se rechazan las 25 candidatas (N1–N3, P1, P2 × 5)
  por el criterio 1 (mejor M2 0.38; M2+ 0.50). No se repite otra ronda de frases sobre estos 5
  indicadores sin evidencia nueva medida. Exclusión: «no medible con este corpus».

## 4. Pendiente de decisión del usuario

1. **Fusión a `radar-max_Septiembre`:** ¿entra `experimentos/`? Tras la reversión, `src/` y los
   entregables ya coinciden con esa rama. Las reglas 5–6 de `CLAUDE.md` siguen diciendo que no
   hay `experimentos/`.
2. Push/merge de `hipotesis-5ind-max`.
3. Qué hacer con `exclusion_beneficios_economicos`, que resultó «no medible» (§5 del
   pre-registro r2). Sigue en el radar con su frase vigente; no se retira salvo que lo diga el
   usuario.
4. Siguiente paso del proyecto: **probar otro modelo NLI** (`vicgalle/xlm-roberta-large-xnli-anli`,
   3 clases, reemplazo directo), en 3 etapas: filtro sin jueces, juicio y escala nacional.
   Propuesta en `informes/05_informe_consolidado_5ind_MAX.md` §7 y en el log
   [2026-09-23] «REAPERTURA». Si se aprueba, primero va un pre-registro y la revisión de
   `orquesta-lead`. El usuario **rechazó** consultar a la profesora (tarea 0 del backlog): no
   proponerlo de nuevo.

## 5. Ronda 2 — resumen del pre-registro congelado

Detalle completo en `experimentos/PREREG_5ind_MAX_r2.md`; textos en
`experimentos/hipotesis_5ind_max_r2.py`.
- Por indicador: la vigente (línea base) y 5 candidatas F1, N1–N3 (nuevas) y P1/P2 (`p1`/`p2`
  de la ronda 1). Cada una con su gemela de osos polares (mismo hueco que en la ronda 1).
  Absurdo total = `NULA_TEST`.
- **Fase A** (4 lugares): GPU de 35 hipótesis × 1.647 (46 min reales; incluye las 5 vigentes como
  sanidad, max|dif| < 1e-4 frente a `scores_5ind_atomicas_lugares.pkl`), a
  `datos/scores/scores_5ind_r2_lugares.pkl`. Pool: top-15 de la vigente y las candidatas por
  indicador × lugar, más el pool de la ronda 1. Se juzgan solo los artículos nuevos, más la
  muestra de exclusión (`REGEX_MUESTREO_EXCLUSION`, 206 sin juzgar) y 40 ya juzgados como
  control entre rondas. Lotes de 40, semilla 20260923, ids `b0000…`, carpeta
  `experimentos/resultados/juicio_5ind_r2/`. Criterios 1–5 de la ronda 1. **Parada: informe
  intermedio y visto bueno antes de la fase B.**
- **Fase B** (finalistas, hasta 2 por indicador): GPU nacional de la frase y su gemela (~15 min
  cada una), holdout Cauca/Chocó/Cundinamarca (criterio 6) y cortes recalibrados una sola vez.
  Parada prevista: informe y visto bueno antes de promover (cambiar solo el texto de la
  hipótesis en `src/Transformer_optimo.py` y los cortes). **No se ejecuta: 0 finalistas.**
- Exclusión: con < 5 SÍ/SÍ en total se declara no medible y decide el usuario.

## 6. Detalles operativos resueltos (no redescubrir)

**Entorno.** Python del sistema 3.11, torch 2.6 cu124, GPU RTX 4050. Scripts desde la raíz de
`pruebas/`. En Windows, `PYTHONIOENCODING=utf-8` al imprimir tildes. El aviso "Token indices
sequence length is longer…" es inocuo. `sed -i` en Git Bash convierte CRLF→LF: inocuo
(`core.autocrlf=true` normaliza), pero para editar archivos con CRLF es más limpio el Edit tool.

**Datos** (los `.pkl` están en `.gitignore`; existen solo en local):
- Nacional V2: `datos/scores/scores_v2_32deptos.pkl` (11.439 × 58: `sesgo`, `ent_`/`neu_` de las
  26 y `NULA_TEST`). **No trae `url`: se une por posición** con
  `datos/corpus/df_corpus_combinado_32deptos.pkl` (verificado en F0).
- Nacional F7: `datos/scores/scores_5ind_atomicas_nacional.pkl` (solo
  `presencia_grupos_armados__vig_abs`); `experimentos/resultados/juicio_5ind_holdout/{premisas_visibles_nacional,variantes_nacional}.pkl`.
- Lugares: `datos/scores/scores_5ind_atomicas_lugares.pkl` (83 hipótesis × 1.647, `ent_/neu_/con_`);
  `resultados/tablas_lugares_max/df_procesado_5lugares.pkl` (producción V2, 26 indicadores);
  `experimentos/resultados/juicio_5ind/url_lugares.csv` (Antioquia 494, Maicao 1.101, Oicatá 32,
  Paraguachón 77 = pkl individual; 57 de Paraguachón también son de Maicao);
  `experimentos/resultados/juicio_5ind/premisas_visibles.pkl` (url → premisa).
- `datos/scores/df_procesado_32deptos.pkl` es V0 sin corregir: **no usarlo**.
- Excel originales de la profesora: `C:\Users\Usuario\Downloads\radar_resumen_{Maicao (6),Oicat_,Paraguach_n}.xlsx`
  (fuera del repo; se hicieron sobre un subconjunto del corpus actual).

**Scripts reutilizables** (`experimentos/`): `hipotesis_5ind_max.py` (fuente única de hipótesis,
gemelas, `REGEX_F5`, `premisa_visible`, `normalizar`, `compuerta`); `exp_5ind_max_atomicas.py`
(GPU con checkpoint); `exp_5ind_max_variantes.py`; `exp_5ind_max_juicio.py lotes|consolidar`;
`exp_5ind_max_metricas.py`; `exp_5ind_max_nacional.py gpu|premisas`;
`exp_5ind_max_holdout.py pool|m4|consolidar|metricas`; `exp_5ind_max_cortes.py` (procedimiento
de cortes de `b060b3b`, verifica las 12 anclas); `exp_5ind_max_f8_equivalencia.py`;
`exp_5ind_max_f8_excel_lugares.py`. NLI fuera de `src/`: `experimentos/nli_core.py`
(`NLIScorer().score(textos, hip, batch_size=32, max_length=512, devolver_todo=True)`).
`hipotesis_v2.TODAS` es un **dict** (usar `list(V2.TODAS)` para columnas).

**Producción** (`src/`): = `radar-max_Septiembre` (sin compuerta desde la reversión); hipótesis
en `src/Transformer_optimo.py`, cortes en `src/config_pipeline.py`. Validar con
`python src/test_integracion.py` (10 tests, sin GPU) y `experimentos/exp_5ind_max_f8_reversion.py`.
`src/` no importa de `experimentos/`. `exp_5ind_max_f8_equivalencia.py` es histórico (depende de
la compuerta revertida).

**Cortes:** el procedimiento se aplica sobre el radar **sin redondear** (sobre `radar_propio`,
redondeado a 4 decimales, el punto medio del hueco alto da 0.9234 en vez de 0.9233).

**Agentes** (`pruebas/.claude/agents/`: `orquesta-lead`, `juez-a`, `juez-b`). La sesión no los
registra como tipos: invocarlos con el Agent tool, `subagent_type: "claude"`, `model` = sonnet
(juez-a) u opus (juez-b, orquesta-lead), prompt "Eres el agente definido en <ruta .md>; léelo
primero y síguelo" + rutas explícitas de lotes y carpeta de salida. Jueces: lotes JSONL de 40,
en segundo plano y en paralelo (F5: 3 instancias por juez, 5 lotes cada una); escriben a
`etiquetas_a/`/`etiquetas_b/` y responden una línea por lote. El codebook del juez es el del
pre-registro congelado; si la 2a ronda lo cambia, hay que crear agentes nuevos (no editar estos).

## 7. Siguiente paso exacto

1. Leer `CLAUDE.md` (regla 15), este documento, `experimentos/PREREG_5ind_MAX_r2.md`,
   `experimentos/RESULTADOS_5ind_MAX_r2.md` y las entradas [2026-09-23] del log.
2. Fase A hecha: scripts `exp_5ind_max_r2_atomicas.py` (GPU), `exp_5ind_max_r2_pool.py
   lotes|consolidar` y `exp_5ind_max_r2_metricas.py`; datos en
   `experimentos/resultados/juicio_5ind_r2/` y `datos/scores/scores_5ind_r2_lugares.pkl`.
3. Ronda 2 cerrada: informe 04 escrito y revisión final de `orquesta-lead` hecha. No queda
   nada que ejecutar del plan 5ind MAX. Esperar las decisiones del usuario de §4 (fusión,
   push/merge, exclusión y siguiente paso del proyecto).
4. Si un juez se corta a mitad (p. ej., por el límite de uso), retomarlo con `SendMessage` a su
   id: conserva los lotes ya leídos. No relanzarlo de cero.
