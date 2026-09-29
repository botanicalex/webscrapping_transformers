# Resultados — pre-filtro por indicador, etapa 2 (tramo 2): análisis final de `zonas_proteccion_alimentaria`

**Veredicto: NO ADOPTAR.** no cumple la regla de inclusión: falla (a), (b); gana el statu quo (PREREG e2 §0).

Generado por `experimentos/exp_prefiltro_e2_t2_analisis.py`; tablas en `experimentos/resultados/exp_prefiltro_e2_t2_analisis.xlsx`. Pre-registro: `PREREG_prefiltro_indicador_e2_t2.md` §4 → `PREREG_prefiltro_indicador_e2.md` §3–§6 tal cual. Referencia: SÍ de `juez-e` y de `juez-f` (`juicio_prefiltro_e2_t2/etiquetas.csv`); kappa (pool) 0.72, SÍ/SÍ 9 (SÍ juez-e 9, juez-f 15), 105 url, cobertura mínima de los top-k 1.00.

## Regla de inclusión (a)–(d)

- (a) M2 medio de los 4 lugares: V01 0.0500 → V08 0.1861, Δ +0.1361 (exigido ≥ +0.20): **falla**.
- (b) M2 medio del holdout: 0.0667 → 0.1333, Δ +0.0667 (exigido ≥ +0.10) y cobertura mínima 1.000 (≥ 0.90): **falla**.
- (c) control absurdo (con − sin máscara de la brecha, tol 5e-5): gemela lugares +0.19926, total lugares +0.05068, gemela holdout +0.06089, total holdout +0.12981: **pasa**.
- (d) M3 (corte 0.7572), violaciones en los 7 lugares: 1 → 1, nuevas 0 (con corte 0.766: 1 nuevas): **pasa**.
- Entra por (a)–(d): **no**.

### M1–M4 por lugar y variante (V01 sin compuerta, V08 con compuerta)

| lugar | tipo | variante | n_positivos | M1 | M2 | cobertura | k | MAX | M3 viola 0.7572 | M3 viola 0.766 | MAX_gemela | MAX absurdo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Antioquia | lugar | V01 | 1 | 1.0000 | 0.1000 | 1.0000 | 10 | 0.9896 | no | no | 0.8075 | 0.3787 |
| Antioquia | lugar | V08 | 1 | 1.0000 | 0.1000 | 1.0000 | 10 | 0.9896 | no | no | 0.8011 | 0.3787 |
| Maicao | lugar | V01 | 3 | 0.0000 | 0.0000 | 1.0000 | 10 | 0.9625 | no | no | 0.8981 | 0.5705 |
| Maicao | lugar | V08 | 3 | 0.0000 | 0.2000 | 1.0000 | 10 | 0.8803 | no | no | 0.6134 | 0.3773 |
| Oicata | lugar | V01 | 1 | 1.0000 | 0.1000 | 1.0000 | 10 | 0.7764 | no | no | 0.7456 | 0.4279 |
| Oicata | lugar | V08 | 1 | 1.0000 | 0.1111 | 1.0000 | 9 | 0.7764 | no | no | 0.7456 | 0.2040 |
| Paraguachon | lugar | V01 | 1 | 0.0000 | 0.0000 | 1.0000 | 10 | 0.8971 | no | no | 0.8906 | 0.2098 |
| Paraguachon | lugar | V08 | 1 | 0.0000 | 0.3333 | 1.0000 | 3 | 0.7650 | no | sí | 0.1703 | 0.2098 |
| Cauca | holdout | V01 | 0 | 0.0000 | 0.0000 | 1.0000 | 10 | 0.9916 | sí | sí | 0.8411 | 0.5532 |
| Cauca | holdout | V08 | 0 | 0.0000 | 0.0000 | 1.0000 | 10 | 0.9916 | sí | sí | 0.8411 | 0.4247 |
| Chocó | holdout | V01 | 2 | 0.0000 | 0.1000 | 1.0000 | 10 | 0.8892 | no | no | 0.7344 | 0.4253 |
| Chocó | holdout | V08 | 2 | 0.0000 | 0.2000 | 1.0000 | 10 | 0.8565 | no | no | 0.7344 | 0.2864 |
| Cundinamarca | holdout | V01 | 2 | 0.0000 | 0.1000 | 1.0000 | 10 | 0.9605 | no | no | 0.8757 | 0.6154 |
| Cundinamarca | holdout | V08 | 2 | 0.0000 | 0.2000 | 1.0000 | 10 | 0.9605 | no | no | 0.6603 | 0.4607 |

M4 = `MAX_gemela` y `MAX_absurdo_total` (razones a MAX en la hoja `M_metricas`). Holdout, detalle de (b):

| indicador | departamento | n_positivos | k_sin | M2_sin | cobertura_sin | k_con | M2_con | cobertura_con |
|---|---|---|---|---|---|---|---|---|
| zonas_proteccion_alimentaria | Cauca | 0 | 10 | 0.0000 | 1.0000 | 10 | 0.0000 | 1.0000 |
| zonas_proteccion_alimentaria | Chocó | 2 | 10 | 0.1000 | 1.0000 | 10 | 0.2000 | 1.0000 |
| zonas_proteccion_alimentaria | Cundinamarca | 2 | 10 | 0.1000 | 1.0000 | 10 | 0.2000 | 1.0000 |

## Mecanismo combinado (§6) y radar nacional

No entra por (a)–(d): el mecanismo combinado no se evalúa como decisión. Informativo (cribado, lista sola): cortes 0.7516/0.9233, anclas 0, Spearman DANE -0.0913, tamaño +0.8640, máx |Δ radar| 0.0194.

## Impacto

No entra: sin impacto (radar y lugares idénticos a producción).

## Trazabilidad del MAX (§7, reporte)

Artículo que fija el MAX de `zonas_proteccion_alimentaria` en los 7 lugares: referencia SÍ 2 de 7 sin filtro y 2 de 7 con filtro (M1: 2 → 2).

| lugar | version | MAX | etiqueta_ref | etiqueta_e | etiqueta_f | M1 | titulo |
|---|---|---|---|---|---|---|---|
| Antioquia | sin_filtro | 0.9896 | SI | SI | SI | 1.0000 | Lluvias, árboles viejos y poca fertilización: así bajó la productividad del agro colombiano |
| Antioquia | con_filtro | 0.9896 | SI | SI | SI | 1.0000 | Lluvias, árboles viejos y poca fertilización: así bajó la productividad del agro colombiano |
| Maicao | sin_filtro | 0.9625 | NO | NO | NO | 0.0000 | Mantienen alerta roja por riesgo de incendios forestales en los 15 municipios de La Guajira |
| Maicao | con_filtro | 0.8803 | NO | NO | NO | 0.0000 | Ministerio de Transporte adjudicará $3,3 billones para intervenir vías de La Guajira |
| Oicata | sin_filtro | 0.7764 | SI | SI | SI | 1.0000 | Los proyectos comunitarios que Urbaser ha venido apoyando en Pirgua y sectores de Oicatá |
| Oicata | con_filtro | 0.7764 | SI | SI | SI | 1.0000 | Los proyectos comunitarios que Urbaser ha venido apoyando en Pirgua y sectores de Oicatá |
| Paraguachon | sin_filtro | 0.8971 | NO | NO | NO | 0.0000 | Educación vial para proteger la vida en corredores escolares |
| Paraguachon | con_filtro | 0.7650 | NO | DUDOSO | NO | 0.0000 | Agua para todos donde está el centavo para el peso |
| Cauca | sin_filtro | 0.9916 | NO | NO | NO | 0.0000 | Desatando el Potencial del Cauca: De Desafíos a Oportunidades |
| Cauca | con_filtro | 0.9916 | NO | NO | NO | 0.0000 | Desatando el Potencial del Cauca: De Desafíos a Oportunidades |
| Chocó | sin_filtro | 0.8892 | NO | NO | NO | 0.0000 | Chocó: riesgo de incumplimiento en cinco proyectos por $86.000 millones |
| Chocó | con_filtro | 0.8565 | NO | NO | NO | 0.0000 | Yurleidy Perea, coordinadora subregión PDET Chocó |
| Cundinamarca | sin_filtro | 0.9605 | NO | NO | DUDOSO | 0.0000 | Páramo de Guacheneque, así trabajan por su restauración y conservación |
| Cundinamarca | con_filtro | 0.9605 | NO | NO | DUDOSO | 0.0000 | Páramo de Guacheneque, así trabajan por su restauración y conservación |

## Salvedades y desviaciones

- n pequeño: 9 SÍ/SÍ en 105 url; el M2 de cada lugar descansa en pocos positivos y el holdout son solo 3 departamentos (PREREG e2 §11).
- La condición R del cribado pasó por igualdad de Spearman DANE: −0.0913 a 4 decimales, igual al de producción (criterio de no empeorar, mejora nula; n = 32).
- Un pase sería marginal: una lista sobreviviente entre once evaluadas en el cribado (multiplicidad, PREREG t2 §9).
- Referencia = SÍ de ambos jueces sobre el pool (top-10 de V01 ∪ V08); lo no juzgado cuenta como negativo en M1/M2 (cotas superiores en el xlsx).
- Se reutilizan `metricas_m`, `inclusion`, `tope`, `criterios`, `cadena` e `impacto` de `exp_prefiltro_e2.py` inyectando el indicador (sin modificar ese archivo); la trazabilidad se reescribe para las etiquetas de juez-e/juez-f.
- Desviaciones del pre-registro: ninguna.

## Sanidad

| chequeo | ok | valor | esperado |
|---|---|---|---|
| S1 sin lista nueva: cortes | sí | (0.7572, 0.9233) | (0.7572, 0.9233) |
| S1 clases 6/19/7 | sí | {'Bajo': 6, 'Medio': 19, 'Alto': 7} | 6/19/7 |
| S1 Spearman DANE | sí | -0.0913 | -0.0913 |
| S1 Spearman tamano | sí | 0.864 | 0.864 |
| S1 anclas rotas | sí | 0 | 0 |
| S2 top-k de V01 y V08 (7 lugares) recalculados = pool.csv | sí | 0 discrepancias [] | 0 |
| S2 lugares del pool = los 7 | sí | ['Antioquia', 'Cauca', 'Chocó', 'Cundinamarca', 'Maicao', 'Oicata', 'Paraguachon'] | 7 lugares |
| S3 cobertura de juicio minima de los 14 top-k | sí | 1.0 | 1.0 |
| S4 condicion C reproduce la del cribado (4 comparaciones) | sí | {'c_dif_gemela_lugares': 0.1993, 'c_dif_total_lugares': 0.0507, 'c_dif_gemela_holdout': 0.0609, 'c_dif_total_holdout': 0.1298} | {'c_dif_gemela_lugares': 0.1993, 'c_dif_total_lugares': 0.0507, 'c_dif_gemela_holdout': 0.0609, 'c_dif_total_holdout': 0.1298} |
| S5 gemelas presentes en los 7 lugares | sí | True | True |
| S6 consolidacion: medible y kappa >= 0.4 | sí | kappa 0.72, SI/SI 9 | kappa >= 0.4 y SI/SI >= 5 |

11 de 11 chequeos OK.
