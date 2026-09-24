# Pre-registro — Prueba de un modelo NLI alternativo (SOLO PRUEBAS)

Fecha: 2026-09-23 · Rama: `prueba-modelo-nli` (worktree
`C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\prueba_modelo_nli`), creada desde
`hipotesis-5ind-max` en 9b14489 · Antecedentes: `informes/05_informe_consolidado_5ind_MAX.md`
§7, `experimentos/PREREG_5ind_MAX_r2.md` y `contexto/08_log_decisiones.md` [2026-09-23]
«REAPERTURA».

**Estado: CONGELADO** (2026-09-23) tras la revisión única de `orquesta-lead` sobre 5909a37: 4
bloqueantes y 8 menores, adoptados los 12 (`contexto/08_log_decisiones.md` [2026-09-23]
«pre-registro congelado»). A partir del commit de congelamiento nada de §0–§8 cambia, y toda
desviación va al log como desviación.

## Restricciones (del usuario, no negociables)

- **El modelo nuevo es solo para pruebas.** No entra a `src/` ni en esta rama ni en ninguna
  otra; `src/` no se toca. Todo se corre desde `experimentos/`. La rama no se fusiona. Si el
  modelo pasa, se informa y el usuario decide aparte; esa decisión queda fuera de este
  pre-registro.
- Agregación por lugar = **MAX**.
- **Regla 15:** las 26 hipótesis vigentes se usan con su texto idéntico. La fórmula es la de
  producción, `s(h) = clip(clip(ent − sesgo, 0)·(1 − neu), 0, 1)`, y el `sesgo` es la media de las
  4 `NULAS_CALIBRACION` puntuadas **con el mismo modelo**. Ni compuertas, ni `min`, ni restas, ni
  columnas nuevas.
- Producción = solo NLI; el LLM solo juzga, en local. Referencia = SÍ de `juez-a` (sonnet)
  **y** `juez-b` (opus), ciegos, con el codebook de la ronda 1 (agentes sin cambios).
- No se retira ningún indicador. Sin push ni merge sin aprobación. Adopciones y rechazos al log.

**Una sola variable (regla 7): el modelo.** La premisa es la de producción (solo `texto`,
`truncation=True`, `max_length=512`), igual que las hipótesis, la fórmula, la agregación y los
cortes de referencia. El tokenizador es parte del modelo y cambia con él (§2).

## 0. Pregunta y refutación

**Pregunta:** ¿un NLI multilingüe más grande y con entrenamiento adversarial lee el *objeto* de
la frase? Es decir, ¿su versión con «osos polares» deja de puntuar como la frase real, y el MAX
por lugar de los 5 indicadores lo fija un artículo que de verdad reporta el concepto?

**Refutación:** el modelo se rechaza si ningún indicador pasa el filtro de la etapa 1 (§4), o si
ninguno cumple los criterios 1–5 en la etapa 2 (§5).

**Veredicto por indicador:** «mejora con el modelo nuevo» si cumple los criterios 1–7 (§5 y §6).
Si cumple 1–5 y falla 6 o 7, queda «no confirmado». En esta prueba nada se adopta: el veredicto
va al informe y decide el usuario.

## 1. Modelo

- **Candidato:** `vicgalle/xlm-roberta-large-xnli-anli`, revisión fijada
  `85981da85b85045fecd6e81e501767de7da370eb`, licencia MIT. Es XLM-RoBERTa-large (24 capas,
  1024 de ancho, 514 posiciones), entrenado con MNLI, XNLI y ANLI. Tiene 3 clases: `id2label` = 0
  contradiction, 1 neutral, 2 entailment. El orden se resuelve por nombre (`_resolver_labels`),
  como en producción.
- **Referencia:** el modelo de producción `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
  (12 capas, 768 de ancho), con sus scores ya calculados: `datos/scores/scores_5ind_atomicas_lugares.pkl`
  (4 lugares) y `datos/scores/scores_v2_32deptos.pkl` (nacional).
- **Descarga (requiere confirmación del usuario):** en la revisión fijada el repositorio tiene
  `config.json`, `model.safetensors` (2.239.626.978 bytes, SHA256
  `3a67d41406a0f00a5e193725e99091efad91be32a40504e892abb1229f466c66`), `sentencepiece.bpe.model`,
  `special_tokens_map.json` y `tokenizer_config.json` (API de Hugging Face, consultada el
  2026-09-23). Se bajan solo esos 5 archivos; no se baja `pytorch_model.bin`. Se usa
  `huggingface_hub.snapshot_download(..., revision=<sha>, allow_patterns=[...])` o, si Python no
  valida el certificado de Hugging Face (pasa en esta máquina; curl sí conecta), curl sobre
  `https://huggingface.co/<repo>/resolve/<sha>/<archivo>`. En los dos casos los archivos van a
  `~/.cache/huggingface/hub/models--vicgalle--xlm-roberta-large-xnli-anli/snapshots/<sha>/`, y
  se comprueban el SHA256 del safetensors y los tamaños. No hay `tokenizer.json`, así que hace
  falta el paquete `sentencepiece` (no instalado; se instala con pip, previa confirmación). El
  modelo y el tokenizador se cargan sin red, desde esa ruta.
- **Inferencia:** fp32 (sin fp16, para no añadir una segunda variable), `batch_size=16` (8 si
  no cabe en los 6 GB de la RTX 4050). El tamaño de lote no cambia el resultado más allá de
  1e-4: se comprueba en 50 artículos con lote 16 frente a 8. **Si difiere más de 1e-4, todo se
  corre con lote 8.**
- **Etiquetas del modelo nuevo (antes de la etapa 1).** Su orden es el contrario al de
  producción: 0 = contradiction y 2 = entailment. Se comprueba con una aserción que
  (ent, neu, con) = (2, 1, 0), resuelto por nombre; si cae al fallback de `_resolver_labels`, se
  aborta. Además, dos pares de control: frases idénticas → ent > 0.9; frases contrarias →
  con > 0.9. Se miden también los 4 tokens especiales del tokenizador con un par real.
- **Sanidad del código:** el script de GPU, corrido con el modelo de producción y **el mismo
  lote que la etapa 1** sobre 300 artículos y la vigente de grupos armados, debe reproducir
  `scores_5ind_atomicas_lugares.pkl` con max|dif| < 1e-4. Los 300 son los de `texto` más largo
  (desempate por URL), para que la truncación entre en juego. Si no se reproduce, se para: el
  script no aísla el modelo.

## 2. Corpus y premisa

- **Etapas 1–2:** los 4 lugares de las rondas 1–2 (`datos/corpus/df_corpus_5lugares.pkl`, 1.647
  URL, repartidas por `experimentos/resultados/juicio_5ind/url_lugares.csv`).
- **Etapa 3:** `df_corpus_combinado_32deptos.pkl`, unido por posición con
  `scores_v2_32deptos.pkl`. Holdout: Cauca, Chocó y Cundinamarca.
- **Premisa del juez:** la de las rondas 1–2 (`…/juicio_5ind/premisas_visibles.pkl` y
  `…/juicio_5ind_holdout/premisas_visibles_nacional.pkl`), así que las 940 etiquetas siguen
  valiendo. **Cobertura** (antes de la GPU, solo CPU): el modelo nuevo ve `512 − 4 − n_hip`
  tokens de su propio tokenizador, donde `n_hip` es la hipótesis más larga de la etapa (las 15
  en las etapas 1–2, las 36 en la 3), medida con el tokenizador nuevo. Por artículo se cuentan
  los tokens XLM-R de la premisa del juez que quedan fuera de esos `508 − n_hip`. Se reportan
  la distribución y la proporción de artículos con alguna pérdida. **Si más del 5 % de los
  artículos pierde más de 10 tokens**, la etapa 1 se corre igual (no usa jueces), pero se para
  antes de juzgar (etapa 2 u holdout) y decide el usuario: el juez estaría viendo más texto que
  el modelo.

## 3. Valores de referencia del modelo actual (fijados de antemano)

De `experimentos/RESULTADOS_5ind_MAX_r2.md` (vigente, referencia de 940 juzgados). Lugares
A/M/O/P = Antioquia / Maicao / Oicatá / Paraguachón.

| Indicador | Positivos A/M/O/P | M2 | M1 (de 4) | MAX vigente | MAX gemela |
|---|---|---|---|---|---|
| exclusión | 0/0/0/0 | 0.00 | 0 | 1.00/1.00/0.99/0.99 | 0.99/0.99/0.90/0.98 |
| rechazo | 1/3/0/0 | 0.00 | 0 | 0.99/1.00/0.98/0.99 | 0.98/0.99/0.97/0.96 |
| desplazamiento | 10/1/0/0 | 0.05 | 0 | 0.99/0.98/0.52/0.98 | 0.98/0.96/0.70/0.94 |
| conflicto | 10/8/0/3 | 0.07 | 1 | 1.00/0.99/0.90/0.99 | 0.95/0.99/0.89/0.72 |
| grupos armados | 42/45/0/5 | 0.17 | 2 | 1.00/0.98/0.65/0.99 | 0.67/0.69/0.65/0.36 |

Absurdo total, MAX por lugar: 0.38/0.57/0.43/0.21. M6 (AUC de grupos armados contra la plata):
0.788. Las gemelas son las `vig_abs` de `experimentos/hipotesis_5ind_max.py`.

Base para el criterio 3 y para el reporte, en el orden de la tabla (exclusión, rechazo,
desplazamiento, conflicto, grupos armados): M3 (violaciones de coherencia) 4/2/1/1/0; M2+
—/0.00/0.10/0.10/0.23; kappa −0.00/0.44/0.88/0.87/0.94. M1, M2, MAX, gemela, absurdo y M6 de la
base no cambian con la referencia ampliada, porque su top-10 ya está juzgado (log, revisión
final de r2, punto 7). Con la referencia ampliada solo se recalculan los positivos por lugar y
M3. La base se lee de las columnas `vig` de `experimentos/resultados/juicio_5ind_r2/candidatas_r2.pkl`.

## 4. Etapa 1 — filtro sin jueces (GPU, 4 lugares)

**Hipótesis (15):** las 5 vigentes (`vig`), sus 5 gemelas (`vig_abs`), las 4
`NULAS_CALIBRACION` y `ABSURDO_TOTAL` (textos de `hipotesis_5ind_max.py`). Salida con `ent_`,
`neu_` y `con_` sin enmascarar (regla 8) en
`experimentos/resultados/modelo_nli/scores_xlmr_lugares.pkl`, que no se versiona, con
checkpoint. Costo estimado: 1–1.5 h de GPU (no medido; se mide con la primera hipótesis y se
informa).

**Filtro, por indicador y con el modelo nuevo:**
- (a) la gemela de la vigente queda con MAX < 0.766 en al menos 3 de los 4 lugares;
- (b) la vigente mantiene MAX ≥ 0.766 en todos los lugares con al menos 1 positivo, para no
  pasar el filtro solo por apagarse.

**La parada se decide solo con rechazo, desplazamiento y conflicto**, los indicadores cuya
gemela actual supera 0.766 en ≥ 3 lugares (§3). Grupos armados ya cumple (a) y (b) con el modelo
actual (gemela 0.67/0.69/0.65/0.36), así que el filtro no lo discrimina. Pasan a la etapa 2 los
de esos tres que cumplen (a) y (b). **Si ninguno de los tres pasa, se para**, se registra el
rechazo del modelo y se informa. Si alguno pasa, grupos armados entra también a la etapa 2 y su
gemela se controla con el criterio 4.

Exclusión no entra al pool ni a la parada. Sigue «no medible» salvo que se llegue a ≥ 5 SÍ/SÍ en
total (regla §5 del pre-registro r2). Se reporta su número de SÍ/SÍ; si llega a ≥ 5, se informa y
decide el usuario, porque su top-10 con el modelo nuevo no estaría juzgado.

**Solo reporte:** distribución del `sesgo` (media, P95, % > 0.5), proporción de artículos con
s > 0.766 por indicador, MAX del absurdo total, cobertura de §2, la razón MAX(gemela)/MAX(vigente)
por lugar (`razon_abs`, que no depende de la escala; el corte 0.766 sí, ver §8) y M2 provisional
con las etiquetas existentes. Ese M2 va sin la aserción de top-10 juzgado de
`exp_5ind_max_r2_metricas.py` y cuenta aparte los artículos del top-10 que no están juzgados.

## 5. Etapa 2 — juicio y criterios (4 lugares)

- **Pool TREC:** para cada indicador que entra a la etapa 2 (§4) y cada lugar, el top-15 de la vigente
  con el modelo nuevo (score > 0, desempate por URL). Se juzgan solo las URL que no tienen
  etiqueta entre las 940. Cada artículo se juzga una vez para los 5 indicadores. Se mezclan 40
  artículos ya juzgados como control entre rondas, elegidos al azar entre los 940 con la semilla
  20260924 y con ids nuevos (solo reporte; la referencia sigue siendo su etiqueta anterior).
  Lotes JSONL de 40, barajados con semilla 20260924, ids `c0000…`, en
  `experimentos/resultados/juicio_modelo_nli/`. Se juzga el pool entero, sin tope.
- **Métricas:** M1–M4, M6 y M2+, igual que en `exp_5ind_max_r2_metricas.py`, solo para los
  indicadores del pool. **M5 no se calcula en la etapa 2**: la plantilla toma los otros 21
  indicadores del modelo actual y mezclaría los dos modelos. La kappa se calcula sobre todos los
  juzgados de los 4 lugares. La candidata es la vigente con el modelo nuevo; la línea base es la
  vigente con el modelo actual, recalculada con la referencia ampliada (§3).
- **Criterios 1–5 del pre-registro r2 §4, sin cambios:**
  1. M2 ≥ max(0.60, M2 de la base + 0.20).
  2. M1 verdadero en ≥ 3 lugares, o en todos los que tienen positivos.
  3. Ninguna violación nueva de coherencia.
  4. En cada lugar, la gemela (`vig_abs` con el modelo nuevo) < 0.766 y ≤ `vig_abs` con el
     modelo actual (§3, MAX gemela) + 0.05; el absurdo total con el modelo nuevo ≤
     0.38/0.57/0.43/0.21 + 0.05 (aquí sí discrimina, porque cambia el modelo).
  5. En grupos armados, M6 ≥ base − 0.02.

  Kappa < 0.4 o indefinida: no cuenta como mejora.
- **Resultado:** un indicador pasa la etapa 2 si cumple 1–5; el veredicto final exige además 6
  y 7 (§0). Si ninguno cumple 1–5, se para, se registra el rechazo y se informa.

## 6. Etapa 3 — escala nacional (solo si algún indicador cumple 1–5)

- **GPU:** las 26 vigentes, las 4 nulas, `NULA_TEST` y las 5 gemelas `vig_abs` (36 hipótesis)
  sobre los 11.439 artículos, con checkpoint. Estimado ~26 min por hipótesis, ~15 h en total (no
  medido). Se hace en segundo plano y puede ocupar varias sesiones.
- **Criterio 6 (holdout),** para los indicadores que cumplieron 1–5: M2 medio en
  Cauca/Chocó/Cundinamarca ≥ 0.50 y ≥ el del modelo actual. Pool: unión de los top-15 de la
  vigente con el modelo nuevo y con el actual (`scores_v2_32deptos.pkl`) en esos 3
  departamentos, como en r2 §6, para que la base también tenga su top-10 juzgado. Se reutilizan las 94 etiquetas de F7 y las de la muestra de exclusión en
  esos departamentos, y se juzgan las nuevas (ids `d0000…`).
- **Criterio 7 (resto del radar),** porque el modelo cambia los 26 indicadores:
  - (a) en los 2 indicadores con estándar de plata (`presencia_grupos_armados` y
    `grupos_etnicos_existentes`), AUC ≥ la del modelo actual − 0.02;
  - (b) proporción nacional de artículos con s(`NULA_TEST`) > 0.766 ≤ la del modelo actual +
    0.01. Esto detecta un modelo que dice que sí a todo.
- **Cortes (regla 2):** procedimiento de `b060b3b` (`exp_5ind_max_cortes.py`, radar sin
  redondear) sobre el radar de 26 indicadores con MAX calculado con el modelo nuevo, comprobando
  las 12 anclas. Si no hay un par que las respete, se informa. Accuracy, Spearman frente al DANE
  y clasificación 6/19/7, solo como constancia.
- **Sin promoción:** el resultado va a un informe en `informes/` (el siguiente número) y el
  usuario decide.

## 7. Ejecución, costos y paradas

1. Revisión única de `orquesta-lead` sobre este borrador, adoptar sus correcciones y congelar
   (commit).
2. Confirmación del usuario para descargar el modelo (2.240 MB, Hugging Face,
   `vicgalle/xlm-roberta-large-xnli-anli`).
3. Etiquetas y pares de control, lote 16 frente a 8, sanidad del código con el lote elegido, cobertura de la premisa (CPU) y etapa 1 (GPU ~1–1.5 h). **Parada si nadie pasa
   el filtro.**
4. Etapa 2: pool, jueces en paralelo y en segundo plano, consolidación, métricas. Tabla en
   `experimentos/RESULTADOS_modelo_nli.md`. **Parada: informe intermedio y visto bueno del
   usuario antes de la etapa 3.**
5. Etapa 3 (~15 h de GPU), holdout y cortes. **Parada:** informe en `informes/` y decisión del
   usuario.
6. **Limpieza cuando el usuario lo diga:** borrar el worktree
   (`git worktree remove ../prueba_modelo_nli`), la rama y el modelo de la caché de Hugging Face
   (`~/.cache/huggingface/hub/models--vicgalle--xlm-roberta-large-xnli-anli`).

## 8. Límites conocidos, declarados de antemano

- No hay evidencia previa de que un modelo más grande corrija el defecto: los modelos NLI tienden
  a apoyarse en el solapamiento léxico. ANLI lo reduce, pero no lo elimina. Un resultado negativo
  es válido.
- El candidato es de 2021 y está poco descargado; el modelo actual se entrenó con más datos
  (NLI en 26 idiomas más ANLI, WANLI, FEVER y LingNLI). Lo que se prueba es sobre todo la
  capacidad: el doble de capas y más ancho.
- El filtro de la etapa 1 usa el corte 0.766 del radar de producción, calibrado para el modelo
  actual. Es un límite declarado: la escala del modelo nuevo puede ser distinta, y por eso la
  etapa 3 recalibra.
- Mismos límites que las rondas 1–2: 4 lugares (Oicatá sin positivos), pocos positivos en
  rechazo y ninguno en exclusión, pool TREC y jueces LLM.
