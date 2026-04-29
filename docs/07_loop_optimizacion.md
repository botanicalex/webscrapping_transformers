# 07 — Loop de optimización (operación real en este repositorio)

## Estado real

En esta versión no existe un único script que ejecute un loop automático completo de optimización con criterio de parada interno.

La optimización se realiza como ciclo manual/repetible:

1. Ajustar configuración de scraping (temas, grupos, corridas)
2. Ejecutar scraping
3. Ejecutar `Transformer_optimo.py`
4. Actualizar `comparacion_radares.xlsx` con columnas de experimento
5. Ejecutar `metricas_y_calculo_de_error.py`
6. Comparar métricas y decidir la siguiente corrida

## Punto de control por etapa

### A. Scraping

- scripts: `grupo_01.py` ... `grupo_11.py`
- salida: `resultados/df_corpus_*.pkl`
- monitor: `monitor.py`

### B. NLP + radar

- script: `Transformer_optimo.py`
- salida:
  - `resultados_pipeline/df_procesado.pkl`
  - `resultados_pipeline/radar_departamentos.csv`

### C. Métricas

- script: `metricas_y_calculo_de_error.py`
- entrada: `comparacion_radares.xlsx`
- salida:
  - `resultado_comparacion_radares_<timestamp>.xlsx`
  - `graficos_metricas/corrida_<timestamp>/`

## Qué sí está automatizado

- ejecución por grupos de scraping
- fallback por departamento en scraping
- pipeline NLP completo de artículos a radar
- cálculo de métricas para múltiples columnas de experimento

## Qué no está automatizado en un solo loop

- generación iterativa automática de nuevas configuraciones
- criterio de parada computado por iteración en un orquestador único
- actualización automática del Excel de comparación desde el radar recién generado

## Práctica recomendada para iterar

- nombrar cada corrida como `experimento_n` en el Excel
- conservar salida timestamp de métricas
- comparar MAE/RMSE/MAPE/Pearson del ranking y elegir siguiente ajuste
