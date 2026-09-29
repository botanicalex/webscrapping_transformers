# Pre-registro — Pre-filtro por indicador, etapa 2 (tramo 1: 6 indicadores)

Fecha: 2026-09-29 · Rama: `hipotesis-5ind-max` · Base: `28e360b` · Textos y listas: `experimentos/hipotesis_prefiltro_e2.py`
(huella `git hash-object` `0c730c76ccecccbaeb62def65ffe16008f0ef664`).

**A partir del commit que introduce este archivo, nada de §0–§11 cambia.** Toda desviación posterior se registra en
`contexto/08_log_decisiones.md` como desviación, con su motivo. Antes de este commit no se calculó ninguna métrica, ninguna
tasa de apertura ni ningún pool de estos 6 indicadores, y ningún artículo se ha elegido para el juicio. Diseño aprobado por el
usuario el 2026-09-29 (tramo de 6, tope de 3, techo del 50 %, sin placebo). **Por la regla 15, las 6 listas requieren además la
confirmación expresa del usuario antes de la F1.**

## 0. Pregunta y refutación

**Pregunta:** ¿extender el pre-filtro por indicador (etapa 1, en producción para grupos armados y desplazamiento) a alguno de
estos 6 indicadores aporta valor al radar MAX sin empeorar ningún indicador?

**Refutación (NO ADOPTAR ninguna lista nueva):** (i) ninguna lista cumple §3 y §4; o (ii) el mecanismo combinado no cumple §6 en
ninguna configuración permitida; o (iii) empate con el statu quo (§6). Gana el statu quo: producción actual (2 listas, cortes
0.7572/0.9233).

## 1. Mecanismo y listas

- El mismo de la etapa 1: `score' = s × 1[regex ∈ premisa visible normalizada]`, con la premisa recortada con la hipótesis de
  cada indicador (como `PREFILTRO_OBJETO` en `src/`). **V01** = hipótesis vigente sin compuerta (producción actual);
  **V08** = V01 × compuerta.
- **Tramo 1** (`TRAMO_1`): `reasentamiento`, `amenaza_lideres`, `amenaza_intimidacion`, `protesta_social`,
  `violacion_derechos_humanos`, `danos_ambientales`. Criterios de elección, fijados sin datos: objeto concreto, riesgo de
  apertura bajo o medio a priori, relación con «cuánto estorba» y sin circularidad con la plata. Fuera del tramo:
  `grupos_etnicos_existentes` (la plata usa palabras casi iguales a su lista), `incentivos_economicos_inequitativos` (vocabulario
  como el de exclusión, que falló en la etapa 1) y los de apertura alta a priori.
- **Listas congeladas** (`LISTAS_TRAMO_1`): las del borrador `PLAN_prefiltro_indicador_etapa2.md` §3, sin retocar. No se retocan
  después de ver datos.
- Los otros 11 concretos (`LISTAS_SOLO_APERTURA`) solo reportan su tasa de apertura (§2); no se evalúan ni deciden nada. Un
  segundo tramo solo se considera si este deja al menos una lista, y exigiría su propio pre-registro.

## 2. Techo de apertura (F1, solo texto)

Tasa de apertura = fracción de los 11.439 artículos nacionales cuya premisa visible (recortada con la hipótesis de su
indicador) cumple la lista. **Si supera 0.50 (`TECHO_APERTURA`), el indicador pasa sin filtro** y no se juzga. Se reporta la de
los 17 y la de las 2 listas de producción como referencia.

## 3. Referencia: jueces nuevos

- Agentes nuevos, ciegos: `juez-c` (sonnet) y `juez-d` (opus), en `.claude/agents/`, con el codebook de abajo congelado. No se
  editan `juez-a` ni `juez-b`. **Referencia = SÍ de los dos**; SÍ frente a {NO, DUDOSO}.
- Codebook (el artículo debe **reportar** el hecho; mencionar la palabra de pasada no basta; premisa cortada que no alcanza →
  DUDOSO; cada indicador se juzga por separado):

| Indicador | SI | NO |
|---|---|---|
| `reasentamiento` | Traslado o reubicación de población, familias o una comunidad fuera de su vivienda o territorio (por obra, riesgo, sentencia o programa), realizado o en curso | Reubicación de vendedores, comercios, oficinas, presos o servicios; desplazamiento por violencia sin programa de reubicación; anuncios genéricos de vivienda |
| `amenaza_lideres` | Amenaza, atentado, agresión u homicidio contra un líder social, comunal, étnico o ambiental, defensor de DDHH, firmante de paz o reclamante de tierras | Contra candidatos, funcionarios o políticos sin rol social; líderes deportivos, religiosos o empresariales; menciones sin agresión |
| `amenaza_intimidacion` | Amenaza, intimidación, hostigamiento, extorsión o panfleto dirigido a personas o grupos identificables en el territorio | «Amenaza» de lluvia, riesgo natural o sanitario; amenazas genéricas sin destinatario; delito sin amenaza (hurto, riña) |
| `protesta_social` | Protesta, marcha, bloqueo, paro o plantón realizado o en curso en el territorio | «Paro cardiorrespiratorio»; protestas en otro país; convocatorias sin realizar; actos culturales o deportivos |
| `violacion_derechos_humanos` | Denuncia de violación de DDHH o hecho grave contra población civil: masacre, desaparición forzada, tortura, reclutamiento de menores, violencia sexual en el conflicto, ejecución extrajudicial | Homicidio común, riña o accidente; informes o campañas genéricas sin un hecho concreto |
| `danos_ambientales` | Daño ambiental concreto ocurrido o en curso: contaminación, derrame, deforestación, minería ilegal, incendio forestal, pérdida de especies o ecosistemas | Campañas, jornadas de limpieza o reciclaje; riesgos futuros; clima o lluvias sin daño ambiental |

- **Kappa < 0.4 en un indicador → ese indicador no se adopta** (codebook no fiable). **Menos de 5 SÍ/SÍ en el pool de los 7
  lugares → «no medible», pasa sin filtro.**
- No hay control entre rondas: ningún artículo tiene etiqueta previa para estos 6 indicadores.

## 4. Muestra, pool y regla de inclusión

- **Desarrollo:** los 4 lugares (Antioquia, Maicao, Oicatá, Paraguachón; 1.647 artículos), puntajes de la corrida de producción
  del 2026-09-29 (`resultados/tablas_lugares_max_prefiltro_2026-09-29/`; estos 6 indicadores no tienen filtro y son iguales a los
  del 1-sep). **Holdout:** Cauca, Chocó y Cundinamarca (1.117), puntajes de `scores_v2_32deptos.pkl` con la fórmula de producción.
  Las listas se congelan antes de ver cualquiera de los dos.
- **Pool:** por indicador del tramo que no supere el techo y por lugar (7): top-k de V01 ∪ top-k de V08, `k = min(10, nº con
  puntaje > 0)`, orden por puntaje descendente y `url` ascendente. Se deduplica por `url` (Paraguachón comparte artículos con
  Maicao). Cada artículo del pool se juzga en los 6 indicadores.
- **Lotes ciegos:** `url` únicas barajadas con `numpy.random.default_rng(20260929)`; ids opacos `e0000…`; lotes JSONL de ≤ 40 líneas
  `{"id","premisa"}` con la premisa recortada con la más larga de las 6 hipótesis, en
  `experimentos/resultados/juicio_prefiltro_e2/lotes/`. `mapa_ids.csv` y `pool.csv`, fuera de esa carpeta.
- **Métricas:** M1–M4 de `PREREG_5ind_MAX.md` §4 tal cual, con el corte de M3 en **0.7572** (vigente; se reporta también 0.766).
- **Regla de inclusión** (las cuatro; la de la etapa 1):
  - **(a) Lugares:** M2(V08) − M2(V01) ≥ +0.20, media de los 4 lugares.
  - **(b) Holdout:** M2(V08) − M2(V01) ≥ +0.10, media de los 3 departamentos, y cobertura de juicio ≥ 90 % en cada uno de los 6
    top-k.
  - **(c) Control absurdo** con la misma máscara: la brecha MAX real − MAX gemela y MAX real − MAX absurdo total (`NULA_TEST`) no
    baja (con máscara ≥ sin máscara − 5e-5) en las cuatro comparaciones {gemela, absurdo total} × {media de los 4 lugares, media
    del holdout}.
  - **(d) M3:** ninguna violación nueva en los 7 lugares.

## 5. Tope de listas

Entran como máximo **3** listas nuevas (`MAX_LISTAS_NUEVAS`). Si cumplen §3–§4 más de 3, entran las 3 de mayor ganancia de M2 en el
holdout; en empate, la de mayor ganancia en los lugares; si persiste, orden alfabético. No se corrige por comparaciones múltiples más
allá de este tope y de exigir la ganancia en dos muestras; un pase marginal se comunica como tal.

## 6. Mecanismo combinado (radar nacional)

Las 2 listas de producción más las nuevas admitidas; radar MAX de los 32 departamentos con cortes recalibrados por
`elegir_cortes` (sobre el radar sin redondear). Criterios:
1. 0 anclas rotas (las 12 de `exp_correlacion_v2_nacional`).
2. Spearman contra `radar_oficial_promedio` ≥ **−0.0913** (producción actual).
3. Spearman(radar, nº de artículos) ≤ **+0.8640**.

Si falla alguno, se retiran listas **nuevas**, de una en una y de forma acumulativa, de menor a mayor ganancia de M2 en el holdout
(desempate como en §5), recalibrando cada vez; la primera configuración que cumple es la que se adopta. Las 2 de producción no se
retiran. **Empate = NO:** no entra ninguna lista nueva, o |Δ radar| < 5e-5 en los 32 departamentos. Desigualdades a 4 decimales.

## 7. Trazabilidad del MAX (reporte, no decide)

Producción ya guarda el artículo que fija el MAX por lugar e indicador (título, url, periódico y fecha). Se reporta, para los 6
indicadores y los 7 lugares, el artículo que fija el MAX **sin y con filtro**, su etiqueta de referencia (SÍ/NO de los jueces) y
M1. Es el dato que se muestra en el front: indica si el artículo que el radar exhibe como evidencia habla del hecho.

## 8. GPU (F1, una sola vez)

Las 6 gemelas (`GEMELAS`) sobre los 1.647 artículos de los lugares y los 1.117 del holdout (unos 15 min), en un pkl nuevo
`datos/scores/scores_prefiltro_e2.pkl` (no versionado), con `ent_`/`neu_` sin enmascarar. Antes, verificación de producción
(max|dif| < 1e-4). El absurdo total ya existe (`scores_prefiltro_lugares.pkl`, `scores_v2_32deptos.pkl`): no se recalcula.

## 9. Fases y paradas

- **F0** (coordinador): este pre-registro, `hipotesis_prefiltro_e2.py`, agentes `juez-c`/`juez-d`, log. Commit. **Parada:**
  confirmación del usuario de las 6 listas (regla 15).
- **F1** (subagente Sonnet nuevo): tasas de apertura (§2), GPU (§8), pools y lotes (§4). Commit. **Parada:** el coordinador lanza
  los jueces.
- **F2** (coordinador): `juez-c` y `juez-d` en paralelo y en segundo plano; consolidación, kappa y cobertura. **Parada:** reporte al
  usuario.
- **F3** (subagente Sonnet nuevo): (a)–(d), §5, §6, §7 e impacto (clases, MAX que cambian, celdas que pasan a 0) →
  `experimentos/resultados/exp_prefiltro_e2.xlsx` y `experimentos/RESULTADOS_prefiltro_e2.md`; entrada en el log. **Parada:**
  veredicto y aprobación del usuario antes de tocar `src/`.
- **F4** (subagente Sonnet nuevo, solo si ADOPTAR y el usuario lo aprueba): `PREFILTRO_OBJETO` y cortes en `src/`, tests,
  equivalencia offline, recorrida de los 4 lugares con `experimentos/exp_prefiltro_correr_lugares.py` (nunca
  `pipeline_lugares.py` tal cual). Informe 13 (también si el veredicto es NO ADOPTAR).

## 10. Costo estimado

GPU unos 15 min (F1) más unos 32 min (F4, si aplica). Jueces: unos 350–450 artículos únicos, 10–12 lotes por juez (unos 1.5–2 M de
tokens, la mitad en opus). Tres subagentes Sonnet, uno por fase.

## 11. Límites declarados de antemano

- n = 32 en el radar: solo una diferencia de Spearman ≥ 0.15 se distingue del ruido; los criterios de §6 son de no empeorar.
- Holdout de 3 departamentos; los indicadores con pocos positivos pueden quedar «no medibles».
- La premisa del juez se recorta con la hipótesis más larga de las 6; la compuerta, con la de cada indicador.
- Seis pruebas: aun con el tope y la doble muestra, alguna lista puede pasar por azar.
- Nada cambia la agregación MAX ni el radar de 26 indicadores.
