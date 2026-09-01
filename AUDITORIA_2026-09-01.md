# Auditoría de consistencia — 2026-09-01 (DSH)

Auditoría en tres capas del worktree `pruebas`: documentación vs código y log,
docstrings/comentarios de `src/` y `experimentos/`, y números citados vs datos reales.
Solo lectura para código; las correcciones de documentación se aplicaron in situ. Los
hallazgos de código quedaron en `.dshwolf/buglog.json` para Claude Code.

Fuente de verdad usada: `contexto/08_log_decisiones.md` y el código real de `src/`.

---

## 1. Correcciones de documentación APLICADAS (por DSH)

| Archivo | Corrección principal |
|---|---|
| `contexto/00_estado_actual.md` | Salvedad de procedencia del +0.067 en las dos menciones; fecha de actualización |
| `contexto/01_objetivo_y_radar.md` | Modelo nulo 28.1%; "Hoy está en +0.067" → +0.42; salvedad +0.067; −0.26 → −0.31; "accuracy en terciles" → cortes fijos; columna oficial no re-tercilada; radar V0 ya no es "actual" |
| `contexto/02_pipeline.md` | Etapa 2 sin pre-filtro (V2, sesgo, fórmula); etapa 3 P75 (ya no MAX ni "aún no aplicado"); etapa 4 cortes fijos + columna oficial; `score_social` fuera del flujo |
| `contexto/03_indicadores.md` | V2 "en producción desde 2026-08-31"; pre-filtro RECHAZADO y retirado (histórico aparte); corrección de "tres indicadores muertos" a escala nacional |
| `contexto/05_scraping.md` | Filtro de relevancia: bug corregido 2026-08-30 (`self.territorio`), fallback histórico; corolario de nombres compuestos |
| `contexto/06_datos.md` | `verificar_contra_produccion_v2()`; baseline_v2 = 38 columnas (no ~35); 27 pares ent_/neu_ (26 + NULA_TEST) en los pkl de scores |
| `contexto/07_backlog.md` | Modelo nulo 28.1%; punto 1 marcado HECHO (vía nli_core) con pendiente re-puntuado desde `src/`; cortes finales 0.2969/0.3527; 15 clases con patrón de timeout; tarea 0 matizada con el +0.42 |
| `contexto/09_riesgos_y_limites.md` | Avance en la discrepancia: V0+MAX recalculado da −0.18 |
| `CLAUDE.md` | Salvedad +0.067; regla 2 "tres veces" (tercer fallo: cortes sobre P75 interpolado); "tres indicadores muertos" → matiz nacional; mapa: ESTADO_DEL_PROYECTO.md existe en `pruebas` |
| `README.md` | "00 a 10"; trampa del filtro corregida; ejemplo de verificación con `_v2()` + baseline_v2 (~5e-7); pre-filtro rechazado; pkl nacional en notas |
| `PROMPT_ARRANQUE.md` | ESTADO_DEL_PROYECTO.md existe en `pruebas` y ya fue sincronizado |
| `ESTADO_DEL_PROYECTO.md` | Refleja V2 en producción: accuracy 25.0% (cortes fijos) / 40.6% (terciles), Spearman +0.42 con salvedad, modelo nulo 28.1%, correcciones aplicadas, "qué falta" actualizado |
| `experimentos/README_experimentos.md` | Verificación `_v2()` + baseline_v2; hipotesis_base como históricas |
| `experimentos/PLAN.md` | Marcado como instantánea histórica completada |
| `experimentos/RESULTADOS.md` | Pendientes 1, 2 y 4 marcados HECHO/RESUELTO; solo el estándar de plata sigue abierto |

Documentos verificados y **correctos** (no tocados): `contexto/08_log_decisiones.md`,
`contexto/10_combinaciones_y_rumbo.md`, `contexto/04_hallazgos_revision_nli.md` (histórico).

---

## 2. Verificación de números contra datos reales (capa 3)

Todas las verificaciones **PASS** (pandas/numpy/scipy, solo lectura, sin GPU ni red):

- `df_corpus_combinado_32deptos.pkl`: 11.439 filas, 6 columnas, 32 departamentos; los 14 conteos citados coinciden.
- `CargadorCorpus.cargar()` replicado: **12.592 artículos y 35 valores de departamento** (confirmado exacto; bloquea el re-puntuado nacional).
- `df_corpus_5lugares.pkl`: 1.647 (Maicao 1.101, Antioquia(2023) 494, Oicatá 32, Paraguachón 20).
- `scores_v2_32deptos.pkl`: 11.439 × 58, sin NaNs, sin enmascarar; **27 pares ent_/neu_** (26 + NULA_TEST).
- Baselines: `df_procesado_baseline_v2.pkl` 1.647 × **38**; los V0 1.647 y 11.439 × 38.
- `comparacion_radares_V3.xlsx`: 32×6; 16 valores citados coinciden; clases oficiales 11 Alto / 11 Bajo / 10 Medio.
- Re-scrapeo: La Guajira 1.553, Norte de Santander 352, Valle del Cauca 145.
- Radar V2 replicado offline: **Spearman +0.4208** (p=0.017) y **Spearman(nº artículos, oficial) −0.3134** — reproducen exactamente lo citado en la documentación.

Los matices encontrados (27 pares en vez de 26, 38 columnas en vez de ~35) eran de
documentación y ya quedaron corregidos en `contexto/06_datos.md`.

---

## 3. Pendientes de CÓDIGO para Claude Code

Registrados en `.dshwolf/buglog.json` (12 entradas). Resumen, en orden sugerido:

1. **[Deuda técnica real]** `src/generar_tablas_por_departamento.py` (líneas 2, 37, 49) todavía usa el pre-filtro social (`score_social >= 0.65`), retirado de producción. **No figura en el inventario de deuda técnica del log 08** (que solo nombra `pipeline_lugares.py` y `generar_max_articulos_por_departamento.py`). Decidir: actualizar a V2 o marcar como legado, y registrarlo en `08_log_decisiones.md`.
2. `src/metricas_y_calculo_de_error.py:5-7` — docstring "terciles directos" (hoy: columna oficial + cortes fijos).
3. `src/pipeline_lugares.py:7,177` — menciona "pre-filtro social 0.65"; contradice su propio comentario correcto en 120-122.
4. `src/orquestador_pipeline.py:335` — "accuracy por terciles" (default usa cortes fijos). Bonus: el módulo no tiene docstring de cabecera; el resumen "LEGADO" del mapa viene del helper `ejecutar_metricas`.
5. `src/test_integracion.py:291` — comentario "accuracy en terciles" obsoleto.
6. `experimentos/nli_core.py:15-17` — docstring apunta a `verificar_contra_produccion()` (legado); vigente es `_v2()`.
7. `experimentos/hipotesis_base.py:2-3` — "como están hoy en producción" (producción es V2).
8. `experimentos/exp_cortes_fijos_v2.py:32-33` — "coincide con el pipeline de producción actual" (falso) y cortes 0.30/0.35 superados.
9. `experimentos/exp_verificar_promocion_v2.py:13` — cita cortes 0.3074/0.3524 (finales: 0.2969/0.3527).
10. `experimentos/exp_smoke_test_produccion_v2.py:22` — función de verificación mal nombrada.
11. `experimentos/exp_correlacion_v2_nacional.py:7` — +0.067 sin salvedad de procedencia.

Ninguno de estos hallazgos es ALTA (no hay código que contradiga la receta V2 en el camino
por defecto); son docstrings/comentarios desactualizados y una deuda técnica real (ítem 1).

---

## 4. Recomendaciones de higiene del repo

- `.gitignore` no ignora `.dshwolf/` ni `AGENTS.md` (aparecen sin trackear). Decidir si se
  versionan a propósito (el buglog y STATUS.md sirven como canal DSH ↔ Claude Code) o se
  agregan al `.gitignore`.
- El resumen del mapa de código de `orquestador_pipeline.py` sale del docstring de un helper
  legado; se arregla solo con el docstring de módulo sugerido en el ítem 4 de la sección 3.

## 5. Reglas respetadas

- No se tocó `src/` ni se corrió GPU, scraping, red ni modelo NLI.
- Las correcciones documentales citan su fuente (`08_log_decisiones.md`) y se fechan
  2026-09-01, siguiendo el estilo de corrección in-place del proyecto.
- No se relitigó nada marcado CERRADO; solo se sincronizó la documentación con esas decisiones.
