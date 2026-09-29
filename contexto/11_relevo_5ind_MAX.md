# 11 — Relevo: plan 5 indicadores bajo MAX (estado al 2026-09-29: etapa 2 del pre-filtro por indicador CERRADA sin listas nuevas)

Documento de traspaso entre conversaciones. **Leerlo entero antes de actuar.** Resume lo que
una conversación nueva necesita para seguir sin redescubrir nada; el detalle y la evidencia
están en los archivos que cita.

## 1. Dónde estamos

- Worktree `C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\pruebas`, rama
  `hipotesis-5ind-max` (desde `radar-max_Septiembre` = 71072a1, lo desplegado). Todo commiteado
  en local; **sin push ni merge**. `Presentacion/` (sin trackear) es del usuario: no tocarlo ni
  añadirlo.
- **Desde el 2026-09-29 `src/` lleva el pre-filtro por indicador** (`PREFILTRO_OBJETO` en
  `src/Transformer_optimo.py`): las listas congeladas de grupos armados y desplazamiento aplicadas a la premisa
  visible del par con la hipótesis de cada indicador, sin columnas nuevas; cortes **0.7572/0.9233**; clases 6/19/7;
  `test_integracion` 16/16; radar con 26. Excepción a la regla 15 confirmada por el usuario (alcance solo esas
  listas). Pre-registro `experimentos/PREREG_prefiltro_indicador.md`, resultados
  `experimentos/RESULTADOS_prefiltro_indicador.md`, plan `experimentos/PLAN_implementacion_prefiltro_indicador.md`,
  equivalencia `experimentos/exp_prefiltro_indicador_equivalencia.py`; informe `informes/12_informe_prefiltro_por_indicador.md`.
  Antes (2026-09-28) el pre-filtro social general se rechazó bajo MAX (informe 11).
- **Etapa 2, tramo 1 (2026-09-29): NO ADOPTAR** (`src/` sin cambios). Pre-registro
  `experimentos/PREREG_prefiltro_indicador_e2.md` (da30a63; tramo de 6, tope 3, techo de apertura 50 %, sin placebo);
  listas/gemelas `experimentos/hipotesis_prefiltro_e2.py`; jueces nuevos `juez-c` (sonnet) y `juez-d` (opus); datos en
  `experimentos/resultados/juicio_prefiltro_e2/` y `datos/scores/scores_prefiltro_e2.pkl`; análisis
  `experimentos/exp_prefiltro_e2.py` → `experimentos/RESULTADOS_prefiltro_e2.md` (600c5d3). Reasentamiento (4 SÍ/SÍ) y daños
  ambientales (3) «no medibles»; amenaza a líderes, amenazas/intimidación, protesta y violación de DDHH no cumplen (a)–(d)
  (la más cercana, amenazas/intimidación: (a) +0.43, (b) +0.27, falla (c) gemela −0.114). Trazabilidad del MAX: artículo SÍ en
  8 → 14 de 42 celdas. Informe 13 (9366c39), que además explica en detalle por qué no se reactiva el pre-filtro social.
- **Etapa 2, tramo 2 (2026-09-29): etapa 2 CERRADA.** Opción C elegida por el usuario: cribado sin jueces de los 11 restantes
  (pre-registro `experimentos/PREREG_prefiltro_indicador_e2_t2.md`, 26618f8; condición C = control absurdo y R = radar con la lista sola).
  Sobrevive solo `zonas_proteccion_alimentaria` (560fa9f); con jueces nuevos `juez-e`/`juez-f` (kappa 0.72, 9 SÍ/SÍ) falla (a) +0.136 y
  (b) +0.067 (343db57): NO ADOPTAR. Ninguna lista nueva en toda la etapa 2; `src/` sin cambios. Informe 14.
- Ronda 1 (fases 0–8 de `experimentos/PLAN_5ind_MAX.md`) cerrada. **La F8 se revirtió el
  2026-09-23** (commit e1546fb) por la regla 15 (entonces `src/` era idéntico a `radar-max_Septiembre`,
  cortes 0.766/0.9233, `test_integracion` 10/10). Informe `informes/03_informe_reversion_f8.md`.
- **Ronda 2: pre-registro `experimentos/PREREG_5ind_MAX_r2.md` CONGELADO** (revisado por
  `orquesta-lead`, 12 correcciones adoptadas). **Fase A HECHA (2026-09-23):** ninguna de las 25
  candidatas pasa los criterios 1–5 (ninguna llega a M2 0.60; la mejor es P2 de grupos armados,
  0.38). 0 finalistas. Exclusión: 0 SÍ/SÍ en 940 juzgados, «no medible». Tabla en
  `experimentos/RESULTADOS_5ind_MAX_r2.md`; log [2026-09-23] «2a ronda, fase A» (tres entradas).
  **Fase A aprobada por el usuario; ronda 2 CERRADA:** los 5 conservan su hipótesis vigente, la
  fase B no se ejecuta y `src/` no cambia. Revisión final de `orquesta-lead`: APROBADO, 0
  bloqueantes, 7 menores adoptados. Informe `informes/04_informe_ronda2_solo_hipotesis.md`.
- Etiquetas locales: `base-26ind-prefiltro-indicador-pre` (3835672, último commit con `src/` sin el pre-filtro
  por indicador), `base-26ind-radar-max` (71072a1), `base-26ind-f5` (cb336fa),
  `base-26ind-f7` (705a557), `base-26ind-f8-compuerta` (85db4e1, versión con la compuerta,
  revertida), `prueba-modelo-nli-rechazado` (27a39a1, historial de la prueba del modelo NLI,
  cuya rama se borró).
- Informes para el jefe/profesora: **`informes/`** (01 a 14; índice en `informes/README.md`;
  el 05 es el consolidado del plan; 06–07, la prueba del modelo NLI; 08, exclusión; 09, avances
  de la rama para el jefe; 10, resumen consolidado 01–09; 11, pre-filtro social general (rechazado);
  12, pre-filtro por indicador (promovido); 13, etapa 2 tramo 1 y pre-filtro social; 14, cierre de la etapa 2). **El siguiente es el 15.**

## 2. Innegociables (del usuario)

- Agregación del radar = **MAX**. No se cambia ni se cuestiona.
- **Regla 15 (2026-09-23): de cada indicador solo se cambia la hipótesis.** Nada de compuertas
  de palabras clave, `min`, restas de confusores ni columnas nuevas. Sustituye al «NLI + reglas
  de palabras clave» del plan. Producción = solo el NLI; el LLM solo juzga, en local.
- Sin humano en el lazo: referencia = SÍ de `juez-a` (sonnet) **y** `juez-b` (opus), ciegos.
- **No se retira ningún indicador**: el radar sigue con 26.
- Sin push ni merge sin aprobación explícita. Toda decisión (adopciones y rechazos) a
  `contexto/08_log_decisiones.md`.
- Economía de tokens. Ejecución pesada: un subagente Sonnet (tipo `claude`) NUEVO por fase, con prompt autocontenido;
  los jueces los lanza el coordinador. Nada de Explore ni general-purpose.
- Proyecto solo backend: el front (que muestra el artículo que fija el MAX) es de otra rama y no se toca.
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

1. **Fusión a `radar-max_Septiembre`: EN ESPERA** (2026-09-24). El usuario le muestra antes la
   rama a su jefe (informe 09); no fusionar hasta que lo diga. ¿Entra `experimentos/`? Tras la reversión, `src/` y los
   entregables ya coinciden con esa rama. Las reglas 5–6 de `CLAUDE.md` siguen diciendo que no
   hay `experimentos/`.
2. Push/merge de `hipotesis-5ind-max`.
3. Qué hacer con `exclusion_beneficios_economicos`, que resultó «no medible» (§5 del
   pre-registro r2). Sigue en el radar con su frase vigente; no se retira salvo que lo diga el
   usuario.
4. **Prueba de otro modelo NLI: CERRADA, modelo RECHAZADO** (2026-09-23).
   `xlm-roberta-large-xnli-anli` no cumple los criterios 1–5 en la etapa 2 (informe 07,
   `experimentos/RESULTADOS_modelo_nli.md`). La rama y el worktree se borraron; su historial está
   en la etiqueta `prueba-modelo-nli-rechazado` y su documentación y resultados, aquí (log,
   informes 06–07, `PREREG_modelo_nli.md`, scripts `exp_modelo_nli_*`, relevo 12 como registro).
   El usuario **rechazó** consultar a la profesora (tarea 0 del backlog): no proponerlo de nuevo.
5. **Etapa 2 del pre-filtro por indicador: CERRADA** (2026-09-29, informe 14). Nada pendiente.

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

**Producción** (`src/`): = `radar-max_Septiembre` + pre-filtro por indicador de grupos armados y desplazamiento
(desde el 2026-09-29); hipótesis y `PREFILTRO_OBJETO` en `src/Transformer_optimo.py`, cortes 0.7572/0.9233 en
`src/config_pipeline.py`. Validar con `python src/test_integracion.py` (16 tests, sin GPU) y
`python experimentos/exp_prefiltro_indicador_equivalencia.py` (offline, contra el experimento). Ojo: un
`df_procesado` calculado antes de esa fecha no trae el pre-filtro y no debe clasificarse con los cortes nuevos
(no hay columna que lo delate: regenerarlo). `experimentos/exp_5ind_max_f8_reversion.py` es histórico.
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

0. (2026-09-29, cierre) Etapa 2 CERRADA sin listas nuevas (informes 13 y 14). Siguiente: esperar las decisiones del usuario de §4
   (fusión, push/merge, exclusión); no proponer más listas de pre-filtro sin evidencia nueva medida. Antes (etapa 1, `f30549e`): Leer las entradas [2026-09-28] y [2026-09-29] del log y los informes 11 y 12.
   Motivo de fondo: la jefa quiere un pre-filtro que se aplique a TODOS los indicadores; el general (una sola pregunta NLI)
   no sirve porque los falsos positivos de la cabeza son específicos de cada indicador (informe 11 y diagnóstico: los
   artículos que fijan el MAX no se distinguen del corpus por territorio, sesgo ni fecha). La etapa 2 es el camino a los 26.
   Lecciones operativas de esa sesión:
   - Un solo subagente ejecutor (Sonnet, tipo `claude`) para tres tareas seguidas se quedó sin contexto al final: en la
     etapa 2, un subagente nuevo por fase, con un prompt autocontenido.
   - Si el límite de uso corta a un agente, revisar `git log`/`git status` antes de retomarlo (suele haber commiteado más
     de lo que alcanzó a reportar) y retomarlo con `SendMessage`.
   - No correr `python src/pipeline_lugares.py` tal cual: su `paso1_combinar()` reescribe `datos/corpus/df_corpus_5lugares.pkl`
     (compartido por junction). Usar el envoltorio `experimentos/exp_prefiltro_correr_lugares.py`, que comprueba el sha256.
   - `juez-a`/`juez-b` solo tienen codebook para 5 indicadores: la etapa 2 necesita agentes jueces nuevos con un codebook
     por indicador (no editar los existentes). Cada lista nueva requiere pre-registro y confirmación expresa del usuario
     (regla 15), y el pre-registro debe fijar cuántas listas se admiten (con 17, alguna pasaría por azar).
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
