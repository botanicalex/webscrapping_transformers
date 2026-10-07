# Radar de riesgo territorial — Colombia (32 departamentos)

Prensa regional → NLI (`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`)
sobre 26 hipótesis → agregación por lugar → clase Bajo/Medio/Alto.

**Radar ALTO = zona difícil o inviable para implementar proyectos** (conflicto activo,
grupos armados, ausencia de Estado). No es un índice de "cuánto pasa", es uno de
"cuánto estorba".

**Métrica oficial:** accuracy de clasificación contra el radar DANE
(`datos/referencia/comparacion_radares_V3.xlsx`, 32 departamentos). Objetivo 0.70.

**Estado real (2026-08-31, producción ya corre V2):** el Spearman contra el objetivo subió
de **+0.067 (cero) a +0.42** — señal real, medida y verificada (salvedad: el +0.067 de
partida proviene de una columna del Excel de referencia cuya procedencia no está
identificada; recalculado desde V0+MAX da −0.18 — ver `08_log_decisiones.md`
[2026-08-31]). **Pero la accuracy sigue sin
superar de forma concluyente a las líneas base**: la configuración en producción da 0.250 y
la mejor medida de todas (no desplegable) 0.406, contra "siempre Bajo" 0.344 y azar 0.333.
Con n=32 nada de eso se distingue del ruido. **El indicador de trabajo es el Spearman, no la
accuracy.** Leer `contexto/10_combinaciones_y_rumbo.md` para la comparación completa entre
configuraciones, y `contexto/09_riesgos_y_limites.md` antes de invertir más trabajo en
optimizar indicadores — hay un techo estructural y una decisión de diseño pendiente.

## Reglas duras

1. **Ninguna variante se adopta sin pasar el control absurdo.** El AUC mide orden; el
   control absurdo mide si el "sí" significa algo. En tres ocasiones el AUC apuntó a la
   opción equivocada y solo el control la delató. Si el AUC sube y el control empeora, se
   rechaza.
2. **Si cambia lo que se mide, hay que recalibrar el umbral.** Un umbral solo significa algo
   respecto de la distribución para la que se calibró. Ya falló tres veces: se conservó el
   0.65 del pre-filtro al cambiarle la hipótesis, los cortes 1/3–2/3 al cambiar la
   agregación, y los cortes 0.3074/0.3524 calibrados sobre P75 interpolado cuando
   producción usa rango-cercano.
3. **El control absurdo se reescribe en el formato de la variante que prueba.** El nivel
   absoluto depende del absurdo elegido (pingüinos 20.5%, osos polares 8.6% en la misma
   configuración): solo son comparables mediciones con el mismo contenido absurdo.
4. **`NULA_TEST` no entra jamás en la calibración del sesgo.** Para eso están las 4 de
   `NULAS_CALIBRACION`. Mezclarlas destruye la única evaluación honesta que queda.
5. **`experimentos/` existe en esta rama** (pre-registros, scripts y resultados de los
   experimentos). Las 26 hipótesis V2 de producción viven en `src/Transformer_optimo.py`;
   `src/` no importa de `experimentos/`.
6. **NLI fuera de `src/`: `experimentos/nli_core.py`** (con la verificación contra
   producción). Para validar cambios en `src/`, correr `python src/test_integracion.py`
   (16 tests, sin GPU).
7. **Un experimento aísla UNA variable.** Dos cambios a la vez no se pueden atribuir.
8. **No repetir GPU.** Puntuar los 32 departamentos son ~4 h. Se guardan `ent_` y `neu_`
   **sin enmascarar** en un pkl y todo el análisis posterior se hace sobre el pkl.
9. **`src/` es producción; los experimentos no lo tocan.** Se promueve solo lo que pasó los
   criterios, y se registra al promoverlo.
10. **Toda decisión, incluidos los rechazos, va a `contexto/08_log_decisiones.md`.** Lo que
    figure ahí como CERRADO no se relitiga sin evidencia nueva medida.
11. **n = 32.** El error estándar de la accuracy es ~8 pp; diferencias menores a ~15 pp no
    se distinguen del ruido. No optimizar a ciegas contra ese número.
12. **Se experimenta en `pruebas`, se entrega desde `master`.** `src/` en master es lo que
    se manda si alguien pide el proyecto.
13. **Promover algo de `pruebas` a `master` no está completo hasta que
    `ESTADO_DEL_PROYECTO.md` lo refleje.** El entregable describe lo probado, no lo
    intentado.
14. **Los rechazos se registran en `contexto/08_log_decisiones.md` en `pruebas`, sobre la
    marcha** — no esperan a la fusión. Registrarlos evita reintentarlos.
15. **De cada indicador solo se cambia la hipótesis** (la frase que evalúa el NLI). No se
    cambia el cálculo interno del indicador (nada de compuertas de palabras clave, `min` de
    varias frases ni restas de confusores) ni se agregan columnas a la salida. Regla del
    usuario del 2026-09-23; por ella se revirtió la compuerta de grupos armados de la F8 del
    plan 5ind MAX (`contexto/08_log_decisiones.md` [2026-09-23]).
    **Única excepción (2026-09-29, confirmada por el usuario): el pre-filtro por indicador.**
    Una lista de palabras de objeto por indicador (hoy solo `presencia_grupos_armados` y
    `desplazamiento_forzado`; `PREFILTRO_OBJETO` en `src/Transformer_optimo.py`), exigida en la
    premisa visible del par y calculada por dentro de `procesar()`, sin columnas nuevas. Alcance:
    solo esas listas congeladas (las de la ronda 1); una lista nueva (etapa 2), una compuerta ad hoc,
    un `min` o una resta de confusores siguen prohibidos sin pre-registro y confirmación expresa
    del usuario (`contexto/08_log_decisiones.md` [2026-09-29]).

## Estado técnico

La revisión NLI encontró **tres defectos independientes**, cada uno medido y corregido:

1. El marco metalingüístico (`"Este artículo reporta que X"`) infla los scores: el 78% de
   las noticias "implica" que menciona pingüinos emperador. → 26 hipótesis reescritas
   describiendo el territorio, no el documento (viven en `src/Transformer_optimo.py`).
2. Sesgo "sí-decidor" por artículo: el 6.5% afirma casi cualquier hipótesis. → descontar la
   línea base estimada con `NULAS_CALIBRACION`.
3. El MAX está dominado por el tamaño del corpus: el artefacto por tamaño (0.3455) supera la
   señal entre lugares (0.3156), razón 0.91. → cuantil **P75** (razón 49.0). TOP3 y TOP5
   comparten el defecto.

Score corregido en uso: `clip(clip(ent − sesgo, 0) * (1 − neu), 0, 1)`, agregado por lugar
con **MAX** (esta rama, `radar-max_Septiembre`, requisito de negocio del jefe — no la
decisión técnica del historial, que fue P75 por rango más cercano; ver
`contexto/08_log_decisiones.md` y `explicacion_alexa.md`).

**Los tres están corregidos EN PRODUCCIÓN desde el 2026-08-31.** `src/` en `pruebas`/`master`
corre P75; **en esta rama corre MAX**: hipótesis V2, **sin pre-filtro social general** (rechazado:
cuesta AUC; reevaluado y rechazado otra vez bajo MAX el 2026-09-28) pero **con pre-filtro por
indicador** en `presencia_grupos_armados` y `desplazamiento_forzado` (2026-09-29, ver regla 15),
sesgo descontado, MAX por departamento, cortes fijos recalibrados sobre esa escala
`Bajo < 0.7572 <= Medio < 0.9233 <= Alto`, y la clasificación oficial del DANE leída de
su columna (antes se recalculaba con terciles propios — era un bug).

**Rama `hipotesis-5ind-max`:** hasta el 2026-09-29 `src/` era idéntico al de `radar-max_Septiembre`.
La compuerta léxica de `presencia_grupos_armados` promovida en la F8 (2026-09-22, cortes
0.7574/0.9233) se **revirtió el 2026-09-23** por la regla 15. El **2026-09-29** se promovió el
**pre-filtro por indicador** (etapa 1, pre-registro `experimentos/PREREG_prefiltro_indicador.md`,
informe 12): las listas congeladas de grupos armados y desplazamiento, sin columnas nuevas, y cortes
**0.7572/0.9233** (clasificación 6/19/7; Spearman contra el DANE −0.1653 → −0.0913; `test_integracion`
16/16). Conflicto territorial, rechazo y exclusión de beneficios quedan sin filtro (no cumplieron la
regla de inclusión). Antes, el pre-filtro social general se rechazó también bajo MAX (informe 11).
La prueba de un modelo NLI alternativo (`vicgalle/xlm-roberta-large-xnli-anli`, solo pruebas)
terminó el 2026-09-23 con el modelo **rechazado** (informe 07; etiqueta `prueba-modelo-nli-rechazado`).

**2026-10-03:** se retiraron 6 indicadores por decisión del jefe (quedan **20**; donde este archivo dice 26, léase 20
para producción). Salida del radar con 4 bloques de 5 (`CalculadorRadar.BLOQUES`, solo descriptivos) y cortes
recalibrados **0.7138/0.905** (clases 6/19/7 iguales; `08_log_decisiones.md` [2026-10-03]).

**2026-10-06 (rama `radar-18ind`):** por orden del jefe quedan **18 indicadores** (se retiran `movimientos_sociales` y
`exclusion_servicios_derechos`), bloques 5/5/4/4, cortes **0.6885/0.8916** (clases 6/19/7 iguales, ningún departamento cambia). Tres
hipótesis nuevas del jefe (`conflicto_territorial`, `zonas_proteccion_alimentaria`, `resistencia_territorial`; solo la frase) con el
**control absurdo fallido en 2** (conflicto y resistencia saturan; zonas falla en brecha): se reporta, no decide, el jefe elige. Quitado el
blanqueo del Excel (valor y título del artículo MAX se muestran aunque el lugar sea Bajo). `test_integracion` 16/16. Donde este archivo dice 26
o 20, léase 18. Informe 15; `08_log_decisiones.md` [2026-10-06]. Sin push ni merge.

**Abierto:** ampliar el estándar de plata (cubre 2 de 26 — es la mayor debilidad, todas las
conclusiones de calidad descansan en dos); los indicadores débiles (solo `danos_ambientales`
queda en cero en P75 a escala nacional — la etiqueta "tres muertos" es del corpus de 5
lugares); re-puntuar los 32
departamentos con el código de `src/` ya promovido (~4 h GPU, nunca se corrió a escala
nacional desde producción); fusionar el corpus re-scrapeado de 3 departamentos; la **etapa 2** del pre-filtro por indicador quedó **cerrada** el 2026-09-29 sin listas nuevas (tramo 1: informe 13;
cribado de los 11 restantes y jueces de la única sobreviviente: informe 14).

## Mapa

| Ruta | Qué es |
|---|---|
| `src/` | Producción: `Transformer_optimo.py`, `radar.py`, `scrappers.py`, `config_pipeline.py`, `orquestador_pipeline.py`, `metricas_y_calculo_de_error.py`. Se ejecuta desde la raíz: `python src/<script>.py` |
| `datos/corpus/` | Texto crudo. `df_corpus_combinado_32deptos.pkl` (11.439) y `df_corpus_5lugares.pkl` (1.647) |
| `datos/referencia/` | Radar oficial DANE |
| `datos/scores/` | Matrices de scores ya calculadas — reutilizar antes de tocar la GPU |
| `../pruebas/` | Worktree hermano en la rama `pruebas`, mismo historial. Ahí se experimenta; `datos/corpus/` y `datos/scores/` están enlazados por junction a los de `desarrollo/` (no duplicar los 107 MB), `resultados/` es independiente en cada worktree |
| `informes/` | Informes para lector externo (jefe, profesora), numerados; índice y convención en `informes/README.md`. Todo informe nuevo va aquí |
| `ESTADO_DEL_PROYECTO.md` | Entregable para lector externo (jefe, profesora). Existe también en `pruebas` (copia, sincronizada por DSH el 2026-09-01); se actualiza al fusionar algo de `pruebas` a `master`, no durante los experimentos |

Los scripts de `src/` se corren **desde la raíz** (`python src/x.py`).

## Contexto bajo demanda — leer solo el que haga falta

- **`contexto/11_relevo_5ind_MAX.md` — leer primero al retomar el plan de 5 indicadores bajo
  MAX** (rama `hipotesis-5ind-max`): estado, decisiones cerradas y pendientes, segunda ronda,
  detalles operativos y siguiente paso exacto.
- `contexto/00_estado_actual.md` — qué corre hoy, qué no, en qué se estaba trabajando.
- `contexto/01_objetivo_y_radar.md` — el radar oficial DANE y cómo se calcula la accuracy.
- `contexto/02_pipeline.md` — flujo end-to-end y contrato de cada etapa.
- `contexto/03_indicadores.md` — las 26 hipótesis, V0 y V2 lado a lado.
- `contexto/04_hallazgos_revision_nli.md` — **tablas completas de los 6 experimentos.**
  Leer antes de tocar hipótesis, calibración o agregación.
- `contexto/05_scraping.md` — cómo funciona la búsqueda por nombre y sus trampas.
- `contexto/06_datos.md` — inventario de pkl: qué contiene cada uno y sus advertencias.
- `contexto/07_backlog.md` — pendientes priorizados.
- `contexto/08_log_decisiones.md` — **decisiones cerradas con su evidencia.** Leer antes de
  proponer cualquier cosa.
- `contexto/09_riesgos_y_limites.md` — **el techo estructural del proyecto.** Leer antes de
  optimizar indicadores: la cobertura de prensa va en contra del objetivo y hay una decisión
  de diseño pendiente que no es técnica.
- `contexto/10_combinaciones_y_rumbo.md` — **el documento de orientación.** Las 5
  combinaciones medidas lado a lado con su accuracy y Spearman, qué se probó y qué falta, y
  cómo se calcula el radar hoy paso a paso. Empezar por aquí al retomar.

## Convenciones

- Español, sin emojis. Los scripts imprimen tablas de texto y guardan un `.xlsx`.
- Los informes para el jefe o la profesora van a `informes/` (`NN_informe_<tema>.md`), no a
  `experimentos/` ni a la raíz.
- Los experimentos se pre-registran y ejecutan en `experimentos/`; `src/` solo cambia al
  promover algo aprobado por el usuario.
- Este proyecto es solo backend: el front vive en otra rama/repositorio y no se toca aquí.
- Todo número citado lleva su archivo de origen. Si no está medido, se dice "no medido".
- Para decidir el siguiente paso, usar el agente `orquesta-lead`
  (`.claude/agents/orquesta-lead.md`). Si el harness no lo registra como subagente
  invocable, seguir su protocolo a mano: leer 08, 07 y 00 antes de proponer, y entregar un
  solo siguiente paso con su costo y su criterio de fracaso fijado de antemano.
