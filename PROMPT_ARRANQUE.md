Retomamos el proyecto del radar de riesgo territorial. Trabajo en la rama `pruebas`
(carpeta pruebas/, no desarrollo/).

Antes de proponer o ejecutar nada, lee en este orden:
  contexto/00_estado_actual.md
  contexto/08_log_decisiones.md   <- lo que ya está cerrado, no relitigar
  contexto/07_backlog.md
  contexto/09_riesgos_y_limites.md

Sobre la tarea 0 del backlog (identificar cuál es el índice del DANE de referencia):
PENDIENTE, la traigo yo.

Arranque propuesto:
1. Lanza en segundo plano:  cd experimentos && python generar_scores_32deptos.py
   (~4 h, guarda checkpoint tras cada hipótesis y reanuda solo). Es el insumo de
   casi todo lo demás.
2. Mientras corre, haz las tareas que no dependen de él: 0b (líneas base en el
   script de métricas) y 3b (probar términos de búsqueda de déficit en un
   departamento).

Recordatorios que ya costaron tiempo:
- Ninguna variante se adopta sin pasar el control absurdo. El AUC solo, no decide.
- Optimiza mirando Spearman contra radar_oficial_promedio; reporta la accuracy.
- Con n=32 no persigas mejoras menores a ~15 pp: son ruido.
- Si cambias lo que se mide, recalibra el umbral que lo corta.
