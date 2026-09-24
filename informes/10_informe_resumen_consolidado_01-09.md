# Informe 10 — Resumen consolidado de los informes 01 a 09

Fecha: 2026-09-24 · Rama `hipotesis-5ind-max` (local, sin push ni fusión; último commit previo
`919ed3e`) · Para los responsables del proyecto.

Reúne los informes 01 a 09 sin repetir lo que se superpone. **No añade mediciones nuevas:** cada
cifra lleva entre paréntesis el informe de donde sale, y ese informe cita su archivo de origen.
Cuando un informe corrige a otro (el 03 revierte el 02 y el 07 corrige el 06), aquí va la versión
final. Lectura rápida: §1 (resumen) y §11 (decisiones); el resto es la evidencia.

## 1. En una página

**Qué se buscó.** Que 5 de los 26 indicadores del radar dejaran de tomar su valor de artículos de
otro tema: exclusión de beneficios económicos, rechazo a proyecto, desplazamiento forzado,
conflicto territorial y presencia de grupos armados.

**Resultado neto.** Producción no cambió. `src/` es idéntico al de la rama desplegada
`radar-max_Septiembre`: 26 indicadores, agregación MAX, cortes Bajo < 0.766 ≤ Medio < 0.9233 ≤
Alto y clasificación 6 Bajo / 19 Medio / 7 Alto. Frente al radar del DANE sigue en accuracy 0.344
(lo mismo que responder siempre «Bajo») y Spearman −0.165 (informes 05 y 09).

**Qué se logró:**
1. Un sistema para medir si un indicador lee lo que debe, que el proyecto no tenía: 962 artículos
   juzgados por dos jueces LLM ciegos, con criterios fijados antes de medir.
2. La causa del problema, medida: el modelo NLI confirma la *forma* de la frase y no su *objeto*.
3. Una mejora validada para grupos armados: precisión de 0.17 a 0.93, y de 0.47 a 0.77 en
   departamentos no usados para diseñarla. Usa palabras clave, así que se revirtió por la regla de
   «solo hipótesis»; queda guardada.
4. El diagnóstico cerrado de exclusión de beneficios: no se puede medir con este corpus y hoy
   funciona como una constante.

**Qué se rechazó, con evidencia:** más de 80 alternativas de frase o de cálculo (55 en la ronda 1,
25 en la ronda 2 y 3 reescrituras previas) y un segundo modelo NLI,
`vicgalle/xlm-roberta-large-xnli-anli`.

**Qué se pide decidir:** la fusión de la rama, qué hacer con exclusión, si se mantiene la regla de
«solo hipótesis» y la siguiente línea de trabajo (§11).

## 2. Punto de partida

- El radar clasifica los 32 departamentos en Bajo / Medio / Alto a partir de prensa regional. Un
  modelo NLI (`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, 12 capas) evalúa 26
  frases («hipótesis») en cada artículo. El valor de cada indicador en un lugar es el **máximo**
  entre sus artículos, y el índice es la media de los 26 máximos (informe 09 §2).
- Con MAX basta un artículo mal leído para fijar el indicador. La auditoría de los Excel de
  Maicao, Oicatá y Paraguachón lo mostró: «hombre asesinado a tiros» fijaba *grupos armados* y
  «Unidad de Búsqueda recuperó diez cuerpos» fijaba *exclusión de beneficios* (informe 01 §1).
- Dos decisiones del usuario enmarcan todo el trabajo:
  - **2026-09-22:** no se retira ningún indicador; el radar sigue con 26 (informe 01 §10).
  - **2026-09-23:** de cada indicador solo se cambia la hipótesis. Nada de reglas de palabras
    clave, combinaciones de frases ni columnas nuevas (informe 03 §1).

## 3. Cómo se midió (igual en todas las pruebas)

| Pieza | En qué consiste |
|---|---|
| Referencia | Dos jueces LLM (Claude Sonnet y Claude Opus) leen cada artículo sin saber de dónde viene ni qué sistema lo eligió. Un artículo es caso real solo si **los dos** dicen SÍ. Solo evalúan, en local: ningún LLM entra a producción. |
| Precisión (criterio principal) | De los 10 artículos con mayor puntaje en cada lugar, qué fracción son casos reales (media de los lugares). Se exigía ≥ 0.60 y 0.20 más que la frase vigente. |
| Acierto del máximo | El artículo que fija el valor del lugar tiene que ser un caso real en al menos 3 de los 4 lugares, o en todos los que tienen casos. |
| Control absurdo | La misma frase con «osos polares» en lugar del objeto (p. ej., «…desplazadas por los osos polares») y una frase absurda general («En este territorio hay colonias de osos polares»). La del objeto debe quedar bajo el corte del radar (0.766) en cada lugar, y ninguna puede superar en más de 0.05 a la de la vigente. |
| Pre-registro | Criterios congelados antes de ver resultados, revisados por un agente independiente (`orquesta-lead`) antes de medir y al cerrar cada ronda. |
| Datos | 4 lugares de diseño: 1.647 artículos (Antioquia 494, Maicao 1.101, Oicatá 32, Paraguachón 77). Comprobación en 3 departamentos no usados para diseñar: Cauca 598, Chocó 148, Cundinamarca 371. Escala nacional: 11.439 artículos de 32 departamentos. |

- **Volumen juzgado:** 962 artículos. Son 565 de la ronda 1, 94 de los departamentos de
  comprobación, 281 de la ronda 2 y 22 de la prueba del modelo (informe 08 §4).
- **Fiabilidad de los jueces:** acuerdo alto en grupos armados, conflicto y desplazamiento (kappa
  0.87–0.95 en los lugares de diseño y 0.75–0.93 en los de comprobación), moderado en rechazo
  (0.44–0.46) y nulo en exclusión. Al volver a juzgar 40 artículos ya etiquetados coinciden en el
  97–100 % (informes 01, 04 y 07).
- **Costo de cómputo:** unas 2 h 45 min de GPU en total, sumando las corridas reportadas (87 min
  en la ronda 1, 7 en la comprobación nacional, 46 en la ronda 2 y 25 en la prueba del modelo;
  informes 01, 04 y 06).

## 4. Cronología: cómo se encadenan los informes

| Fecha | Paso | Resultado | Informe |
|---|---|---|---|
| 2026-09-22 | Ronda 1: la frase vigente y 11 alternativas por indicador, en los 4 lugares | Solo pasa la compuerta de palabras clave de grupos armados (variante V08) | 01 |
| 2026-09-22 | Comprobación en Cauca, Chocó y Cundinamarca; recalibración de cortes | V08 pasa; corte bajo 0.766 → 0.7574; ninguna clase cambia | 01 |
| 2026-09-22 | V08 se promueve a `src/` (sin desplegar); Excel de lugares antes y después | Promovida y verificada (15/15 tests) | 02 |
| 2026-09-23 | Regla de «solo hipótesis» | V08 se revierte; cortes de nuevo 0.766 / 0.9233 | 03 |
| 2026-09-23 | Ronda 2: 25 frases, cambiando solo la hipótesis | Ninguna pasa; exclusión, no medible | 04 |
| 2026-09-23 | Consolidado de las dos rondas; propuesta de probar otro modelo NLI | Se aprueba la prueba, en rama aparte y por etapas | 05 |
| 2026-09-23 | Modelo nuevo, etapa 1 (sin jueces) | Conflicto pasa el control absurdo; va a juicio con grupos armados | 06 |
| 2026-09-23 | Modelo nuevo, etapa 2 (con jueces) | Ningún indicador cumple: modelo rechazado, sin etapa 3 | 07 |
| 2026-09-24 | Diagnóstico de exclusión de beneficios | Funciona como constante; quitarlo no cambia ninguna clase | 08 |
| 2026-09-24 | Avances de la rama para el responsable | Lista de decisiones pendientes | 09 |

## 5. Qué se logró

### 5.1 Un sistema de evaluación que el proyecto no tenía

- **Antes:** la única referencia de calidad era un estándar de plata por palabras clave que cubre 2
  de los 26 indicadores (informe 09 §3.1).
- **Ahora:** 962 artículos juzgados para 5 indicadores, reutilizables. La prueba del modelo solo
  necesitó juzgar 22 artículos nuevos (informe 07 §2). Cualquier cambio futuro (una frase, un
  modelo o una regla) se puede evaluar en horas con la misma vara.

### 5.2 La causa del problema, medida

- El modelo actual responde a la forma de la frase, no a su objeto. «Familias fueron desplazadas
  de sus veredas por los osos polares» puntúa como «…por la violencia armada»: máximos de 0.99 /
  0.98 frente a 1.00 / 0.98 en Antioquia y Maicao (informe 04 §6).
- En rechazo, desplazamiento y conflicto, la frase vigente con «osos polares» supera el corte del
  radar (0.766) en al menos 3 de los 4 lugares. En rechazo llega a 0.96–0.99 en los 4 (informe 06
  §3).
- Con MAX basta un artículo que «suene» al tema para disparar el indicador. Por eso reescribir la
  frase no alcanza, y dos rondas lo confirman.

### 5.3 Una mejora real para grupos armados, validada y guardada

Es la frase vigente más una **compuerta de palabras clave**: el indicador solo cuenta si el texto
que lee el modelo nombra un grupo armado organizado (ELN, disidencias de las FARC, Clan del Golfo,
autodefensas, «frente 36»…). «Combo», «banda» o «Tren de Aragua» no abren la compuerta, porque la
definición los trata como delincuencia común (informe 02 §2).

| Medida | Vigente | Con compuerta | Informe |
|---|---|---|---|
| Precisión en los 4 lugares | 0.17 | **0.93** | 01 §7 |
| Lugares con el máximo bien puesto | 2 de 4 | **4 de 4** | 01 §7 |
| Precisión en Cauca / Chocó / Cundinamarca | 0.70 / 0.50 / 0.20 (media 0.47) | **1.00 / 0.80 / 0.50 (media 0.77)** | 01 §7 |
| Departamentos con control absurdo > 0.766 (de 32) | 3 | 1 | 02 §3 |
| Cortes del radar | 0.766 / 0.9233 | 0.7574 / 0.9233, misma clasificación 6 / 19 / 7 | 01 §7 |
| Accuracy / Spearman frente al DANE | 0.344 / −0.165 | 0.344 / −0.117 (con 32 departamentos no se distingue) | 02 §4 |

- Cumplió los 6 criterios del pre-registro y nunca subió el control absurdo (informe 01 §7).
- Ejemplos: en Maicao el máximo pasó de «Maicao fortalece su seguridad… contra el crimen» (falso)
  a «…esclarecer masacre en Maicao que dejó cinco víctimas» (real). Oicatá, sin artículos del
  tema, bajó de 65 a 0 en su Excel. A escala nacional bajó donde el artículo que fijaba el máximo
  no nombraba ningún grupo: Quindío 0.996 → 0.553, Caldas 0.978 → 0.725, San Andrés 0.861 → 0 y
  Guainía 0.640 → 0.011 (informes 01 §7 y 02 §6).
- Se promovió a `src/` en la rama el 2026-09-22, sin desplegar, con tests 15/15 y resultado
  idéntico al del experimento en los 11.439 artículos. Se revirtió el 2026-09-23 por la regla de
  «solo hipótesis» (informe 03). Está en la etiqueta git `base-26ind-f8-compuerta`, lista si la
  regla cambia.
- De paso se vio que los Excel de lugares que vio la profesora se hicieron sobre un subconjunto de
  los artículos actuales (probablemente una descarga anterior): al regenerarlos, 26 de 78 celdas
  dan un valor mayor, aunque los puntajes de sus 69 artículos coinciden con los nuestros (informe
  02 §6).

### 5.4 Producción intacta y trazable

- `src/` es idéntico al de `radar-max_Septiembre` y los tests de integración pasan 10 de 10
  (informes 03 §3 y 09 §3.5).
- Cada paso, incluidos los revertidos, está en el registro de decisiones y tiene su etiqueta git.

## 6. Qué se rechazó

| Qué se probó | Resultado | Motivo | Informe |
|---|---|---|---|
| Reescritura de 3 frases (rechazo, exclusión y derechos vulnerados) sobre 102 artículos de Antioquia leídos a mano, 2026-09-08 | El control absurdo empeora en las tres: de 2.2 % a 47.8 % en rechazo, a 25.8 % en exclusión y a 13.5 % en derechos | Si el control absurdo empeora, se rechaza (regla 1 del proyecto) | log [2026-09-08]; 08 §5 |
| Ronda 1: 11 alternativas por indicador, 55 en total (frases nuevas, paráfrasis, combinaciones de frases, resta de confusores, compuertas y cruces) | Solo pasa la compuerta de grupos armados. Las mejores del resto: conflicto 0.59 y desplazamiento 0.40 (ambas con compuerta); rechazo ≤ 0.03; exclusión, sin casos | Por debajo de 0.60; en conflicto, además, el control absurdo supera 0.766 en Antioquia | 01 §7 |
| Compuerta de grupos armados (V08) | Pasó todos los criterios | No la descartó la evidencia: se revirtió por la regla de «solo hipótesis» | 03 |
| Ronda 2: 25 frases (15 nuevas y 10 paráfrasis de la ronda 1), cambiando solo la hipótesis | Mejor precisión 0.38 (grupos armados); 20 de 25 fallan el control absurdo | Ninguna llega a 0.60 | 04 §4 |
| Modelo NLI `vicgalle/xlm-roberta-large-xnli-anli` | Grupos armados 0.17 → 0.35; conflicto 0.07 → 0.07 | Ningún indicador cumple los criterios (§8) | 06, 07 |
| Otros modelos, descartados sin probar | `MoritzLaurer/bge-m3-zeroshot-v2.0` no tiene salida «neutral» (obliga a cambiar la fórmula); `joeddav/xlm-roberta-large-xnli` no tiene entrenamiento adversarial; el proyecto no permite un LLM en producción | No son un reemplazo directo o rompen las reglas | 05 §7 |
| Fusionar exclusión con «incentivos económicos inequitativos», 2026-09-22 | Con MAX, el valor casi fijo de exclusión (≈ 0.99) taparía a incentivos, que sí varía (desviación 0.113) | Estropearía un indicador que funciona | 08 §7 |

## 7. Datos por indicador

**Casos reales y acuerdo de los jueces.** Casos en los 4 lugares tras la ronda 2 (940 artículos
juzgados; informe 04 §4) y en los departamentos de comprobación (informe 01 §7). A / M / O / P =
Antioquia / Maicao / Oicatá / Paraguachón.

| Indicador | Casos en A / M / O / P | Casos en Cauca, Chocó y Cundinamarca | Kappa de la ronda 1, lugares / comprobación |
|---|---|---|---|
| Presencia de grupos armados | 42 / 45 / 0 / 5 | 40 | 0.94 / 0.81 |
| Conflicto territorial | 10 / 8 / 0 / 3 | 16 | 0.87 / 0.75 |
| Desplazamiento forzado | 10 / 1 / 0 / 0 | 18 | 0.88 / 0.93 |
| Rechazo a proyecto | 1 / 3 / 0 / 0 | 3 | 0.46 / 1.00 |
| Exclusión de beneficios | 0 / 0 / 0 / 0 | 0 | ≈ 0 / sin definir |

**Precisión** (fracción de casos reales entre los 10 artículos con mayor puntaje por lugar; se
exigía ≥ 0.60). Fuentes: informes 01 §7, 04 §4 y 07 §3.

| Indicador | Frase vigente | Ronda 1, mejor alternativa | Ronda 2, mejor frase | Modelo nuevo, frase vigente | Estado hoy |
|---|---|---|---|---|---|
| Grupos armados | 0.17 | **0.93** (compuerta) | 0.38 | 0.35 | Vigente; compuerta guardada |
| Conflicto territorial | 0.07 | 0.59 (compuerta) | 0.26 | 0.07 | Vigente |
| Desplazamiento forzado | 0.05 | 0.40 (compuerta y combinación) | 0.07 | No pasó la etapa 1 | Vigente |
| Rechazo a proyecto | 0.00 | ≤ 0.03 | 0.25 (*) | No pasó la etapa 1 | Vigente |
| Exclusión de beneficios | 0.00 | Sin casos | 0.00 | Solo reporte | Vigente; no medible |

(*) Sale entero de Oicatá, que no tiene casos: ahí una frase vale 1 si no puntúa nada. En los
lugares con casos es 0.00 (informe 04 §4).

**Frases.** La vigente se queda en los 5 indicadores (informe 05 §5); la mejor alternativa de la
ronda 2 no alcanzó el criterio (informe 04 §4).

| Indicador | Frase vigente (se queda) | Mejor frase nueva de la ronda 2 |
|---|---|---|
| Grupos armados | «En este territorio hay presencia de grupos armados ilegales.» | «Hay presencia de guerrilla o paramilitares en este territorio.» |
| Conflicto territorial | «Hay una disputa por el control, el uso o la propiedad de un territorio.» | «Grupos armados ilegales se enfrentan entre sí por el control de esta zona.» |
| Desplazamiento forzado | «Hubo un desplazamiento forzado o éxodo de comunidades.» | «Familias fueron desplazadas de sus veredas por la violencia armada.» |
| Rechazo a proyecto | «Hay oposición de comunidades o autoridades a un proyecto.» | «La comunidad rechaza que construyan una mina, una represa o un parque eólico.» |
| Exclusión de beneficios | «Una comunidad quedó excluida de los beneficios económicos de un proyecto.» | Todas dieron 0.00 |

## 8. La prueba del nuevo modelo NLI

**Por qué.** Dos rondas mostraron que el problema no está en la redacción. Sin romper la regla de
«solo hipótesis», lo que quedaba por probar era el modelo que lee las frases (informe 05 §7).

**Candidato:** `vicgalle/xlm-roberta-large-xnli-anli`, frente al de producción,
`mDeBERTa-v3-base`.
- Es el doble de profundo (24 capas frente a 12), multilingüe y lee 512 tokens, igual que el
  actual.
- Se entrenó con MNLI, XNLI y ANLI. ANLI está hecho para romper los atajos de estos modelos, como
  el que se observó aquí. Licencia MIT.
- Tiene las mismas 3 salidas (implicación, neutral y contradicción). Es un reemplazo directo: no
  cambian la fórmula, la calibración del sesgo, el MAX ni las 26 frases.

**Diseño.** Rama aparte, sin tocar producción. Pre-registro congelado (`710c7be`) con las 12
correcciones de la revisión independiente adoptadas antes de medir. Tres etapas, parando en la
primera que fallara. Antes de medir se comprobó que el orden de las salidas es el correcto, que el
tamaño de lote no cambia el resultado, que con el modelo actual el script reproduce los puntajes
guardados y que el modelo nuevo ve el mismo texto que vieron los jueces (informe 06 §2).

**Etapa 1: filtro sin jueces** (25 min de GPU, 15 frases sobre los 1.647 artículos). Máximo de la
frase vigente con «osos polares» en A / M / O / P. Para pasar debía quedar bajo 0.766 en al menos
3 lugares (informe 06 §3):

| Indicador | Modelo actual | Modelo nuevo | Resultado |
|---|---|---|---|
| Conflicto territorial | 0.95 / 0.99 / 0.89 / 0.72 | 0.47 / 0.68 / 0.26 / 0.43 | Pasa → etapa 2 |
| Grupos armados | 0.67 / 0.69 / 0.65 / 0.36 | 0.60 / 0.24 / 0.15 / 0.16 | Pasa → etapa 2 (ya pasaba con el actual) |
| Rechazo a proyecto | 0.98 / 0.99 / 0.97 / 0.96 | 0.94 / 0.96 / 0.53 / 0.80 | No pasa |
| Desplazamiento forzado | 0.98 / 0.96 / 0.70 / 0.94 | 0.80 / 0.68 / 0.94 / 0.33 | No pasa |
| Exclusión de beneficios | 0.99 / 0.99 / 0.90 / 0.98 | 0.73 / 0.97 / 0.48 / 0.57 | Solo reporte (no medible) |

- Fue la primera vez que la frase vigente, **sin cambiarla**, dejó de puntuar su versión absurda
  como la real en un indicador que fallaba (conflicto). Una frase reescrita de la ronda 2 ya lo
  había logrado, con precisión 0.12 (corrección del informe 07 §6 al 06).
- El modelo nuevo dice «sí» más a menudo a cualquier frase: sesgo medio por artículo de 0.475
  frente a 0.364. La fórmula de producción lo descuenta.

**Etapa 2: juicio.** Los jueces revisaron los 22 artículos que el modelo nuevo ponía arriba y no
estaban juzgados, más 40 de control (coinciden en el 97–100 %). La referencia pasó a 962
artículos (informe 07 §2–3).

| Indicador | Precisión, modelo actual | Precisión, modelo nuevo | Máximo bien puesto (de 3 lugares con casos), actual → nuevo | Kappa |
|---|---|---|---|---|
| Conflicto territorial | 0.07 | 0.07 | 1 → 0 | 0.88 |
| Grupos armados | 0.17 | 0.35 | 2 → 1 (solo Antioquia) | 0.95 |

- **Grupos armados** duplica la precisión (y su AUC frente al estándar de plata sube de 0.788 a
  0.877), pero queda lejos de 0.60.
- **Conflicto** no mejora. El modelo deja de confirmar la frase absurda, pero los artículos que
  pone arriba siguen sin reportar conflicto.
- **Control absurdo general** («colonias de osos polares»): baja en Maicao, Oicatá y Paraguachón
  (0.57 / 0.43 / 0.21 → 0.11 / 0.03 / 0.00), pero en Antioquia sube de 0.38 a 0.51 y supera el
  tope pre-registrado (0.43). Lo causa un solo artículo de 494 («Celsia sembró más de 13 millones
  de árboles nativos»), y basta para que ningún indicador cumpla ese criterio.

**Decisión.** El modelo queda rechazado según el pre-registro y no se hizo la etapa 3 (escala
nacional, unas 6–7 h de GPU estimadas, no medidas). Una revisión independiente confirmó que el
rechazo se sigue de lo fijado de antemano. Producción no cambió; la rama de prueba se borró y su
historial quedó en la etiqueta `prueba-modelo-nli-rechazado` (informe 07 §5).

**Lectura.** Que el modelo deje de confirmar la frase absurda es necesario, pero no suficiente:
además tiene que poner arriba artículos que reporten el hecho. Solo se probó este modelo.

## 9. Exclusión de beneficios económicos

- **No medible con este corpus.** No hay ningún caso confirmado en los 962 artículos juzgados ni
  en 102 de Antioquia leídos a mano. Se juzgaron a propósito los 237 artículos que mencionan
  regalías, compensaciones, consulta previa, indemnizaciones o «no han recibido». El juez A dijo
  SÍ 5 veces y el B 3, nunca en el mismo artículo. El pre-registro fija que con menos de 5 casos
  el indicador es «no medible» (informe 08 §3–4).
- **Por qué.** La prensa casi no lo cuenta así: los 18 casos dudosos son, por ejemplo, columnas de
  opinión, municipios que pierden regalías o comunidades que *reclaman* compensaciones. Los jueces
  no coinciden en esos casos grises (kappa ≈ 0). Y el modelo confirma la forma: con «un criadero
  de osos polares» puntúa casi igual (Antioquia 0.993 frente a 0.996; Maicao 0.994 frente a 0.996)
  (informe 08 §5).
- **Qué hace hoy.** Vale entre 0.950 y 0.998 en los 32 departamentos (mediana 0.994). Su
  desviación, 0.0125, es la segunda más baja de los 26. El 20.3 % de los 11.439 artículos pasa de
  0.766. Funciona como una constante.
- **Efecto de quitarlo** (medido sin GPU): el orden de los departamentos no cambia (Spearman
  1.0000 con el de 26 indicadores); el índice baja 0.0055 de media y 0.0199 como mucho; ninguna
  clase cambia; la concordancia con el DANE sigue en 0.344 / −0.165 (informe 08 §6).
- **Opciones** (informe 08 §7): mantenerlo, que es lo recomendado mientras se decide porque no
  altera nada; retirarlo, que no cambia ninguna clase pero exige recalibrar formalmente los cortes
  (minutos, sin GPU); buscar casos en otra fuente (días, con riesgo de no encontrarlos); o
  redefinir el concepto hacia lo que la prensa sí cuenta, que sin casos tampoco se puede evaluar.

## 10. Lo que no se logró

- **Ningún indicador mejoró en producción.** Con la regla de «solo hipótesis» no apareció ninguna
  mejora, y la única medida (la compuerta) queda fuera de la regla.
- **La concordancia con el DANE no se movió** (0.344 / −0.165). Los 5 indicadores son 5 de 26 y
  cada uno pesa 1/26. Además hay límites que no dependen de las frases: con MAX, el valor de un
  departamento tiende a subir con su número de artículos (medido con la versión anterior de los
  indicadores), y es posible que los temas de búsqueda del scraping tiren hacia conflicto mientras
  el índice oficial mide más bien déficit (hipótesis registrada, no medida) (informe 09 §4).
- **Hay fenómenos que la prensa casi no reporta:** rechazo a proyecto tiene 4 casos en los 4
  lugares y exclusión ninguno. Sin casos no se puede medir ni mejorar.

## 11. Qué se pide decidir

1. **Fusión de `hipotesis-5ind-max` en `radar-max_Septiembre`.** No cambia producción. Añade
   `experimentos/` (scripts y resultados), `informes/` y el registro de decisiones. Al fusionar hay
   que ajustar dos reglas de `CLAUDE.md` de esa rama, que dicen que no existe `experimentos/`.
2. **Exclusión de beneficios** (§9). Es una decisión de negocio: si el concepto importa, primero
   hay que conseguir casos; si no, retirarlo no cambia ninguna clase.
3. **La regla de «solo hipótesis».** Con ella no queda ninguna mejora disponible para estos 5
   indicadores. La única medida es la compuerta de grupos armados, lista en
   `base-26ind-f8-compuerta`.
4. **Siguiente línea de trabajo** (todas por aprobar): aplicar el método de jueces a los otros 21
   indicadores para saber cuáles fallan bajo MAX (antes hay que escribir su definición para los
   jueces; costo en horas de jueces, no medido); revisar los temas de búsqueda del scraping (días
   de re-scraping); o diseñar indicadores de déficit estructural (informe 09 §5).

## 12. Límites

- La referencia son jueces LLM, no personas, y no se ha medido cuánto coinciden con un juicio
  humano. Su alto acuerdo la hace creíble, no infalible.
- 4 lugares de diseño, dos pequeños (Oicatá 32 y Paraguachón 77 artículos). Oicatá no tiene casos
  en ningún indicador.
- El modelo y los jueces leen solo el comienzo de cada artículo (512 tokens); el 77 % de los
  artículos es más largo.
- Solo se juzgan los artículos que alguna variante pone entre sus 15 primeros: un caso real que
  ninguna suba no se ve.
- Con 32 departamentos, diferencias de accuracy menores a ~15 puntos no se distinguen del ruido.

## Trazabilidad

| Dato | Dónde |
|---|---|
| Detalle de cada paso | Informes 01 a 09 de esta carpeta (índice en `informes/README.md`) |
| Criterios fijados antes de medir | `experimentos/PREREG_5ind_MAX.md` (ronda 1), `experimentos/PREREG_5ind_MAX_r2.md` (ronda 2), `experimentos/PREREG_modelo_nli.md` (modelo) |
| Tablas de resultados | `experimentos/RESULTADOS_5ind_MAX.md`, `experimentos/RESULTADOS_5ind_MAX_r2.md`, `experimentos/RESULTADOS_modelo_nli.md` |
| Etiquetas de los jueces (962 artículos) | `experimentos/resultados/juicio_5ind/`, `juicio_5ind_holdout/`, `juicio_5ind_r2/` y `juicio_modelo_nli/` |
| Etapa 1 del modelo | `experimentos/resultados/modelo_nli/etapa1_filtro.log` |
| Exclusión de beneficios | `experimentos/resultados/exclusion/diagnostico_exclusion.log` |
| Decisiones y rechazos | `contexto/08_log_decisiones.md`, entradas [2026-09-08], [2026-09-22] y [2026-09-23] |
| Estados en git | Etiquetas `base-26ind-radar-max` (producción de partida), `base-26ind-f8-compuerta` (con la compuerta) y `prueba-modelo-nli-rechazado` (prueba del modelo) |
