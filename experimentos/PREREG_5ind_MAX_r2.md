# Pre-registro — 2a ronda: solo hipótesis, 5 indicadores bajo MAX

Fecha: 2026-09-23 · Rama: `hipotesis-5ind-max` · Antecedentes: `experimentos/PREREG_5ind_MAX.md`
(ronda 1, congelado), `informes/01_…`, `02_…`, `03_informe_reversion_f8.md`,
`contexto/08_log_decisiones.md` [2026-09-22] y [2026-09-23].

**Estado: CONGELADO** el 2026-09-23, tras la revisión única de `orquesta-lead` (1 bloqueante
y 11 menores, las 12 adoptadas; ver el log).

**A partir del commit que congela este archivo (y `experimentos/hipotesis_5ind_max_r2.py`),
nada de §1–§7 cambia.** Toda desviación posterior se registra en el log como desviación, con su
motivo.

## Restricciones (del usuario, no negociables)

- Agregación por lugar = **MAX**, fija.
- **Regla 15 (2026-09-23): de cada indicador solo se cambia la hipótesis.** Nada de compuertas
  de palabras clave, `min` de varias frases, restas de confusores ni columnas nuevas. Por eso
  las candidatas son solo de la familia F1 (una frase) y su score es la fórmula vigente
  `s(h) = clip(clip(ent − sesgo, 0)·(1 − neu), 0, 1)`, con el `sesgo` de las 4
  `NULAS_CALIBRACION`.
- Producción = solo el NLI `mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`. El LLM solo juzga,
  en local.
- Sin humano en el lazo: referencia = SÍ de `juez-a` (sonnet) **y** `juez-b` (opus), ciegos.
- No se retira ningún indicador: el radar sigue con 26.
- Sin push ni merge sin aprobación. Adopciones y rechazos al log.

**Qué es nuevo respecto a la ronda 1.** (a) Solo F1. Las variantes de la ronda 1 que no
pasaron siguen rechazadas y no se vuelven a probar (V02 y V03 no se repiten). La V08 de grupos
armados sí pasó los 6 criterios, pero es una compuerta y la regla 15 impide promoverla.
(b) `presencia_grupos_armados` vuelve a la lista. (c) Candidatas
nuevas N1–N3 por indicador, más P1/P2 = las paráfrasis `p1`/`p2` de la ronda 1, que solo se
midieron dentro de `min()` (V04) y nunca como frase única. Sus métricas como frase única no se
calcularon antes de este pre-registro. (d) Muestreo por palabras clave para buscar casos reales
de exclusión (§5). Los criterios de adopción son los de la ronda 1, sin cambios.

## 0. Pregunta y refutación

**Pregunta:** ¿existe, para alguno de los 5 indicadores, una frase NLI cuyo MAX por lugar lo
fije un artículo que de verdad reporta el concepto (precisión en la cola), sin empeorar el
control absurdo?

**Refutación (por indicador):** ninguna de sus 5 candidatas cumple los 6 criterios de §4. En
ese caso el indicador queda con su hipótesis vigente y se registra el rechazo.

## 1. Codebook del juez

Idéntico al de la ronda 1 (`PREREG_5ind_MAX.md` §1, embebido en
`.claude/agents/juez-a.md` y `juez-b.md`, que se reutilizan sin cambios). Por eso las etiquetas
de la ronda 1 (565 artículos de los lugares y 94 del holdout) valen como referencia aquí.

## 2. Corpus y premisa

- **Filtro (fase A):** los 4 lugares de la ronda 1. Son 1.647 URL únicas de
  `datos/corpus/df_corpus_5lugares.pkl`, repartidas por `…/juicio_5ind/url_lugares.csv`:
  Antioquia 494, Maicao 1.101, Oicatá 32 y Paraguachón 77.
- **Nacional y holdout (fase B):** `df_corpus_combinado_32deptos.pkl` +
  `scores_v2_32deptos.pkl` (unión por posición). Holdout: Cauca, Chocó y Cundinamarca.
- **Premisa visible (juez):** la de la ronda 1, reutilizada
  (`…/juicio_5ind/premisas_visibles.pkl` y `…/juicio_5ind_holdout/premisas_visibles_nacional.pkl`).
  Es solo el `texto`, truncado a `512 − 3 − 25` tokens, donde 25 son los tokens de la hipótesis
  más larga de la ronda 1. Ninguna hipótesis de esta ronda pasa de 25 tokens
  (`TOKENS_HIP_MAX` y `comprobar_tokens()` en `hipotesis_5ind_max_r2.py`; el script de GPU
  aborta si alguna la supera), así que el NLI ve con cada candidata al menos la premisa que ve
  el juez.

## 3. Candidatas

Textos exactos en `experimentos/hipotesis_5ind_max_r2.py` (fuente única). Por indicador: la
vigente `vig` (línea base, = V01 de la ronda 1) y 5 candidatas.

| Indicador | N1 | N2 | N3 |
|---|---|---|---|
| exclusión | La comunidad reclama regalías que no ha recibido por la explotación de un recurso. | Una empresa no le pagó a la comunidad las compensaciones de un proyecto. | Las regalías de una mina o de un pozo petrolero no llegan a la población local. |
| rechazo | La comunidad rechaza que construyan una mina, una represa o un parque eólico. | Habitantes protestan para impedir la explotación minera o petrolera en su región. | Pobladores exigen retirar un peaje, un relleno sanitario o una concesión. |
| desplazamiento | Familias fueron desplazadas de sus veredas por la violencia armada. | Llegaron a la ciudad familias desplazadas por el conflicto armado. | Personas tuvieron que dejar sus casas y sus tierras por amenazas o combates. |
| conflicto | Grupos armados ilegales se enfrentan entre sí por el control de esta zona. | Hay una guerra entre grupos criminales por el dominio de un territorio. | Actores armados mantienen una disputa violenta y prolongada por unas tierras. |
| grupos armados | Guerrilleros, disidentes de las FARC o paramilitares actúan en esta zona. | Un grupo armado organizado, como el ELN o el Clan del Golfo, opera en la región. | La población de esta zona vive bajo la presencia de guerrillas o paramilitares. |

P1/P2 = `p1`/`p2` de `hipotesis_5ind_max.py` (por ejemplo, grupos armados: «El ELN, las
disidencias o el Clan del Golfo tienen presencia en esta zona.» / «Hay presencia de guerrilla o
paramilitares en este territorio.»).

**Controles absurdos (reglas 1, 3 y 4).** Cada candidata lleva su **gemela de objeto absurdo**:
la misma frase con el mismo hueco por indicador que en la ronda 1 y solo «osos polares»
(exclusión y rechazo → el proyecto, «un criadero de osos polares»; desplazamiento → la causa,
«por los osos polares»; conflicto → el territorio, «una colonia de osos polares»; grupos armados
→ el actor, «osos polares»). Las gemelas de P1/P2 son `p1_abs`/`p2_abs` de la ronda 1. El
**absurdo total** es `ABSURDO_TOTAL` («En este territorio hay colonias de osos polares.», =
`NULA_TEST`) y es el mismo para todas. Prohibidos en controles: pingüinos, helio-3, caligrafía
y metano.

Las 5 candidatas por indicador se evalúan una por una contra la vigente. Cada comparación
cambia una sola cosa, la frase (regla 7).

## 4. Métricas y criterio de adopción (los de la ronda 1, sin cambios)

**Referencia.** Positivo = SÍ de ambos jueces; cualquier otra combinación es negativo. Las
etiquetas de la ronda 1 se reutilizan por URL; solo se juzgan artículos nuevos.

**Pool de la fase A (TREC).** Por indicador × lugar, se toma la unión de los top-15 de la
vigente y las 5 candidatas (score > 0, desempate por URL), más el pool de la ronda 1 y la
muestra de §5 que caiga en el lugar. Cada artículo nuevo se juzga una vez para los 5
indicadores. **Positivo de X en el lugar L** = cualquier artículo juzgado de L con SÍ/SÍ en X.

**Métricas.** La vigente se recalcula con esta misma referencia. Por candidata e indicador,
sobre los 4 lugares:
- **M1:** el artículo que fija el MAX (desempate por URL) es positivo. Si el MAX es 0, cuenta
  como verdadero si el lugar no tiene positivos y como falso si los tiene.
- **M2:** precisión@k con k = min(10, nº de artículos con score > 0), promediada en los 4
  lugares. Un lugar sin artículos > 0 vale 1 si no tiene positivos y 0 si los tiene.
- **M3:** violaciones de coherencia del MAX. Un lugar sin positivos debe quedar < 0.766; uno
  con positivos, ≥ 0.766.
- **M4:** MAX por lugar de la gemela de objeto absurdo y del absurdo total, proporción de
  artículos > 0.766 y razón MAX(gemela)/MAX(candidata).
- **M5:** solo reporte; nº de los 26 indicadores cuyo MAX lo fija el mismo artículo. Se
  reporta aparte cuántas veces conflicto y grupos armados comparten el artículo del MAX.
- **M6:** solo `presencia_grupos_armados`; AUC contra `silver.py`.
- **M2+:** solo reporte; M2 medio solo en los lugares con ≥ 1 positivo. No entra en el
  criterio 1 ni en la selección (ver §8).

**Kappa** de Cohen por indicador (SÍ frente a {NO, DUDOSO}) sobre todos los artículos juzgados
de los 4 lugares (ronda 1 + ronda 2). Con kappa < 0.4, o indefinida (ningún SÍ), ese indicador
no se adopta y se informa.

**Una candidata reemplaza a la vigente si cumple TODO:**
1. M2 medio ≥ max(0.60, M2(vig) + 0.20).
2. M1 verdadero en ≥ 3 de los 4 lugares, o en todos los lugares con algún positivo.
3. M3: no viola la coherencia en ningún lugar donde la vigente no la viola (como en la ronda 1).
4. M4, por lugar: la gemela de objeto absurdo tiene MAX < 0.766 y ≤ la de la vigente + 0.05.
   El absurdo total, MAX ≤ el de la vigente + 0.05 (en F1 es idéntico, así que no discrimina).
5. M6 (solo grupos armados): AUC ≥ AUC(vig) − 0.02.
6. Holdout (fase B): M2 medio en Cauca/Chocó/Cundinamarca ≥ 0.50 y ≥ el de la vigente.

El umbral 0.766 es el corte Bajo/Medio vigente del radar (otra vez el de producción desde la
reversión) y el mismo de la ronda 1. Es de nivel radar, no de indicador (límite declarado).

**Selección.** Hasta 2 finalistas por indicador pasan a la fase B: las que cumplen 1–5,
ordenadas por mayor M2, luego más lugares con M1 verdadero, luego menor MAX medio de la
gemela y, si sigue el empate, en el orden fijo N1 < N2 < N3 < P1 < P2. Si ninguna cumple 1–5,
el indicador queda igual y se registra por qué. Si pasan el holdout las dos finalistas, se
adopta la de mayor M2 en el holdout; si empatan, se aplica el mismo orden de desempate.

## 5. Exclusión de beneficios económicos: búsqueda de casos reales

En la ronda 1 no hubo ningún SÍ/SÍ (565 + 94 juzgados); el top de su propia vigente no los
encuentra. Por eso se juzgan **todos** los artículos cuya premisa visible contiene
`REGEX_MUESTREO_EXCLUSION` (regalía, compensación sin «caja de», consulta previa, «no han
recibido», indemnización), en el corpus nacional y en el de los 4 lugares. En el recuento
hecho al redactar este documento (premisas visibles de la ronda 1) son 237 URL, de las que 206
no se han juzgado. El script de la fase A lo recalcula e imprime. Van mezcladas y barajadas con
el pool de la fase A en los mismos lotes ciegos. La regex **solo sirve para evaluar**: no entra
en ningún score ni en producción.

- «En total» = todos los artículos juzgados en las dos rondas (565 + 94 + el pool nuevo + esta
  muestra).
- Si hay **< 5 SÍ/SÍ** de exclusión en total, se declara «no medible con este corpus», se
  informa al usuario y decide él (el indicador no se retira salvo que el usuario lo diga).
- Si hay **≥ 5 SÍ/SÍ**, exclusión se evalúa como los demás: en los 4 lugares, con los
  criterios 1–6. Los positivos fuera de esos lugares solo se reportan. No hay anexo posterior.
- Las etiquetas de esta muestra en Cauca, Chocó y Cundinamarca cuentan para la referencia del
  holdout (fase B), porque la regex no depende de las candidatas. No entran en la fase A.

## 6. Fase B: nacional, holdout y cortes (solo finalistas)

- GPU: cada finalista y su gemela sobre los 11.439 artículos (~7.3 min por hipótesis). La
  vigente, el sesgo y el absurdo total se reutilizan de `scores_v2_32deptos.pkl`.
- Holdout: pool con los top-15 (score > 0, desempate por URL) de la vigente y las finalistas en
  Cauca, Chocó y Cundinamarca. Se reutilizan las etiquetas de F7 (94) y las de §5 en esos
  departamentos, y se juzgan los nuevos (ids ciegos). Se aplica el criterio 6. M4 nacional en
  los 32 departamentos, solo como reporte.
- Si se adopta alguna, se recalibran los cortes (regla 2) **una sola vez**, con todas las
  adoptadas juntas, con el procedimiento de `b060b3b` (`exp_5ind_max_cortes.py`, radar sin
  redondear). Se comprueba que ninguna de las 12 anclas se rompa y se reportan accuracy y
  Spearman solo como constancia. Si el procedimiento no encuentra un par de cortes que respete
  las 12 anclas, se para y se informa, sin promover.
- La promoción a `src/` (cambiar solo el texto de la hipótesis en `Transformer_optimo.py`, más
  los cortes en `config_pipeline.py`) se hace **solo con visto bueno del usuario**.

## 7. Ejecución, costos y paradas

1. Fase A, GPU: las 35 hipótesis de `hipotesis_gpu()` (15 candidatas N, 15 gemelas y, como
   control de sanidad, las 5 vigentes) sobre los 1.647 artículos, ~37 min, en segundo plano y
   con checkpoint. Salida: `datos/scores/scores_5ind_r2_lugares.pkl`, con `ent_`/`neu_`/`con_`
   sin enmascarar. **Sanidad:** las 5 vigentes puntuadas ahora deben reproducir las de
   `scores_5ind_atomicas_lugares.pkl` con max|dif| < 1e-4; si no, se para antes de juzgar. Lo
   demás se reutiliza de ese pkl: vigente, P1/P2 y sus gemelas, sesgo y absurdo total.
2. Pool y lotes JSONL de ~40, barajados con semilla 20260923, ids `b0000…`, en
   `experimentos/resultados/juicio_5ind_r2/`. **Se juzga el pool entero, sin tope.** El pool
   nuevo no se conoce hasta tener los scores: estimado 200–400 artículos más los 206 de §5, unos
   10–15 lotes por juez. **Control entre rondas:** se mezclan 40 artículos ya juzgados en la
   ronda 1 (elegidos al azar con la misma semilla, con ids nuevos). Se reporta el acuerdo con
   sus etiquetas anteriores, por indicador, solo como reporte. La referencia sigue siendo la
   etiqueta de la ronda 1.
3. Métricas y selección. Tabla en `experimentos/RESULTADOS_5ind_MAX_r2.md`.
4. **Parada: informe intermedio al usuario y visto bueno antes de la fase B.**
5. Fase B (GPU ~15 min por finalista), holdout, cortes. **Parada:** informe en `informes/` y
   visto bueno antes de promover.

## 8. Límites conocidos, declarados de antemano

- En la ronda 1 ninguna frase reescrita pasó. El mejor M2 con solo cambiar la frase fue 0.38 en
  grupos armados, 0.17 en conflicto, 0.05 en desplazamiento y 0.00 en rechazo y exclusión. El NLI
  confirma la forma de la frase con independencia de su objeto (con la vigente de rechazo, la
  gemela de objeto absurdo da MAX 0.96–0.99). Es probable que ninguna candidata pase; ese es un
  resultado válido.
- Solo 4 lugares, dos pequeños (Oicatá 32, Paraguachón 77); pocos positivos de rechazo (4) y
  ninguno de exclusión en la ronda 1.
- En un lugar sin positivos, M2 vale 0 salvo que el MAX sea 0. Con las etiquetas de la ronda 1,
  Oicatá no tiene positivos en ningún indicador: el criterio 1 le exige a la frase puntuar 0 en
  todos sus artículos. Lo mismo exige el criterio 6 en Cundinamarca para desplazamiento. Por
  eso se reporta M2+ (solo lugares con positivos), sin cambiar el criterio: «ninguna pasa» no
  significa necesariamente que las frases no sirvan.
- El pool TREC no ve positivos fuera del top-15 de alguna candidata o de la ronda 1.
- Las candidatas se redactaron mirando los falsos positivos juzgados en la ronda 1 en los 4
  lugares (datos de diseño). Del holdout se conocían los recuentos de positivos (log F7), no
  sus artículos. Este es su segundo uso: ya se usó para validar la V08 en la ronda 1.
- Las candidatas N1 y N2 de conflicto son más estrechas que el codebook: nombran grupos
  armados o criminales, mientras el codebook admite «cualesquiera actores», por ejemplo
  comunidades frente a propietarios. N3 cubre las tierras. N1 se acerca al constructo de grupos
  armados; M5 reporta cuánto comparten el artículo del MAX.
- M6 de grupos armados usa una plata por palabras clave. Se reporta y exige el criterio 5, pero
  no desempata.
