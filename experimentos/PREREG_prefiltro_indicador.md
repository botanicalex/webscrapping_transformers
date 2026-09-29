# Pre-registro — Pre-filtro por indicador (listas de objeto) bajo MAX, etapa 1

Fecha: 2026-09-28 · Rama: `hipotesis-5ind-max` · Base: `0ec5d28` · Scripts: `experimentos/exp_prefiltro_indicador_pool.py`
(pool y lotes), `experimentos/exp_prefiltro_indicador_gpu.py` (gemelas del holdout) y
`experimentos/exp_prefiltro_indicador.py` (análisis).

**A partir del commit que introduce este archivo, nada de §0–§9 cambia.** Toda desviación posterior se registra en
`contexto/08_log_decisiones.md` como desviación, con su motivo. Antes de este commit solo se leyeron resultados ya
versionados (ronda 1, F7, informe 11) y se tomó la huella de las listas; ninguna métrica nueva se ha calculado y
ningún artículo del holdout se ha elegido para el juicio.

## 0. Pregunta y refutación

**Pregunta:** ¿el pre-filtro por indicador —una lista de palabras de objeto por indicador, exigida en la premisa
visible antes de puntuar— aporta valor al radar MAX sin empeorar ningún indicador?

**Refutación (NO ADOPTAR):** (i) ninguna lista cumple (a)–(d) de §4; o (ii) el mecanismo combinado no cumple los tres
criterios del radar de §6 en ninguna de las configuraciones que §6 permite probar; o (iii) hay empate con el statu quo
(§6). Gana el statu quo (sin mecanismo).

## 1. El mecanismo

- **Mecanismo único para los 26 indicadores**, aplicado antes de puntuar (por dentro de `procesar()`, sin columnas
  nuevas). Cada indicador **con lista** exige que su objeto aparezca en la premisa visible normalizada (minúsculas,
  sin tildes): `score' = s × 1[regex ∈ premisa]`, con `s = clip(clip(ent − sesgo, 0)·(1 − neu), 0, 1)`. Los indicadores
  **sin lista** pasan sin filtro. Es la compuerta de la F8 generalizada.
- **Listas: las 5 de `REGEX_F5`** de `experimentos/hipotesis_5ind_max.py`, **congeladas**: no se retoca ninguna
  (retocarlas sería sobreajustar). Huella `git hash-object` del archivo: `74b2dd699dd0eb35a44efb3215bb8093d46fbebc`;
  sus únicos commits son los de la F1 del 2026-09-22 (`293a80e`, `6dc6ef5`). **V01** = hipótesis vigente sin compuerta
  (producción); **V08** = V01 × compuerta del indicador.
- **Premisa visible del experimento:** `experimentos/resultados/juicio_5ind/premisas_visibles.pkl` (4 lugares) y
  `experimentos/resultados/juicio_5ind_holdout/premisas_visibles_nacional.pkl` (11.439 artículos), recortadas con la
  hipótesis más larga del experimento, igual que en F3/F7. Comprobación de robustez (se reporta, no decide): la compuerta
  con la truncación de producción de cada indicador (`512 − 3 − tokens(hipótesis de ese indicador)`).
- **Regla 15.** Según el encargo del coordinador (que transmite una decisión del usuario), la excepción a la regla 15 se
  extiende a este diseño: listas de palabras por indicador, calculadas por dentro y sin columnas nuevas. La regla sigue
  valiendo para todo lo demás. **Esta etapa no toca `src/`**, y nada se implementa allí sin la aprobación del usuario
  después de la Fase 4.

## 2. Lo que ya se sabe (no es evidencia nueva)

| Indicador | M2 lugares V01 → V08 | Violación de M3 nueva en V08 | Fuente |
|---|---|---|---|
| `presencia_grupos_armados` | 0.175 → 0.925 | no | `RESULTADOS_5ind_MAX.md`, `juicio_5ind/metricas_5ind.xlsx` |
| `conflicto_territorial` | 0.075 → 0.567 | **sí**: Paraguachón, MAX 0.993 → 0.634 con 3 positivos | ídem |
| `desplazamiento_forzado` | 0.050 → 0.350 | no | ídem |
| `rechazo_proyecto` | 0.000 → 0.025 | no | ídem |
| `exclusion_beneficios_economicos` | 0.000 → 0.000 | no | ídem |

- Holdout de grupos armados (F7, `juicio_5ind_holdout/metricas_holdout.csv`): M2 V01 0.70/0.50/0.20 (media 0.467) → V08
  1.00/0.80/0.50 (media 0.767) en Cauca/Chocó/Cundinamarca; 0 violaciones de M3; gemela de objeto absurdo V08 ≤ V01.
- F8 (log [2026-09-22]): con la compuerta solo en grupos armados, cortes **0.7574 / 0.9233**, Spearman contra el DANE
  **−0.1653 → −0.1173**, accuracy 0.344 → 0.344, clasificación 6/19/7, 0 anclas rotas; el MAX de grupos armados baja en
  Quindío (0.996 → 0.553), Caldas (0.978 → 0.725), San Andrés (0.861 → 0.000) y Guainía (0.640 → 0.011).
- **Aviso de diseño.** Con esos datos, (d) puede fallar para `conflicto_territorial` sin depender del holdout. Se
  recalcula con la referencia actual (940 juzgados más los nuevos) y se reporta; el juicio del holdout de conflicto se
  hace igual, porque (b) y el reporte por lista lo necesitan.

## 3. Datos

Todo offline salvo lo marcado. Los `.pkl` son compartidos y no versionados; los archivos nuevos llevan nombre nuevo.

- **Nacional / holdout:** `datos/scores/scores_v2_32deptos.pkl` (unión por posición con
  `datos/corpus/df_corpus_combinado_32deptos.pkl`, comprobando `titulo` y `departamento`): `sesgo`, `ent_`/`neu_` de los 26
  y de `NULA_TEST`. Holdout = artículos con `departamento` ∈ {Cauca 598, Chocó 148, Cundinamarca 371} = 1.117.
- **Lugares** (convención del plan, `juicio_5ind/url_lugares.csv`: Antioquia 494, Maicao 1.101, Oicatá 32, Paraguachón 77):
  scores vigentes, gemelas `vig_abs` y `ABSURDO_TOTAL` de `datos/scores/scores_5ind_atomicas_lugares.pkl`; los 26 de
  producción de `resultados/tablas_lugares_max/df_procesado_5lugares.pkl` (radar de los lugares, Fase 4).
- **Gemela de objeto absurdo de grupos armados en el nacional:** `datos/scores/scores_5ind_atomicas_nacional.pkl`.
- **GPU nueva, acotada (solo si falta):** las gemelas `conflicto_territorial__vig_abs` y `desplazamiento_forzado__vig_abs`
  no existen para el holdout. Se calculan **solo para los 1.117 artículos de los 3 departamentos** en un pkl NUEVO,
  `datos/scores/scores_prefiltro_indicador_holdout.pkl` (`experimentos/exp_prefiltro_indicador_gpu.py`; premisa = `texto`,
  `batch_size=32`, `max_length=512`, textos de `H.HIPOTESIS[ind]["vig_abs"]`). Antes, `verificar_contra_produccion_v2`
  (paso 0 del skill, `max|dif| < 1e-4`); junto con ellas se recalcula la gemela de grupos armados para esos 1.117 y debe
  coincidir con el pkl nacional (`max|dif| < 1e-4`). Si algo falla, se para.
- **Referencia (SÍ de `juez-a` y de `juez-b`):** los 940 juzgados de `exp_5ind_max_r2_metricas.referencia()` más los
  juzgados nuevos de §7. Positivos de un indicador en un lugar = juzgados de ese lugar con SÍ/SÍ en él.

## 4. Regla de inclusión por indicador

Una lista entra al mecanismo **solo si cumple las cuatro condiciones**. M1–M3 son las definiciones de
`PREREG_5ind_MAX.md` §4 (orden por puntaje descendente y `url` ascendente entre los de puntaje > 0; `k = min(10, nº con
puntaje > 0)`; M2 = precisión@k; M3 = coherencia del MAX con el corte 0.766).

- **(a) Lugares.** M2(V08) − M2(V01) ≥ +0.20, media de los 4 lugares. Es un dato conocido de la ronda 1 (§2) y decide con
  esos valores congelados; se recalcula con la referencia actual como comprobación y, si difiriera, se reporta.
  Deja fuera `exclusion_beneficios_economicos` y `rechazo_proyecto`, que pasan sin filtro.
- **(b) Holdout.** M2(V08) − M2(V01) ≥ +0.10 en la media de Cauca, Chocó y Cundinamarca, **y** cobertura de juicio ≥ 90 %
  en cada uno de los 6 top-k (3 departamentos × {sin filtro, con filtro}): fracción de sus artículos que tienen etiqueta
  de ambos jueces.
- **(c) Control absurdo**, con la **misma máscara** (la gemela y el absurdo total se multiplican por la compuerta del
  indicador). Por lugar: `brecha = MAX real − MAX de la gemela`, sin y con máscara, y lo mismo con el absurdo total
  (`NULA_TEST`; en los lugares `ABSURDO_TOTAL`, que es el mismo texto). La brecha media **no baja** (con máscara ≥ sin
  máscara − 5e-5) en cuatro comparaciones: {gemela de objeto absurdo, absurdo total} × {media de los 4 lugares, media de
  los 3 departamentos del holdout}. La lectura estricta (dos medias por separado) es la que decide; la media de los 7
  se reporta.
- **(d) M3.** Ninguna violación nueva: en ninguno de los 7 lugares (4 + 3 del holdout) V08 viola M3 sin que V01 la viole
  también.

**Grupos armados** ya cumplió todo en la ronda 1 y entra por ese registro; se recalcula (a)–(d) con las mismas
definiciones y se reporta cualquier diferencia. La sanidad de §5 se aplica a él.

## 5. Sanidad (bloqueante: si falla, se para)

1. Sin mecanismo, radar nacional MAX con 0.766/0.9233: clasificación 6/19/7; `elegir_cortes` devuelve 0.766/0.9233;
   Spearman contra el DANE −0.1653; Spearman(radar, nº de artículos) +0.884.
2. **Mecanismo solo con grupos armados = F8:** cortes 0.7574 / 0.9233, Spearman −0.1173, clasificación 6/19/7, 0 anclas
   rotas, y los cuatro MAX de grupos armados que cambian (Quindío, Caldas, San Andrés, Guainía) iguales a los de §2.
3. Holdout de grupos armados: M2 V01 0.467 y V08 0.767; M2 de los lugares V01/V08 de los 5 indicadores iguales a §2.
4. GPU de §3: las comprobaciones que allí se indican.

## 6. Criterios del mecanismo combinado, retirada de listas y veredicto

Con las listas que entran por §4, radar nacional MAX de 32 departamentos, sin redondear, con **cortes recalibrados** para esa
distribución mediante `exp_5ind_max_cortes.elegir_cortes` (regla 2; sin mirar el oficial; si ningún par evita romper anclas
= «sin cortes válidos» = falla). Los tres criterios, comparados a 4 decimales:

1. **0 anclas rotas** (las 12 de `exp_correlacion_v2_nacional`) con esos cortes.
2. **Spearman contra `radar_oficial_promedio` ≥ el de sin mecanismo** (−0.1653).
3. **Spearman(radar, número de artículos por departamento) no sube** respecto del de sin mecanismo (+0.884).

**Si falla alguno**, se retiran listas **una a una y de forma acumulativa, en este orden declarado de antemano**:
`desplazamiento_forzado`, `conflicto_territorial`, `presencia_grupos_armados` (de menor a mayor ganancia de M2 conocida, §2:
+0.30, +0.50, +0.75). Tras cada retirada se recalibran los cortes y se vuelven a probar los tres criterios; la primera
configuración que los cumple es la que se adopta. Si ninguna los cumple, o si al retirar se agotan las listas,
**NO ADOPTAR**. Solo se retiran listas que hubieran entrado por §4.

**Por separado (reporte, no decide):** cada una de las 5 listas sola, con sus cortes recalibrados y los tres criterios, y todas
las combinaciones de las que entran; y la media de los 7 lugares de (c).

**Veredicto:** **ADOPTAR** el mecanismo con las listas que sobreviven, o **NO ADOPTAR**. **Un empate es NO:** no entra ninguna
lista, o el radar con mecanismo es idéntico al de sin mecanismo (|Δ| < 5e-5 en los 32 radares). Los tres criterios de arriba
se aplican con las desigualdades tal como están escritas (≥, ≥, «no sube»), a 4 decimales.

## 7. Juicio del holdout (Fase 2)

- **Pool.** Para cada uno de `conflicto_territorial` y `desplazamiento_forzado` y cada departamento del holdout: el top-k de V01
  (sin filtro) y el top-k de V08 (con filtro), `k = min(10, nº con puntaje > 0)`, orden por puntaje descendente y `url`
  ascendente, sobre todos los artículos del departamento (puntajes de `scores_v2_32deptos.pkl`, compuerta de
  `premisas_visibles_nacional.pkl`). Se juzgan **solo los aún no juzgados** (fuera de los 940 de la referencia).
- **Control entre rondas.** 10 artículos ya juzgados de los departamentos del holdout, elegidos al azar con
  `numpy.random.default_rng(20260928)` (`permutation` de sus `url` ordenadas; los 10 primeros).
- **Lotes ciegos.** Se barajan (mismo generador, siguiente `permutation`) las `url` únicas de pool nuevo + control; ids opacos
  `p0000…`; lotes JSONL de ≤ 40 líneas `{"id","premisa"}` con la premisa de `premisas_visibles_nacional.pkl`, en
  `experimentos/resultados/juicio_prefiltro_indicador/lotes/`. El mapa id → `url` (`mapa_ids.csv`, con el origen) y
  `pool.csv` quedan fuera de esa carpeta.
- **Jueces.** `juez-a` y `juez-b` con el codebook congelado de `PREREG_5ind_MAX.md` §1, tal cual; los lanza el coordinador y
  escriben en `etiquetas_a/` y `etiquetas_b/` de la carpeta del juicio. Referencia = SÍ de los dos. Se consolida como en la
  ronda 2 (kappa por indicador; acuerdo de los 10 de control con su etiqueta previa, solo reporte). No se lanzan subagentes desde
  este trabajo.

## 8. Impacto y propuesta (Fase 4, sin tocar `src/`)

- Radar y clase de los 32 departamentos y de los 4 lugares (convención de producción: Paraguachón 20) con el mecanismo final y
  con los cortes recalibrados: qué cambia de clase, qué MAX por indicador se mueven (media de |ΔMAX|, celdas > 0.05, celdas
  que pasan a 0). Si hubo retirada de listas, también con el conjunto de §4 completo.
- Si el veredicto es **ADOPTAR**: plan de implementación para `src/` (diccionario indicador → regex sobre la premisa visible con la
  hipótesis de ese indicador, sin columnas nuevas, cortes nuevos, tests) en `experimentos/PLAN_implementacion_prefiltro_indicador.md`,
  y se para hasta la aprobación del usuario.
- Sea cual sea el veredicto: borrador de la etapa 2 en `experimentos/PLAN_prefiltro_indicador_etapa2.md`: los otros 21
  indicadores clasificados en «objeto concreto» (con lista propuesta) o «abstracto» (pasa sin filtro), escrito solo a partir del
  texto de la hipótesis y del sentido del indicador, sin mirar puntajes ni jueces.
- Informe 12: si **NO ADOPTAR**, se escribe con esta etapa, para lector externo, con su fila en `informes/README.md`; si
  **ADOPTAR**, después de la aprobación.

## 9. Entregables

`experimentos/exp_prefiltro_indicador.py` → `experimentos/resultados/exp_prefiltro_indicador.xlsx` (una hoja por bloque),
`experimentos/RESULTADOS_prefiltro_indicador.md`, entrada `[fecha real]` en `contexto/08_log_decisiones.md`, y lo de §8. Commits
locales; sin push ni merge.

## 10. Límites declarados de antemano

- Las listas se diseñaron mirando los lugares de la ronda 1: la ganancia de (a) es en muestra; el holdout es la comprobación
  fuera de muestra, con solo 3 departamentos y pocos positivos por indicador (Cundinamarca no tiene desplazamiento confirmado).
- (b) mide precisión en la cabeza del ranking solo con los top-10 juzgados; la cobertura de 90 % se exige para que un top-10
  sin juzgar no cuente como «no confirmado» por omisión.
- El diseño es un mecanismo con cinco listas y tres candidatas: no se corrige por comparaciones múltiples; un pase marginal
  se comunica como tal.
- La premisa del experimento se recorta con la hipótesis más larga; producción recorta con la de cada indicador (la
  comprobación de robustez de §1 reporta la diferencia).
- El radar nacional tiene n = 32; con eso solo una diferencia de Spearman de 0.15 o más se distingue del ruido (regla 11),
  así que los criterios 2 y 3 de §6 son de **no empeorar**, no de demostrar mejora.
