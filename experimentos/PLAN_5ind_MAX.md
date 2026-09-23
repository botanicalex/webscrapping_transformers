# Plan — Reformulación de 5 indicadores bajo el radar MAX

Fecha: 2026-09-22 · Autor: Santiago Mendoza (con Claude) · Estado: APROBADO PARA EJECUTAR

## 1. Contexto y restricciones (no negociables)

- **Motivo.** Auditoría externa (ChatGPT, a pedido de la profesora) sobre los Excel
  `radar_resumen_Maicao/Oicatá/Paraguachón.xlsx`: cinco indicadores confunden su concepto
  con cosas vecinas. El problema es real y se ve en los datos (ver §2).
- **Agregación = MAX. No se cambia, no se discute, no se propone alternativa.** Todo el
  trabajo modifica solo el **score por artículo**; la agregación por lugar sigue siendo
  `max()` como en `radar-max_Septiembre`.
- **Rama base:** `radar-max_Septiembre` (la que está en GitHub y se desplegó para Alexa).
- **Producción = solo NLI** (`mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`). Reglas de
  texto (palabras clave) sí se permiten. **Ningún LLM entra a producción**: el LLM solo se
  usa aquí, en local, como juez de evaluación.
- **Sin humano en el lazo.** No hay etiquetado manual; la verdad de referencia la da un
  juez LLM doble y ciego (§6).
- **Alcance:** solo estos 5 indicadores. No generalizar a los otros 21.
- Reglas del `CLAUDE.md` del repo vigentes: 1 (control absurdo obligatorio), 2 (recalibrar
  cortes si cambia lo medido), 3 (absurdo en el formato de la variante), 4 (`NULA_TEST`
  nunca en calibración), 7 (una variable por experimento *dentro de un indicador*),
  8 (no repetir GPU, guardar `ent_`/`neu_` sin enmascarar), 9, 10.

## 2. Diagnóstico ya medido (sin GPU, sobre `resultados/tablas_lugares_max/df_procesado_5lugares.pkl`)

- Con MAX el indicador vale **lo que puntúa un solo artículo**. Un falso positivo entre
  1.101 artículos (Maicao) satura el indicador a ~99.
- Los falsos positivos que fijan el MAX tienen **`sesgo = 0.00`**: no son artículos
  "sí-decidores", son **vecinos semánticos** (textos densos en conflicto/comunidad/protesta).
  La calibración con nulas absurdas no los toca.
- Un mismo artículo es el MAX de muchos indicadores: "Nueva asonada en Antioquia" (8),
  "Tensión del lado venezolano…" (7 en Paraguachón), "Peaje gratis en Tuta" (6 en Oicatá).
- Ejemplos: exclusión beneficios Oicatá 99 = "Unidad de Búsqueda recuperó diez cuerpos en
  el cementerio"; rechazo proyecto Antioquia = protesta laboral del Hospital San Rafael;
  grupos armados Maicao = "hombre asesinado a tiros", "porte ilegal de arma".
- Exclusión beneficios >0.9 en 46/494 artículos de Antioquia y 101/1.101 de Maicao.
- **Consecuencia de diseño:** bajo MAX cada indicador debe comportarse como un
  **detector de alta precisión en la cola** ("¿existe al menos un artículo que de verdad
  reporte X?"). Precisión arriba > AUC global.
- El rechazo del 2026-09-08 (`08_log_decisiones.md`) tuvo fallas de método que justifican
  reabrir (evidencia nueva, regla 10): comparó la vieja contra "osos polares" y la nueva
  contra "pingüinos" (contenidos absurdos distintos, viola regla 3); usó pingüinos, que
  están en `NULAS_CALIBRACION`; n_pos = 2 y 0; métrica = media (no MAX); solo Antioquia.

## 3. Definiciones (codebook del juez — CONGELADO)

| Indicador | SÍ | NO |
|---|---|---|
| `exclusion_beneficios_economicos` | Una comunidad no recibe regalías, compensaciones o beneficios económicos de un proyecto concreto | Falta de servicios, deportaciones, hallazgo de cuerpos, pobreza general |
| `rechazo_proyecto` | Oposición a una obra/proyecto identificable (mina, peaje, parque eólico, hidroeléctrica, relleno, concesión…) | Protestas laborales, bloqueos por agua/luz, asonadas contra militares, paros generales |
| `desplazamiento_forzado` | Personas/familias **ya** abandonaron su territorio por violencia o presión (incluye llegada de desplazados a otra ciudad) | Amenaza o riesgo sin desplazamiento consumado, migración económica/venezolana |
| `conflicto_territorial` | Disputa violenta o armada **y sostenida** por el control, uso o propiedad de un territorio, entre cualesquiera actores (grupos armados entre sí, indígenas vs. colonos, etc.) | Protestas, bloqueos, amenazas aisladas, conflictividad política o electoral |
| `presencia_grupos_armados` | Guerrillas, disidencias, paramilitares o grupos armados organizados (ELN, FARC-disidencias, EMC, Segunda Marquetalia, Clan del Golfo/AGC/EGC, ACSN/Autodefensas Conquistadoras, Los Pachenca…) operando en la zona | **Combos de Medellín**, delincuencia común, bandas de hurto, porte ilegal de armas, sicariato sin grupo armado identificado |

El juez ve **exactamente la premisa que ve el NLI** (título + texto, truncado como en
`Transformer_optimo.py`, `max_length=512`), no el artículo completo.

## 4. Corpus

- **Corpus de trabajo (lugares):** Antioquia 2023 (494) + Maicao (1.101) + Oicatá (32) +
  **Paraguachón = pkl individual (77)**, porque es el corpus que vio la profesora y el
  reparto Maicao/Paraguachón del combinado lo decidió el orden alfabético. Se puntúa
  deduplicado por URL (~1.704 artículos únicos) y se guarda una tabla `url → lugares`
  (un artículo puede pertenecer a dos lugares).
- **Corpus nacional:** `datos/corpus/df_corpus_combinado_32deptos.pkl` (11.439), para la
  fase 7 (holdout + recalibración de cortes).
- **Holdout de sobreajuste (fijo, anclas de `contexto/09_riesgos_y_limites.md`):**
  **Cauca y Chocó** ("nunca Bajo", ricos en conflicto → positivos de grupos armados,
  desplazamiento, conflicto territorial) y **Cundinamarca** ("nunca Alto", mucha protesta
  urbana → negativos difíciles). Se excluye Boyacá por solaparse con Oicatá, y Antioquia y
  La Guajira por ser el conjunto de diseño.

## 5. Espacio de variantes (familias; todas NLI-only)

Score atómico por hipótesis = fórmula V2 vigente `clip(clip(ent − sesgo, 0)·(1 − neu), 0, 1)`
con el `sesgo` de las 4 `NULAS_CALIBRACION`. Las familias combinan scores atómicos
**offline**; nada de esto toca la agregación (MAX sigue igual).

| Familia | Construcción | Parámetros |
|---|---|---|
| F1 Frase única | `s(h)` | vigente, ChatGPT, nuestra |
| F2 Composición Y | `min(s(A1), s(A2))` | dos frases cortas atómicas |
| F3 Resta de confusores | `clip(s(h) − max_c s(c), 0, 1)` | λ = 1 fijo (no se ajusta) |
| F4 Acuerdo de paráfrasis | `min(s(p1), s(p2), s(p3))` | 3 redacciones equivalentes |
| F5 Compuerta léxica | `s(h) · 1[regex de palabras clave en la premisa]` | lista fija por indicador |
| Cruces | solo pares F5+F2, F5+F3, F2+F3 | máx. ~12 variantes por indicador |

### Hipótesis atómicas iniciales (se pueden pulir en la Fase 2, se congelan antes de la Fase 3)

**exclusion_beneficios_economicos**
- vigente: "Una comunidad quedó excluida de los beneficios económicos de un proyecto."
- ChatGPT: "Una comunidad no recibió beneficios, regalías o compensaciones de un proyecto."
- nuestra: "Una comunidad reclama regalías o compensaciones que no recibió."
- paráfrasis: "Una comunidad denuncia que no le pagaron las compensaciones de un proyecto." / "Los beneficios económicos de un proyecto no llegaron a la comunidad."
- F2: A1 "Un proyecto genera regalías o compensaciones." · A2 "Una comunidad reclama dinero que no ha recibido."
- F3 confusores: "Hay población sin acceso a servicios básicos." · "Se deportó o expulsó a una persona." · "Se encontraron cuerpos de personas desaparecidas."
- F5 regex: `regal[ií]a|compensaci|indemniz|contraprestaci|beneficios? econ|inversi[oó]n social|empleo local`

**rechazo_proyecto**
- vigente: "Hay oposición de comunidades o autoridades a un proyecto."
- ChatGPT: "Una comunidad se opuso a la ejecución de un proyecto específico."
- nuestra: "Una comunidad se opone a una obra o proyecto minero, energético o vial."
- paráfrasis: "Habitantes rechazan la construcción de una obra." / "Una comunidad protesta contra un proyecto minero o energético."
- F2: A1 "Hay oposición comunitaria." · A2 "Se discute un proyecto minero, energético o de infraestructura."
- F3 confusores: "Hubo una protesta por falta de servicios públicos." · "Trabajadores protestaron por sus condiciones laborales." · "Una comunidad expulsó a militares o policías."
- F5 regex: `proyecto|obra|miner[ií]a|\bmina\b|e[oó]lic|hidroel[eé]ctric|represa|relleno sanitario|peaje|concesi[oó]n|licencia ambiental|exploraci[oó]n|fracking|puerto` (NO incluir "vía": "bloquea la vía" es el confusor típico)

**desplazamiento_forzado**
- vigente: "Hubo un desplazamiento forzado o éxodo de comunidades."
- ChatGPT: "Personas o comunidades fueron obligadas a abandonar su territorio."
- nuestra: "Familias huyeron de su territorio por la violencia."
- paráfrasis: "Hubo familias desplazadas por el conflicto armado." / "Personas abandonaron sus hogares por amenazas de grupos armados."
- F2: A1 "Personas abandonaron sus hogares." · A2 "Hubo violencia o amenazas de grupos armados."
- F3 confusores: "Hay riesgo o amenaza de desplazamiento." · "Llegaron migrantes venezolanos." · "Hubo amenazas contra personas."
- F5 regex: `desplaz|huy(eron|endo)|hu[ií]r|[eé]xodo|abandonar(on)? sus (casas|hogares|tierras|veredas)`

**conflicto_territorial**
- vigente: "Hay una disputa por el control, el uso o la propiedad de un territorio."
- ChatGPT: "Dos o más actores disputan el control, uso o propiedad de un territorio."
- nuestra: "Hay enfrentamientos violentos por el control de un territorio."
- paráfrasis: "Grupos armados se disputan el control de un territorio." / "Dos grupos se enfrentan con armas por unas tierras."
- F2: A1 "Hay enfrentamientos armados o violentos." · A2 "Dos grupos se disputan un territorio."
- F3 confusores: "Hubo una protesta o un bloqueo de vías." · "Hubo amenazas contra una persona." · "Hay un debate político o electoral."
- F5 regex: `disput|enfrentamient|combate|control territorial|invasi[oó]n de (tierras|predios)|lindero|guerra entre|confrontaci`

**presencia_grupos_armados** (único con estándar de plata: `experimentos/silver.py`)
- vigente: "En este territorio hay presencia de grupos armados ilegales."
- ChatGPT: "Un grupo armado ilegal identificado opera en este territorio."
- nuestra: "En este territorio operan guerrillas, disidencias o grupos paramilitares."
- paráfrasis: "El ELN, las disidencias o el Clan del Golfo tienen presencia en esta zona." / "Hay presencia de guerrilla o paramilitares en este territorio."
- F2: A1 = vigente · A2 "Hay un conflicto armado en este territorio."
- F3 confusores: "Hubo un homicidio o un robo." · "La policía capturó a una persona por porte ilegal de armas." · "Una banda delincuencial cometió hurtos."
- F5 regex: `\bELN\b|FARC|disidencia|Clan del Golfo|\bAGC\b|\bEGC\b|Autodefensas|\bACSN\b|Pachenca|paramilitar|guerrill|Segunda Marquetalia|Estado Mayor Central|\bEMC\b|frente \w+` (sin "combo", "banda", "Los Costeños", "Tren de Aragua")

### Controles absurdos (regla 3 y 4)
- Contenido absurdo único para **todas** las variantes: **osos polares** (`NULA_TEST`
  reservada). **Prohibido pingüinos, helio-3, caligrafía, metano** (están en calibración).
- Por cada variante se escribe su **gemela absurda en el mismo formato**, dos tipos:
  - *absurdo total*: "En este territorio hay colonias de osos polares." (y su versión en el formato de cada variante);
  - *objeto absurdo*: la frase real con el objeto reemplazado (p. ej. "Una comunidad se opone a una obra de cría de osos polares."). Para F2 se reemplaza una pieza; para F3/F4/F5 se aplica la misma operación sobre las gemelas.
- Se mide como **MAX por lugar** (lo que ve el radar) y como proporción > 0.766.

## 6. Juez LLM (solo evaluación, local)

- **Pooling (TREC):** por indicador × lugar, unión de los top-15 de todas las variantes →
  conjunto de artículos únicos. Cada artículo se juzga **una vez para los 5 indicadores**
  (ahorra tokens).
- **Dos jueces independientes y ciegos** (no ven variante, score ni orden original; orden
  barajado con semilla fija):
  - Juez A: subagente `juez-a` — modelo **sonnet**, esfuerzo bajo.
  - Juez B: subagente `juez-b` — modelo **opus**, esfuerzo bajo.
  - Definidos en `.claude/agents/` con el codebook de §3 embebido. Leen lotes JSONL de
    disco (~40 artículos por lote), escriben etiquetas JSONL a disco y devuelven **solo**
    "lote N listo, k artículos" (nada de texto largo al orquestador).
- Salida por artículo × indicador: `SI | NO | DUDOSO` + cita de ≤ 20 palabras.
- **Positivo de referencia = SI de ambos jueces.** Cualquier otra combinación = negativo.
  Se reporta el acuerdo (kappa de Cohen) por indicador; si kappa < 0.4 en un indicador,
  ese indicador se marca "referencia débil" y no se adopta nada en él sin aviso al usuario.

## 7. Métricas y criterio de adopción (CONGELADO antes de la Fase 3)

Por variante e indicador, sobre los 4 lugares:

- **M1** Top-1 verdadero: ¿el artículo que fija el MAX es positivo de referencia?
- **M2** Precisión@10 por lugar (media de lugares con ≥ 10 artículos puntuados > 0).
- **M3** Coherencia del MAX: en lugares **sin** ningún positivo en el pool → MAX < 0.766;
  en lugares **con** positivo → MAX ≥ 0.766.
- **M4** Control absurdo como MAX por lugar (misma gemela de osos polares para vieja y nueva).
- **M5** Diferenciación: nº de indicadores (de los 26) cuyo MAX es el mismo artículo.
- **M6** Solo `presencia_grupos_armados`: AUC contra plata.

**Una variante reemplaza a la vigente si cumple TODO:**
1. M2 medio ≥ max(0.60, vigente + 0.20).
2. M1 verdadero en ≥ 3 de los 4 lugares, o en todos los lugares que tienen algún positivo.
3. M3 sin violaciones nuevas respecto a la vigente.
4. M4: MAX absurdo < 0.766 en los 4 lugares y ≤ vigente + 0.05.
5. M6 (solo grupos armados): AUC ≥ vigente − 0.02.
6. Holdout (Fase 7): M2 en Cauca/Chocó/Cundinamarca ≥ 0.50 y ≥ vigente.

Desempate: la más simple (F1 > F5 > F2 > F3 > F4 > cruces). Si ninguna pasa, el
indicador queda como está y se registra el porqué. Si el pool no contiene **ningún**
positivo de `exclusion_beneficios_economicos` en ningún lugar ni en el holdout, se
reporta al usuario la opción de fusionarlo con `incentivos_economicos_inequitativos` o
retirarlo — **decide el usuario**.

## 8. Fases

**F0 — Preparación (sin GPU).**
- En el worktree `pruebas/` (hoy en `radar-max_Septiembre`, limpio salvo `Presentacion/`
  sin trackear): `git switch -c hipotesis-5ind-max`.
- `git cherry-pick a9c84a0 2a0a01d` (de `prueba_radar_max`: restaura `experimentos/`,
  `nli_core.py`, `silver.py`, el skill `experimento-hipotesis` y el registro del rechazo).
  Resolver conflictos a favor de MAX en `src/`.
- Copiar este plan a `experimentos/PLAN_5ind_MAX.md` y commitearlo.
- Verificar: `verificar_contra_produccion_v2()` OK (max|dif| < 1e-4) y
  `python src/test_integracion.py` verde.
- Construir el corpus de trabajo (§4) y reproducir el MAX actual de los 5 indicadores por
  lugar; comparar con los Excel de la profesora (esperar coincidencia salvo Paraguachón si
  difiere de corpus). Documentar cualquier diferencia.
- Verificar qué contiene `datos/scores/df_procesado_32deptos.pkl` (¿V2 corregido? ¿columna
  `sesgo`?) para saber si la Fase 7 puede reutilizar los 21 indicadores no tocados.

**F1 — Pre-registro.** Escribir `experimentos/PREREG_5ind_MAX.md` con §3, §5 (lista final
de hipótesis, regex y gemelas absurdas), §7. Commit. Pedir revisión **una vez** al
subagente `orquesta-lead` ("¿contradice algo cerrado en el log? ¿el criterio es refutable?").
Aplicar sus correcciones. **A partir del commit de pre-registro, nada de §3/§5/§7 cambia.**

**F2 — Script de puntuación** `experimentos/exp_5ind_max_atomicas.py`: puntúa todas las
hipótesis atómicas + 4 nulas de calibración + gemelas absurdas sobre el corpus de trabajo;
guarda `ent_`, `neu_`, `con_` sin enmascarar en
`datos/scores/scores_5ind_atomicas_lugares.pkl` (regla 8). Estimado ~80 hipótesis ×
~1.704 artículos ≈ 2 h GPU. **Correr en segundo plano.**

**F3 — Construcción offline de variantes** (sin GPU) `experimentos/exp_5ind_max_variantes.py`:
familias F1–F5 + cruces, MAX por lugar, top-15 por variante × indicador × lugar.

**F4 — Pool y juicio.** Armar lotes JSONL de artículos únicos del pool
(`experimentos/resultados/juicio_5ind/lotes/`), lanzar `juez-a` y `juez-b` en paralelo por
lotes, consolidar etiquetas, kappa.

**F5 — Métricas y selección** `experimentos/exp_5ind_max_metricas.py`: M1–M6, aplicar el
criterio de §7, elegir ≤ 2 finalistas por indicador. Tabla en
`experimentos/RESULTADOS_5ind_MAX.md`.

**F6 — Informe intermedio al usuario.** Parar y mostrar: tabla por indicador (vigente vs
finalistas), ejemplos de artículos que cambian de top, y la estimación de GPU de la Fase 7.
**Esperar visto bueno antes de la corrida nacional.**

**F7 — Nacional (tras visto bueno).** Puntuar sobre los 11.439 artículos solo las hipótesis
atómicas de los finalistas (+ sus confusores/piezas y gemelas absurdas) → pkl sin
enmascarar. Luego:
- Holdout: pool + juicio sobre Cauca, Chocó, Cundinamarca; criterio 6 de §7.
- Recalibrar `CORTE_BAJO_MEDIO_RADAR` / `CORTE_MEDIO_ALTO_RADAR` con el procedimiento de
  `b060b3b` (huecos naturales > 0.008 sobre la distribución nacional MAX, sin mirar el
  oficial), verificar que **ninguna de las 12 anclas** se rompa; accuracy y Spearman solo
  como constancia.

**F8 — Promoción y registro.**
- Solo para los indicadores que pasaron: actualizar hipótesis en `src/Transformer_optimo.py`
  (y, si la ganadora es F2/F3/F4/F5, la lógica mínima en `procesar()` — sigue siendo NLI +
  regex), cortes en `src/config_pipeline.py`, `test_integracion.py` verde.
- Entradas en `contexto/08_log_decisiones.md` (adopciones **y** rechazos, con evidencia),
  actualizar `ESTADO_DEL_PROYECTO.md` y `explicacion_alexa.md` si cambia algo visible.
- Regenerar los 3 Excel de lugares con el formato de los de la profesora (antes/después).
- Revisión final **una vez** con `orquesta-lead`.
- **No hacer push ni merge a `radar-max_Septiembre` sin aprobación explícita del usuario.**

## 9. Economía de tokens (obligatorio)

- Orquestador (conversación principal): **Opus 5.5, esfuerzo medio**. Escribe los scripts
  él mismo; no delega código a subagentes.
- Subagentes solo para: `orquesta-lead` (2 llamadas en total: F1 y F8) y jueces (F4, F7).
- Jueces: **sonnet + opus en esfuerzo bajo**, lotes de ~40 artículos, premisa truncada,
  respuesta al orquestador de una línea. Todo el detalle va a disco.
- Nada de subagentes Explore/general-purpose para leer el repo: el contexto necesario está
  en este plan y en `CLAUDE.md`.
- No volcar dataframes grandes a la conversación: imprimir resúmenes (≤ 40 líneas).
- GPU una sola vez por corpus (F2 lugares, F7 nacional). Todo lo demás, offline sobre pkl.

## 10. Entregables

1. `datos/scores/scores_5ind_atomicas_lugares.pkl` y `…_nacional.pkl` (sin enmascarar).
2. `experimentos/PREREG_5ind_MAX.md`, `experimentos/RESULTADOS_5ind_MAX.md`.
3. Etiquetas del juez en `experimentos/resultados/juicio_5ind/`.
4. Entradas en `contexto/08_log_decisiones.md`.
5. Excel de lugares regenerados (antes/después) para mostrar a la profesora.
6. Rama `hipotesis-5ind-max` con commits locales, lista para revisión del usuario.
