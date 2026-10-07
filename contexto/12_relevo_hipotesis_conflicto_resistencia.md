# Relevo 12 — Optimizar las hipótesis de `conflicto_territorial` y `resistencia_territorial`

Fecha: 2026-10-07. Worktree `pruebas`, rama local **`radar-18ind`** (commit `f4b2719`, sin push). Leer entero
antes de actuar. Este archivo es el ancla de una conversación nueva cuyo papel es **orquestador científico**.

## 1. Misión

Encontrar, para cada uno de los dos indicadores, **una frase (hipótesis NLI) que muestre avance** sobre la
situación actual: que pase el control absurdo y que distinga departamentos, conservando la **intención del jefe**.
No se busca la frase perfecta: lluvia de propuestas → cribado rápido → finalistas → validación → recomendación.

- **Decidido por el usuario (2026-10-07):** `zonas_proteccion_alimentaria` se queda con la frase nueva del jefe
  («El territorio tiene una figura de protección especial para la producción de alimentos.»). **No se toca.**
- Los otros 16 indicadores tampoco se tocan. Solo estos dos.

## 2. Situación de partida (números medidos)

Fuente: `experimentos/resultados/exp_hipotesis_jefe_18ind.csv` (corpus nacional, 32 deptos, 11.439 arts) y
`experimentos/resultados/exp_retiro_2ind_cortes.csv`. Nula = contenido absurdo de `V2.NULA_TEST` (colonias de osos
polares) escrito **en el mismo formato** que la frase.

| Indicador | Frase | Nula cruda >0.9 | Nula corregida media | Brecha real−nula (MAX por depto, media) | MAX por depto mín/med/máx |
|---|---|---|---|---|---|
| conflicto | V2: «Hay una disputa por el control, el uso o la propiedad de un territorio.» | 5.7 % | 0.020 | **0.520** | 0.702 / 0.989 / 0.998 |
| conflicto | Jefe: «Dos o más actores disputan el control, uso o propiedad de un territorio.» (**hoy en `src/`**) | **78.7 %** | 0.517 | **0.005** | 0.909 / 0.996 / 0.998 |
| resistencia | V2: «Hay resistencia comunitaria en defensa del territorio o el medio ambiente.» | 5.7 % | 0.020 | **0.347** | 0.000 / 0.822 / 0.992 |
| resistencia | Jefe: «Una comunidad realiza acciones para defender su territorio frente a proyectos, intervenciones o decisiones externas.» (**hoy en `src/`**) | **44.8 %** | 0.313 | **0.041** | 0.948 / 0.996 / 0.999 |

Lectura: las frases del jefe **saturan**: el modelo afirma la *estructura* (actor + verbo de acción + territorio)
sea cual sea el contenido; suman una constante ≈0.99 a todos los departamentos. Ejemplos reales
(`experimentos/resultados/tabla_antioquia_lugares_18ind.md`): en Oicatá conflicto=0.975 por un choque de un camión
de gas; en Paraguachón resistencia pasa de 0.000 a 0.995 por «Migración Colombia expulsa a venezolana…».

**Ojo:** V2 de conflicto también roza la saturación (mediana 0.989) aunque pasa el control. «Avance» no es
volver a V2: es acercarse a la intención del jefe sin saturar.

**Intención del jefe** (lo que la frase debe capturar):
- conflicto: **disputa entre actores** identificables (dos o más) por control/uso/propiedad de tierra o territorio.
- resistencia: **una comunidad actúa** para defender su territorio **frente a algo externo** (proyecto,
  intervención, decisión).

## 3. Reglas duras que aplican (de `CLAUDE.md`; no se negocian)

1. **Control absurdo obligatorio** y con nula **en el mismo formato** que cada candidata (reglas 1 y 3). Mismo
   contenido absurdo siempre (osos polares) para que todo sea comparable.
2. **Solo cambia la frase** (regla 15). Prohibido: compuertas de palabras, `min` de varias frases, restas de
   confusores, columnas nuevas, listas nuevas de pre-filtro (etapa 2 CERRADA).
3. `NULA_TEST` **jamás** entra en el sesgo; el sesgo es la columna `sesgo` de producción (regla 4).
4. **No repetir GPU** (regla 8): guardar `ent_`/`neu_` sin enmascarar en pkl **nuevos** (no sobrescribir), y todo
   análisis posterior sobre el pkl.
5. `src/` es producción: solo se toca al promover, con aprobación del usuario (regla 9). Todo, incluidos los
   rechazos, al log `contexto/08_log_decisiones.md` (reglas 10 y 14).
6. Sin push ni merge. Commits locales sí, en `radar-18ind`, con la línea
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
7. Regla del usuario: **economía de tokens**; subagentes con encargos pequeños y archivos disjuntos.

## 4. Cómo medir sin estándar de plata

No hay plata para estos indicadores (`hipotesis_base.KEYWORDS_SILVER` solo cubre grupos armados y étnicos): **el AUC
no es medible**. Se mide con tres cosas:

- **Control absurdo (puertas, fijadas en `experimentos/exp_hipotesis_jefe_18ind.py`, función `analizar()`):**
  P1 `prop(nula cruda > 0.9) ≤ 5 %` y `media(nula corregida) ≤ 0.10`; P2 no peor que V2; P3 brecha media real−nula
  ≥ la de V2 (0.520 conflicto, 0.347 resistencia).
- **Discriminación:** dispersión del MAX por departamento (IQR y mín/mediana/máx). Saturada = mediana ≥ 0.98 con
  IQR pequeño. Se quiere dispersión.
- **Precisión por jueces (proxy de plata):** subagentes juzgan si el artículo top de cada departamento (o una
  muestra estratificada por score) cumple de verdad la intención del jefe. Precedente con dos jueces
  independientes y kappa: `experimentos/exp_5ind_max_juicio.py` y `experimentos/resultados/juicio_prefiltro_e2_t2/`
  (`lotes/`, `etiquetas_*`, `consolidacion.csv`). Premisa que ve el juez = premisa visible recortada
  (`premisa_visible` de `src/Transformer_optimo.py`).

El control autoriza a **rechazar**, nunca a adoptar solo; la recomendación final combina las tres.

## 5. Herramientas y datos ya disponibles (reutilizar, no reescribir)

- Scoring: `experimentos/nli_core.py` → `NLIScorer().score(premisas, hipotesis, devolver_todo=True)`; verificación
  bloqueante `verificar_contra_produccion_v2(s, "datos/scores/df_procesado_baseline_v2.pkl", "presencia_grupos_armados", V2.TODAS["presencia_grupos_armados"])`
  (dio 9.77e-07 el 2026-10-06).
- Plantilla de experimento completa: `experimentos/exp_hipotesis_jefe_18ind.py` (puntuar + `analizar()` con P1–P3;
  `NULAS_NUEVAS` muestra cómo escribir la nula del mismo formato).
- Datos: `datos/corpus/df_corpus_combinado_32deptos.pkl` + `datos/scores/scores_v2_32deptos.pkl` (mismo orden; V2 y
  `sesgo`); `datos/scores/scores_hipotesis_jefe_18ind.pkl` (frases del jefe + sus nulas, nacional y lugares);
  `datos/corpus/df_corpus_5lugares.pkl`.
- Después de elegir: `experimentos/exp_retiro_2ind_cortes.py` (recalibra cortes, sanidad 0.7138/0.905 con 20) y
  `experimentos/exp_tabla_antioquia_lugares_18ind.py` (tabla Antioquia + Paraguachón, Maicao, Güintiva, Oicatá, que
  es **lo que el jefe siempre pide**).
- Skill `.claude/skills/experimento-hipotesis/SKILL.md` (ciclo y trampas). Leerlo.

## 6. Restricción física: UNA sola GPU (RTX 4050)

Costo medido: un par (frase + su nula) sobre el nacional completo ≈ **19 min**. Los subagentes **no pueden usar la
GPU a la vez**. Diseño obligatorio:

- **Una sola cola de GPU**: un script que recibe una lista de candidatas y las puntúa en serie, **guardando cada
  candidata en cuanto termina** (lección del 2026-10-06: el script que guardaba solo al final obligó a esperar).
- **Cribado sobre submuestra fija**: muestra estratificada por departamento del nacional (p. ej. 1.500 arts, semilla
  fija, guardada en `experimentos/resultados/`), ≈ 2–3 min por par. Solo los finalistas (≤ 3 por indicador) van al
  nacional completo + lugares.
- Todo lo demás (ideación, análisis, jueces, redacción) es CPU y **sí se paraleliza** con subagentes.

## 7. Protocolo del orquestador (sugerido)

Fase 0. Leer este archivo, `CLAUDE.md`, el skill y `git log -3`. Correr la verificación bloqueante.
Fase 1. **Lluvia de ideas** (2 subagentes en paralelo, uno por indicador): 12–20 candidatas cada uno, organizadas por
  **ejes mecanísticos**, cada candidata con su nula del mismo formato. Ejes a explorar (no exhaustivo):
  - forma existencial corta («Hay …», la que funcionó en V2) frente a actor + verbo;
  - qué ancla el contenido: objeto concreto (tierra, predio, resguardo, baldío; consulta previa, bloqueo, minga,
    plantón) frente a abstracto («territorio», «acciones»);
  - quitar disyunciones genéricas («proyectos, intervenciones o decisiones») frente a conservar las sustantivas;
  - nombrar a los actores (comunidad indígena/campesina, empresa, grupo armado, Estado) frente a «actores»;
  - longitud (~10 tokens, XNLI) y sin marco metalingüístico ni «explícitamente».
  Pre-registrar en `experimentos/PREREG_hipotesis_conflicto_resistencia.md` las candidatas y los criterios **antes**
  de ver números (regla de la casa).
Fase 2. **Cribado en GPU** (un subagente dueño de la cola): todas las candidatas + nulas sobre la submuestra.
Fase 3. **Análisis** (subagente CPU): P1–P3 + dispersión en la submuestra; ranking; descartes registrados.
Fase 4. **Jueces** (2 subagentes independientes por indicador) sobre los artículos top de las 3–5 mejores; kappa.
Fase 5. **Finalistas** (≤ 3 por indicador) al nacional completo y lugares (cola de GPU), análisis completo.
Fase 6. Recomendación al usuario con tabla corta. **Si el usuario aprueba**: cambiar la frase en
  `src/Transformer_optimo.py`, recalibrar cortes, tabla Antioquia + lugares, `test_integracion` 16/16, log
  `[fecha]`, informe 16 (`informes/`, + fila en `informes/README.md`), commit local.

Iterar fases 1–3 si ninguna candidata pasa P1: la segunda ronda se diseña a partir del patrón de la primera.

## 8. Encargo tipo para un subagente (plantilla)

> Worktree `pruebas`, rama `radar-18ind`. Español. Lee `contexto/12_relevo_hipotesis_conflicto_resistencia.md`
> §3–§6. TAREA ÚNICA: <…>. Archivos que puedes crear/editar: <lista>. PROHIBIDO: git add/commit/push/stash, tocar
> `src/`, otros archivos, la GPU (salvo si eres el dueño de la cola). Entrega breve: <qué números/archivos>.

Modelo recomendado para subagentes: Sonnet. Máximo ~4 en paralelo. El orquestador verifica cada entrega
(re-leer números en los archivos de salida) antes de pasar de fase.
