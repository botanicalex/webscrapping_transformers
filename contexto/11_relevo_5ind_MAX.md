# 11 — Relevo: plan 5 indicadores bajo MAX (estado al 2026-09-23)

Documento de traspaso entre conversaciones. **Leerlo entero antes de actuar.** Resume lo que
una conversación nueva necesita para seguir sin redescubrir nada; el detalle y la evidencia
están en los archivos que cita.

## 1. Dónde estamos

- Worktree `C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\pruebas`, rama
  `hipotesis-5ind-max` (desde `radar-max_Septiembre` = 71072a1, lo desplegado). Todo commiteado
  en local; **sin push ni merge**. `Presentacion/` (sin trackear) es del usuario: no tocarlo ni
  añadirlo.
- Fases 0–8 del plan `experimentos/PLAN_5ind_MAX.md` **cerradas**. Resultado:
  `presencia_grupos_armados` = V08 (score vigente × compuerta léxica), **ya en `src/`**; cortes
  del radar `Bajo < 0.7574 <= Medio < 0.9233 <= Alto`. Los otros 25 indicadores, intactos. Radar
  con 26.
- Etiquetas locales de protección: `base-26ind-radar-max` (71072a1), `base-26ind-f5` (cb336fa),
  `base-26ind-f7` (705a557, último commit con `src/` intacto).
- Commits de F8: `062ab20` (promoción, tests, equivalencia, Excel) y `50a553a` (correcciones de
  la revisión final de `orquesta-lead`, veredicto APROBADO, 0 bloqueantes). Después: carpeta
  `informes/` y este relevo.
- Informes para el jefe/profesora: **`informes/`** (índice y convención en `informes/README.md`).
  Todo informe nuevo va ahí, numerado (`03_…`, `04_…`).

## 2. Innegociables (del usuario)

- Agregación del radar = **MAX**. No se cambia ni se cuestiona; solo cambia el score por artículo.
- Producción = solo NLI (`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`) + reglas
  de palabras clave. El LLM solo juzga, en local.
- Sin humano en el lazo: referencia = SÍ de `juez-a` (sonnet) **y** `juez-b` (opus), ciegos.
- **No se retira ningún indicador**: el radar sigue con 26.
- Sin push ni merge sin aprobación explícita. Toda decisión (adopciones y rechazos) a
  `contexto/08_log_decisiones.md`.
- Economía de tokens: el orquestador (conversación principal) escribe los scripts; subagentes
  solo `orquesta-lead` (una vez por pre-registro y una al final) y los jueces. Nada de Explore
  ni general-purpose. Resúmenes ≤ 40 líneas; no volcar dataframes. GPU una sola vez por corpus.
- Si el contexto se llena: parar en un punto limpio (todo commiteado) y entregar un prompt de
  relevo con estado, decisiones, detalles operativos y siguiente paso exacto (actualizar este
  documento).

## 3. Decisiones cerradas en este experimento (no relitigar)

Todas en `contexto/08_log_decisiones.md`, entradas [2026-09-22]:
- Pre-registro `experimentos/PREREG_5ind_MAX.md` **congelado** (codebook, 12 variantes, gemelas
  absurdas con osos polares, métricas M1–M6, 6 criterios). No se edita; la 2a ronda lleva uno nuevo.
- Premisa = solo `texto` (sin título), truncado como el NLI. El juez ve exactamente eso.
- F5: grupos armados V08 pasa 1–5. **Rechazadas** las 11 alternativas de conflicto territorial
  (mejores V08/V09/V10, M2 0.57–0.59 < 0.60, gemela de objeto absurdo > 0.766 en Antioquia),
  desplazamiento (mejor V10, M2 0.40), rechazo a proyecto (M2 ≤ 0.03, 4 positivos) y exclusión
  (0 positivos, kappa ≈ 0: referencia débil).
- F7: V08 pasa el holdout (M2 0.467 → 0.767) → adoptada. Cortes 0.766 → 0.7574 (misma clase 6/19/7).
- F8: promovida a `src/` (ver `informes/02_…`). Exclusión **no se retira** (decisión del usuario).
- Hallazgo de método clave: **la vigente de rechazo, desplazamiento y conflicto suspende su
  propio control de objeto absurdo** (MAX 0.96–0.99 con "osos polares" en el hueco del objeto):
  el NLI confirma la forma de la frase, no el contenido. Reescribir frases no lo arregla; las
  compuertas léxicas sí movieron la cola.

## 4. Pendiente de decisión del usuario

1. **Aprobar (o ajustar) la segunda ronda** (§5). Estado: **propuesta, no aprobada**.
2. **Fusión a `radar-max_Septiembre`:** ¿entra `experimentos/`? `CLAUDE.md` (reglas 5–6,
   Convenciones), `README.md` y `explicacion_alexa.md` ("Qué se eliminó") dicen que la rama no
   tiene `experimentos/` ni `nli_core`, pero esta rama sí. Si entra, corregir esas reglas; si no,
   quitar de los entregables las referencias a `experimentos/` (los informes ya están fuera, en
   `informes/`). Registrado como corrección 5 no aplicada en el log.
3. Push/merge de `hipotesis-5ind-max`.

## 5. Segunda ronda — propuesta (para redactar su pre-registro)

Experimento **nuevo** (no reabre lo cerrado): `experimentos/PREREG_5ind_MAX_r2.md`, revisado una
vez por `orquesta-lead` antes de ejecutar nada. Indicadores: `conflicto_territorial`,
`desplazamiento_forzado`, `rechazo_proyecto`, `exclusion_beneficios_economicos`. Un cambio por
indicador (regla 7).

**Evidencia de partida** (log F5 y F7; tablas en `experimentos/RESULTADOS_5ind_MAX.md`):

| Indicador | Positivos SÍ/SÍ F5 (Ant/Mai/Oic/Par) | Positivos holdout (Cau/Cho/Cun) | kappa F5 / holdout | Mejor intento F5 |
|---|---|---|---|---|
| conflicto_territorial | 9/8/0/3 | 7/8/1 | 0.87 / 0.75 | V08/V09/V10, M2 0.57–0.59; gemela absurda > 0.766 en Antioquia |
| desplazamiento_forzado | 10/1/0/0 | 5/13/0 | 0.88 / 0.93 | V10 (F5+F2), M2 0.40 |
| rechazo_proyecto | 1/3/0/0 | 1/0/2 | 0.46 / 1.00 | M2 ≤ 0.03 |
| exclusion_beneficios_economicos | 0/0/0/0 | 0/0/0 (ningún SÍ) | ≈0 / indef. | — |

**Diseño propuesto:**
1. Variantes: compuertas léxicas sobre la **vigente** (como V08) con regex refinadas a partir de
   los falsos positivos ya juzgados; para conflicto y rechazo, compuerta doble actor + acción
   (p. ej. grupo armado/comunidad **y** disputa/enfrentamiento; comunidad **y** obra/proyecto
   identificable). Controles absurdos específicos por indicador (gemela de objeto absurdo con
   osos polares, regla 3) antes que reescribir frases. Regex actuales de las 5 en
   `experimentos/hipotesis_5ind_max.py` (`REGEX_F5`), con sus hipótesis y gemelas.
2. Muestra: diseñar sobre el **corpus nacional sin Cauca, Chocó ni Cundinamarca**; holdout =
   esos tres (sus etiquetas de F7 se reutilizan; lo nuevo del pool se juzga). Unidad = departamento.
3. Exclusión: el top-k de su propia vigente no encuentra casos. Muestreo por **palabras clave de
   regalías / compensación / consulta previa / "no han recibido" + proyecto** sobre el corpus
   nacional (sin GPU: la vigente ya está en `scores_v2_32deptos.pkl`). Si salen < 5 SÍ/SÍ, se
   declara no medible con este corpus y decide el usuario.
4. Criterio: el M2 medio actual obliga a MAX = 0 en lugares sin positivos (con pocos positivos es
   casi inalcanzable). Proponer M2 solo sobre lugares con ≥ 1 positivo, y que M3 cubra los demás.
   Es un criterio **nuevo**; declararlo como tal en el pre-registro.
5. Costo: GPU ~30 min (gemelas de objeto absurdo de las 4 vigentes a escala nacional, ~7–8 min
   cada una; `experimentos/exp_5ind_max_nacional.py` sirve de plantilla); jueces ~300–400
   artículos en lotes de 40.

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

**Producción** (`src/`): compuerta en `src/Transformer_optimo.py`
(`REGEX_COMPUERTA_GRUPOS_ARMADOS`, `normalizar`, `premisa_visible`, `compuerta_grupos_armados`;
columna auxiliar `compuerta_grupos_armados`); cortes en `src/config_pipeline.py`. Validar con
`python src/test_integracion.py` (15 tests, sin GPU). `src/` no importa de `experimentos/`.

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

1. Leer `CLAUDE.md`, este documento, `experimentos/PLAN_5ind_MAX.md` §7–§9,
   `experimentos/PREREG_5ind_MAX.md`, las entradas [2026-09-22] del log y
   `informes/01_…`/`02_…`.
2. Preguntar/confirmar con el usuario la aprobación de la 2a ronda (§5) si su prompt no la trae.
3. Con la aprobación: redactar `experimentos/PREREG_5ind_MAX_r2.md` (sin ejecutar GPU ni jueces),
   commitearlo, revisión única de `orquesta-lead`, aplicar o registrar cada corrección, congelar,
   y **mostrar el pre-registro al usuario antes de puntuar**.
