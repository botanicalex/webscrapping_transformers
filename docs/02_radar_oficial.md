# 02 — Radar de referencia y comparación en el código

## Qué usa realmente el repositorio como referencia oficial

La comparación con radar oficial se hace en `metricas_y_calculo_de_error.py` leyendo:

- `comparacion_radares.xlsx`

La columna de referencia usada en cálculos es:

- `radar_oficial_promedio`

El script no reconstruye el radar oficial desde fuentes primarias; asume que ese valor ya viene consolidado en el Excel.

## Qué compara el script de métricas

Para cada columna de experimento detectada (`experimento_*`) o `radar_prensa_calculado`:

- compara contra `radar_oficial_promedio`
- calcula MAE, RMSE, R2, Pearson, MAPE y sesgo
- construye tabla de errores por departamento

## Archivos vinculados en esta etapa

- Entrada: `comparacion_radares.xlsx`
- Salida: `resultado_comparacion_radares_<timestamp>.xlsx`
- Gráficas: `graficos_metricas/corrida_<timestamp>/`

## Relación con el radar calculado desde prensa

El radar propio se produce en `Transformer_optimo.py` mediante `CalculadorRadar` y se guarda como:

- `resultados_pipeline/radar_departamentos.csv`
- `resultados_pipeline/radar_departamentos.pkl`

Ese resultado puede usarse para alimentar columnas de experimento en `comparacion_radares.xlsx` y luego correr el script de métricas.
