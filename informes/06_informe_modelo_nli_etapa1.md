# Informe 06 — Prueba de un modelo NLI alternativo: etapa 1 (filtro sin jueces)

Fecha: 2026-09-23 · Rama de prueba `prueba-modelo-nli` (temporal, no se fusiona) · Pre-registro
`experimentos/PREREG_modelo_nli.md` (congelado en 710c7be) · Antecedente: informe 05, §7.

## 1. Qué se prueba

Solo el **modelo** que lee las frases. Se compara `vicgalle/xlm-roberta-large-xnli-anli` (24
capas, entrenado con ANLI) con el de producción (`mDeBERTa-v3-base`, 12 capas). Todo lo demás
queda idéntico: las mismas frases de los indicadores, la fórmula del puntaje, el descuento del
sesgo (calculado con el propio modelo), la agregación MAX por lugar y el texto del artículo.
**Es solo una prueba:** producción (`src/`) no se toca y el modelo nuevo no se promueve.

El defecto que se busca corregir (informe 05) es que el modelo actual confirma la *forma* de la
frase y no su *objeto*. Si en la frase se cambia el objeto por «osos polares» (la «gemela»),
puntúa casi igual que la real.

## 2. Qué se hizo

1. Revisión independiente del pre-registro. Se adoptaron sus 12 correcciones antes de medir.
2. Descarga del modelo (autorizada), con verificación de su huella digital.
3. Comprobaciones previas, todas superadas: el orden de las salidas del modelo es el correcto; el
   tamaño de lote no cambia el resultado; con el modelo actual, el script reproduce los puntajes
   ya guardados; y el modelo nuevo ve todo el texto que vieron los jueces en las rondas 1–2.
4. Etapa 1: 15 frases sobre los 1.647 artículos de los 4 lugares, en **25 minutos de GPU**.

## 3. Resultado

Puntaje máximo de la gemela (la frase con «osos polares») en Antioquia / Maicao / Oicatá /
Paraguachón. Para no pasar el control, debe quedar por debajo de 0.766 en al menos 3 lugares, sin
que la frase real se apague donde hay casos reales.

| Indicador | Gemela, modelo actual | Gemela, modelo nuevo | Resultado |
|---|---|---|---|
| Conflicto territorial | 0.95 / 0.99 / 0.89 / 0.72 | 0.47 / 0.68 / 0.26 / 0.43 | **pasa** |
| Presencia de grupos armados | 0.67 / 0.69 / 0.65 / 0.36 | 0.60 / 0.24 / 0.15 / 0.16 | pasa a la etapa 2 (ya pasaba con el modelo actual, así que no decide) |
| Rechazo a proyectos | 0.98 / 0.99 / 0.97 / 0.96 | 0.94 / 0.96 / 0.53 / 0.80 | no pasa |
| Desplazamiento forzado | 0.98 / 0.96 / 0.70 / 0.94 | 0.80 / 0.68 / 0.94 / 0.33 | no pasa |
| Exclusión de beneficios | 0.99 / 0.99 / 0.90 / 0.98 | 0.73 / 0.97 / 0.48 / 0.57 | solo reporte (no medible) |

El control absurdo general («colonias de osos polares») baja de 0.38 / 0.57 / 0.43 / 0.21 a
0.51 / 0.11 / 0.03 / 0.00. Sube en Antioquia y baja en los otros tres lugares.

**Lectura:** es la primera vez en tres rondas que un control deja de puntuar como la frase real
en un indicador que antes fallaba (conflicto). Pero el filtro solo muestra que el modelo nuevo
*podría* estar leyendo el objeto. Todavía no muestra que los artículos que pone arriba reporten
de verdad el hecho: 9 de los 10 primeros de cada indicador no están juzgados. Eso se mide en la
etapa 2.

## 4. Advertencias

- El modelo nuevo tiende más a decir «sí» a frases absurdas: el sesgo medio por artículo es 0.475
  frente a 0.364. La fórmula de producción lo descuenta. Si se llega a la escala nacional, hay un
  criterio pre-registrado que vigila que no diga «sí» a todo.
- El corte 0.766 está calibrado para el modelo actual. La escala del nuevo puede ser distinta.
- Son 4 lugares (Oicatá sin casos reales), y la referencia son jueces LLM, no humanos.

## 5. Siguiente paso

Etapa 2: dos jueces LLM ciegos revisan los 22 artículos nuevos que el modelo pone arriba en
conflicto y grupos armados, más 40 ya juzgados como control. Luego se aplican los mismos
criterios de las rondas 1–2 (precisión ≥ 0.60, entre otros). Al terminar se entrega un informe
intermedio, y la etapa 3 (escala nacional, unas 6–7 h de GPU según lo medido aquí) solo se hace
con el visto bueno del responsable.

## Trazabilidad

Cifras: `experimentos/resultados/modelo_nli/etapa1_filtro.log` y `etapa1_filtro.xlsx`; GPU
`etapa1_gpu.log`; comprobaciones y decisiones en `contexto/08_log_decisiones.md` [2026-09-23]
(entradas «pre-registro congelado», «chequeos previos» y «etapa 1»).
