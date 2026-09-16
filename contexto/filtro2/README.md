# Filtro 2 (gate tematico) — trabajo en pausa

Insumos guardados para retomar la calibracion del gate tematico sin rehacer el muestreo.
Ver el detalle y las decisiones en `contexto/08_log_decisiones.md` [2026-09-16] y el
pendiente en `contexto/07_backlog.md` punto 8.

## Archivos
- `muestra_60_para_etiquetar.xlsx` / `.csv`: 60 articulos del pkl de 5 lugares, barajados y
  SIN `max_26` (para no sesgar el etiquetado hacia la prediccion del modelo). Columna
  `etiqueta (social / no_social / dudoso)` vacia. `id` = indice estable del pkl.
- `mapeo_id_max26.csv`: mapeo privado `id -> max_26`. NO mirar antes de etiquetar; se usa
  recien en el Paso 3.2 para cruzar etiquetas con la señal del modelo.

## Como retomar
1. Etiquetar la columna de `muestra_60_para_etiquetar.*` (social / no_social / dudoso).
   Criterio: SOCIAL = conflicto, comunidades, derechos, instituciones o condiciones de vida
   del territorio; NO SOCIAL = deportes, farandula, clima, avisos, notas de color; DUDOSO
   se analiza aparte.
2. Cruzar `id` con `mapeo_id_max26.csv` y ver la distribucion de `max_26` por clase (3.2).
3. Proponer umbral (nivel articulo + fraccion de la muestra por lugar), con basura rechazada
   y buenos perdidos (3.3).

## Insumo de scores (NO esta en el repo, .gitignore lo excluye)
Escala V2 de produccion, por articulo, con `sesgo`, 26 columnas bias-discounted, sin
`score_social`:
`C:\Users\alexa\Downloads\tablas_lugares_max\tablas_lugares_max\df_procesado_5lugares.pkl`
