# Pre-registro — Pre-filtro de relevancia social bajo MAX

Fecha: 2026-09-28 · Rama: `hipotesis-5ind-max` · Base: `6b03729` · Script: `experimentos/exp_prefiltro_max.py`

**A partir del commit que introduce este archivo, nada de §0–§7 cambia.** Toda desviación
posterior se registra en `contexto/08_log_decisiones.md` como desviación, con su motivo. Antes de
este commit solo se miraron conteos de etiquetas de los jueces (para fijar «suficiente muestra»);
ninguna métrica del pre-filtro se ha calculado.

## 0. Pregunta y refutación

**Pregunta:** con la agregación MAX y los 26 indicadores, ¿reintegrar el pre-filtro de relevancia
social (hipótesis `HIPOTESIS_SOCIAL`, score = P(entailment) crudo, umbral 0.85; el artículo con
score social < 0.85 recibe score 0 en los 26 indicadores) mejora el radar y los indicadores lo
bastante como para revertir el rechazo del 2026-08-31?

**Refutación:** si falla cualquiera de los criterios C1–C4 de §5, el pre-filtro NO se reintegra.
Un empate también es NO: gana el statu quo (sin pre-filtro).

## 1. Por qué se reabre (regla 10: evidencia nueva)

El rechazo del 2026-08-31 (`contexto/08_log_decisiones.md`, «A/B del pre-filtro social V2…») fue un
AUC por artículo contra el estándar de plata (2 de 26 indicadores) sobre el corpus nacional; el
A/B de radar del 2026-08-30 se hizo con P75. Hay dos hechos nuevos:

1. La agregación pasó de P75 a MAX y el efecto del pre-filtro sobre el radar bajo MAX nunca se
   midió. Con MAX solo cuenta la cabeza del ranking, y el AUC por artículo no la mide.
2. Hay una referencia nueva de jueces (SÍ de `juez-a` Y de `juez-b`, ciegos) para 5 indicadores,
   que permite medir la precisión en la cabeza del ranking.

El AUC por artículo contra plata no depende de la agregación: se reproduce exacto como
comprobación (bloque A), no como evidencia nueva.

**Regla 15** (decisión del usuario, 2026-09-28): el pre-filtro se admite como EXCEPCIÓN si gana. En
ese caso el score social se calcularía solo por dentro de `procesar()`, sin columna nueva en la
salida. La regla sigue valiendo para los 26 indicadores. Si el veredicto es REINTEGRAR, no se toca
`src/` ni se corren los lugares hasta que el usuario apruebe.

## 2. Variable única

**Máscara sí/no, con umbral 0.85.**

- 0.85 es el umbral calibrado para `HIPOTESIS_SOCIAL` y el del A/B del 2026-08-31.
  `hipotesis_v2.UMBRAL_SOCIAL` (0.65) es el heredado de la hipótesis anterior: por la regla 2 no aplica.
- Pasa el filtro si `score_social_v2 >= 0.85`; si no, el score de los 26 indicadores es 0.
- Todo lo demás es idéntico a producción: hipótesis V2, sesgo (media de las 4 `NULAS_CALIBRACION`),
  score corregido `s = clip(clip(ent − sesgo, 0)·(1 − neu), 0, 1)`, MAX por lugar, radar = promedio de
  los 26 MAX. `NULA_TEST` nunca entra en el sesgo (regla 4) y lleva la misma máscara.
- Los cortes se evalúan de dos formas: los vigentes (`Bajo < 0.766 <= Medio < 0.9233 <= Alto`) y
  los recalibrados para la distribución con máscara (regla 2). Recalibrar es consecuencia de cambiar
  lo que se mide, no una segunda variable.
- Sensibilidad (§4, solo descriptiva, no decide): umbrales 0.50, 0.65 y 0.75.

## 3. Datos

Todo offline salvo lo indicado. Los `.pkl` son compartidos y no versionados; los archivos nuevos
llevan nombre nuevo.

- **Nacional:** `datos/scores/scores_v2_32deptos.pkl` (11.439 × 58: `sesgo`, `score_social_v2`,
  `ent_`/`neu_` de las 26 y de `NULA_TEST`), unido POR POSICIÓN con
  `datos/corpus/df_corpus_combinado_32deptos.pkl` (se comprueba `titulo` y `departamento`). De ahí sale la `url`.
- **Referencia DANE:** `datos/referencia/comparacion_radares_V3.xlsx`
  (`radar_oficial_promedio`, `Clasificacion_radar_oficial_promedio`).
- **Lugares** (`datos/corpus/df_corpus_5lugares.pkl`, 1.647 artículos):
  - Scores de producción de los 26: `resultados/tablas_lugares_max/df_procesado_5lugares.pkl` (1-sep).
  - `ent`/`neu` de los 5 indicadores vigentes y `sesgo`: `datos/scores/scores_5ind_atomicas_lugares.pkl`
    (`ent_<ind>__vig`); son los que usaron las M1–M3 del plan.
  - **GPU (única):** `score_social_v2` y `ent`/`neu` de `NULA_TEST` para los 1.647, con
    `experimentos/exp_prefiltro_gpu_lugares.py` a `datos/scores/scores_prefiltro_lugares.pkl` (nuevo).
    Premisa = `texto`, `batch_size=32`, `max_length=512`, igual que producción. Antes: (i)
    `verificar_contra_produccion_v2` (paso 0 del skill; `max|dif| < 1e-4`); después: (ii) el
    `score_social_v2` y la nula de los 494 de Antioquia coinciden con los del pkl nacional, unidos
    por `url` (`max|dif| < 1e-4`); (iii) la nula coincide con `ent_/neu_ABSURDO_TOTAL` del pkl de
    atómicas, que es el mismo texto (`max|dif| < 1e-4`). Si algo falla, se para.
  - Dos convenciones de lugar: **producción** (Paraguachón 20, `departamento` del corpus) para el
    radar (D(b), F); **plan** (`experimentos/resultados/juicio_5ind/url_lugares.csv`, Paraguachón 77,
    57 de ellos también de Maicao) para B y C, como las M1–M3.
- **Jueces** (etiqueta 1 = SÍ de los dos), 940 artículos únicos, con la unión y deduplicación de
  `exp_5ind_max_r2_metricas.referencia()`: `juicio_5ind` (565) + `juicio_5ind_holdout` (94) +
  `juicio_5ind_r2` sin los 40 de control (281). Los 22 juzgados de `juicio_modelo_nli` no se usan
  (no están en las fuentes del encargo). 5 indicadores: `exclusion_beneficios_economicos`,
  `rechazo_proyecto`, `desplazamiento_forzado`, `conflicto_territorial`, `presencia_grupos_armados`.
- **Holdout:** artículos del corpus nacional con `departamento` ∈ {Cauca, Chocó, Cundinamarca}.

## 4. Métricas

Todas con y sin máscara. IC95% = percentiles 2.5 y 97.5 de 2.000 remuestreos con reemplazo,
semilla 20260928, generador nuevo por bloque y por umbral (mismos índices en todos los umbrales);
en A la semilla es la del script viejo (20260831), ver A. `AUC` = `silver.auc` (rango promedio).
«Cruda» = `ent`; «corregida» = `s`. Los decimales de los informes son 4.

**A. AUC por artículo contra plata** (nacional, 11.439). `grupos_etnicos_existentes` y
`presencia_grupos_armados`, etiquetas de `silver.etiquetar` con `hipotesis_base.KEYWORDS_SILVER`
(título + texto; ≥ 2 palabras clave = positivo, 0 = negativo, 1 = descartado). Cruda y corregida,
sin/con máscara; delta con IC95% por bootstrap pareado; retención de positivos. Igual que
`exp_prefiltro_auc_indicador.py` (se importan/replican sus funciones, sin llamar a su `main()`), con
`default_rng(20260831)` y el mismo orden de llamadas: los 2 indicadores reales (cruda, corregida) y
luego la nula contra las mismas etiquetas de cada indicador (cruda, corregida). **Reproducción
exacta** contra `experimentos/resultados/exp_prefiltro_auc_indicador.xlsx` y el log [2026-08-31]: AUC
sin/con iguales a ≤ 1e-9; delta e IC95% iguales a ≤ 5e-5. Si no, se PARA y se reporta. En los
umbrales de la sensibilidad se usa el mismo procedimiento con generador nuevo.

**B. AUC por artículo contra los jueces.** Por indicador, sobre los artículos juzgados que están en
los 4 lugares (convención del plan) o en el holdout: 759 (646 + 113). Positivo = SÍ de los dos;
negativo = todo lo demás juzgado. Corregida (principal) y cruda (secundaria); scores de producción en
los lugares (atómicas) y del pkl nacional en el holdout. Delta con IC95% (remuestreo pareado de los
artículos juzgados). **Suficiente muestra** = ≥ 20 positivos y ≥ 20 negativos: hay 29
(`desplazamiento_forzado`), 34 (`conflicto_territorial`) y 128 (`presencia_grupos_armados`);
`rechazo_proyecto` (8) es solo descriptivo y `exclusion_beneficios_economicos` (0) no tiene AUC.

**C. M1–M3 del MAX con jueces** (definiciones de `PREREG_5ind_MAX.md` §4, sobre la vigente).
- Celdas: (indicador, lugar) de los 5 indicadores × 4 lugares (20) y (`presencia_grupos_armados`,
  Cauca/Chocó/Cundinamarca) (3). En el holdout solo grupos armados: el pool del holdout se armó con el
  top-15 de grupos armados y de exclusión, así que el top-k de los demás indicadores no está juzgado.
- Por celda, con `positivos` = SÍ/SÍ juzgados de ese indicador dentro del lugar: orden por (score
  desc, `url` asc) de los artículos con score > 0; `k = min(10, n con score > 0)`;
  **M2** = precisión@k (si k = 0: 1 si no hay positivos, 0 si los hay); **M1** = el artículo que fija
  el MAX es positivo (si k = 0: verdadero si no hay positivos); **M3** = violación si (sin positivos y
  MAX ≥ 0.766) o (con positivos y MAX < 0.766).
- **Cotas con máscara** (pueden entrar al top-k artículos sin juzgar): cota inferior = no juzgado
  cuenta como NO; cota superior = cuenta como SÍ. Se reporta la **cobertura** (juzgados en el top-k / k).
  Sin máscara la cobertura debe ser 1 por construcción del pool (se verifica; si no lo fuera, se
  reporta). **Para decidir se usa la cota inferior.**
- **Unidades de decisión:** grupos armados (7 celdas: 4 lugares + 3 del holdout) y el conjunto de las
  23 celdas. Métricas: M1 (fracción de celdas con M1 verdadero) y M2 (media de M2). Una unidad es
  elegible si tiene ≥ 20 artículos positivos distintos en sus celdas: grupos armados tiene 128; el
  conjunto, más; conflicto territorial tiene 18 en sus 4 lugares (21 pares artículo-lugar, porque
  Paraguachón repite artículos de Maicao), desplazamiento 11, rechazo 4 y exclusión 0, así que esas
  unidades son solo descriptivas. Se reportan también M2+ y M1+ (solo celdas con ≥ 1 positivo) y M3
  (número de violaciones), sin uso en la decisión.
- **IC95%:** remuestreo de los artículos de cada lugar con reemplazo (mismo remuestreo para los
  indicadores y para la nula, y para ambas condiciones); los positivos y las celdas sin positivos se
  fijan con los datos originales.
- **Control de la nula en C:** la misma métrica calculada con `NULA_TEST` corregida (con y sin máscara)
  contra las mismas etiquetas del indicador de la celda. La **mejora neta** = Δreal − Δnula, con
  el IC95% del remuestreo pareado.

**D. Control absurdo con `NULA_TEST`, con la misma máscara.**
- (a) AUC de la nula contra las etiquetas de A (plata) y de B (jueces), cruda y corregida, sin/con
  máscara, con delta e IC95%; y la mejora neta de B (Δreal − Δnula, IC95% pareado).
- (b) Bajo MAX, **brecha** = radar_real − MAX de la nula corregida, por departamento (32) y por
  lugar (4, convención de producción), sin/con máscara; se reporta la brecha media y el número de
  unidades cuya brecha baja. Radar_real = promedio de los 26 MAX.
- (c) Media y proporción > 0.9 de la nula, cruda y corregida, sobre todos los artículos (nacional) y
  por lugar, sin/con máscara.

**E. Radar nacional MAX** (32 departamentos, sin redondear).
- Spearman contra `radar_oficial_promedio` (continuo).
- Las 12 anclas de `exp_correlacion_v2_nacional` (Cundinamarca, Quindío, Boyacá, San Andrés, Caldas y
  Risaralda nunca Alto; Cauca, Nariño, Chocó, Arauca, Norte de Santander y Putumayo nunca Bajo) y la
  accuracy contra `Clasificacion_radar_oficial_promedio` (solo constancia, n = 32), con **cortes
  vigentes** y con **cortes recalibrados** para el radar con máscara: `exp_5ind_max_cortes.elegir_cortes`
  (huecos naturales > 0.008, entre los pares que no rompen ninguna ancla el más balanceado; sin
  mirar el oficial). Si ningún par evita romper anclas: «sin cortes válidos».
- Artefacto de tamaño: Spearman(radar, número de artículos por departamento).

**F. Impacto** (descriptivo).
- % de artículos enmascarados: nacional y por lugar (convención de producción).
- Por departamento y por lugar: radar sin y con máscara, diferencia y clase (cortes vigentes y
  recalibrados). Departamentos que cambian de clase: (i) vigentes → vigentes y (ii) vigentes sin
  máscara → recalibrados con máscara.
- Por indicador (26 × 32 celdas): media de |ΔMAX| entre departamentos, nº de celdas con
  |ΔMAX| > 0.05 y nº de celdas que pasan a 0 (MAX sin máscara > 0 y con máscara = 0).

**Sensibilidad** (umbrales 0.50, 0.65, 0.75; no decide): A, D(b), E y F resumidos, más la lectura de
C1–C4 (con el mismo procedimiento) por si algún umbral las pasara todas: entonces se registra como
candidato para un experimento aparte (regla 7); aquí no se adopta.

**Sanidad (bloqueante; si falla, se para).** Sin máscara se reproduce la producción vigente:
1. Radar nacional MAX con 0.766/0.9233: clasificación 6/19/7 y `elegir_cortes` devuelve 0.766/0.9233.
2. Lugares: radar y clase de cada lugar iguales a los del encabezado de
   `resultados/tablas_lugares_max/resumen_indicadores_MAX_y_articulos_por_lugar.xlsx`, y MAX por
   indicador iguales (4 decimales) en los lugares no Bajo. El lugar «Antioquia (2023)» debe coincidir
   con el departamento Antioquia del nacional.
3. Scores de atómicas vs producción en los 5 indicadores (`max|dif| < 1e-4`).
4. Las M1–M3 sin máscara reproducen las filas `vig` de
   `experimentos/resultados/juicio_5ind_r2/metricas_r2.xlsx` (lugares) y `V01` de
   `experimentos/resultados/juicio_5ind_holdout/metricas_holdout.csv` (holdout). En el holdout la
   referencia de aquí incluye también los 19 juzgados de la ronda 2 de esos departamentos (no están
   en el top-15 de grupos armados); si hubiera una diferencia, se explica con el artículo que la causa.

## 5. Regla de decisión (umbral 0.85)

Se REINTEGRA solo si se cumplen los 4 criterios. Si falla uno, NO. Un empate es NO.

- **C1 — Control absurdo (eliminatorio):** con la máscara no baja la brecha media radar_real − nula
  bajo MAX, ni en los 32 departamentos ni en los 4 lugares (D(b): brecha media con máscara ≥ sin
  máscara en ambos conjuntos; diferencia dentro de ±5e-5 = «igual», no baja).
- **C2 — Radar nacional** con cortes recalibrados: 0 anclas rotas (existe un par de cortes
  válido) y Spearman con máscara ≥ Spearman sin máscara.
- **C3 — AUC por artículo:** si el AUC en score corregido cae más de 0.04 en algún indicador con
  referencia (A: los 2 de plata; B: los de suficiente muestra), la mejora que exige C4 tiene que venir
  del bloque C, con la cota inferior (es la razón mecanicista explícita: con MAX solo cuenta la cabeza
  del ranking). C3 pasa si no se dispara, o si se dispara y C4 se cumple con una métrica del bloque C.
- **C4 — Mejora distinguible** en al menos una métrica con suficiente muestra:
  - Métricas elegibles: ΔAUC corregida de B (desplazamiento, conflicto, grupos armados) y ΔM1, ΔM2 de C
    (cota inferior) en las 2 unidades de decisión (grupos armados y las 23 celdas). Sus IC95% deben
    excluir cero a favor de la máscara.
  - Debe superar a la nula: el IC95% de la mejora neta (Δreal − Δnula) también excluye cero a favor de
    la máscara. Si mejora igual que la nula, es un artefacto de tema.
  - Un Δ Spearman de E cuenta solo si es ≥ +0.15 (menos es ruido con n = 32); no cuenta si C3 se disparó.
  - No hay corrección por multiplicidad: el criterio es «al menos una métrica» y esa es la definición
    del encargo. Si el único pase fuera marginal, así se comunica.

## 6. Qué se hace según el veredicto

- **NO REINTEGRAR:** `src/` intacto. Se vuelven a correr los indicadores y el radar de los 4 lugares
  con `src/` tal cual (`experimentos/exp_prefiltro_correr_lugares.py`: lee `df_corpus_5lugares.pkl` sin
  regenerarlo, comprueba su sha256 antes y después, y escribe a `resultados/tablas_lugares_max_2026-09-28/`),
  se compara con `resultados/tablas_lugares_max/` (1-sep), se corre `python src/test_integracion.py`
  (10/10) y se escribe el informe 11.
- **REINTEGRAR:** parar antes de tocar `src/`; reportar el veredicto, los cortes recalibrados
  propuestos y el plan de implementación (score social dentro de `procesar()`, máscara sobre los 26
  indicadores, sin columna nueva, tests). El usuario aprueba antes de implementar.
- En ambos casos: `experimentos/RESULTADOS_prefiltro_max.md`, entrada en `contexto/08_log_decisiones.md`
  y commit local. Sin push ni merge.

## 7. Límites declarados de antemano

- La plata cubre 2 de 26 indicadores y los jueces 5 de 26. En los otros 21 el efecto solo se ve en el
  impacto (F). `exclusion_beneficios_economicos` no tiene positivos (no medible): cuenta en el radar,
  no en la decisión.
- Los 940 juzgados son un pool (TREC) armado con el top del score sin máscara: favorece a la vigente.
  Con máscara pueden entrar artículos sin juzgar; de ahí las cotas y la cobertura.
- Bases pequeñas: Oicatá (32) sin positivos de ningún indicador; Paraguachón 20 (producción) o 77 (plan);
  rechazo con 8 positivos.
- El bootstrap por artículo ignora la dependencia entre artículos del mismo medio o hecho.
- E tiene n = 32: solo el Spearman ≥ +0.15 se distingue del ruido (regla 11).
- Un solo umbral decide (0.85, por diseño del encargo); los otros son sensibilidad.

## 8. Salidas

- `experimentos/resultados/exp_prefiltro_max.xlsx` (una hoja por bloque A–F, con más de una tabla
  cuando hace falta, más la sensibilidad y la decisión) y `experimentos/resultados/exp_prefiltro_max.log`.
- `experimentos/RESULTADOS_prefiltro_max.md`, entrada `[2026-09-28]` en `contexto/08_log_decisiones.md`.
- `datos/scores/scores_prefiltro_lugares.pkl` (nuevo, local, no versionado).
- Si NO: `resultados/tablas_lugares_max_2026-09-28/`, `experimentos/resultados/exp_prefiltro_lugares_recorrida.xlsx`
  (comparación con el 1-sep) e `informes/11_informe_prefiltro_social_max.md`.
