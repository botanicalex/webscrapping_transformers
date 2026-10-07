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
| 08 | [`08_informe_exclusion_beneficios_economicos.md`](08_informe_exclusion_beneficios_economicos.md) | 2026-09-24 | Por qué exclusión de beneficios económicos no se ha podido medir (0 casos confirmados en 962 juzgados y 102 leídos a mano), qué hace hoy en el radar (casi una constante: quitarlo no cambia ninguna clase) y opciones para decidir. |
| 09 | [`09_informe_avances_rama_hipotesis_5ind_max.md`](09_informe_avances_rama_hipotesis_5ind_max.md) | 2026-09-24 | Avances de la rama `hipotesis-5ind-max` para el responsable, antes de decidir la fusión: sistema de evaluación con jueces, causa medida del problema, mejora de grupos armados (fuera de producción por la regla), descartes con evidencia y decisiones pendientes. |
| 10 | [`10_informe_resumen_consolidado_01-09.md`](10_informe_resumen_consolidado_01-09.md) | 2026-09-24 | Resumen para los responsables de los informes 01 a 09, sin repeticiones: qué se logró, qué se rechazó, datos por indicador, la prueba del modelo NLI `xlm-roberta-large-xnli-anli` y decisiones pendientes. No añade mediciones nuevas. |
| 11 | [`11_informe_prefiltro_social_max.md`](11_informe_prefiltro_social_max.md) | 2026-09-28 | ¿Conviene reintegrar el pre-filtro de relevancia social bajo MAX (umbral 0.85)? No: el radar casi no cambia (0 cambios de clase, 51 de 832 celdas), el filtro cuesta capacidad de ordenar y no mejora la cabeza del ranking con jueces. Los 4 lugares, vueltos a correr con la producción actual, dan lo mismo que el 1-sep. Producción no cambia. |
| 12 | [`12_informe_prefiltro_por_indicador.md`](12_informe_prefiltro_por_indicador.md) | 2026-09-29 | Pre-filtro por indicador (una lista de palabras de objeto por indicador) en lugar del general, que no servía: con jueces en el holdout entran grupos armados y desplazamiento (conflicto, rechazo y exclusión quedan fuera); el radar apenas cambia (ninguna clase) y los 4 lugares dan lo predicho; se promueve a `src/` con cortes 0.7572/0.9233. Incluye la propuesta de la etapa 2 (17 listas y 4 indicadores abstractos). |
| 13 | [`13_informe_prefiltro_etapa2_y_prefiltro_social.md`](13_informe_prefiltro_etapa2_y_prefiltro_social.md) | 2026-09-29 | Por qué no se reactiva el pre-filtro social (medido dos veces: no mejora el radar ni la cabeza del ranking, cuesta AUC; el 87 % de los errores de cabeza son socialmente relevantes) y resultado del tramo 1 de la etapa 2 del pre-filtro por indicador (6 indicadores): ninguna lista nueva entra (2 no medibles; 4 fallan la regla, sobre todo el control absurdo). Producción no cambia. Incluye la trazabilidad del artículo que fija el MAX (8 → 14 de 42 casos confirmados con listas). |
| 14 | [`14_informe_prefiltro_etapa2_cierre.md`](14_informe_prefiltro_etapa2_cierre.md) | 2026-09-29 | Cierre de la etapa 2 del pre-filtro por indicador: cribado sin jueces de los 11 indicadores restantes (control absurdo y radar); sobrevive solo zonas de protección alimentaria, que con jueces no alcanza la ganancia exigida. Ninguna lista nueva; producción no cambia (listas solo en grupos armados y desplazamiento). |
| 15 | [`15_informe_radar_18ind_hipotesis_jefe.md`](15_informe_radar_18ind_hipotesis_jefe.md) | 2026-10-07 | Radar de 18 indicadores (se retiran movimientos sociales y exclusión de servicios) con tres hipótesis nuevas pedidas por el jefe y el blanqueo del Excel quitado; cortes 0.6885/0.8916, ningún lugar ni departamento cambia de clase. El control absurdo falla en conflicto territorial y resistencia territorial (suman casi una constante) y en brecha en zonas de protección alimentaria; se reporta, no decide. Decisión pendiente del jefe. |

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
