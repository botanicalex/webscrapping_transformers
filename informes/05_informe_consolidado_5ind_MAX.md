# Informe — Consolidado del plan de 5 indicadores bajo MAX y propuesta de cambio de modelo

Fecha: 2026-09-23 · Rama: `hipotesis-5ind-max` (commits locales, sin push ni merge) ·
Resume los informes 01 a 04, que tienen el detalle, y cierra con una propuesta pendiente de
decisión.

## 1. Resumen

- Se intentó que 5 indicadores del radar dejaran de confundir su tema con temas vecinos. Son
  exclusión de beneficios económicos, rechazo a proyecto, desplazamiento forzado, conflicto
  territorial y presencia de grupos armados.
- Hubo dos rondas, siempre con criterios fijados antes de medir y con dos jueces LLM ciegos como
  referencia (sin etiquetado humano):
  - **Ronda 1:** 11 alternativas por indicador. Solo pasó una regla de palabras clave para grupos
    armados: la precisión subió de 0.17 a 0.93. Se llevó a producción y **se revirtió** al fijarse
    la regla de que de cada indicador solo se puede cambiar la hipótesis.
  - **Ronda 2:** 25 frases nuevas, solo cambiando la hipótesis. **No pasó ninguna**; la mejor
    precisión fue 0.38 frente al 0.60 exigido.
- **Resultado final:** ningún indicador cambió. Producción es exactamente la rama desplegada
  `radar-max_Septiembre`: 26 indicadores, agregación MAX, cortes Bajo < 0.766 ≤ Medio <
  0.9233 ≤ Alto y clasificación 6 Bajo / 19 Medio / 7 Alto.
- **Hallazgo principal:** el modelo NLI actual confirma la *forma* de la frase sin mirar su
  *objeto*. Por eso cambiar la redacción no alcanza, y lo siguiente razonable es probar otro
  modelo NLI (sección 7).

## 2. Punto de partida

- El radar clasifica los 32 departamentos en Bajo / Medio / Alto a partir de prensa regional.
  Un modelo NLI (`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`) evalúa 26 frases
  («hipótesis») en cada artículo, y el valor de cada indicador en un lugar es el **máximo** de sus
  artículos (agregación MAX, requisito del proyecto).
- Con MAX, un solo artículo mal leído fija el indicador. Una auditoría de los Excel de Maicao,
  Oicatá y Paraguachón mostró máximos fijados por artículos de otro tema: por ejemplo, «hombre
  asesinado a tiros» como máximo de grupos armados (informe 01, §1).
- Frente al radar oficial del DANE, la versión MAX desplegada da accuracy 0.344, igual que
  responder siempre «Bajo», y Spearman −0.165. Fuente: fase 7, informe 01 §7.

## 3. Qué se hizo, en orden

| Fecha | Paso | Resultado | Informe |
|---|---|---|---|
| 2026-09-22 | Ronda 1, fases 0–5: 12 variantes por indicador (la vigente y 11 alternativas: frases, paráfrasis, combinaciones y reglas de palabras clave) en 4 lugares; 565 artículos juzgados | Solo pasa la regla de palabras clave de grupos armados (V08): precisión 0.17 → 0.93 | 01 |
| 2026-09-22 | Fase 7: comprobación en departamentos no usados para diseñar (Cauca, Chocó, Cundinamarca; 94 juzgados) y recalibración de cortes | V08 pasa: 0.47 → 0.77; corte bajo 0.766 → 0.7574; ninguna clase cambia | 01 |
| 2026-09-22 | Fase 8: V08 a producción, Excel de lugares antes/después | Promovida | 02 |
| 2026-09-23 | Regla nueva: de cada indicador solo se cambia la hipótesis | V08 es una regla de palabras clave: **se revierte**; cortes de nuevo 0.766 / 0.9233 | 03 |
| 2026-09-23 | Ronda 2: 25 frases (15 nuevas y 10 paráfrasis), cada una con su control absurdo; 281 artículos más juzgados (940 en total) | Ninguna pasa; exclusión no medible | 04 |
| 2026-09-23 | Revisión final independiente (agente `orquesta-lead`) | Aprobada, sin errores que cambien el resultado | 04 |

## 4. Cómo se midió (igual en las dos rondas)

- **Referencia:** dos jueces LLM (Claude Sonnet y Claude Opus) leen cada artículo sin saber qué
  sistema lo eligió. Es positivo solo si los dos dicen SÍ. Su acuerdo es alto en grupos armados,
  desplazamiento y conflicto (kappa 0.87–0.94), moderado en rechazo (0.44–0.46) y nulo en
  exclusión. El LLM solo evalúa, en local; nunca entra a producción.
- **Precisión:** de los 10 artículos con mayor puntaje en cada lugar, cuántos hablan de verdad
  del tema. Se exigía al menos 0.60, además de superar a la frase vigente.
- **Control absurdo:** la misma frase con «osos polares» en lugar del objeto. Por ejemplo, «Hay
  oposición de comunidades a un criadero de osos polares». Una frase útil debe quedar por debajo
  del corte del radar (0.766) con su versión absurda.

## 5. Estado final por indicador

| Indicador | Frase que se queda (vigente) | Vigente | Mejor intento solo con la frase | Por qué no cambió |
|---|---|---|---|---|
| Exclusión de beneficios | «Una comunidad quedó excluida de los beneficios económicos de un proyecto.» | 0.00 | 0.00 | 0 casos en 940 artículos, aun buscando a propósito los 237 que hablan de regalías o compensaciones: no medible con este corpus |
| Rechazo a proyecto | «Hay oposición de comunidades o autoridades a un proyecto.» | 0.00 | 0.25, que sale entera de un lugar sin casos (0.00 donde sí los hay) | Solo 4 casos reales; la vigente responde casi igual con osos polares (0.96–0.99) |
| Desplazamiento forzado | «Hubo un desplazamiento forzado o éxodo de comunidades.» | 0.05 | 0.07 | «Desplazadas por los osos polares» puntúa igual que «por la violencia» (0.99) |
| Conflicto territorial | «Hay una disputa por el control, el uso o la propiedad de un territorio.» | 0.07 | 0.26 | Lejos de 0.60 y falla el control absurdo |
| Presencia de grupos armados | «En este territorio hay presencia de grupos armados ilegales.» | 0.17 | 0.38 (0.93 con la regla de palabras clave, no permitida) | Lejos de 0.60 y su control absurdo sale peor que el de la vigente |

Todas las alternativas de las dos rondas quedaron registradas como rechazadas, con su evidencia,
para no volver a probarlas (`contexto/08_log_decisiones.md`).

## 6. Qué se aprendió

1. **El modelo confirma la forma, no el objeto.** Si la frase «suena» a desplazamiento o a
   oposición, el modelo dice que sí aunque el objeto sea absurdo. Por eso ninguna redacción, en
   dos rondas, pasó el control.
2. **Solo filtrar por palabras clave funcionó** (grupos armados, 0.17 → 0.93, confirmado fuera de
   los lugares de diseño). La regla vigente no lo permite.
3. **Hay fenómenos que la prensa casi no reporta.** Rechazo a proyecto tiene 4 casos en los 4
   lugares y exclusión de beneficios ninguno. Con tan pocos casos no se puede medir la mejora.
4. **Exclusión de beneficios suma casi una constante al radar:** su máximo va de 0.95 a 0.99 en
   los 32 departamentos (informe 01, §8).

## 7. Propuesta: probar otro modelo NLI (pendiente de decisión)

Dos rondas de reformulación descartan que el problema esté en la redacción. Lo que queda por
probar, sin cambiar la regla de «solo hipótesis», es el modelo que lee las frases.

**Candidato recomendado: `vicgalle/xlm-roberta-large-xnli-anli`.** Es un reemplazo directo:
- Tiene las **mismas 3 salidas** que el modelo actual (implicación, neutral y contradicción),
  así que la fórmula del puntaje, la calibración del sesgo, la agregación MAX y las 26 frases
  quedan idénticas. Solo cambia el nombre del modelo.
- Es multilingüe y lee 512 tokens, igual que el actual. Es el **doble de profundo**: 24 capas
  frente a 12 (configuración publicada del modelo).
- Se entrenó con MNLI, XNLI y ANLI (ficha del modelo; licencia MIT). ANLI es un conjunto hecho
  para romper los atajos que usan estos modelos, como el que se observó aquí.

**Descartados como reemplazo directo:**
- `MoritzLaurer/bge-m3-zeroshot-v2.0`: es más moderno y lee artículos enteros, pero tiene solo 2
  salidas (no tiene «neutral»). Habría que cambiar la fórmula del puntaje, y eso lo prohíbe la
  regla vigente.
- `joeddav/xlm-roberta-large-xnli`: mismo tamaño, pero sin entrenamiento adversarial.
- Un LLM en producción: los jueces muestran que un LLM sí distingue el objeto, pero el proyecto
  fija que producción use solo NLI.

**Riesgo honesto:** no está medido que un modelo más grande corrija el defecto. Por eso se
propone probarlo por etapas, parando en cuanto falle:
1. **Filtro barato, sin jueces** (~1–1.5 h de GPU, estimado): en los 4 lugares, las 5 frases
   vigentes con sus controles absurdos. Solo cambia el modelo. **Se para** si el control absurdo
   no baja de 0.766 en ninguno de los indicadores donde hoy lo supera.
2. **Juicio** de los artículos nuevos que el modelo ponga arriba, reutilizando las 940 etiquetas,
   y los mismos criterios de las rondas 1 y 2 (el modelo nuevo frente al actual, con la misma
   frase).
3. **Si mejora al menos un indicador:** puntuar los 26 a escala nacional (~13 h de GPU,
   estimado), comprobar en Cauca, Chocó y Cundinamarca, revisar que los otros 21 no empeoren y
   recalibrar los cortes una sola vez. El cambio de modelo afecta a todo el radar, así que se
   adopta completo o no se adopta.

Antes de medir se escribiría un pre-registro con estos criterios.

## 8. Pendientes (decisión del responsable)

1. Aprobar o no la prueba del modelo (sección 7).
2. Qué hacer con exclusión de beneficios económicos, que resultó no medible. Mientras tanto
   sigue en el radar con su frase vigente.
3. Fusión de la rama a `radar-max_Septiembre` y push.

## 9. Limitaciones

- La referencia es de jueces LLM, no humana. El acuerdo alto la hace creíble, no infalible.
- Solo 4 lugares de diseño, dos pequeños (Oicatá 32 y Paraguachón 77 artículos). El modelo y el
  juez ven solo el comienzo del artículo en el 77 % de los casos.
- Con 32 departamentos, diferencias de accuracy menores a ~15 puntos no se distinguen del ruido.
- Los tiempos de GPU de la sección 7 son estimaciones a partir del tamaño del modelo (no
  medidos).

## Anexo — Trazabilidad

| Elemento | Dónde |
|---|---|
| Informes con el detalle | `informes/01` a `informes/04` |
| Pre-registros | `experimentos/PREREG_5ind_MAX.md` (ronda 1), `experimentos/PREREG_5ind_MAX_r2.md` (ronda 2) |
| Tablas | `experimentos/RESULTADOS_5ind_MAX.md`, `experimentos/RESULTADOS_5ind_MAX_r2.md` |
| Decisiones y rechazos | `contexto/08_log_decisiones.md`, entradas [2026-09-22] y [2026-09-23] |
| Configuración de los modelos candidatos | `config.json` de cada modelo en Hugging Face (consultado el 2026-09-23) |
