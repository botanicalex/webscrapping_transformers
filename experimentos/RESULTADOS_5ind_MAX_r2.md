# Resultados — 2a ronda 5ind MAX, fase A (4 lugares, solo hipótesis)

Generado por `experimentos/exp_5ind_max_r2_metricas.py`; detalle en `experimentos/resultados/juicio_5ind_r2/metricas_r2.xlsx`. Pre-registro `experimentos/PREREG_5ind_MAX_r2.md`. Criterio 6 (holdout) pendiente de la fase B.

Referencia: 940 artículos juzgados (ronda 1: 565 lugares + 94 holdout; ronda 2: 281 nuevos, por origen {'muestra': 205, 'pool': 75, 'control': 40, 'pool+muestra': 1}). Los 40 de control conservan su etiqueta de la ronda 1.

M2 = precisión@10 media en los 4 lugares (A/M/O/P = Antioquia/Maicao/Oicatá/Paraguachón); M2+ = solo lugares con positivos; gemela = frase con «osos polares»; absurdo total idéntico para todas (no discrimina).

## `exclusion_beneficios_economicos` — kappa -0.00 — positivos 0/0/0/0 — finalistas: ninguna — NO MEDIBLE (§5)

Absurdo total, máx por lugar: 0.38/0.57/0.43/0.21.

| cand | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | M5 | c1 | c2 | c3 | c4 | c5 | pasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vig | 0.00 | — | 0 | 4 | 1.00/1.00/0.99/0.99 | 0.99/0.99/0.90/0.98 | 0.50 | no | no | sí | no | sí | no |
| N1 | 0.00 | — | 0 | 4 | 0.99/0.99/0.98/0.89 | 0.94/0.81/0.79/0.50 | 1.50 | no | no | sí | no | sí | no |
| N2 | 0.00 | — | 0 | 4 | 0.99/0.99/0.93/0.94 | 0.92/0.97/0.85/0.85 | 2.00 | no | no | sí | no | sí | no |
| N3 | 0.00 | — | 0 | 2 | 0.81/0.83/0.22/0.49 | 0.96/0.80/0.24/0.25 | 0.00 | no | no | sí | no | sí | no |
| P1 | 0.00 | — | 0 | 4 | 0.99/0.99/0.90/0.77 | 0.78/0.93/0.20/0.82 | 3.25 | no | no | sí | no | sí | no |
| P2 | 0.00 | — | 0 | 4 | 0.99/0.99/0.97/0.98 | 0.96/0.97/0.69/0.82 | 2.25 | no | no | sí | no | sí | no |

## `rechazo_proyecto` — kappa 0.44 — positivos 1/3/0/0 — finalistas: ninguna

Absurdo total, máx por lugar: 0.38/0.57/0.43/0.21.

| cand | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | M5 | c1 | c2 | c3 | c4 | c5 | pasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vig | 0.00 | 0.00 | 0 | 2 | 0.99/1.00/0.98/0.99 | 0.98/0.99/0.97/0.96 | 2.25 | no | no | sí | no | sí | no |
| N1 | 0.25 | 0.00 | 1 | 2 | 0.39/0.91/0.00/0.82 | 0.11/0.34/0.00/0.00 | 1.25 | no | no | no | sí | sí | no |
| N2 | 0.00 | 0.00 | 0 | 0 | 0.79/0.77/0.00/0.09 | 0.28/0.69/0.00/0.09 | 0.50 | no | no | sí | sí | sí | no |
| N3 | 0.00 | 0.00 | 0 | 2 | 0.76/0.62/0.09/0.31 | 0.28/0.33/0.00/0.44 | 1.25 | no | no | no | sí | sí | no |
| P1 | 0.03 | 0.05 | 0 | 0 | 0.83/0.93/0.39/0.08 | 0.28/0.34/0.00/0.00 | 0.25 | no | no | sí | sí | sí | no |
| P2 | 0.00 | 0.00 | 0 | 1 | 0.97/0.99/0.69/0.86 | 0.91/0.86/0.00/0.31 | 1.00 | no | no | sí | no | sí | no |

## `desplazamiento_forzado` — kappa 0.88 — positivos 10/1/0/0 — finalistas: ninguna

Absurdo total, máx por lugar: 0.38/0.57/0.43/0.21.

| cand | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | M5 | c1 | c2 | c3 | c4 | c5 | pasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vig | 0.05 | 0.10 | 0 | 1 | 0.99/0.98/0.52/0.98 | 0.98/0.96/0.70/0.94 | 3.50 | no | no | sí | no | sí | no |
| N1 | 0.07 | 0.15 | 0 | 1 | 1.00/0.98/0.51/0.87 | 0.99/0.98/0.46/0.80 | 2.00 | no | no | sí | no | sí | no |
| N2 | 0.03 | 0.05 | 0 | 1 | 0.99/0.98/0.29/0.94 | 0.89/0.95/0.35/0.95 | 2.00 | no | no | sí | no | sí | no |
| N3 | 0.03 | 0.05 | 1 | 1 | 1.00/0.98/0.48/0.97 | 0.99/0.99/0.41/0.98 | 0.00 | no | no | sí | no | sí | no |
| P1 | 0.00 | 0.00 | 0 | 2 | 1.00/1.00/0.99/0.97 | 1.00/0.99/0.94/0.99 | 2.50 | no | no | no | no | sí | no |
| P2 | 0.05 | 0.10 | 0 | 1 | 1.00/0.99/0.52/0.97 | 0.99/0.98/0.31/0.98 | 1.75 | no | no | sí | no | sí | no |

## `conflicto_territorial` — kappa 0.87 — positivos 10/8/0/3 — finalistas: ninguna

Absurdo total, máx por lugar: 0.38/0.57/0.43/0.21.

| cand | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | M5 | c1 | c2 | c3 | c4 | c5 | pasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vig | 0.07 | 0.10 | 1 | 1 | 1.00/0.99/0.90/0.99 | 0.95/0.99/0.89/0.72 | 4.25 | no | no | sí | no | sí | no |
| N1 | 0.26 | 0.34 | 2 | 1 | 0.99/0.96/0.04/0.63 | 0.78/0.89/0.00/0.83 | 2.00 | no | no | no | no | sí | no |
| N2 | 0.10 | 0.13 | 1 | 0 | 1.00/0.98/0.44/0.99 | 0.93/0.98/0.04/0.51 | 2.75 | no | no | sí | no | sí | no |
| N3 | 0.12 | 0.17 | 1 | 0 | 0.98/0.98/0.51/0.86 | 0.70/0.70/0.02/0.06 | 1.75 | no | no | sí | sí | sí | no |
| P1 | 0.10 | 0.13 | 1 | 0 | 1.00/0.98/0.73/0.99 | 0.88/0.89/0.47/0.87 | 2.50 | no | no | sí | no | sí | no |
| P2 | 0.10 | 0.13 | 1 | 1 | 1.00/1.00/0.97/0.99 | 0.98/0.98/0.73/0.59 | 3.25 | no | no | sí | no | sí | no |

Lugares (de 4) cuyo artículo del MAX coincide con el de la vigente de `presencia_grupos_armados`: vig 1, N1 1, N2 2, N3 0, P1 1, P2 1

## `presencia_grupos_armados` — kappa 0.94 — positivos 42/45/0/5 — finalistas: ninguna

Absurdo total, máx por lugar: 0.38/0.57/0.43/0.21.

| cand | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | M5 | c1 | c2 | c3 | c4 | c5 | pasa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vig | 0.17 | 0.23 | 2 | 0 | 1.00/0.98/0.65/0.99 | 0.67/0.69/0.65/0.36 | 1.75 | no | no | sí | sí | sí | no |
| N1 | 0.33 | 0.43 | 2 | 1 | 0.90/0.93/0.10/0.50 | 0.87/0.97/0.42/0.77 | 0.00 | no | no | no | no | sí | no |
| N2 | 0.25 | 0.33 | 2 | 1 | 0.99/0.98/0.83/0.95 | 0.97/0.99/0.59/0.89 | 0.00 | no | no | no | no | no | no |
| N3 | 0.33 | 0.43 | 3 | 1 | 0.92/0.93/0.09/0.63 | 0.49/0.63/0.12/0.61 | 1.75 | no | sí | no | no | no | no |
| P1 | 0.30 | 0.40 | 1 | 0 | 0.98/0.96/0.70/0.91 | 0.79/0.89/0.75/0.60 | 0.50 | no | no | sí | no | no | no |
| P2 | 0.38 | 0.50 | 1 | 0 | 0.99/0.97/0.47/0.83 | 0.75/0.76/0.69/0.38 | 2.50 | no | no | sí | no | sí | no |

M6 (AUC contra la plata): vig 0.788, N1 0.785, N2 0.667, N3 0.729, P1 0.610, P2 0.837

Lugares (de 4) cuyo artículo del MAX coincide con el de la vigente de `conflicto_territorial`: vig 1, N1 0, N2 0, N3 1, P1 0, P2 1

## Exclusión de beneficios económicos (§5)

SÍ/SÍ en total (las dos rondas): **0** → NO MEDIBLE con este corpus (< 5): decide el usuario. Por origen: {}.


## Control entre rondas (40 artículos ya juzgados, solo reporte)

| indicador | acuerdo SI/SI r2 vs r1 | SI/SI r1 | SI/SI r2 |
|---|---|---|---|
| `exclusion_beneficios_economicos` | 1.00 | 0 | 0 |
| `rechazo_proyecto` | 0.97 | 1 | 2 |
| `desplazamiento_forzado` | 1.00 | 2 | 2 |
| `conflicto_territorial` | 1.00 | 1 | 1 |
| `presencia_grupos_armados` | 0.97 | 7 | 8 |

GPU estimada de la fase B: 0 min (finalistas × 2 frases × 7.3 min).

