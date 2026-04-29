# 06 — Cálculo de radar y métricas

## Cálculo de radar desde `Transformer_optimo.py`

Clase: `CalculadorRadar`

### Agregación departamental

- Convierte columnas booleanas a numéricas
- Agrupa por `departamento` y promedia (`groupby.mean`) las señales
- Calcula `n_articulos` por departamento

### Variables invertidas

Las variables en `VARS_INVERTIR` se transforman con `1 - valor` antes de construir bloques.

### Bloques A-E

`BLOQUES_PCA` define variables por bloque:

- `bloque_A`
- `bloque_B`
- `bloque_C`
- `bloque_D`
- `bloque_E`

Para cada bloque:

- si hay suficiente información, usa PCA (1 componente) sobre datos estandarizados
- si no, usa promedio simple
- luego aplica escalado min-max a 0–100

### Fórmulas implementadas

- `corr_raw = 0.80*bloque_B + 0.35*bloque_A - 0.15*bloque_C`
- `vul_raw = 0.50*bloque_D + 0.50*bloque_E`
- `corrupcion_score = minmax(corr_raw)`
- `vulneracion_score = minmax(vul_raw)`
- `radar_raw = 0.60*corrupcion_score + 0.40*vulneracion_score`
- `radar_propio = minmax(radar_raw)`

### Categorización de riesgo

- `bajo` si `radar_propio <= p25`
- `alto` si `radar_propio >= p75`
- `medio` en caso contrario

Salida final ordenada por `radar_propio` descendente con columnas:

- `departamento`
- `n_articulos`
- `bloque_A ... bloque_E`
- `corrupcion_score`
- `vulneracion_score`
- `radar_propio`
- `categoria_riesgo`

## Métricas desde `metricas_y_calculo_de_error.py`

Entrada:

- `comparacion_radares.xlsx`

Métricas por experimento:

- MAE
- RMSE
- R2
- Pearson
- Pearson_p
- MAPE_pct
- sesgo_promedio

También genera:

- tabla de errores absolutos por departamento
- ranking global de experimentos por score ponderado
- gráficos de ranking, scatter y error departamental
