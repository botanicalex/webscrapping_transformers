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
5. **`experimentos/hipotesis_base.py` es de solo lectura.** Son las 26 cadenas V0, que
   fueron producción hasta el 2026-08-31 y quedan como punto de comparación histórico. Las
   variantes van en archivos nuevos.
6. **Antes de cualquier experimento, `nli_core.verificar_contra_produccion_v2()` contra
   `datos/scores/df_procesado_baseline_v2.pkl` debe dar OK** (max|dif| < 1e-4; hoy da
   ~5e-7). Si no, `nli_core` se desvió y nada es comparable. La función sin sufijo
   (`verificar_contra_produccion`) verifica contra V0 y es legado.
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

## Estado técnico

La revisión NLI encontró **tres defectos independientes**, cada uno medido y corregido:

1. El marco metalingüístico (`"Este artículo reporta que X"`) infla los scores: el 78% de
   las noticias "implica" que menciona pingüinos emperador. → 26 hipótesis reescritas
   describiendo el territorio, no el documento (`experimentos/hipotesis_v2.py`).
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
corre P75; **en esta rama corre MAX**: hipótesis V2, **sin pre-filtro social** (rechazado:
cuesta AUC), sesgo descontado, MAX por departamento, cortes fijos recalibrados sobre esa
escala `Bajo < 0.766 <= Medio < 0.9233 <= Alto`, y la clasificación oficial del DANE leída de
su columna (antes se recalculaba con terciles propios — era un bug).

**Abierto:** ampliar el estándar de plata (cubre 2 de 26 — es la mayor debilidad, todas las
conclusiones de calidad descansan en dos); los indicadores débiles (solo `danos_ambientales`
queda en cero en P75 a escala nacional — la etiqueta "tres muertos" es del corpus de 5
lugares); re-puntuar los 32
departamentos con el código de `src/` ya promovido (~4 h GPU, nunca se corrió a escala
nacional desde producción); fusionar el corpus re-scrapeado de 3 departamentos.

## Mapa

| Ruta | Qué es |
|---|---|
| `src/` | Producción: `Transformer_optimo.py`, `radar.py`, `scrappers.py`, `config_pipeline.py`, `orquestador_pipeline.py`, `metricas_y_calculo_de_error.py`. Se ejecuta desde la raíz: `python src/<script>.py` |
| `experimentos/nli_core.py` | Motor NLI que reproduce producción sin importar `scrappers`/playwright. `NLIScorer.score(premisas, hipotesis, devolver_todo=)`, `verificar_contra_produccion_v2()` (vigente) y `verificar_contra_produccion()` (legado V0), dict `PREMISAS` |
| `experimentos/silver.py` | Estándar de plata por keywords: `etiquetar()`, `auc()`, `evaluar()`. Cubre 2 de 26 indicadores |
| `experimentos/hipotesis_v2.py` | Las 26 reescritas, `HIPOTESIS_SOCIAL`, `NULAS_CALIBRACION` (4), `NULA_TEST` (reservada) |
| `datos/corpus/` | Texto crudo. `df_corpus_combinado_32deptos.pkl` (11.439) y `df_corpus_5lugares.pkl` (1.647) |
| `datos/referencia/` | Radar oficial DANE |
| `datos/scores/` | Matrices de scores ya calculadas — reutilizar antes de tocar la GPU |
| `../pruebas/` | Worktree hermano en la rama `pruebas`, mismo historial. Ahí se experimenta; `datos/corpus/` y `datos/scores/` están enlazados por junction a los de `desarrollo/` (no duplicar los 107 MB), `resultados/` es independiente en cada worktree |
| `ESTADO_DEL_PROYECTO.md` | Entregable para lector externo (jefe, profesora). Existe también en `pruebas` (copia, sincronizada por DSH el 2026-09-01); se actualiza al fusionar algo de `pruebas` a `master`, no durante los experimentos |

Los scripts de `src/` se corren **desde la raíz** (`python src/x.py`); los de
`experimentos/`, **desde `experimentos/`**.

## Contexto bajo demanda — leer solo el que haga falta

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
- Un experimento = un archivo `experimentos/exp_<tema>.py` cuyo docstring declara, **antes**
  de correr: la pregunta, qué sería evidencia a favor y qué sería evidencia en contra.
- Todo número citado lleva su archivo de origen. Si no está medido, se dice "no medido".
- Para probar variantes de hipótesis, usar el skill `experimento-hipotesis`.
- Para decidir el siguiente paso, usar el agente `orquesta-lead`
  (`.claude/agents/orquesta-lead.md`). Si el harness no lo registra como subagente
  invocable, seguir su protocolo a mano: leer 08, 07 y 00 antes de proponer, y entregar un
  solo siguiente paso con su costo y su criterio de fracaso fijado de antemano.
