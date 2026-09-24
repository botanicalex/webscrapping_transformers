# Informe 07 — Prueba de un modelo NLI alternativo: etapa 2 (juicio) y rechazo del modelo

Fecha: 2026-09-23 · Rama de prueba `prueba-modelo-nli` (temporal, no se fusiona) · Pre-registro
`experimentos/PREREG_modelo_nli.md` (congelado en 710c7be) · Etapa 1 en e161796 (informe 06).

## 1. Resumen

El modelo `vicgalle/xlm-roberta-large-xnli-anli` **no mejora el radar lo suficiente y queda
rechazado**, según la regla fijada de antemano. Ningún indicador cumple los 5 criterios, así que
no se hace la etapa 3 (escala nacional; unas 6–7 h de GPU según una estimación a partir de la
etapa 1, no medida). Producción no cambia.

## 2. Qué se hizo

En la etapa 1, conflicto territorial pasó el control de «osos polares» y entró a juicio junto con
grupos armados. En esta etapa, dos jueces LLM ciegos (de dos modelos distintos) revisaron los 22
artículos que el modelo nuevo pone arriba y que nunca se habían juzgado. Además revisaron 40 ya
juzgados, como control de que juzgan igual que en las rondas anteriores (coinciden en el 97–100 %).
Con eso la referencia pasa a 962 artículos juzgados. Luego se aplicaron los mismos criterios de
las rondas 1–2 al modelo nuevo y al actual, con la misma frase, fórmula y agregación MAX.

## 3. Resultado

Precisión de los 10 artículos con puntaje más alto (M2), media en Antioquia / Maicao / Oicatá /
Paraguachón. Se exigía ≥ 0.60.

| Indicador | Modelo actual | Modelo nuevo | Acuerdo entre jueces (kappa) | ¿Cumple 1–5? |
|---|---|---|---|---|
| Conflicto territorial | 0.07 | 0.07 | 0.88 | no |
| Presencia de grupos armados | 0.17 | 0.35 | 0.95 | no |

- **Grupos armados** mejora: duplica la precisión y sube el acuerdo con el estándar de palabras
  clave (AUC 0.788 → 0.877). Pero queda lejos de 0.60, y el artículo que fija el máximo solo es un
  caso real en Antioquia. Con el modelo actual lo era en dos lugares.
- **Conflicto territorial** no mejora. El modelo nuevo deja de confirmar la frase con «osos
  polares», pero los artículos que pone arriba siguen sin reportar conflicto. El artículo que fija
  el máximo no es un caso real en ninguno de los 4 lugares.
- **Control absurdo general** («colonias de osos polares»): en Antioquia sube de 0.38 a 0.51 y
  supera el tope pre-registrado (0.43). Lo causa un solo artículo de 494 («Celsia sembró más de 13
  millones de árboles nativos»; tabla «Criterio 4» de `experimentos/RESULTADOS_modelo_nli.md`).
  Basta para que ningún indicador cumpla el criterio 4.
- Exclusión de beneficios económicos: 0 casos confirmados en 962 artículos. Sigue sin poder
  medirse con este corpus.

**Lectura:** que el modelo deje de confirmar la frase absurda es necesario, pero no suficiente.
Con este modelo, el artículo que fija el máximo es un caso real en 1 de los 6 pares
lugar-indicador que tienen casos reales. Con el actual lo es en 3 (`metricas_modelo_nli.xlsx`,
columnas M1). Esto vale para este modelo; no se probó ningún otro.

## 4. Límites

Son 4 lugares (Oicatá sin casos reales) y la referencia son jueces LLM, no humanos; no se ha
medido cuánto coinciden con un juicio humano. El corte 0.766 está calibrado para el modelo
actual, pero no cambia el resultado: la precisión (criterio 1) y el acierto del máximo
(criterio 2) no dependen de él.

## 5. Decisión y pendientes

- El modelo queda rechazado para el radar (pre-registro §5) y no hay etapa 3.
- Una revisión final independiente confirmó que el rechazo se sigue del pre-registro. Sus
  correcciones menores están aplicadas en este informe y en la sección 6.
- Cierre, aprobado por el responsable: la documentación y los resultados de la prueba pasan a la
  rama principal del plan (`hipotesis-5ind-max`) sin tocar producción. La rama de prueba se borra y
  queda una etiqueta con todo su historial. El modelo descargado (2.24 GB) va a la papelera.

## 6. Correcciones al informe 06

Las detectó la revisión final independiente de la prueba:

- Donde dice «es la primera vez en tres rondas que un control deja de puntuar como la frase real
  en un indicador que antes fallaba», debe decir «la primera vez **con la frase vigente, sin
  cambiarla**». En la segunda ronda, una frase reescrita de conflicto (N3) ya lo había logrado
  (gemela 0.70/0.70/0.02/0.06, `experimentos/RESULTADOS_5ind_MAX_r2.md`), con precisión 0.12.
- Donde dice «9 de los 10 primeros de cada indicador no están juzgados», debe decir: 9 de los 40
  puestos del top-10 de los 4 lugares en conflicto, y 9 de 34 en grupos armados (Oicatá solo tiene
  4 artículos con puntaje). Fuente: `etapa1_filtro.log` y `etapa2_lotes.log`.
- Las «6–7 h de GPU» de la etapa 3 son una estimación a partir de la etapa 1, no una medida.

## Trazabilidad

Tablas: `experimentos/RESULTADOS_modelo_nli.md` y
`experimentos/resultados/juicio_modelo_nli/metricas_modelo_nli.xlsx`. Juicio:
`juicio_modelo_nli/etapa2_consolidar.log`, `referencia.csv`, `etiquetas_a/` y `etiquetas_b/`.
Decisión: `contexto/08_log_decisiones.md` [2026-09-23], entradas «etapa 2» y «revisión final».
