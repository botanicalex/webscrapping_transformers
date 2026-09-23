# Estado del proyecto — Radar de riesgo territorial (Colombia)

*Última actualización: 2026-08-31 (rama `radar-max_Septiembre`, derivada de `pruebas` a
pedido del jefe: agregación **MAX** en vez de P75, ver "En qué estado está" abajo). Este
documento está escrito para alguien que no ha seguido el proyecto día a día — un lector
externo. Para trabajar en el código, ver `CLAUDE.md` y `contexto/`.*

## Qué es

Un radar que clasifica los 32 departamentos de Colombia en riesgo **Bajo / Medio / Alto**
a partir de prensa regional. Un valor **Alto** no significa "mucho pasa ahí": significa
**zona difícil o inviable para implementar un proyecto** — conflicto activo, presencia de
grupos armados, ausencia de Estado.

El objetivo final no es el nivel departamental: es poder aplicar el mismo radar a
**veredas, municipios y ventanas de tiempo donde no existe estadística oficial**. Los 32
departamentos son el único terreno donde hay con qué comparar, así que sirven para
validar el método antes de bajarlo a una escala donde no hay forma de verificarlo.

## Cómo funciona, de punta a punta

1. **Scraping** de periódicos regionales por departamento (o por municipio/vereda).
2. Cada artículo se evalúa contra **26 hipótesis** ("hay desplazamiento forzado en este
   territorio", "hay presencia de grupos armados", etc.) con un modelo de lenguaje
   (NLI — inferencia de lenguaje natural) que da una probabilidad de que el texto respalde
   cada hipótesis.
3. Los 26 puntajes por artículo se agregan por departamento y se combinan en un único
   **radar propio**.
4. El radar propio se clasifica en Bajo/Medio/Alto y se compara contra un radar de
   referencia publicado por el DANE, para medir qué tan bien coincide.

## Qué funciona hoy

- El pipeline corre de punta a punta: scraping → 26 indicadores → radar → clasificación.
- Corpus de **11.439 artículos** en los 32 departamentos, más un corpus de trabajo de
  1.647 artículos en 4 lugares sub-departamentales (para iterar rápido: Antioquia,
  Maicao, Oicatá, Paraguachón).
- Una revisión de seis experimentos encontró y corrigió tres defectos de medición
  distintos en cómo se calculan los indicadores (ver más abajo; **aplicados a producción
  desde el 2026-08-31**).

## En qué estado está, honestamente

**Esta rama (`radar-max_Septiembre`) usa agregación MAX en vez de P75, a pedido explícito
del jefe.** El resto de la receta V2 no cambia (hipótesis reescritas, sesgo descontado,
sin pre-filtro social). Es una decisión de negocio, no técnica: la evidencia medida en el
historial del proyecto (`contexto/08_log_decisiones.md`, `contexto/04_hallazgos_revision_nli.md`)
favorecía P75 sobre MAX (razón señal/artefacto 49.0 contra 0.91), porque el MAX favorece a
los departamentos con más artículos en el corpus, con independencia del riesgo real.

Recalibrando los cortes Bajo/Medio/Alto sobre la escala MAX (huecos naturales de la
distribución, sin mirar el oficial, sin romper las anclas de validez aparente), la accuracy
contra el DANE sobre los 32 departamentos da **34.4%** y la correlación de Spearman contra
el valor oficial continuo da **−0.1653** (negativa, calculado offline desde
`datos/scores/scores_v2_32deptos.pkl`, sin volver a tocar la GPU). Líneas base para
contexto:

| Método | Accuracy |
|---|---|
| Azar (3 clases) | 33.3% |
| Predecir siempre "Bajo" sin leer nada | 34.4% |
| Predecir solo por el número de artículos del corpus | 28.1% |
| **Radar MAX de esta rama (cortes fijos recalibrados)** | **34.4%** |
| Radar P75 en producción (`pruebas`/`master`) | 25.0% |
| Objetivo del proyecto | 70.0% |

Con solo 32 departamentos ninguna de esas diferencias es concluyente (error estándar ~8
puntos porcentuales). El Spearman negativo de esta rama es consistente con lo ya medido en
el historial: la variante V0+MAX (antes de las otras dos correcciones) también daba
Spearman negativo (−0.18, ver `contexto/09_riesgos_y_limites.md`). La versión que sí
mostró señal positiva (+0.42) usa P75, no MAX — ver `contexto/08_log_decisiones.md`
[2026-08-31] para la comparación completa.

Esto **no** significa que el radar no lleve ninguna señal: por criterio de conflicto
armado, su ranking es razonable (Caquetá, Putumayo, Nariño, Arauca y Norte de Santander
arriba; Cundinamarca, Quindío y Boyacá abajo). El problema es que **el índice del DANE
contra el que se compara no parece medir conflicto** — parece medir vulnerabilidad
socioeconómica y ausencia de Estado (Vichada, Guainía y el Amazonas arriba; Antioquia y
el Valle abajo), que es un fenómeno relacionado pero distinto. Son dos formas distintas
de "difícil para un proyecto" que no siempre coinciden.

**Con solo 32 departamentos, diferencias de accuracy menores a ~15 puntos porcentuales no
se distinguen del ruido estadístico.** El diagnóstico de fondo no se resuelve ajustando
indicadores: es una decisión sobre qué debe medir el radar (ver "qué falta" abajo).

## Qué se encontró

La revisión de indicadores identificó tres defectos de medición, cada uno medido y
corregido:

1. **El formato de las hipótesis inflaba los puntajes.** Preguntas del tipo "este
   artículo reporta que X" hacían que un artículo sobre pingüinos emperador "implicara"
   casi cualquier hipótesis el 78% de las veces. Se reescribieron las 26 preguntas para
   describir el territorio directamente, no el documento.
2. **Sesgo de "casi todo se afirma un poco".** Por artículo, el 6.5% del puntaje se puede
   afirmar sin evidencia real; hay que descontarlo antes de interpretar un puntaje como
   señal.
3. **El puntaje máximo por departamento reflejaba el tamaño del corpus, no el riesgo.**
   Un departamento con más artículos tendía a sacar puntajes más altos solo por tener más
   oportunidades de que algo puntuara alto, no porque el riesgo fuera mayor. Cambiar la
   forma de agregar (de "el máximo" a "el percentil 75") corrige la mayor parte de este
   efecto. **Esta rama (`radar-max_Septiembre`) vuelve al máximo a pedido del jefe**, con
   esa limitación conocida y sin corregirla — ver "En qué estado está" arriba.

Las tres correcciones **están en producción desde el 2026-08-31 en `pruebas`/`master`** y
fueron validadas a escala nacional sobre los 32 departamentos con el motor de experimentos
(Spearman +0.42, con P75). Producción aún no se ha re-corrido sobre los 32 con su propio
código (~4 h GPU, pendiente). Esta rama reemplaza únicamente la agregación por MAX; las
otras dos correcciones (hipótesis V2, sesgo descontado) se mantienen.

## Qué falta y qué lo bloquea

1. **Re-correr el scoring con el código de producción ya promovido sobre los 32
   departamentos** (~4 horas de GPU, reanudable). Antes hay que decidir qué corpus debe
   cargar producción (hoy levanta 12.592 artículos y 35 lugares, no 11.439/32) y si se
   fusiona el corpus re-scrapeado de 3 departamentos. El scoring ya hecho con el motor de
   experimentos sí muestra mejora real frente al DANE (Spearman +0.42).
2. **Decidir qué hacer con el desajuste de fondo.** El radar mide conflicto; el índice
   oficial parece medir otra cosa. Hay tres caminos —cambiar contra qué se compara,
   cambiar los indicadores para que cubran también esa otra dimensión, o dejar de medir
   accuracy contra el DANE y presentar el radar como instrumento propio— y ninguno es una
   decisión técnica: es una decisión sobre qué se quiere que el radar mida.
3. **Ampliar el estándar de validación interno.** Hoy solo 2 de los 26 indicadores tienen
   con qué verificarse automáticamente; el resto se evalúa por inspección. Es la mayor
   debilidad de cara a defender los resultados.
4. **Reforzar la cobertura de prensa en los departamentos que más importan.** De los 11
   departamentos que el DANE marca como Alto riesgo, 5 tenían menos de 100 artículos
   (Guainía, La Guajira, Vaupés, Sucre, Vichada). La Guajira ya tiene 1.553 artículos
   re-scrapeados esperando la decisión de fusión; San Andrés depende 100% de El Tiempo
   (caída intermitente externa).

## Qué se necesita de terceros

**Identificar exactamente cuál es el índice del DANE usado como referencia.** Hoy se sabe
que la cifra de comparación viene del DANE y se copió de una página web cuya dirección no
quedó guardada; no se sabe cuál de los indicadores oficiales del DANE es. Es la tarea más
barata y de mayor impacto pendiente: decide cuál de los caminos del punto 2 corresponde,
y sin ella cualquier ajuste a los indicadores se hace a ciegas sobre qué se está tratando
de predecir.
