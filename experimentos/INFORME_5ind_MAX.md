# Informe — Reformulación de 5 indicadores del radar bajo agregación MAX

Fecha: 2026-09-22 · Rama: `hipotesis-5ind-max` (desde `radar-max_Septiembre`) · Estado: fases 0–8
cerradas. V08 de `presencia_grupos_armados` adoptada y promovida a `src/` (commits locales, sin
push ni merge). Los otros 4 indicadores, pendientes de una segunda ronda.

Documentos fuente: plan `experimentos/PLAN_5ind_MAX.md`, pre-registro
`experimentos/PREREG_5ind_MAX.md`, tablas `experimentos/RESULTADOS_5ind_MAX.md`, registro de
decisiones `contexto/08_log_decisiones.md` (entradas del 2026-09-22).

---

## 1. Por qué se hizo

Una auditoría externa de los Excel de lugares (Maicao, Oicatá, Paraguachón) señaló que cinco
indicadores confunden su concepto con temas vecinos. El problema se verificó en los datos:

- Con agregación **MAX**, el valor de un indicador en un lugar es el de **un solo artículo**.
  Basta un falso positivo entre 1.101 artículos para que el indicador marque ~0.99.
- Los artículos que fijaban esos máximos no eran artículos "que dicen sí a todo" (su sesgo
  calibrado era 0): eran **vecinos semánticos**, textos densos en conflicto, comunidad o
  protesta. Ejemplos: "Unidad de Búsqueda recuperó diez cuerpos" como máximo de *exclusión
  de beneficios económicos*; una protesta laboral de un hospital como máximo de *rechazo a
  proyecto*; "hombre asesinado a tiros" como máximo de *presencia de grupos armados*.

Por eso, bajo MAX, cada indicador tiene que funcionar como un **detector de alta precisión en
la cola**: lo que importa es que el artículo con mayor puntaje de verdad reporte el concepto.
La precisión en la cola pesa más que el AUC global.

Indicadores estudiados: `exclusion_beneficios_economicos`, `rechazo_proyecto`,
`desplazamiento_forzado`, `conflicto_territorial`, `presencia_grupos_armados`.

## 2. Restricciones del diseño (fijadas antes de empezar)

| Restricción | Detalle |
|---|---|
| Agregación | **MAX** por lugar, sin cambios. Solo se modifica el score de cada artículo. |
| Producción | Solo NLI (`mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`) más reglas de palabras clave. **Ningún LLM entra a producción.** |
| Referencia | Sin etiquetado humano. La "verdad" la dan **dos jueces LLM independientes y ciegos**, solo en evaluación local. |
| Alcance | Solo los 5 indicadores; los otros 21 no se tocan. |
| Reglas del proyecto | Control absurdo obligatorio (regla 1); recalibrar cortes si cambia lo medido (2); absurdo en el formato de la variante (3); la nula de prueba nunca en calibración (4); no repetir GPU, guardar `ent_`/`neu_` sin enmascarar (8); toda decisión al log (10). |
| Pre-registro | Hipótesis, gemelas absurdas, regex, métricas y criterio se congelaron **antes** de ver resultados (commit `6dc6ef5`). |

## 3. Datos

- **Corpus de trabajo:** `datos/corpus/df_corpus_5lugares.pkl`, **1.647 artículos únicos**.
  Lugares: Antioquia 2023 (494), Maicao (1.101), Oicatá (32) y Paraguachón (77, el corpus que
  vio la profesora; 57 de esos artículos también son de Maicao). Tabla `url → lugar` en
  `experimentos/resultados/juicio_5ind/url_lugares.csv`.
- **Premisa:** la misma que usa producción, **solo el cuerpo** del artículo (sin título),
  truncado a lo que cabe en 512 tokens junto a la hipótesis. El 77% de los artículos es más
  largo, así que el modelo ve solo el comienzo. El juez ve exactamente ese mismo texto
  (decisión del usuario).
- **Corpus nacional (fase 7):** `df_corpus_combinado_32deptos.pkl` (11.439 artículos) y
  `datos/scores/scores_v2_32deptos.pkl`, los scores V2 nacionales ya calculados. Estaban fuera
  del repo; se verificaron re-puntuando 300 artículos en GPU (diferencia ≤ 3e-05).

## 4. Qué se probó: 12 variantes por indicador

Todas son NLI + reglas. El score atómico de una hipótesis `h` es la fórmula vigente de
producción:

`s(h) = clip( clip(ent − sesgo, 0) · (1 − neutral), 0, 1 )`

donde `sesgo` es la media del entailment de 4 hipótesis nulas absurdas (pingüinos, helio-3,
caligrafía japonesa, metano líquido), que mide cuánto "dice sí" cada artículo a cualquier cosa.

Las variantes combinan scores atómicos (offline, sin nueva GPU):

| Id | Familia | Construcción | Idea |
|---|---|---|---|
| V01 | F1 | `s(vigente)` | Línea base: la hipótesis de producción |
| V02 | F1 | `s(redacción de la auditoría)` | Frase propuesta por la auditoría externa |
| V03 | F1 | `s(redacción propia)` | Frase más concreta |
| V04 | F4 Acuerdo de paráfrasis | `min(s(propia), s(p1), s(p2))` | Solo puntúa alto si tres redacciones equivalentes coinciden |
| V05 | F2 Composición "Y" | `min(s(A1), s(A2))` | El concepto partido en dos piezas cortas que deben cumplirse a la vez |
| V06 | F3 Resta de confusores | `s(vigente) − máx s(confusor)` | Se descuenta lo que se parece al vecino semántico (p. ej., "protesta por servicios públicos") |
| V07 | F3 | `s(propia) − máx s(confusor)` | Igual, sobre la redacción propia |
| V08 | F5 Compuerta léxica | `s(vigente) · g` | `g` = 1 solo si el texto contiene palabras clave del concepto |
| V09 | F5 | `s(propia) · g` | Igual, sobre la redacción propia |
| V10–V12 | Cruces | F5+F2, F5+F3, F2+F3 | Combinaciones de dos familias |

En total, 83 hipótesis atómicas distintas (incluidas gemelas absurdas y nulas). Textos exactos
y listas de palabras clave: `experimentos/hipotesis_5ind_max.py`. Ejemplos de palabras clave de
la compuerta: grupos armados `ELN, FARC, disidencia, Clan del Golfo, AGC, autodefensas,
paramilitar, guerrilla, Segunda Marquetalia, frente N…` (sin "combo", "banda", "Tren de Aragua");
desplazamiento `desplaz-, huyó/huyeron, éxodo, abandonaron sus casas…`.

### Controles absurdos (el "detector de mentiras")

Para cada variante se construyó su **gemela absurda en el mismo formato**, con un contenido
reservado que nunca se usó para calibrar (**osos polares**):

- **Objeto absurdo:** la misma frase con el objeto cambiado por osos polares, siempre en el
  mismo hueco para cada indicador. Ejemplo para rechazo: "Hay oposición de comunidades o
  autoridades a *un criadero de osos polares*".
- **Absurdo total:** "En este territorio hay colonias de osos polares", pasado por la misma
  operación de la variante.

Si una variante da puntajes altos también a su gemela absurda, su "sí" no significa nada: el
modelo está confirmando la *forma* de la frase, no su contenido.

## 5. Cómo se juzgó: dos jueces LLM ciegos

1. **Puntuación en GPU (fase 2):** 83 hipótesis × 1.647 artículos, 87 minutos en una RTX 4050,
   una sola vez. Se guardaron las probabilidades crudas (`ent_`, `neu_`, `con_`) en
   `datos/scores/scores_5ind_atomicas_lugares.pkl`. Control: V01 reproduce producción con una
   diferencia máxima de 5.4e-07.
2. **Pool (método TREC, fase 3):** por indicador y lugar, se tomó la unión de los 15 artículos
   con mayor puntaje de cada una de las 12 variantes (sin artículos con score 0). Resultado:
   **565 artículos únicos**. Cada artículo se juzga una vez para los 5 indicadores.
3. **Lotes ciegos (fase 4):** los 565 artículos se barajaron con semilla fija (20260922) y se
   repartieron en 15 lotes de 40. Cada entrada del lote tiene solo un id opaco y la premisa.
   Los jueces **no ven** título, lugar, variante, puntaje ni orden original; el mapa id → url
   se guarda aparte.
4. **Jueces:** dos agentes definidos en `.claude/agents/`:
   - `juez-a`: modelo **Sonnet**, esfuerzo bajo.
   - `juez-b`: modelo **Opus**, esfuerzo bajo.

   Ambos llevan embebido el **codebook congelado** (tabla siguiente). Por cada artículo e
   indicador responden `SI`, `NO` o `DUDOSO`, con una cita literal de ≤ 20 palabras. Escriben
   las etiquetas en disco (`etiquetas_a/`, `etiquetas_b/`) y devuelven solo "lote N listo". Se
   corrieron 3 instancias de cada juez en paralelo, con 5 lotes por instancia.
5. **Referencia:** un artículo es **positivo solo si ambos jueces dicen SI**. Cualquier otra
   combinación es negativa. El acuerdo se mide con la **kappa de Cohen** por indicador; si
   kappa < 0.4, la referencia es débil y el indicador no se adopta.

**Codebook (lo que cuenta como SÍ y como NO):**

| Indicador | SÍ | NO |
|---|---|---|
| Exclusión de beneficios económicos | Una comunidad no recibe regalías, compensaciones o beneficios de un proyecto concreto | Falta de servicios, deportaciones, hallazgo de cuerpos, pobreza general |
| Rechazo a proyecto | Oposición a una obra o proyecto identificable (mina, peaje, eólico, hidroeléctrica, relleno, concesión) | Protestas laborales, bloqueos por agua o luz, asonadas contra militares, paros generales |
| Desplazamiento forzado | Personas o familias **ya** abandonaron su territorio por violencia o presión | Amenaza o riesgo sin desplazamiento, migración económica o venezolana |
| Conflicto territorial | Disputa violenta y sostenida por el control, uso o propiedad de un territorio | Protestas, bloqueos, amenazas aisladas, conflictividad política |
| Presencia de grupos armados | Guerrillas, disidencias, paramilitares o grupos armados organizados (ELN, EMC, Clan del Golfo, ACSN…) operando en la zona | Combos, delincuencia común, bandas de hurto, porte ilegal de armas, sicariato sin grupo identificado |

**Revisión metodológica independiente.** Antes de puntuar, el agente `orquesta-lead` (Opus)
revisó el pre-registro buscando contradicciones con decisiones cerradas y ambigüedades.
Propuso 10 correcciones; se adoptaron 9 (entre ellas: gemelas absurdas con una sola operación
por indicador, reglas para lugares sin artículos, kappa sobre SÍ contra el resto, regex más
precisas) y se rechazó 1 (cambiar el umbral 0.766, fijado en el plan aprobado).

## 6. Métricas y criterio de adopción

Por variante e indicador, sobre los 4 lugares:

| Métrica | Qué mide |
|---|---|
| **M1** Top-1 verdadero | ¿El artículo que fija el MAX es un positivo real? |
| **M2** Precisión@10 | Fracción de positivos entre los 10 artículos con mayor puntaje de cada lugar (media de los 4 lugares) |
| **M3** Coherencia del MAX | Lugar sin positivos → MAX < 0.766; lugar con positivos → MAX ≥ 0.766 (se cuentan violaciones) |
| **M4** Control absurdo | MAX por lugar de la gemela de objeto absurdo y del absurdo total |
| **M5** Diferenciación | Cuántos de los otros 25 indicadores comparten el mismo artículo máximo (solo se reporta) |
| **M6** AUC contra plata | Solo grupos armados, contra el estándar de plata por palabras clave |

**Una variante reemplaza a la vigente solo si cumple TODO:**
1. M2 ≥ 0.60 y al menos 0.20 más que la vigente.
2. Top-1 verdadero en ≥ 3 de 4 lugares (o en todos los que tienen positivos).
3. Ninguna violación de coherencia nueva respecto a la vigente.
4. Control absurdo: gemela de objeto absurdo < 0.766 en cada lugar y ≤ vigente + 0.05; absurdo total ≤ vigente + 0.05.
5. (Grupos armados) AUC ≥ vigente − 0.02.
6. (Fase 7) Holdout Cauca, Chocó y Cundinamarca: M2 ≥ 0.50 y ≥ vigente.

Si empatan varias, gana la más simple.

## 7. Resultados

### Acuerdo de los jueces

| Indicador | SÍ juez A | SÍ juez B | Positivos (SÍ/SÍ) | Kappa |
|---|---|---|---|---|
| Presencia de grupos armados | 91 | 82 | 82 | 0.94 |
| Desplazamiento forzado | 14 | 11 | 11 | 0.88 |
| Conflicto territorial | 19 | 20 | 17 | 0.87 |
| Rechazo a proyecto | 6 | 11 | 4 | 0.46 |
| Exclusión de beneficios económicos | 1 | 2 | 0 | ≈ 0 (referencia débil) |

Los jueces coinciden casi siempre en grupos armados, desplazamiento y conflicto. Rechazo a
proyecto tiene acuerdo moderado. En exclusión de beneficios no hay ningún caso real en los 565
artículos del pool.

### Veredicto por indicador

| Indicador | Vigente (V01): M2 / top-1 | Mejor alternativa | Decisión |
|---|---|---|---|
| **Presencia de grupos armados** | 0.17 / 2 de 4 | **V08: 0.93 / 4 de 4**, AUC 0.788→0.879, control absurdo sin empeorar | **Adoptada**: pasó el holdout (fase 7) y está en `src/` (fase 8) |
| Conflicto territorial | 0.07 / 1 de 4 | V09: 0.59 / 2 de 4; V08: 0.57 / 3 de 4 | Rechazado: no llega a 0.60 y el control absurdo supera 0.766 en Antioquia |
| Desplazamiento forzado | 0.05 / 0 de 4 | V10: 0.40 / 1 de 4 | Rechazado |
| Rechazo a proyecto | 0.00 / 0 de 4 | ≤ 0.03 | Rechazado (solo 4 positivos en todo el pool) |
| Exclusión de beneficios | 0.00 / 0 de 4 | — | No se puede evaluar (0 positivos) |

**Ejemplo del cambio en grupos armados (V01 → V08):**
- **Maicao:** el máximo pasa de "Maicao fortalece su seguridad… contra el crimen" (0.98, un
  falso positivo) a "Autoridades… esclarecer masacre en Maicao que dejó cinco víctimas" (0.98,
  un positivo según ambos jueces).
- **Oicatá:** baja de 0.65 (un hurto en zona rural) a 0. Oicatá no tiene ningún artículo con
  grupos armados, y ahora el indicador lo refleja.
- **Antioquia y Paraguachón:** sin cambio; el artículo máximo ya era un positivo.

V08 no inventa una frase nueva: conserva la hipótesis de producción y le exige que el texto
mencione un grupo armado identificable. Es la regla de palabras clave que la restricción de
diseño permite en producción.

### Fase 7 — holdout nacional y recalibración de cortes

Scripts `experimentos/exp_5ind_max_{nacional,holdout,cortes}.py`; resultados en
`experimentos/resultados/juicio_5ind_holdout/`. Solo se puntuó en GPU la gemela absurda de
grupos armados sobre los 11.439 artículos (7.3 min); lo demás se reutilizó de
`scores_v2_32deptos.pkl`.

**Holdout** (Cauca 598, Chocó 148, Cundinamarca 371 artículos; departamentos que no se usaron
para diseñar): pool de 94 artículos juzgados a ciegas por los mismos dos jueces.

| Indicador | SÍ/SÍ | Kappa |
|---|---|---|
| Presencia de grupos armados | 40 | 0.81 |
| Desplazamiento forzado | 18 (Cauca 5, Chocó 13) | 0.93 |
| Conflicto territorial | 16 (Cauca 7, Chocó 8, Cund. 1) | 0.75 |
| Rechazo a proyecto | 3 | 1.00 |
| Exclusión de beneficios económicos | 0 (ningún SÍ de ningún juez) | indefinida |

**Criterio 6 (grupos armados):** precisión en los 10 más altos, Cauca/Chocó/Cundinamarca, V01
0.70/0.50/0.20 (media 0.47) → **V08 1.00/0.80/0.50 (media 0.77)**. Top-1 verdadero en los 3,
0 violaciones de coherencia, gemela absurda de V08 ≤ la de V01 y < 0.766 en los 3. **V08 pasa
los 6 criterios del pre-registro → se adopta.** A escala nacional (solo reporte), la gemela de
objeto absurdo supera 0.766 en 3 de 32 departamentos con V01 y en 1 con V08 (Cesar, cuyo
artículo sí nombra un grupo armado); V08 nunca sube el MAX de la gemela.

**Cortes (regla 2, cambia lo medido).** Mismo procedimiento que la calibración original
(huecos naturales > 0.008 en la distribución nacional de los 32, sin mirar el oficial,
verificando las 12 anclas); con V01 reproduce exactamente 0.766 / 0.9233. Con V08:
**Bajo < 0.7574 ≤ Medio < 0.9233 ≤ Alto**. La clasificación de los 32 no cambia (6 Bajo / 19
Medio / 7 Alto) y ninguna ancla se rompe. Constancia: accuracy 0.344 → 0.344; Spearman −0.1653
→ −0.1173. El corte bajo se mueve porque San Andrés baja de 0.7376 a 0.7045. MAX de grupos
armados que cambian: Quindío 0.996→0.553, Caldas 0.978→0.725, San Andrés 0.861→0, Guainía
0.640→0.011 (los artículos que los fijaban no nombran un grupo armado en el texto visible).

### Fase 8 — promoción a producción

- `src/Transformer_optimo.py`: en `procesar()`, `presencia_grupos_armados = score corregido ×
  compuerta`. La compuerta es 1 si la regex de grupos armados (copiada literal del experimento,
  `REGEX_COMPUERTA_GRUPOS_ARMADOS`) aparece en la premisa que ve el NLI con la hipótesis de
  grupos armados, en minúsculas y sin tildes. Se guarda como columna auxiliar
  `compuerta_grupos_armados` (como `sesgo`); no está entre los 26 indicadores del radar ni de
  los exportadores. El NLI y los otros 25 indicadores no cambian. `src/` no importa nada de
  `experimentos/`.
- `src/config_pipeline.py`: `CORTE_BAJO_MEDIO_RADAR` 0.766 → 0.7574 (`CORTE_MEDIO_ALTO_RADAR`
  0.9233 igual).
- Verificación: `src/test_integracion.py` 14/14 (4 tests nuevos: la compuerta abre con ELN o
  disidencias y no con combo, banda o Tren de Aragua; solo mira la premisa visible; `procesar()`
  la aplica solo a grupos armados; la columna auxiliar no entra al radar).
  Equivalencia offline (`exp_5ind_max_f8_equivalencia.py`, sin GPU): la compuerta de `src/` es
  idéntica a la de F7 con truncación de producción en los 11.439 artículos; MAX de grupos
  armados y radar por departamento con max|dif| 0; `CalculadorRadar` de `src/` da 6/19/7 con la
  misma clase que F7 en los 32; el procedimiento de cortes sobre ese radar devuelve 0.7574/0.9233.
- **Excel de lugares** (`experimentos/resultados/excel_lugares_f8/`, script
  `exp_5ind_max_f8_excel_lugares.py`, sin GPU), con el formato de los de la profesora (hoja
  `Resumen`: Dimensión, Indicador, Score 0–100, URL del artículo top) y una hoja `Radar` añadida
  con el valor del radar, la clase y los cortes:

  | Lugar | Artículos | Radar antes (V01) | Clase (0.766) | Radar después (V08) | Clase (0.7574) | Grupos armados |
  |---|---|---|---|---|---|---|
  | Maicao | 1.101 | 0.9625 | Alto | 0.9624 | Alto | 98 → 98, otro artículo: de "Maicao fortalece su seguridad… contra el crimen" a "…esclarecer masacre en Maicao" |
  | Oicatá | 32 | 0.6688 | Bajo | 0.6437 | Bajo | 65 → 0 (el máximo era un hurto) |
  | Paraguachón | 77 | 0.8188 | Medio | 0.8188 | Medio | 99 → 99 (mismo artículo) |

  Solo cambia `presencia_grupos_armados`; ningún lugar cambia de clase.
  **Diferencia con los Excel de la profesora:** el "antes" regenerado no coincide con los
  suyos en 26 de 78 celdas (Maicao 9, Oicatá 3, Paraguachón 14), y en todas el nuestro es
  mayor. Todas sus URL top están en nuestro corpus y nuestro score para esos artículos coincide
  con el suyo (±0.5 por redondeo): sus Excel se generaron sobre **un subconjunto** de los
  artículos que tenemos hoy. Además, sus archivos dejan la URL vacía en algunos scores bajos
  (≤ 7); los regenerados la ponen siempre que el score sea > 0. Comparación celda a celda:
  `comparacion_antes_despues.csv`.

## 8. Hallazgos

1. **El NLI confirma la forma de la frase, no su contenido.** Con la hipótesis vigente de
   rechazo, "Hay oposición… a un criadero de osos polares" alcanza un MAX de 0.96–0.99 en los 4
   lugares. Pasa lo mismo en desplazamiento y conflicto. **La propia vigente suspende el control
   absurdo** en esos tres indicadores. Es la cuarta vez que el control absurdo detecta un
   problema que el AUC no ve (regla 1).
2. **Solo las compuertas léxicas mejoran la cola sin disparar el control.** Las familias
   puramente NLI (reescritura, paráfrasis, composición, resta de confusores) mueven poco la
   precisión y a menudo solo "apagan" el ranking.
3. **La escasez de positivos limita lo medible.** Rechazo a proyecto tiene 4 positivos en todo
   el pool y exclusión de beneficios ninguno: en estos lugares esos fenómenos casi no aparecen
   en la prensa.
4. **Exclusión de beneficios no distingue entre lugares.** A escala nacional, su MAX va de 0.95
   a 0.99 en los 32 departamentos (desviación 0.012, la segunda menor de los 26 indicadores).
   Suma una constante al radar sin separar un lugar de otro.

## 9. Limitaciones

- La referencia es de jueces LLM, no humana; el acuerdo alto (kappa ≥ 0.87 en tres indicadores)
  la hace creíble, pero no infalible.
- Solo 4 lugares, dos de ellos pequeños (Oicatá 32 y Paraguachón 77 artículos).
- El juez y el NLI ven solo el comienzo del artículo en el 77% de los casos.
- El umbral 0.766 es el corte del radar (media de 26 indicadores), no uno propio de cada
  indicador; se declaró como límite antes de medir.
- La AUC de V08 contra la plata es en parte circular (ambas usan palabras clave); por eso no se
  usó para desempatar.

## 10. Exclusión de beneficios económicos: se conserva

**Decisión del usuario (2026-09-22): no se retira ningún indicador.** El radar sigue con 26. El
trabajo va en orden, como muñecas rusas: primero se corrigen los indicadores problemáticos y
solo después, si hiciera falta, se discute cuáles sobran.

Para exclusión la evidencia sigue siendo la misma: 0 positivos en 565 artículos juzgados (y 0
en los 94 del holdout, donde ningún juez dijo SÍ), y un MAX nacional de ~0.99 en los 32
departamentos (std 0.012) que no distingue lugares. Queda como **indicador problemático
pendiente**, con un problema distinto al de los otros: no hay casos reales con los que medir.
El muestreo por los artículos mejor puntuados por la propia vigente no encuentra ninguno, así
que la segunda ronda necesita otra forma de buscarlos.

Retirarlo, incluso de forma temporal, **no ayuda a corregir los otros**: cada indicador se
puntúa por separado. Quitarlo solo cambiaría la media del radar y sus cortes. Por eso no se retira.

Protección del estado de 26 indicadores (etiquetas git locales): `base-26ind-radar-max`
(= `radar-max_Septiembre`, 71072a1, lo desplegado), `base-26ind-f5` (esta rama tras F5) y
`base-26ind-f7` (705a557, tras F7, último commit con `src/` intacto). `src/` solo se modificó
en F8 (compuerta de grupos armados y cortes); el radar sigue con 26 indicadores.

## 11. Próximos pasos (en orden)

1. **Revisión del usuario** de la rama `hipotesis-5ind-max` (commits locales). Sin push ni
   merge a `radar-max_Septiembre` hasta su aprobación.
2. **Segunda ronda para los problemáticos que faltan** (experimento nuevo, con su propio
   pre-registro, sin reabrir lo cerrado): conflicto territorial (compuertas con M2 0.57–0.59),
   desplazamiento (0.40), rechazo a proyecto (4 positivos en el pool + 3 en el holdout) y
   exclusión (0 positivos en 565 + 94). El hallazgo 1 orienta el diseño: compuertas léxicas y
   controles específicos antes que reescribir frases. El holdout ya aporta casos (desplazamiento
   18, conflicto 16, rechazo 3); para exclusión hace falta otro muestreo.
3. Re-puntuar los 32 departamentos con el código de `src/` (pendiente desde antes de este
   experimento, ~4 h GPU); la compuerta no cambia nada del NLI, así que no lo exige.

## Anexo — Trazabilidad

| Commit | Contenido |
|---|---|
| `b715ec2`, `5a6bbd6` | Restauración de `experimentos/` y del registro previo (cherry-pick) |
| `4566efc` | Plan aprobado |
| `303ca12`, `bc0f98f` | Fase 0: verificación del entorno; pkl nacional V2 localizado y verificado |
| `293a80e`, `6dc6ef5` | Fase 1: pre-registro y congelamiento tras la revisión de `orquesta-lead` |
| `fabddb7` | Scripts `exp_5ind_max_{atomicas,variantes,juicio,metricas}.py` y agentes `juez-a`/`juez-b` |
| `00497f8` | Fases 2–5: pool, lotes, etiquetas de ambos jueces, referencia, métricas |
| `cb336fa` | Este informe (etiqueta `base-26ind-f5`) |
| `5631fbd` | Corrección: exclusión no se retira, el radar sigue con 26 |
| `705a557` | Fase 7: holdout nacional y recalibración de cortes (etiqueta `base-26ind-f7`) |
| F8 (ver `git log`) | Promoción de V08 a `src/`, cortes 0.7574/0.9233, tests, equivalencia, Excel de lugares, este informe |

Archivos clave: `experimentos/resultados/juicio_5ind/` (`lotes/`, `etiquetas_a/`,
`etiquetas_b/`, `referencia.csv`, `pool.csv`, `max_por_lugar.csv`, `metricas_5ind.xlsx`),
`experimentos/resultados/juicio_5ind_holdout/` (holdout, `cortes_radar.xlsx`,
`f8_equivalencia.csv`) y `experimentos/resultados/excel_lugares_f8/`.
