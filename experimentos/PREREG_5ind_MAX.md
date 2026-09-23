# Pre-registro — 5 indicadores bajo el radar MAX

Fecha: 2026-09-22 · Rama: `hipotesis-5ind-max` · Plan: `experimentos/PLAN_5ind_MAX.md`

**A partir del commit que introduce este archivo (y `hipotesis_5ind_max.py`), nada de §1–§4
cambia.** Toda desviación posterior se registra en `contexto/08_log_decisiones.md` como
desviación, con su motivo.

Agregación por lugar = **MAX**, fija. Solo cambia el score por artículo. Producción = NLI
(`mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`) + regex; el LLM solo juzga, en local.

## 0. Pregunta y refutación

**Pregunta:** ¿existe, para cada uno de los 5 indicadores, una construcción NLI-only del
score por artículo cuyo MAX por lugar lo fije un artículo que de verdad reporta el concepto
(precisión en la cola), sin empeorar el control absurdo?

**Refutación (por indicador):** ninguna variante cumple los 6 criterios de §4 → el
indicador queda como está y se registra el rechazo.

## 1. Codebook del juez (congelado)

| Indicador | SÍ | NO |
|---|---|---|
| `exclusion_beneficios_economicos` | Una comunidad no recibe regalías, compensaciones o beneficios económicos de un proyecto concreto | Falta de servicios, deportaciones, hallazgo de cuerpos, pobreza general |
| `rechazo_proyecto` | Oposición a una obra/proyecto identificable (mina, peaje, parque eólico, hidroeléctrica, relleno, concesión…) | Protestas laborales, bloqueos por agua/luz, asonadas contra militares, paros generales |
| `desplazamiento_forzado` | Personas/familias **ya** abandonaron su territorio por violencia o presión (incluye llegada de desplazados a otra ciudad) | Amenaza o riesgo sin desplazamiento consumado, migración económica/venezolana |
| `conflicto_territorial` | Disputa violenta o armada **y sostenida** por el control, uso o propiedad de un territorio, entre cualesquiera actores | Protestas, bloqueos, amenazas aisladas, conflictividad política o electoral |
| `presencia_grupos_armados` | Guerrillas, disidencias, paramilitares o grupos armados organizados (ELN, FARC-disidencias, EMC, Segunda Marquetalia, Clan del Golfo/AGC/EGC, ACSN, Los Pachenca…) operando en la zona | Combos de Medellín, delincuencia común, bandas de hurto, porte ilegal de armas, sicariato sin grupo armado identificado |

**Premisa que ve el juez = la del NLI:** solo el cuerpo (`texto`), sin título, truncado a
los primeros 480 tokens del tokenizador del modelo NLI (512 − ~32 de la hipótesis más
larga). Decisión del usuario 2026-09-22 (el §3 del plan decía título+texto; producción no
usa el título).

## 2. Corpus

- **Trabajo:** `datos/corpus/df_corpus_5lugares.pkl`, 1.647 URL únicas. Lugares desde
  `experimentos/resultados/juicio_5ind/url_lugares.csv`: Antioquia 494, Maicao 1.101,
  Oicatá 32, **Paraguachón 77** (pkl individual; las 77 están en el combinado, 57 como
  Maicao). Un artículo puede estar en dos lugares.
- **Nacional (F7):** `df_corpus_combinado_32deptos.pkl` + `datos/scores/scores_v2_32deptos.pkl`
  (V2 verificado; unión por posición). Holdout: Cauca, Chocó, Cundinamarca.

## 3. Variantes (todas NLI + regex)

Textos exactos, gemelas y regex: `experimentos/hipotesis_5ind_max.py` (fuente única).
Score atómico `s(h) = clip(clip(ent − sesgo, 0)·(1 − neu), 0, 1)`, `sesgo` = media de las
4 `NULAS_CALIBRACION` (recalculadas en F2 junto al resto). `g` = compuerta F5 (1 si la regex
del indicador aparece en `texto` normalizado sin tildes, 0 si no).

| id | Familia | Score | Gemela absurda (misma operación) |
|---|---|---|---|
| V01 | F1 vigente | `s(vig)` | `s(vig_abs)` |
| V02 | F1 ChatGPT | `s(gpt)` | `s(gpt_abs)` |
| V03 | F1 nuestra | `s(nue)` | `s(nue_abs)` |
| V04 | F4 paráfrasis | `min(s(nue), s(p1), s(p2))` | `min(s(nue_abs), s(p1_abs), s(p2_abs))` |
| V05 | F2 composición | `min(s(A1), s(A2))` | la pieza de `PIEZA_F2_ABS` por su `_abs` |
| V06 | F3 sobre vigente | `clip(s(vig) − max_c s(c), 0, 1)` | `clip(s(vig_abs) − max_c s(c), 0, 1)` |
| V07 | F3 sobre nuestra | `clip(s(nue) − max_c s(c), 0, 1)` | `clip(s(nue_abs) − max_c s(c), 0, 1)` |
| V08 | F5 sobre vigente | `s(vig)·g` | `s(vig_abs)·g` |
| V09 | F5 sobre nuestra | `s(nue)·g` | `s(nue_abs)·g` |
| V10 | F5+F2 | `V05·g` | gemela de V05 · g |
| V11 | F5+F3 | `V07·g` | gemela de V07 · g |
| V12 | F2+F3 | `clip(V05 − max_c s(c), 0, 1)` | `clip(gemela V05 − max_c s(c), 0, 1)` |

Dos controles por variante: **objeto absurdo** (columna de la tabla) y **absurdo total**
(misma operación con `ABSURDO_TOTAL` = "En este territorio hay colonias de osos polares."
en lugar de la hipótesis principal; en F2, en lugar de la pieza gemelada; en F4, en las tres).
Los confusores `c` y la compuerta `g` no se gemelan. Prohibidos en controles: pingüinos,
helio-3, caligrafía, metano (regla 4).

Límites conocidos, declarados de antemano:
- La regex de `rechazo_proyecto` abre en el 41% del corpus (incluye "proyecto de ley",
  "Puerto …"); las demás entre 6% y 13%.
- M6 para V08–V11 de grupos armados es parcialmente circular (la plata es por palabras
  clave y la compuerta también); se reporta, pero en F5 no desempata.

## 4. Métricas y criterio de adopción (congelado)

Referencia: **positivo = SÍ de ambos jueces** (`juez-a` sonnet, `juez-b` opus, ciegos,
orden barajado con semilla 20260922). Cualquier otra combinación = negativo.
Pool (TREC): por indicador × lugar, unión de los top-15 de las 12 variantes (desempate por
URL); cada artículo del pool se juzga una vez para los 5 indicadores. Kappa de Cohen por
indicador; **kappa < 0.4 → "referencia débil": no se adopta nada en ese indicador sin
aviso al usuario.**

Por variante e indicador, sobre los 4 lugares:
- **M1** el artículo que fija el MAX (desempate por URL) es positivo de referencia.
- **M2** precisión@10 por lugar: fracción de positivos en los 10 primeros; media sobre los
  lugares con ≥ 10 artículos con score > 0 (si ninguno cumple, se usa precisión@k con k =
  nº de artículos > 0 y se marca).
- **M3** coherencia del MAX: lugar sin positivos en el pool (del indicador) → MAX < 0.766;
  con positivo → MAX ≥ 0.766. Se cuentan violaciones.
- **M4** MAX por lugar de la gemela de objeto absurdo y del absurdo total; y proporción de
  artículos > 0.766.
- **M5** nº de los 26 indicadores cuyo MAX por lugar lo fija el mismo artículo que el de
  este indicador (los otros 21 con el score V2 vigente). Solo reporte.
- **M6** (solo `presencia_grupos_armados`): AUC contra `silver.py` sobre el corpus de trabajo.

**Una variante reemplaza a la vigente (V01) si cumple TODO:**
1. M2 medio ≥ max(0.60, M2(V01) + 0.20).
2. M1 verdadero en ≥ 3 de los 4 lugares, o en todos los lugares con algún positivo.
3. M3 sin violaciones nuevas respecto a V01.
4. M4: MAX de **ambos** controles < 0.766 en los 4 lugares y ≤ el de V01 + 0.05.
5. M6 (solo grupos armados): AUC ≥ AUC(V01) − 0.02.
6. Holdout (F7): M2 en Cauca/Chocó/Cundinamarca (media) ≥ 0.50 y ≥ la de V01.

Desempate: la más simple (F1 > F5 > F2 > F3 > F4 > cruces); dentro de la misma familia,
mayor M2. Hasta 2 finalistas por indicador pasan a F7 (el mejor que cumple 1–5 y, si
existe, el segundo). Si ninguna pasa, el indicador queda igual y se registra por qué. Si no
hay **ningún** positivo de `exclusion_beneficios_economicos` en el pool ni en el holdout, se
informa al usuario la opción de fusionarlo con `incentivos_economicos_inequitativos` o
retirarlo — decide el usuario.

## 5. Ejecución

- F2 `exp_5ind_max_atomicas.py`: 83 hipótesis únicas (incluye 4 nulas y el absurdo total)
  × 1.647 → `datos/scores/scores_5ind_atomicas_lugares.pkl` con `ent_`, `neu_`, `con_` sin
  enmascarar. Una sola corrida GPU, en segundo plano, con checkpoint.
- F3 `exp_5ind_max_variantes.py`, F5 `exp_5ind_max_metricas.py`: offline sobre el pkl.
- F4 jueces: lotes JSONL de ~40 en `experimentos/resultados/juicio_5ind/lotes/`, etiquetas
  en `…/etiquetas_a/` y `…/etiquetas_b/`.
