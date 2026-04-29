# 01 — Objetivo y métricas (implementación actual)

## Objetivo operativo del código

El objetivo implementado es:

- Generar un radar departamental desde noticias (`radar_propio`) con escala 0–100.
- Compararlo contra `radar_oficial_promedio` desde un archivo Excel externo.
- Medir error por experimento para priorizar configuraciones con menor desviación.

No existe un loop automático de optimización en un solo script; la optimización se ejecuta por corridas sucesivas.

## Umbral de éxito y criterio de aceptación

Para considerar una corrida como exitosa, el **MAPE** debe situarse en:

- **Ideal:** < 10%
- **Aceptable (meta actual):** 10% – 23%
- **Crítico:** > 25% → requiere revisión de keywords o fuentes

## Métricas calculadas en el proyecto

En `metricas_y_calculo_de_error.py` se calculan por cada columna `experimento_*` (o `radar_prensa_calculado`):

- MAE
- RMSE
- R2
- Pearson y p-value
- MAPE (%)
- sesgo promedio
- n_departamentos

Además, se calcula un ranking compuesto:

- `score_ranking = 0.35*rank_MAE + 0.30*rank_RMSE + 0.20*rank_MAPE + 0.15*rank_Pearson`

## Hipótesis de optimización (Weekly 2026-04-28)

1. **Correlación fuentes–error:** El error (MAE/MAPE) es inversamente proporcional al número de fuentes y artículos procesados por departamento. Departamentos con mayor volumen de artículos tienden a mostrar errores menores.
2. **Sesgo por keywords agresivas:** La sobreestimación sistemática (bias positivo) puede deberse a un exceso de noticias negativas capturadas por keywords muy amplias, sin suficiente contraste de artículos neutrales.

## Entradas requeridas para métricas

Archivo esperado:

- `comparacion_radares.xlsx`

Columnas requeridas:

- `departamento`
- `radar_oficial_promedio`
- al menos una columna de experimento (`experimento_1`, `experimento_2`, ...) o `radar_prensa_calculado`

## Salidas de métricas

- Excel: `resultado_comparacion_radares_<timestamp>.xlsx`
  - hoja `metricas`
  - hoja `ranking`
  - hoja `errores`
- Gráficas en `graficos_metricas/corrida_<timestamp>/`
  - `ranking_experimentos.png`
  - `<experimento>_scatter.png`
  - `<experimento>_error_departamento.png`

## Notas de interpretación

- Error por departamento se define como `radar_experimento - radar_oficial_promedio`.
- Error positivo implica sobreestimación del experimento frente al oficial.
- MAPE ignora divisiones por cero al convertir ceros del oficial a `NaN` para ese cálculo.
