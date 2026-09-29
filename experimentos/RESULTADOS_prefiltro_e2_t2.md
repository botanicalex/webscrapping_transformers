# Resultados — pre-filtro por indicador, etapa 2 (tramo 2): cribado sin jueces de los 11

Generado por `experimentos/exp_prefiltro_e2_t2.py`; tablas completas en `experimentos/resultados/exp_prefiltro_e2_t2.xlsx` (hojas `S_sanidad`, `C_control`, `C_detalle`, `R_radar`, `K_cribado`). Pre-registro: `experimentos/PREREG_prefiltro_indicador_e2_t2.md`. GPU: `experimentos/resultados/exp_prefiltro_e2_t2_gpu.log`.

**Veredicto: PARADA: 1 sobreviviente(s): zonas_proteccion_alimentaria. Se reporta al usuario antes de cualquier juez.**

Sobrevivientes (C y R): zonas_proteccion_alimentaria (hoja `K_cribado`).

## Resumen del cribado (hoja `K_cribado`)

| indicador | pasa C | cortes (lista sola) | anclas | Spearman DANE | Spearman tamaño | pasa R | sobrevive |
|---|---|---|---|---|---|---|---|
| resistencia_territorial | no | 0.7319/0.9209 | 0 | -0.0663 | 0.8545 | sí | no |
| exclusion_comunidades | no | 0.7414/0.9216 | 0 | -0.1133 | 0.8647 | no | no |
| deficit_participacion_comunitaria | no | 0.7540/0.9179 | 0 | -0.1059 | 0.8790 | no | no |
| incentivos_economicos_inequitativos | no | 0.7440/0.9229 | 0 | -0.1305 | 0.8977 | no | no |
| conflictos_socioambientales | no | 0.7542/0.9226 | 0 | -0.0865 | 0.8625 | sí | no |
| exclusion_servicios_derechos | sí | 0.7553/0.9108 | 0 | -0.0887 | 0.8680 | no | no |
| grupos_etnicos_existentes | no | 0.7572/0.9233 | 0 | -0.0949 | 0.8677 | no | no |
| movimientos_sociales | no | 0.7459/0.9225 | 0 | -0.1140 | 0.8834 | no | no |
| irregularidad_contractual | no | 0.7572/0.9233 | 0 | -0.0887 | 0.8644 | no | no |
| zonas_proteccion_alimentaria | sí | 0.7516/0.9233 | 0 | -0.0913 | 0.8640 | sí | sí |
| dano_territorios | no | 0.7454/0.9111 | 0 | -0.1034 | 0.8717 | no | no |

## Condición C: control absurdo (hojas `C_control`, `C_detalle`)

Diferencia de la brecha media «MAX real − MAX control» (con − sin máscara); exigido ≥ −5e-5 en las cuatro:

| indicador | gemela, lugares | total, lugares | gemela, holdout | total, holdout | pasa C |
|---|---|---|---|---|---|
| resistencia_territorial | 0.00243 | -0.05735 | 0.14517 | 0.01320 | no |
| exclusion_comunidades | 0.00180 | 0.12772 | -0.00297 | 0.09069 | no |
| deficit_participacion_comunitaria | -0.03900 | -0.12110 | 0.34673 | 0.07284 | no |
| incentivos_economicos_inequitativos | -0.07737 | -0.28983 | -0.01769 | 0.01420 | no |
| conflictos_socioambientales | 0.10722 | -0.09422 | 0.16729 | 0.08514 | no |
| exclusion_servicios_derechos | 0.01981 | 0.08593 | 0.01660 | 0.04803 | sí |
| grupos_etnicos_existentes | -0.05727 | -0.01057 | 0.12887 | 0.22289 | no |
| movimientos_sociales | -0.04883 | -0.07081 | -0.00859 | 0.13463 | no |
| irregularidad_contractual | -0.11216 | 0.00473 | 0.06622 | 0.35097 | no |
| zonas_proteccion_alimentaria | 0.19926 | 0.05068 | 0.06089 | 0.12981 | sí |
| dano_territorios | -0.02575 | 0.07944 | 0.00171 | 0.20513 | no |

## Condición R: radar nacional con la lista sola (hoja `R_radar`)

Producción (base): cortes 0.7572/0.9233, Spearman DANE -0.0913, tamaño 0.8640, 0 anclas, clases 6/19/7. Criterios: 0 anclas, DANE ≥ -0.0913, tamaño ≤ 0.864 (4 decimales).

| indicador | cortes | anclas | Spearman DANE | Spearman tamaño | clases_B/M/A | 0 anclas | DANE ok | tamaño ok | pasa R | máx |Δ radar| |
|---|---|---|---|---|---|---|---|---|---|---|
| resistencia_territorial | 0.7319/0.9209 | 0 | -0.0663 | 0.8545 | 6/22/4 | sí | sí | sí | sí | 0.0367 |
| exclusion_comunidades | 0.7414/0.9216 | 0 | -0.1133 | 0.8647 | 6/19/7 | sí | no | no | no | 0.0249 |
| deficit_participacion_comunitaria | 0.7540/0.9179 | 0 | -0.1059 | 0.8790 | 6/20/6 | sí | no | no | no | 0.0308 |
| incentivos_economicos_inequitativos | 0.7440/0.9229 | 0 | -0.1305 | 0.8977 | 6/21/5 | sí | no | no | no | 0.0352 |
| conflictos_socioambientales | 0.7542/0.9226 | 0 | -0.0865 | 0.8625 | 6/19/7 | sí | sí | sí | sí | 0.0193 |
| exclusion_servicios_derechos | 0.7553/0.9108 | 0 | -0.0887 | 0.8680 | 6/18/8 | sí | sí | no | no | 0.0287 |
| grupos_etnicos_existentes | 0.7572/0.9233 | 0 | -0.0949 | 0.8677 | 6/19/7 | sí | no | no | no | 0.0101 |
| movimientos_sociales | 0.7459/0.9225 | 0 | -0.1140 | 0.8834 | 6/19/7 | sí | no | no | no | 0.0284 |
| irregularidad_contractual | 0.7572/0.9233 | 0 | -0.0887 | 0.8644 | 6/19/7 | sí | sí | no | no | 0.0024 |
| zonas_proteccion_alimentaria | 0.7516/0.9233 | 0 | -0.0913 | 0.8640 | 6/19/7 | sí | sí | sí | sí | 0.0194 |
| dano_territorios | 0.7454/0.9111 | 0 | -0.1034 | 0.8717 | 6/18/8 | sí | no | no | no | 0.0284 |

## Sanidad (hoja `S_sanidad`)

| chequeo | ok | valor | esperado |
|---|---|---|---|
| S1 sin listas nuevas: cortes | sí | (0.7572, 0.9233) | (0.7572, 0.9233) |
| S1 clases 6/19/7 | sí | {'Bajo': 6, 'Medio': 19, 'Alto': 7} | 6/19/7 |
| S1 Spearman DANE | sí | -0.0913 | -0.0913 |
| S1 Spearman tamano | sí | 0.864 | 0.864 |
| S1 anclas rotas | sí | 0 | 0 |
| S2 verificacion de produccion del NLI (log GPU) | sí | max|dif|=9.77e-07 | < 1e-4 |
| S3 C tramo 1 amenaza_lideres | sí | (-0.03515, 0.08585, 0.18113, 0.09288) | (-0.03515, 0.08585, 0.18113, 0.09288) |
| S3 R tramo 1 amenaza_lideres | sí | ('0.7450/0.9233', -0.1085, 0.8702) | ('0.7450/0.9233', -0.1085, 0.8702) |
| S3 C tramo 1 amenaza_intimidacion | sí | (-0.11386, 0.0102, 0.06461, 0.16896) | (-0.11386, 0.0102, 0.06461, 0.16896) |
| S3 R tramo 1 amenaza_intimidacion | sí | ('0.7572/0.9230', -0.1015, 0.8666) | ('0.7572/0.9230', -0.1015, 0.8666) |
| S3 C tramo 1 protesta_social | sí | (0.0, 0.1525, 0.06937, 0.28841) | (0.0, 0.1525, 0.06937, 0.28841) |
| S3 R tramo 1 protesta_social | sí | ('0.7559/0.9093', -0.096, 0.8666) | ('0.7559/0.9093', -0.096, 0.8666) |
| S3 C tramo 1 violacion_derechos_humanos | sí | (0.155, -0.03488, 0.02038, 0.32134) | (0.155, -0.03488, 0.02038, 0.32134) |
| S3 R tramo 1 violacion_derechos_humanos | sí | ('0.7541/0.9233', -0.0872, 0.8658) | ('0.7541/0.9233', -0.0872, 0.8658) |
| S3 ninguna de las 4 del tramo 1 sobrevive | sí | ninguna | ninguna |
| S4 aperturas nacionales de los 11 = aperturas.csv (n_abre) | sí | 11/11 iguales | iguales |
| S5 puntajes reales lugares (produccion 2026-09-29) = tablas_lugares_max, 11 indicadores | sí | max|dif|=0.0e+00 | < 1e-4 |

17 de 17 chequeos OK.

## Desviaciones y notas

- Ninguna desviación del pre-registro.
- Puntajes reales de lugares = columnas de la corrida de producción 2026-09-29 (`df_procesado_5lugares.pkl` de `tablas_lugares_max_prefiltro_2026-09-29/`); las 11 no están entre las 2 listas de producción, así que equivalen a las tablas sin filtro (S5).
- Máscaras nacionales con `premisa_visible_prod` y la hipótesis V2 de cada indicador (verificada igual a `hipotesis_prefiltro_e2_t2.HIPOTESIS`), sobre `df_corpus_combinado_32deptos.pkl`.
- Once pruebas: el cribado reduce multiplicidad, no la elimina (PREREG §9).
