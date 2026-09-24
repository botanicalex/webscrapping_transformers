# Informes

Informes de lo que se ha hecho en el proyecto del radar, escritos para un lector externo (jefe,
profesora). Cada uno se puede leer solo; el orden numérico es el cronológico.

| N.º | Informe | Fecha | Qué cubre |
|---|---|---|---|
| 01 | [`01_informe_5ind_MAX_fases_0-7.md`](01_informe_5ind_MAX_fases_0-7.md) | 2026-09-22 | Reformulación de 5 indicadores bajo MAX: diseño, jueces LLM ciegos, 12 variantes, resultados, holdout nacional y recalibración de cortes. Se adopta la compuerta de grupos armados (V08); los otros 4 quedan pendientes. |
| 02 | [`02_informe_fase_8_promocion_grupos_armados.md`](02_informe_fase_8_promocion_grupos_armados.md) | 2026-09-22 | La compuerta de grupos armados pasa a producción, cortes 0.7574/0.9233, verificación y Excel de lugares antes/después. |
| 03 | [`03_informe_reversion_f8.md`](03_informe_reversion_f8.md) | 2026-09-23 | Regla nueva (solo se cambian hipótesis): se revierte la compuerta de grupos armados; producción vuelve a `radar-max_Septiembre`, cortes 0.766/0.9233; la segunda ronda será solo de hipótesis. |
| 04 | [`04_informe_ronda2_solo_hipotesis.md`](04_informe_ronda2_solo_hipotesis.md) | 2026-09-23 | Segunda ronda: 25 frases candidatas para 5 indicadores, ninguna pasa el criterio (la mejor precisión es 0.38 frente al 0.60 exigido); producción no cambia; exclusión de beneficios no es medible con este corpus. |
| 05 | [`05_informe_consolidado_5ind_MAX.md`](05_informe_consolidado_5ind_MAX.md) | 2026-09-23 | Consolidado del plan de 5 indicadores (rondas 1 y 2, reversión): ningún indicador cambia, el NLI confirma la forma de la frase y no su objeto; propuesta de probar otro modelo NLI (`xlm-roberta-large-xnli-anli`) por etapas, pendiente de decisión. |
| 06 | [`06_informe_modelo_nli_etapa1.md`](06_informe_modelo_nli_etapa1.md) | 2026-09-23 | Prueba (solo pruebas, rama aparte) del modelo NLI `xlm-roberta-large-xnli-anli`, etapa 1: conflicto territorial pasa el control de «osos polares» y va a juicio con grupos armados; rechazo y desplazamiento no pasan; producción no cambia. |
| 07 | [`07_informe_modelo_nli_etapa2.md`](07_informe_modelo_nli_etapa2.md) | 2026-09-23 | Etapa 2 de la prueba del modelo NLI: con jueces, ni conflicto ni grupos armados cumplen los criterios (precisión 0.07 y 0.35 frente a 0.60 exigido; el control absurdo sube en Antioquia). El modelo queda rechazado, no hay etapa 3 y producción no cambia. Incluye correcciones al 06. |

Documentos relacionados (no son informes, no se mueven aquí):

- `ESTADO_DEL_PROYECTO.md` (raíz): el estado general del proyecto para lector externo.
- `experimentos/PLAN_5ind_MAX.md`, `experimentos/PREREG_5ind_MAX.md`,
  `experimentos/RESULTADOS_5ind_MAX.md`: plan, pre-registro congelado y tablas técnicas.
- `contexto/08_log_decisiones.md`: registro de todas las decisiones, con su evidencia.

## Convención

- Todo informe nuevo va en esta carpeta, con número correlativo de dos cifras y un nombre que
  diga qué cubre: `NN_informe_<tema>.md`. Se añade una fila a la tabla de arriba.
- Fecha, rama y commits en la cabecera; todo número con su archivo de origen; lenguaje para
  alguien que no ha seguido el trabajo día a día; limitaciones y pendientes explícitos.
- Un informe no se reescribe después de entregado: si algo cambia, va en el informe siguiente.
