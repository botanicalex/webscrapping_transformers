# Experimentos — registro operativo

Este archivo se usa para registrar corridas reales realizadas con el código actual.

## Formato recomendado por corrida

- Fecha
- Configuración de scraping (temas, grupos, rango de fecha)
- Ruta de salida de pipeline (`resultados_pipeline/...`)
- Archivo de métricas generado (`resultado_comparacion_radares_<timestamp>.xlsx`)
- Resumen de métricas (MAE, RMSE, MAPE, Pearson, sesgo)
- Observaciones

## Corrida baseline registrada

- Fuente disponible en repositorio:
  - `resultado_comparacion_radares.xlsx`
  - `resultado_comparacion_radares_20260429_0053.xlsx`

Para mantener trazabilidad, cada nueva corrida debe agregarse como sección nueva con el siguiente template.

## Template

### Experimento N

- Fecha:
- Scraping:
  - FECHA_DESDE:
  - FECHA_HASTA:
  - TEMAS_BUSQUEDA:
  - Grupos ejecutados:
- Pipeline:
  - Comando usado:
  - Archivos de salida:
- Métricas:
  - Archivo entrada: `comparacion_radares.xlsx`
  - Archivo salida:
  - MAE:
  - RMSE:
  - MAPE:
  - Pearson:
  - sesgo_promedio:
- Observaciones:
