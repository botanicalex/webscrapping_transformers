# Resultados — pre-filtro de relevancia social bajo MAX (umbral 0.85)

Generado por `experimentos/exp_prefiltro_max.py`; todas las tablas salen de `experimentos/resultados/exp_prefiltro_max.xlsx` (hoja indicada en cada sección). Pre-registro congelado antes de calcular: `experimentos/PREREG_prefiltro_max.md` (3849793). Log de consola: `experimentos/resultados/exp_prefiltro_max.log`. GPU única: `experimentos/exp_prefiltro_gpu_lugares.py` (`experimentos/resultados/exp_prefiltro_gpu_lugares.log`).

**Veredicto: NO REINTEGRAR** (umbral 0.85). Fallan: C2, C3, C4.

## Criterios de decisión (hoja `H_decision`)

| Criterio | Pasa | Número clave | Origen (hoja del Excel) |
|---|---|---|---|
| C1 control absurdo (brecha real − nula bajo MAX) | sí | Δ brecha media +0.0028 en los 32 departamentos (mediana -0.0003; baja en 19) y +0.0302 en los 4 lugares (baja en 2) | `D_brecha_dep, D_brecha_lugar` |
| C2 radar nacional con cortes recalibrados | no | cortes 0.7582/0.9105, anclas rotas 0, Spearman -0.1653 sin máscara → -0.1712 con máscara | `E_radar_nacional` |
| C3 caída de AUC corregida > 0.04 exige mejora del bloque C | no | disparada; ΔAUC corregida: A grupos_etnicos_existentes -0.0532, A presencia_grupos_armados -0.0269, B desplazamiento_forzado +0.0041, B conflicto_territorial +0.0064, B presencia_grupos_armados -0.0168 | `A_auc_plata, B_auc_jueces` |
| C4 mejora distinguible, neta de la nula | no | vía C (M1/M2, cota inferior): no; vía B: no; vía E (ΔSpearman -0.006 frente a +0.15): no; el mayor cambio de C es todas (23 celdas) M2 -0.0043 [-0.0130, +0.0130] | `B_auc_jueces, C_unidades, E_radar_nacional` |
| VEREDICTO (umbral 0.85) | no | NO REINTEGRAR | `H_decision` |

## Insumos y sanidad (hojas `S_sanidad`, `A_reproduccion`)

- Sanidad: 21 de 21 chequeos OK (clasificación nacional 6/19/7 con 0.766/0.9233, lugares iguales al Excel del 1-sep, M1–M3 sin máscara iguales a `metricas_r2.xlsx` y `metricas_holdout.csv`).
- Reproducción del A/B del 2026-08-31 (bloque A) contra `experimentos/resultados/exp_prefiltro_auc_indicador.xlsx`: **exacta**, máxima diferencia 5.6e-17 en las 11 columnas comparadas (incluido el bootstrap).
- sha256 de los insumos: `scores_prefiltro_lugares.pkl` `bdba4e39497dbdf8…`; `df_corpus_5lugares.pkl` `b4ccb0e6122c91b7…`; `scores_v2_32deptos.pkl` `115367c4e9733f56…`; `df_corpus_combinado_32deptos.pkl` `eb3e030937df5c79…`.

## A. AUC por artículo contra plata, nacional (hoja `A_auc_plata`)

| tipo | indicador | escala | AUC sin | AUC con | delta | IC95 inf | IC95 sup | retención |
|---|---|---|---|---|---|---|---|---|
| real | grupos_etnicos_existentes | ent_crudo | 0.8413 | 0.7823 | -0.0589 | -0.0734 | -0.0450 | 0.8909 |
| real | grupos_etnicos_existentes | score_corregido | 0.8323 | 0.7791 | -0.0531 | -0.0662 | -0.0402 | 0.8909 |
| real | presencia_grupos_armados | ent_crudo | 0.8578 | 0.8210 | -0.0369 | -0.0469 | -0.0278 | 0.9273 |
| real | presencia_grupos_armados | score_corregido | 0.8232 | 0.7963 | -0.0269 | -0.0355 | -0.0191 | 0.9273 |
| absurdo | NULA_TEST_vs_grupos_etnicos_existentes | ent_crudo | 0.4722 | 0.4839 | 0.0117 | 0.0024 | 0.0204 | — |
| absurdo | NULA_TEST_vs_grupos_etnicos_existentes | score_corregido | 0.4988 | 0.5007 | 0.0019 | -0.0011 | 0.0044 | — |
| absurdo | NULA_TEST_vs_presencia_grupos_armados | ent_crudo | 0.4880 | 0.5115 | 0.0234 | 0.0167 | 0.0296 | — |
| absurdo | NULA_TEST_vs_presencia_grupos_armados | score_corregido | 0.5117 | 0.5139 | 0.0022 | -0.0002 | 0.0043 | — |

`delta` es la media del bootstrap (como en el script del 08-31). n de positivos/negativos de plata: 871/9.935 (grupos étnicos) y 1.335/9.694 (grupos armados).

## B. AUC por artículo contra los jueces, 759 juzgados en lugares o holdout (hoja `B_auc_jueces`)

| indicador | n_pos | n_neg | suficiente | AUC sin | AUC con | delta | IC95 inf | IC95 sup | Δ nula | Δ neta | neta inf | neta sup | pasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exclusion_beneficios_economicos | 0 | 759 | no | — | — | — | — | — | — | — | — | — | — |
| rechazo_proyecto | 8 | 751 | no | 0.8191 | 0.8261 | 0.0070 | 0.0014 | 0.0146 | 0.0020 | 0.0050 | -0.0008 | 0.0127 | no |
| desplazamiento_forzado | 29 | 730 | sí | 0.8481 | 0.8522 | 0.0041 | 0.0011 | 0.0080 | 0.0021 | 0.0021 | -0.0014 | 0.0063 | no |
| conflicto_territorial | 34 | 725 | sí | 0.7932 | 0.7996 | 0.0064 | 0.0024 | 0.0115 | 0.0021 | 0.0043 | -0.0003 | 0.0100 | no |
| presencia_grupos_armados | 128 | 631 | sí | 0.8214 | 0.8046 | -0.0168 | -0.0435 | 0.0049 | 0.0024 | -0.0192 | -0.0452 | 0.0027 | no |

Score corregido (principal). La escala cruda está en la hoja. «Δ neta» = Δ del indicador − Δ de la nula, con remuestreo pareado; para contar en C4 su IC95% debe excluir cero.

## C. M1–M3 del MAX con jueces (hojas `C_celdas`, `C_unidades`, `C_descriptivo`)

| unidad | metrica | elegible | sin | con (cota inf) | con (cota sup) | Δ cota inf | IC95 inf | IC95 sup | Δ nula | neta inf | cobertura con | pasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grupos_armados (7 celdas) | M1 | sí | 0.7143 | 0.5714 | 0.5714 | -0.1429 | -0.1429 | 0.0000 | 0.0000 | -0.1429 | 1.0000 | no |
| grupos_armados (7 celdas) | M2 | sí | 0.3000 | 0.2857 | 0.2857 | -0.0143 | -0.0429 | 0.0429 | 0.0000 | -0.0429 | 1.0000 | no |
| todas (23 celdas) | M1 | sí | 0.2609 | 0.2174 | 0.2174 | -0.0435 | -0.0435 | 0.0000 | 0.0000 | -0.0435 | 1.0000 | no |
| todas (23 celdas) | M2 | sí | 0.1130 | 0.1087 | 0.1087 | -0.0043 | -0.0130 | 0.0130 | 0.0000 | -0.0130 | 1.0000 | no |

Descriptivo: en las 13 celdas con positivos, M1+ pasa de 0.4615 a 0.3846 y M2+ de 0.2000 a 0.1923; violaciones de M3 (20 celdas de los lugares): 8 sin máscara, 8 con máscara.

Celdas donde la máscara cambia algo (k, M1, M2 o MAX): 7 de 23.

| indicador | lugar | n_positivos | pasan filtro | n_articulos | k_sin | k_con | M1 sin | M1 con | M2 sin | M2 con | MAX sin | MAX con | cobertura_con |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exclusion_beneficios_economicos | Maicao | 0 | 988 | 1101 | 10 | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9961 | 0.9948 | 1.0000 |
| exclusion_beneficios_economicos | Oicata | 0 | 19 | 32 | 10 | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9887 | 0.9755 | 1.0000 |
| rechazo_proyecto | Oicata | 0 | 19 | 32 | 10 | 9 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9792 | 0.9746 | 1.0000 |
| desplazamiento_forzado | Oicata | 0 | 19 | 32 | 8 | 6 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5170 | 0.3863 | 1.0000 |
| presencia_grupos_armados | Oicata | 0 | 19 | 32 | 7 | 5 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.6522 | 0.6522 | 1.0000 |
| exclusion_beneficios_economicos | Paraguachon | 0 | 64 | 77 | 10 | 10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9939 | 0.9936 | 1.0000 |
| presencia_grupos_armados | Chocó | 16 | 127 | 148 | 10 | 10 | 1.0000 | 0.0000 | 0.5000 | 0.4000 | 0.9905 | 0.9869 | 1.0000 |

## D. Control absurdo con `NULA_TEST` y la misma máscara (hojas `D_brecha_dep`, `D_brecha_lugar`, `D_escala_nula`)

- Brecha = radar real − MAX de la nula corregida. Δ brecha media con máscara: +0.0028 en los 32 departamentos (mediana -0.0003; la brecha baja en 19) y +0.0302 en los 4 lugares (baja en 2).
- Departamentos con mayor Δ brecha: Atlántico +0.0840, Boyacá +0.0770, Nariño +0.0016; con menor: San Andrés y Providencia -0.0161, Valle del Cauca -0.0140, Risaralda -0.0072.

| lugar | radar sin | MAX nula sin | brecha sin | radar con | MAX nula con | brecha con | Δ brecha |
|---|---|---|---|---|---|---|---|
| Antioquia (2023) | 0.9354 | 0.3787 | 0.5567 | 0.9354 | 0.3787 | 0.5567 | 0.0000 |
| Municipio Maicao | 0.9625 | 0.5705 | 0.3920 | 0.9614 | 0.5705 | 0.3909 | -0.0011 |
| Municipio Oicatá | 0.6688 | 0.4279 | 0.2409 | 0.6458 | 0.2822 | 0.3637 | 0.1227 |
| Vereda Paraguachón | 0.6801 | 0.0105 | 0.6697 | 0.6793 | 0.0105 | 0.6689 | -0.0008 |

Escala de la nula (media y proporción > 0.9, cruda y corregida):

| ambito | mascara | n | media_cruda | prop cruda > 0.9 | media_corregida | prop corregida > 0.9 |
|---|---|---|---|---|---|---|
| nacional | sin | 11439 | 0.2142 | 0.0567 | 0.0203 | 0.0000 |
| nacional | con | 11439 | 0.2034 | 0.0553 | 0.0193 | 0.0000 |
| lugares | sin | 1647 | 0.2336 | 0.0856 | 0.0190 | 0.0000 |
| lugares | con | 1647 | 0.2254 | 0.0850 | 0.0184 | 0.0000 |

## E. Radar nacional MAX, 32 departamentos (hojas `E_radar_nacional`, `E_artefacto_tamano`)

| radar | cortes | corte_bajo_medio | corte_medio_alto | n_Medio | n_Alto | n_Bajo | anclas_rotas | accuracy | spearman |
|---|---|---|---|---|---|---|---|---|---|
| sin mascara | vigentes | 0.7660 | 0.9233 | 19 | 7 | 6 | 0 | 0.3438 | -0.1653 |
| con mascara | vigentes | 0.7660 | 0.9233 | 19 | 7 | 6 | 0 | 0.3438 | -0.1712 |
| con mascara | recalibrados | 0.7582 | 0.9105 | 18 | 8 | 6 | 0 | 0.3438 | -0.1712 |

Spearman del radar contra el número de artículos del departamento (artefacto de tamaño): radar sin +0.884, radar con +0.889, nula sin +0.736, nula con +0.714.

## F. Impacto (hojas `F_deptos`, `F_lugares`, `F_indicadores`, `F_celdas_005`)

- Artículos enmascarados: nacional 12.6%; por lugar Antioquia (2023) 13.2%, Municipio Maicao 10.3%, Municipio Oicatá 40.6%, Vereda Paraguachón 25.0%.
- Spearman del radar contra el oficial: -0.1653 sin máscara, -0.1712 con máscara.
- Departamentos que cambian de clase: 0 con los cortes vigentes en ambos radares; 1 de vigentes sin máscara a recalibrados con máscara (cortes 0.7582/0.9105): Meta.
- Celdas departamento × indicador: 51 de 832 cambian su MAX; 10 lo hacen en más de 0.05; 0 pasan a 0.
- El radar baja en 23 de 32 departamentos; diferencia media -0.0023, mínima -0.0161.

Los tres indicadores más afectados (media de |ΔMAX| entre departamentos):

| indicador | media |ΔMAX| | celdas > 0.05 | pasan a 0 |
|---|---|---|---|
| irregularidad_contractual | 0.0168 | 2 | 0 |
| debilidad_institucional | 0.0093 | 2 | 0 |
| zonas_proteccion_alimentaria | 0.0057 | 1 | 0 |

Celdas con |ΔMAX| > 0.05:

| departamento | indicador | n_articulos | MAX_sin | MAX_con | dMAX |
|---|---|---|---|---|---|
| Valle del Cauca | irregularidad_contractual | 117 | 0.9171 | 0.5528 | -0.3643 |
| San Andrés y Providencia | debilidad_institucional | 79 | 0.8442 | 0.6014 | -0.2428 |
| Guaviare | irregularidad_contractual | 311 | 0.8850 | 0.7122 | -0.1728 |
| Risaralda | zonas_proteccion_alimentaria | 367 | 0.9133 | 0.7811 | -0.1322 |
| San Andrés y Providencia | exclusion_servicios_derechos | 79 | 0.9566 | 0.8380 | -0.1186 |
| Magdalena | reasentamiento | 1538 | 0.9327 | 0.8187 | -0.1140 |
| Córdoba | deficit_participacion_comunitaria | 913 | 0.3044 | 0.2083 | -0.0961 |
| Quindío | deficit_participacion_comunitaria | 275 | 0.4191 | 0.3342 | -0.0849 |
| Caldas | amenaza_intimidacion | 300 | 0.9425 | 0.8663 | -0.0762 |
| Amazonas | debilidad_institucional | 243 | 0.5764 | 0.5216 | -0.0548 |

Radar por lugar (convención de producción):

| lugar | % enmascarado | radar sin | radar con | diferencia | clase sin (vig.) | clase con (vig.) | clase con (recal.) |
|---|---|---|---|---|---|---|---|
| Antioquia (2023) | 0.1316 | 0.9354 | 0.9354 | 0.0000 | Alto | Alto | Alto |
| Municipio Maicao | 0.1026 | 0.9625 | 0.9614 | -0.0011 | Alto | Alto | Alto |
| Municipio Oicatá | 0.4062 | 0.6688 | 0.6458 | -0.0230 | Bajo | Bajo | Bajo |
| Vereda Paraguachón | 0.2500 | 0.6801 | 0.6793 | -0.0008 | Bajo | Bajo | Bajo |

## Sensibilidad a otros umbrales, descriptiva y sin efecto en la decisión (hojas `G_sensibilidad`, `G_sens_B`, `G_sens_C`)

| umbral | % enmasc. nac. | A ΔAUC étnicos | A ΔAUC armados | D Δbrecha deptos | D Δbrecha lugares | E Spearman con | E cortes recal. | F cambian clase (recal.) | F celdas > 0.05 | C1 | C2 | C3 | C4 | REINTEGRAR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5000 | 0.0650 | -0.0211 | -0.0104 | 0.0019 | -0.0007 | -0.1639 | 0.7627/0.9233 | 0 | 4 | no | sí | sí | sí | no |
| 0.6500 | 0.0827 | -0.0288 | -0.0169 | 0.0018 | -0.0021 | -0.1639 | 0.7627/0.9233 | 0 | 5 | no | sí | sí | sí | no |
| 0.7500 | 0.1014 | -0.0386 | -0.0233 | 0.0011 | -0.0021 | -0.1635 | 0.7582/0.9105 | 1 | 8 | no | sí | sí | sí | no |
| 0.8500 | 0.1261 | -0.0532 | -0.0269 | 0.0028 | 0.0302 | -0.1712 | 0.7582/0.9105 | 1 | 10 | sí | no | no | no | no |

ΔAUC por artículo contra los jueces (score corregido) por umbral:

| umbral | indicador | n_pos | delta | IC95 inf | IC95 sup | Δ nula | neta inf | pasa |
|---|---|---|---|---|---|---|---|---|
| 0.5000 | rechazo_proyecto | 8 | 0.0028 | 0.0000 | 0.0072 | 0.0000 | 0.0000 | no |
| 0.5000 | desplazamiento_forzado | 29 | 0.0019 | 0.0001 | 0.0050 | 0.0000 | 0.0001 | sí |
| 0.5000 | conflicto_territorial | 34 | 0.0009 | 0.0001 | 0.0024 | 0.0000 | 0.0001 | sí |
| 0.5000 | presencia_grupos_armados | 128 | -0.0035 | -0.0189 | 0.0050 | 0.0000 | -0.0189 | no |
| 0.6500 | rechazo_proyecto | 8 | 0.0037 | 0.0004 | 0.0087 | 0.0000 | 0.0004 | no |
| 0.6500 | desplazamiento_forzado | 29 | 0.0026 | 0.0004 | 0.0059 | 0.0000 | 0.0004 | sí |
| 0.6500 | conflicto_territorial | 34 | 0.0036 | 0.0008 | 0.0074 | 0.0000 | 0.0008 | sí |
| 0.6500 | presencia_grupos_armados | 128 | -0.0072 | -0.0265 | 0.0060 | 0.0000 | -0.0265 | no |
| 0.7500 | rechazo_proyecto | 8 | 0.0047 | 0.0007 | 0.0105 | 0.0000 | 0.0007 | no |
| 0.7500 | desplazamiento_forzado | 29 | 0.0034 | 0.0008 | 0.0070 | 0.0000 | 0.0008 | sí |
| 0.7500 | conflicto_territorial | 34 | 0.0043 | 0.0013 | 0.0086 | 0.0000 | 0.0013 | sí |
| 0.7500 | presencia_grupos_armados | 128 | -0.0107 | -0.0335 | 0.0065 | 0.0000 | -0.0335 | no |
| 0.8500 | rechazo_proyecto | 8 | 0.0070 | 0.0014 | 0.0146 | 0.0020 | -0.0008 | no |
| 0.8500 | desplazamiento_forzado | 29 | 0.0041 | 0.0011 | 0.0080 | 0.0021 | -0.0014 | no |
| 0.8500 | conflicto_territorial | 34 | 0.0064 | 0.0024 | 0.0115 | 0.0021 | -0.0003 | no |
| 0.8500 | presencia_grupos_armados | 128 | -0.0168 | -0.0435 | 0.0049 | 0.0024 | -0.0452 | no |

Δ de M1/M2 (cota inferior) por umbral:

| umbral | unidad | metrica | sin | con (cota inf) | Δ | IC95 inf | IC95 sup | neta inf | pasa |
|---|---|---|---|---|---|---|---|---|---|
| 0.5000 | grupos_armados (7 celdas) | M1 | 0.7143 | 0.5714 | -0.1429 | -0.1429 | 0.0000 | -0.1429 | no |
| 0.5000 | grupos_armados (7 celdas) | M2 | 0.3000 | 0.2857 | -0.0143 | -0.0286 | 0.0286 | -0.0286 | no |
| 0.5000 | todas (23 celdas) | M1 | 0.2609 | 0.2174 | -0.0435 | -0.0435 | 0.0000 | -0.0435 | no |
| 0.5000 | todas (23 celdas) | M2 | 0.1130 | 0.1087 | -0.0043 | -0.0087 | 0.0087 | -0.0087 | no |
| 0.6500 | grupos_armados (7 celdas) | M1 | 0.7143 | 0.5714 | -0.1429 | -0.1429 | 0.0000 | -0.1429 | no |
| 0.6500 | grupos_armados (7 celdas) | M2 | 0.3000 | 0.2857 | -0.0143 | -0.0429 | 0.0143 | -0.0429 | no |
| 0.6500 | todas (23 celdas) | M1 | 0.2609 | 0.2174 | -0.0435 | -0.0435 | 0.0000 | -0.0435 | no |
| 0.6500 | todas (23 celdas) | M2 | 0.1130 | 0.1087 | -0.0043 | -0.0130 | 0.0087 | -0.0130 | no |
| 0.7500 | grupos_armados (7 celdas) | M1 | 0.7143 | 0.5714 | -0.1429 | -0.1429 | 0.0000 | -0.1429 | no |
| 0.7500 | grupos_armados (7 celdas) | M2 | 0.3000 | 0.2857 | -0.0143 | -0.0429 | 0.0286 | -0.0429 | no |
| 0.7500 | todas (23 celdas) | M1 | 0.2609 | 0.2174 | -0.0435 | -0.0435 | 0.0000 | -0.0435 | no |
| 0.7500 | todas (23 celdas) | M2 | 0.1130 | 0.1087 | -0.0043 | -0.0130 | 0.0087 | -0.0130 | no |
| 0.8500 | grupos_armados (7 celdas) | M1 | 0.7143 | 0.5714 | -0.1429 | -0.1429 | 0.0000 | -0.1429 | no |
| 0.8500 | grupos_armados (7 celdas) | M2 | 0.3000 | 0.2857 | -0.0143 | -0.0429 | 0.0429 | -0.0429 | no |
| 0.8500 | todas (23 celdas) | M1 | 0.2609 | 0.2174 | -0.0435 | -0.0435 | 0.0000 | -0.0435 | no |
| 0.8500 | todas (23 celdas) | M2 | 0.1130 | 0.1087 | -0.0043 | -0.0130 | 0.0130 | -0.0130 | no |

## Lectura (escrita a mano después de la corrida; los números salen de las tablas de arriba)

**Veredicto: NO REINTEGRAR en el umbral 0.85.** Fallan tres criterios, cada uno por su lado; solo C1 pasa.

1. **C2 falla:** el Spearman del radar contra el oficial baja de −0.1653 a −0.1712 con la máscara (cortes
   recalibrados 0.7582/0.9105, 0 anclas rotas). Es una diferencia de −0.006, muy lejos del +0.15 que haría falta.
2. **C3 se dispara:** la caída de AUC en `grupos_etnicos_existentes` (−0.0532) y en `presencia_grupos_armados` (−0.0269)
   del bloque A reproduce exacta la del 2026-08-31 (diferencia máxima 5.6e-17). La mejora tenía que venir entonces
   del bloque C con la cota inferior, y no viene.
3. **C4 falla:** en C, M1 de grupos armados pasa de 5/7 a 4/7 celdas (Δ −0.1429) y M2 de 0.3000 a 0.2857
   (Δ −0.0143, IC95% [−0.0429, +0.0429]); en las 23 celdas, M1 baja de 0.2609 a 0.2174 y M2 de 0.1130 a 0.1087
   (Δ −0.0043, IC95% [−0.0130, +0.0130]). La cobertura con máscara es 100 %, así que la cota inferior y la superior coinciden.

**La máscara casi no toca el radar bajo MAX.** Solo 51 de 832 celdas departamento × indicador cambian su MAX; 10 lo hacen en
más de 0.05 y ninguna pasa a 0. Con los cortes vigentes no cambia la clase de ningún departamento; el radar baja en
23 de 32 (media −0.0023, mínimo −0.0161 en San Andrés). Con los cortes recalibrados solo cambia Meta (Medio → Alto), y no
por la máscara (su radar pasa de 0.9171 a 0.9169) sino porque el corte de arriba baja de 0.9233 a 0.9105. Los lugares
no cambian de clase (Antioquia 2023 0.9354 → 0.9354, Maicao 0.9625 → 0.9614, Oicatá 0.6688 → 0.6458, Paraguachón
0.6801 → 0.6793). El artefacto de tamaño de MAX sigue intacto: Spearman(radar, nº de artículos) +0.884 → +0.889.

**Por qué no mejora la cabeza del ranking** (exploratorio, posterior al pre-registro, no decide:
`experimentos/exp_prefiltro_max_mecanismo.py`, `experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx`).
- De los 225 puestos de los top-10 de las 23 celdas, la máscara saca 27 artículos: 26 no positivos y 1 positivo. Limpia
  ruido, pero los reemplazos también son no positivos (la referencia tiene 13 celdas con positivos y pocos en cada una),
  así que la precisión no sube. De los 199 puestos que ocupan artículos no positivos, 173 (87 %) pasan el filtro, con una
  mediana de puntaje social de 0.998 (hoja `resumen_top10`): los falsos positivos de la cabeza son artículos socialmente
  relevantes, que un filtro general de relevancia no toca. Y el único positivo que se lleva es el nº 1 de grupos armados en
  Chocó, «Chocó: 79 % de los
  confinamientos y el segundo con más desplazamientos», con puntaje social 0.049: un texto de cifras que el filtro no
  reconoce como riesgo para una comunidad.
- En los 759 juzgados enmascara el 13.2 % de los negativos y el 3.9 % de los positivos de grupos armados (5 de 128:
  rangos 1, 11, 20, 48 y 64 del ranking sin máscara); no enmascara ninguno de los positivos de los otros tres indicadores.
  Esa selectividad explica los ΔAUC pequeños y positivos del bloque B.

**Bloque B (AUC contra jueces).** Rechazo +0.0070, desplazamiento +0.0041 y conflicto +0.0064; grupos armados −0.0168
(IC95% [−0.0435, +0.0049]). La nula gana +0.002 con la misma máscara; restada, el IC95% de la mejora neta incluye el cero
en los tres indicadores con mejora. Aunque no fuera así, C3 impide que B cuente.

### Salvedades

- **C1 pasa con el criterio pre-registrado (la media), pero con poca holgura.** Por unidad la brecha baja en 19 de 32
  departamentos y en 2 de 4 lugares (Maicao −0.0011, Paraguachón −0.0008); la mediana por departamento es −0.0003. La media
  positiva (+0.0028 y +0.0302) la sostienen tres casos donde la máscara sacó el artículo que fijaba el MAX de la nula:
  Atlántico +0.0840, Boyacá +0.0770 y Oicatá +0.1227 (un lugar de 32 artículos, del que la máscara elimina el 40.6 %).
  Como el veredicto no depende de C1, no cambia nada; pero no debe leerse como «la máscara mejora el control absurdo».
- **Lectura estricta de la nula (C4).** Se exigió que el IC95% de Δ real − Δ nula excluya el cero. Con la lectura
  laxa (solo Δ real > Δ nula con el IC de Δ real fuera del cero), B pasaría C4 en el 0.85 para rechazo, desplazamiento y
  conflicto; el veredicto sería el mismo, porque C3 exige que la mejora venga del bloque C.
- **Sensibilidad (no decide).** Ningún umbral pasa los cuatro criterios, así que no se registra ningún candidato.
  En 0.50, 0.65 y 0.75 C3 no se dispara (la caída en grupos étnicos es −0.0211, −0.0288 y −0.0386, esta última a un paso del
  −0.04), C2 pasa por +0.001 de Spearman y C4 pasa solo por B, con mejoras triviales (ΔAUC +0.0009 a +0.0043 en desplazamiento y
  conflicto; límite inferior del IC 0.0001 a 0.0013); pero C1 falla porque la brecha de los lugares baja (−0.0007, −0.0021 y
  −0.0021). Las métricas M1/M2 del bloque C son idénticas en los cuatro umbrales: el positivo de Chocó se pierde incluso
  con el 0.50 (su puntaje social es 0.049).
- **Alcance de la referencia.** La plata cubre 2 de 26 indicadores y los jueces 5 de 26; en los otros 21 solo se mide el
  impacto (F). `exclusion_beneficios_economicos` no tiene positivos (no medible) y Oicatá (32 artículos) no tiene positivos de
  ningún indicador. Los 759 juzgados son un pool armado con el top del score sin máscara, que favorece a la vigente; por
  eso se reportan las dos cotas (coinciden). Los 22 juzgados de la prueba del modelo NLI no se usaron.
- **Comentario de `src/Transformer_optimo.py:168-175`** (no se tocó): dice que el pre-filtro está retirado por la
  caída de AUC de 2026-08-31. Sigue siendo cierto. Si se quisiera, bastaría añadir una línea que remita a
  `contexto/08_log_decisiones.md` [2026-09-28] («reevaluado bajo MAX: sigue rechazado»); se propone, no se aplica.
