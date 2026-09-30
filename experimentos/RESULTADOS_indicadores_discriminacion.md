# Resultados — cuánto discrimina cada indicador (producción actual, 32 departamentos)

Generado por `experimentos/exp_indicadores_discriminacion.py`; tablas en `experimentos/resultados/exp_indicadores_discriminacion.xlsx`. Descriptivo: no decide nada.

Sanidad: 5/5 OK (base = producción).

## Indicadores (ordenados de menos a más amplitud)

| indicador | mediana | min | amplitud_P90_P10 | frac_MAX_ge_095 | rho_dane | rho_tam | delta_rho_dane | delta_rho_tam | PLANO | SIN_SENAL_DANE | TAMANO |
|---|---|---|---|---|---|---|---|---|---|---|---|
| derechos_vulnerados | 0.997 | 0.950 | 0.010 | 1.000 | -0.165 | 0.561 | 0.000 | 0.000 | sí | sí |  |
| exclusion_beneficios_economicos | 0.994 | 0.950 | 0.016 | 0.969 | -0.363 | 0.661 | 0.000 | 0.000 | sí | sí |  |
| exclusion_servicios_derechos | 0.988 | 0.888 | 0.040 | 0.906 | -0.179 | 0.479 | 0.001 | 0.002 | sí | sí |  |
| conflicto_activo | 0.993 | 0.922 | 0.049 | 0.875 | -0.022 | 0.633 | 0.000 | 0.000 | sí | sí |  |
| poblacion_afectada | 0.990 | 0.834 | 0.050 | 0.875 | -0.299 | 0.745 | -0.009 | 0.001 |  | sí | sí |
| conflicto_territorial | 0.989 | 0.702 | 0.074 | 0.812 | -0.302 | 0.611 | -0.001 | 0.005 |  | sí |  |
| violacion_derechos_humanos | 0.977 | 0.192 | 0.102 | 0.719 | -0.051 | 0.710 | -0.009 | 0.001 |  | sí | sí |
| rechazo_proyecto | 0.979 | 0.244 | 0.105 | 0.781 | -0.239 | 0.774 | 0.000 | 0.000 |  | sí | sí |
| exclusion_comunidades | 0.961 | 0.572 | 0.111 | 0.594 | -0.303 | 0.736 | -0.012 | 0.001 |  | sí | sí |
| amenaza_intimidacion | 0.977 | 0.449 | 0.133 | 0.688 | -0.232 | 0.576 | -0.007 | 0.003 |  | sí |  |
| grupos_etnicos_existentes | 0.977 | 0.504 | 0.177 | 0.688 | -0.065 | 0.443 | 0.003 | 0.003 |  | sí |  |
| conflictos_socioambientales | 0.930 | 0.449 | 0.183 | 0.312 | -0.155 | 0.611 | 0.002 | -0.003 |  | sí |  |
| amenaza_lideres | 0.968 | 0.287 | 0.224 | 0.625 | -0.118 | 0.612 | -0.007 | 0.003 |  | sí |  |
| movimientos_sociales | 0.955 | 0.485 | 0.238 | 0.531 | -0.220 | 0.793 | -0.010 | 0.006 |  | sí | sí |
| zonas_proteccion_alimentaria | 0.950 | 0.505 | 0.251 | 0.500 | -0.351 | 0.626 | 0.009 | 0.004 |  | sí |  |
| presencia_grupos_armados | 0.985 | 0.000 | 0.260 | 0.719 | 0.009 | 0.639 | -0.055 | 0.008 |  |  |  |
| incentivos_economicos_inequitativos | 0.888 | 0.544 | 0.284 | 0.188 | -0.277 | 0.653 | -0.003 | 0.008 |  | sí |  |
| desplazamiento_forzado | 0.903 | 0.000 | 0.381 | 0.375 | 0.003 | 0.602 | -0.020 | 0.005 |  |  |  |
| resistencia_territorial | 0.822 | 0.000 | 0.411 | 0.188 | -0.234 | 0.657 | -0.014 | 0.000 |  | sí |  |
| dano_territorios | 0.893 | 0.032 | 0.440 | 0.219 | -0.162 | 0.519 | -0.022 | 0.020 |  | sí |  |
| irregularidad_contractual | 0.838 | 0.037 | 0.471 | 0.125 | -0.182 | 0.692 | -0.005 | 0.011 |  | sí |  |
| reasentamiento | 0.743 | 0.128 | 0.474 | 0.062 | -0.022 | 0.705 | -0.023 | 0.001 |  | sí | sí |
| debilidad_institucional | 0.753 | 0.000 | 0.609 | 0.062 | -0.368 | 0.842 | 0.022 | -0.044 |  | sí | sí |
| protesta_social | 0.863 | 0.081 | 0.648 | 0.188 | -0.223 | 0.691 | -0.019 | 0.009 |  | sí |  |
| danos_ambientales | 0.336 | 0.000 | 0.701 | 0.000 | -0.277 | 0.749 | 0.002 | 0.008 |  | sí | sí |
| deficit_participacion_comunitaria | 0.536 | 0.000 | 0.766 | 0.031 | -0.015 | 0.414 | -0.003 | 0.005 |  | sí |  |

PLANO: amplitud P90−P10 < 0.05 y mediana ≥ 0.95. SIN_SENAL_DANE: Spearman con el DANE ≤ 0. TAMANO: Spearman con el nº de artículos ≥ 0.7. delta_*: cambio del radar al retirar solo ese.

## Configuraciones

| config | n_indicadores | rho_dane | rho_tam | cortes | anclas_rotas | clases_B/M/A | accuracy |
|---|---|---|---|---|---|---|---|
| base (26) | 26 | -0.0913 | 0.8640 | 0.7572/0.9233 | 0.0000 | 6/19/7 | 0.3438 |
| R1 sin PLANO (4) | 22 | -0.0913 | 0.8640 | 0.7148/0.9105 | 0.0000 | 6/19/7 | 0.3438 |
| R2 sin PLANO ni SIN_SENAL (24; circular) | 2 | 0.0337 | 0.6576 | sin cortes validos |  |  |  |

R1 retira: derechos_vulnerados, exclusion_beneficios_economicos, exclusion_servicios_derechos, conflicto_activo.

R2 retira: derechos_vulnerados, exclusion_beneficios_economicos, exclusion_servicios_derechos, conflicto_activo, poblacion_afectada, conflicto_territorial, violacion_derechos_humanos, rechazo_proyecto, exclusion_comunidades, amenaza_intimidacion, grupos_etnicos_existentes, conflictos_socioambientales, amenaza_lideres, movimientos_sociales, zonas_proteccion_alimentaria, incentivos_economicos_inequitativos, resistencia_territorial, dano_territorios, irregularidad_contractual, reasentamiento, debilidad_institucional, protesta_social, danos_ambientales, deficit_participacion_comunitaria (circular: se elige con el DANE y se mide contra el DANE).

## MAX en los 4 lugares (producción 2026-09-29)

| indicador | Antioquia | Maicao | Oicata | Paraguachon |
|---|---|---|---|---|
| desplazamiento_forzado | 0.990 | 0.983 | 0.000 | 0.768 |
| reasentamiento | 0.969 | 0.966 | 0.010 | 0.966 |
| protesta_social | 0.981 | 0.990 | 0.852 | 0.943 |
| amenaza_intimidacion | 0.994 | 0.995 | 0.564 | 0.995 |
| conflicto_territorial | 0.996 | 0.994 | 0.900 | 0.993 |
| rechazo_proyecto | 0.991 | 0.996 | 0.979 | 0.989 |
| derechos_vulnerados | 0.998 | 0.998 | 0.990 | 0.996 |
| conflicto_activo | 0.996 | 0.995 | 0.985 | 0.989 |
| resistencia_territorial | 0.873 | 0.956 | 0.548 | 0.388 |
| exclusion_comunidades | 0.974 | 0.993 | 0.953 | 0.990 |
| deficit_participacion_comunitaria | 0.957 | 0.835 | 0.370 | 0.259 |
| incentivos_economicos_inequitativos | 0.981 | 0.948 | 0.894 | 0.862 |
| debilidad_institucional | 0.707 | 0.944 | 0.596 | 0.327 |
| danos_ambientales | 0.322 | 0.802 | 0.000 | 0.070 |
| conflictos_socioambientales | 0.953 | 0.978 | 0.890 | 0.879 |
| violacion_derechos_humanos | 0.995 | 0.996 | 0.899 | 0.996 |
| exclusion_servicios_derechos | 0.987 | 0.996 | 0.950 | 0.989 |
| grupos_etnicos_existentes | 0.989 | 0.995 | 0.668 | 0.914 |
| movimientos_sociales | 0.925 | 0.987 | 0.866 | 0.927 |
| poblacion_afectada | 0.996 | 0.996 | 0.911 | 0.994 |
| exclusion_beneficios_economicos | 0.996 | 0.996 | 0.989 | 0.994 |
| irregularidad_contractual | 0.894 | 0.814 | 0.000 | 0.450 |
| zonas_proteccion_alimentaria | 0.990 | 0.962 | 0.776 | 0.897 |
| dano_territorios | 0.889 | 0.943 | 0.000 | 0.589 |
| presencia_grupos_armados | 0.995 | 0.982 | 0.000 | 0.988 |
| amenaza_lideres | 0.982 | 0.977 | 0.633 | 0.919 |

Límites: n = 32 (Spearman < 0.15 de diferencia no se distingue del ruido); el DANE mide otra cosa; accuracy de 'siempre Bajo' = 0.344.
