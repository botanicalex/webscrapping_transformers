# Resultados — pre-filtro por indicador (listas de objeto) bajo MAX, etapa 1

Generado por `experimentos/exp_prefiltro_indicador.py`; todas las tablas salen de `experimentos/resultados/exp_prefiltro_indicador.xlsx` (hoja indicada). Pre-registro congelado antes de calcular: `experimentos/PREREG_prefiltro_indicador.md` (12c494c). Juicio: `experimentos/resultados/juicio_prefiltro_indicador/`.

**Veredicto: ADOPTAR.** Cumple los tres criterios del radar. Listas que entran por (a)–(d): presencia_grupos_armados, desplazamiento_forzado. Configuración final: presencia_grupos_armados, desplazamiento_forzado.

## Inclusión por indicador (hoja `I_inclusion`)

| indicador | (a) ΔM2 lugares | (a) | (b) ΔM2 holdout | cobertura mín. | (b) | (c) | M3 nuevas | (d) | entra |
|---|---|---|---|---|---|---|---|---|---|
| exclusion_beneficios_economicos | 0.0000 | no | — | — | — | — | — | — | no |
| rechazo_proyecto | 0.0250 | no | — | — | — | — | — | — | no |
| desplazamiento_forzado | 0.3000 | sí | 0.2000 | 1.0000 | sí | sí | 0.0000 | sí | sí |
| conflicto_territorial | 0.4920 | sí | 0.3333 | 1.0000 | sí | no | 1.0000 | no | no |
| presencia_grupos_armados | 0.7500 | sí | 0.3000 | 1.0000 | sí | sí | 0.0000 | sí | sí |

(a) usa los valores congelados de la ronda 1 (`juicio_5ind/metricas_5ind.xlsx`); recalculados con la referencia actual coinciden en los 5 indicadores (columna `a_coincide`).

### (b) Holdout por departamento (hoja `I_holdout_b`)

| indicador | departamento | n_positivos | k sin filtro | M2 sin | cobertura sin | k con filtro | M2 con | cobertura con |
|---|---|---|---|---|---|---|---|---|
| desplazamiento_forzado | Cauca | 9 | 10 | 0.3000 | 1.0000 | 10 | 0.8000 | 1.0000 |
| desplazamiento_forzado | Chocó | 14 | 10 | 0.8000 | 1.0000 | 10 | 0.9000 | 1.0000 |
| desplazamiento_forzado | Cundinamarca | 0 | 10 | 0.0000 | 1.0000 | 10 | 0.0000 | 1.0000 |
| conflicto_territorial | Cauca | 9 | 10 | 0.4000 | 1.0000 | 10 | 0.6000 | 1.0000 |
| conflicto_territorial | Chocó | 8 | 10 | 0.3000 | 1.0000 | 10 | 0.6000 | 1.0000 |
| conflicto_territorial | Cundinamarca | 1 | 10 | 0.0000 | 1.0000 | 2 | 0.5000 | 1.0000 |
| presencia_grupos_armados | Cauca | 20 | 10 | 0.7000 | 1.0000 | 10 | 1.0000 | 1.0000 |
| presencia_grupos_armados | Chocó | 18 | 10 | 0.5000 | 1.0000 | 10 | 0.8000 | 1.0000 |
| presencia_grupos_armados | Cundinamarca | 6 | 10 | 0.2000 | 1.0000 | 10 | 0.5000 | 1.0000 |

### (c) Control absurdo con la misma máscara (hoja `I_control_c`)

Diferencia de la brecha media «MAX real − MAX de la gemela» (con máscara − sin máscara); debe ser ≥ −5e-5 en las cuatro primeras columnas.

| indicador | gemela, lugares | total, lugares | gemela, holdout | total, holdout | gemela, los 7 | total, los 7 | (c) |
|---|---|---|---|---|---|---|---|
| desplazamiento_forzado | 0.0013 | 0.0460 | 0.0000 | 0.2864 | 0.0008 | 0.1490 | sí |
| conflicto_territorial | 0.1387 | -0.0089 | 0.0960 | 0.3898 | 0.1204 | 0.1620 | no |
| presencia_grupos_armados | 0.0969 | 0.0703 | 0.0514 | 0.1999 | 0.0774 | 0.1258 | sí |

MAX de la hipótesis real, de su gemela de objeto absurdo y del absurdo total, sin → con máscara, en las listas que entran:

| indicador | lugar | real sin | real con | gemela sin | gemela con | total sin | total con |
|---|---|---|---|---|---|---|---|
| desplazamiento_forzado | Antioquia | 0.990 | 0.990 | 0.985 | 0.985 | 0.379 | 0.206 |
| desplazamiento_forzado | Maicao | 0.985 | 0.983 | 0.961 | 0.961 | 0.570 | 0.436 |
| desplazamiento_forzado | Oicata | 0.517 | 0.000 | 0.701 | 0.000 | 0.428 | 0.000 |
| desplazamiento_forzado | Paraguachon | 0.985 | 0.768 | 0.942 | 0.901 | 0.210 | 0.025 |
| desplazamiento_forzado | Cauca | 0.985 | 0.985 | 0.944 | 0.944 | 0.553 | 0.336 |
| desplazamiento_forzado | Chocó | 0.991 | 0.991 | 0.906 | 0.906 | 0.425 | 0.201 |
| desplazamiento_forzado | Cundinamarca | 0.919 | 0.919 | 0.858 | 0.858 | 0.615 | 0.197 |
| presencia_grupos_armados | Antioquia | 0.995 | 0.995 | 0.669 | 0.611 | 0.379 | 0.337 |
| presencia_grupos_armados | Maicao | 0.985 | 0.982 | 0.688 | 0.456 | 0.570 | 0.266 |
| presencia_grupos_armados | Oicata | 0.652 | 0.000 | 0.649 | 0.000 | 0.428 | 0.000 |
| presencia_grupos_armados | Paraguachon | 0.988 | 0.988 | 0.360 | 0.256 | 0.210 | 0.048 |
| presencia_grupos_armados | Cauca | 0.996 | 0.996 | 0.674 | 0.610 | 0.553 | 0.553 |
| presencia_grupos_armados | Chocó | 0.990 | 0.981 | 0.524 | 0.424 | 0.425 | 0.201 |
| presencia_grupos_armados | Cundinamarca | 0.993 | 0.993 | 0.709 | 0.709 | 0.615 | 0.230 |

### (d) M3 (hoja `I_m3_d`)

Lugares donde V01 o V08 violan M3 (el MAX contradice la existencia de casos confirmados); «nueva» = solo V08 la viola:

| indicador | lugar | n_positivos | MAX_V01 | MAX_V08 | viola_V01 | viola_V08 | nueva |
|---|---|---|---|---|---|---|---|
| desplazamiento_forzado | Paraguachon | 0 | 0.985 | 0.768 | sí | sí | no |
| desplazamiento_forzado | Cundinamarca | 0 | 0.919 | 0.919 | sí | sí | no |
| conflicto_territorial | Oicata | 0 | 0.900 | 0.000 | sí | no | no |
| conflicto_territorial | Paraguachon | 3 | 0.993 | 0.634 | no | sí | sí |

## Juicio (hojas `J_kappa`, `J_control`)

| indicador | SI_a | SI_b | SI_SI | kappa | referencia_debil |
|---|---|---|---|---|---|
| exclusion_beneficios_economicos | 0 | 0 | 0 | — | — |
| rechazo_proyecto | 0 | 0 | 0 | — | — |
| desplazamiento_forzado | 9 | 8 | 8 | 0.9231 | no |
| conflicto_territorial | 3 | 3 | 3 | 1.0000 | no |
| presencia_grupos_armados | 12 | 12 | 11 | 0.8750 | no |

| indicador | n_control | acuerdo_SI_SI | SI_SI_previo | SI_SI_nuevo |
|---|---|---|---|---|
| exclusion_beneficios_economicos | 10 | 1.0000 | 0 | 0 |
| rechazo_proyecto | 10 | 1.0000 | 0 | 0 |
| desplazamiento_forzado | 10 | 1.0000 | 3 | 3 |
| conflicto_territorial | 10 | 1.0000 | 1 | 1 |
| presencia_grupos_armados | 10 | 0.8000 | 5 | 7 |

Los 10 de control conservan su etiqueta previa en la referencia; aquí solo se mide el acuerdo.

## Radar nacional: cada lista y cada combinación (hoja `R_configs`)

| listas | cortes | anclas_rotas | Spearman DANE | Spearman tamaño | clases_B/M/A | 0 anclas | DANE ≥ base | tamaño no sube | pasa |
|---|---|---|---|---|---|---|---|---|---|
| exclusion_beneficios_economicos | 0.7424/0.9209 | 0 | -0.1514 | 0.8757 | 6/19/7 | sí | sí | sí | sí |
| rechazo_proyecto | 0.7660/0.9225 | 0 | -0.1782 | 0.8893 | 6/19/7 | sí | no | no | no |
| desplazamiento_forzado | 0.7621/0.9233 | 0 | -0.1459 | 0.8724 | 6/19/7 | sí | sí | sí | sí |
| conflicto_territorial | 0.7534/0.9097 | 0 | -0.1448 | 0.8680 | 6/18/8 | sí | sí | sí | sí |
| presencia_grupos_armados | 0.7574/0.9233 | 0 | -0.1173 | 0.8695 | 6/19/7 | sí | sí | sí | sí |
| presencia_grupos_armados + conflicto_territorial | 0.7359/0.9097 | 0 | -0.1133 | 0.8633 | 6/18/8 | sí | sí | sí | sí |
| presencia_grupos_armados + desplazamiento_forzado | 0.7572/0.9233 | 0 | -0.0913 | 0.8640 | 6/19/7 | sí | sí | sí | sí |
| conflicto_territorial + desplazamiento_forzado | 0.7495/0.9097 | 0 | -0.1250 | 0.8618 | 6/18/8 | sí | sí | sí | sí |
| presencia_grupos_armados + conflicto_territorial + desplazamiento_forzado | 0.7327/0.9097 | 0 | -0.0924 | 0.8607 | 6/18/8 | sí | sí | sí | sí |

Sin mecanismo: Spearman DANE -0.1653; Spearman con el tamaño +0.8842; cortes 0.766/0.9233.

## Cadena de retirada (hoja `R_cadena`)

| paso | listas | cortes | anclas_rotas | rho_dane | rho_size | pasa |
|---|---|---|---|---|---|---|
| 0 | presencia+desplazamiento | 0.7572/0.9233 | 0 | -0.0913 | 0.8640 | sí |

## Impacto (hojas `F_*`)

| configuracion | cortes | deptos_cambian_vigentes | deptos_cambian_recalibrados | celdas_que_cambian | celdas_gt_0.05 | celdas_a_cero | lugares_cambian_clase |
|---|---|---|---|---|---|---|---|
| F8: solo grupos armados | 0.7574/0.9233 | 0 | 0 | 12 | 4 | 1 | 0 |
| incluidas por (a)-(d) | 0.7572/0.9233 | 0 | 0 | 27 | 14 | 2 | 0 |

Configuración «incluidas por (a)-(d)» (cortes recalibrados 0.7572/0.9233):

- El radar baja en 20 de 32 departamentos; diferencia media -0.0048, mínima -0.0407. Cambian de clase: 0 con los cortes vigentes y 0 con los recalibrados.

Mayores caídas del radar:

| departamento | n_articulos | radar_sin | radar_con | diferencia | clase_sin_vigentes | clase_con_recalibrados |
|---|---|---|---|---|---|---|
| San Andrés y Providencia | 79 | 0.7376 | 0.6969 | -0.0407 | Bajo | Bajo |
| Guainía | 6 | 0.4578 | 0.4282 | -0.0297 | Bajo | Bajo |
| Caldas | 300 | 0.8557 | 0.8266 | -0.0290 | Medio | Medio |
| Quindío | 275 | 0.8941 | 0.8744 | -0.0197 | Medio | Medio |
| Santander | 190 | 0.8852 | 0.8731 | -0.0121 | Medio | Medio |
| Boyacá | 380 | 0.8998 | 0.8948 | -0.0050 | Medio | Medio |

MAX que se mueven, por indicador:

| indicador | media_abs_dMAX | celdas_gt_0.05 | celdas_a_cero | MAX_medio_sin | MAX_medio_con |
|---|---|---|---|---|---|
| presencia_grupos_armados | 0.0709 | 4 | 1 | 0.9638 | 0.8930 |
| desplazamiento_forzado | 0.0547 | 10 | 1 | 0.8909 | 0.8362 |

Celdas departamento × indicador con |ΔMAX| > 0.05:

| departamento | indicador | n_articulos | MAX_sin | MAX_con | dMAX |
|---|---|---|---|---|---|
| San Andrés y Providencia | presencia_grupos_armados | 79 | 0.861 | 0.000 | -0.861 |
| Guainía | presencia_grupos_armados | 6 | 0.640 | 0.011 | -0.629 |
| Caldas | desplazamiento_forzado | 300 | 0.947 | 0.446 | -0.502 |
| Quindío | presencia_grupos_armados | 275 | 0.996 | 0.553 | -0.443 |
| Santander | desplazamiento_forzado | 190 | 0.969 | 0.654 | -0.315 |
| Caldas | presencia_grupos_armados | 300 | 0.978 | 0.724 | -0.253 |
| San Andrés y Providencia | desplazamiento_forzado | 79 | 0.801 | 0.604 | -0.197 |
| Guainía | desplazamiento_forzado | 6 | 0.142 | 0.000 | -0.142 |
| Boyacá | desplazamiento_forzado | 380 | 0.883 | 0.752 | -0.130 |
| Valle del Cauca | desplazamiento_forzado | 117 | 0.991 | 0.884 | -0.107 |
| Casanare | desplazamiento_forzado | 161 | 0.976 | 0.893 | -0.083 |
| Bolívar | desplazamiento_forzado | 267 | 0.883 | 0.806 | -0.077 |
| Magdalena | desplazamiento_forzado | 1538 | 0.994 | 0.924 | -0.070 |
| Quindío | desplazamiento_forzado | 275 | 0.860 | 0.792 | -0.069 |

Los 4 lugares (convención de producción):

| lugar | radar_sin | radar_con | diferencia | clase_sin_vigentes | clase_con_recalibrados | indicadores_que_cambian |
|---|---|---|---|---|---|---|
| Antioquia (2023) | 0.9354 | 0.9354 | 0.0000 | Alto | Alto |  |
| Municipio Maicao | 0.9625 | 0.9623 | -0.0002 | Alto | Alto | desplazamiento_forzado 0.985->0.983, presencia_grupos_armados 0.985->0.982 |
| Municipio Oicatá | 0.6688 | 0.6239 | -0.0450 | Bajo | Bajo | desplazamiento_forzado 0.517->0.000, presencia_grupos_armados 0.652->0.000 |
| Vereda Paraguachón | 0.6801 | 0.6523 | -0.0278 | Bajo | Bajo | desplazamiento_forzado 0.723->0.000 |

## Robustez: compuerta con la truncación de producción de cada indicador (hoja `Z_robustez`)

| indicador | articulos_distintos | listas | max_dif_radar |
|---|---|---|---|
| presencia_grupos_armados | 16 | presencia_grupos_armados + desplazamiento_forzado | 0.000000 |
| desplazamiento_forzado | 4 | presencia_grupos_armados + desplazamiento_forzado | 0.000000 |

## Sanidad (hoja `S_sanidad`)

13 de 13 chequeos OK.

## Lectura (escrita a mano después de la corrida; los números salen de las tablas de arriba)

**Veredicto pre-registrado: ADOPTAR el mecanismo con dos listas, `presencia_grupos_armados` y `desplazamiento_forzado`.**
La aprobación para implementarlo en `src/` la da el usuario; esta etapa no lo toca.

1. **Entran dos listas y salen tres.** Grupos armados cumple (a)–(d) y reproduce la F8 (cortes 0.7574/0.9233, Spearman −0.1173).
   Desplazamiento cumple (a) (+0.30 en los lugares), (b) (+0.20 en el holdout, con cobertura del 100 %), (c) y (d). Conflicto
   territorial pasa (a) (+0.49) y (b) (+0.33), pero **falla (c)** —con el absurdo total, la brecha media de los lugares baja 0.0089— y
   **falla (d)** —una violación de M3 nueva en Paraguachón, donde el MAX pasa de 0.993 a 0.634 con 3 casos confirmados—. Exclusión y
   rechazo no pasan (a) (0.000 y +0.025) y quedan sin filtro.
2. **Radar nacional.** Con las dos listas y cortes recalibrados 0.7572/0.9233: 0 anclas rotas, Spearman contra el DANE
   −0.1653 → −0.0913 y Spearman con el tamaño +0.8842 → +0.8640. Pasa los tres criterios en la primera configuración, así que no
   hizo falta retirar listas. La clasificación no cambia (6/19/7, accuracy 0.3438 igual que sin mecanismo). La mejora del
   Spearman (+0.074) es menor que el +0.15 que se distingue del ruido con 32 departamentos (regla 11): los criterios del
   radar eran de **no empeorar**, y eso se cumple.
3. **Impacto.** El radar baja en 20 de 32 departamentos (media −0.0048; la mayor caída, San Andrés y Providencia, −0.0407) y
   ningún departamento ni lugar cambia de clase. Cambian 27 celdas de MAX (15 de desplazamiento, 12 de grupos armados), 14 en más
   de 0.05, y dos pasan a 0: grupos armados en San Andrés (0.861) y desplazamiento en Guainía (0.142, con 6 artículos). En los
   lugares (convención de producción): Antioquia 0.9354 → 0.9354, Maicao 0.9625 → 0.9623, Oicatá 0.6688 → 0.6239 y
   Paraguachón 0.6801 → 0.6523, todos en su misma clase.

### Salvedades (deben conocerse antes de aprobar)

- **Desplazamiento pasa el control absurdo por no empeorar, no por mejorar.** Su gemela de objeto absurdo («…por los osos
  polares») sigue con MAX entre 0.86 y 0.99 en los seis lugares con artículos, con y sin filtro: la brecha real − gemela no
  cambia (+0.0013 en los lugares, 0.0000 en el holdout). El filtro no distingue el objeto; solo quita artículos sin palabras de
  desplazamiento. Lo que sí mejora es el absurdo total (por ejemplo, Antioquia 0.379 → 0.206). Grupos armados, en cambio, baja
  su gemela (0.669 → 0.611 en Antioquia, 0.688 → 0.456 en Maicao) y la mantiene por debajo de 0.766.
- **Desplazamiento no cumple los criterios absolutos de la ronda 1** (M2 ≥ 0.60, M1 en 3 de 4 lugares, gemela por debajo
  de 0.766): su M2 en los lugares es 0.35 y en el holdout 0.567. Entra porque la regla de esta etapa mide ganancia
  relativa (+0.20 y +0.10), que es lo pre-registrado.
- **La ganancia de desplazamiento en el holdout la sostienen Cauca (0.30 → 0.80) y Chocó (0.80 → 0.90).** Cundinamarca no
  tiene casos confirmados (0 → 0), y aun así su MAX sin filtro (0.919) y con filtro sigue violando M3 (no es violación nueva).
- **Las listas están diseñadas con los lugares de la ronda 1** y el holdout (3 departamentos) es la comprobación fuera de
  muestra. Los positivos por indicador son pocos (desplazamiento 9 y 14 en Cauca y Chocó; grupos armados 20, 18 y 6).
- **Juicio.** Solo 26 artículos nuevos (el pool ya estaba juzgado en un 67 %) y 10 de control, en un lote. Kappa 0.923
  (desplazamiento), 1.000 (conflicto) y 0.875 (grupos armados). En los controles, `juez-a`/`juez-b` coinciden con la etiqueta
  previa en 4 indicadores (10 de 10) y en 8 de 10 en grupos armados (los dos discrepantes pasan a SÍ/SÍ); los controles
  conservan su etiqueta previa en la referencia.
- **Sanidad.** El chequeo de «los cuatro MAX de grupos armados que cambian» del pre-registro se hizo contra el archivo
  original de la F7 (`cortes_radar.xlsx`), a 4 decimales y en los 32 departamentos (diferencia 0), porque el log de la F7
  cita 3 decimales redondeados desde 4 (Caldas 0.7245 figura como 0.725; exacto 0.724465). Es una comprobación más fuerte, no
  más débil.
- **Truncación de producción.** Con la premisa recortada con la hipótesis de cada indicador, la compuerta difiere en 16
  artículos (grupos armados) y 4 (desplazamiento) de los 11.439 y no cambia ningún MAX departamental (diferencia 0 en el radar).
- **Regla 15.** La excepción para listas por indicador la transmitió el coordinador como decisión del usuario; implementar
  en `src/` exige su confirmación (`experimentos/PLAN_implementacion_prefiltro_indicador.md`).
