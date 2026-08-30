# Resultados — revisión de los indicadores NLI

Seis experimentos sobre 1.647 artículos (Antioquia 2023, Maicao, Oicatá, Paraguachón).
Todo reproducible: `nli_core` replica producción bit a bit (max|dif| = 0.00e+00).

---

## Resumen

Se encontraron **tres defectos independientes**, cada uno medido y corregido:

| # | Defecto | Evidencia | Corrección |
|---|---|---|---|
| 1 | El marco metalingüístico infla los scores | El 78% de las noticias "implica" que menciona pingüinos emperador | Reescribir las 26 sin *"Este artículo reporta que…"* |
| 2 | Sesgo "sí-decidor" por artículo | El 6.5% afirma casi cualquier hipótesis | Descontar la línea base con hipótesis nulas |
| 3 | El MAX está dominado por el tamaño del corpus | El artefacto por tamaño es **mayor** que la diferencia entre lugares | Usar un cuantil (P75/P90) |

**Descartado con evidencia:** la sospecha de inversión de etiquetas
entailment/contradiction. `id2label = {0: entailment, 1: neutral, 2: contradiction}`;
el fallback nunca se ejecuta y coincidiría con el orden real.

---

## 1. El formato metalingüístico

Control absurdo — misma estructura de las hipótesis reales, contenido imposible:

| Formato | media | prop>0.9 |
|---|---|---|
| V0 producción | 0.9098 | **78.45%** |
| Sin metalenguaje | 0.4660 | 20.46% |
| Corta | 0.4337 | 14.88% |
| Sin disyunción (conserva metalenguaje) | 0.9231 | 83.24% |

El modelo evalúa si el texto *es un artículo que menciona algo* — trivialmente
cierto para cualquier noticia. La disyunción múltiple y `"explícitamente"` no
son la causa (quitar la disyunción sola **empeora**).

AUC contra el estándar de plata:

| Indicador | V0 | Sin metalenguaje |
|---|---|---|
| `presencia_grupos_armados` | 0.7430 | 0.8261 |
| `grupos_etnicos_existentes` | 0.6303 | 0.8212 |

## 2. Sesgo por artículo

Estimado con 4 hipótesis nulas de dominios variados; evaluado con una quinta
**reservada**. Media 0.3638, y el **6.5% de los artículos supera 0.9** contra
cualquier disparate.

Correcciones probadas: `P(ent)−P(neu)` conserva el AUC y duplica la separación
(+0.364 → +0.721), pero **no arregla la cola**, que es lo único que ve el MAX.
La combinada `clip(P(ent)−sesgo, 0) × (1−P(neu))` sacrifica ~0.04 de AUC y sí
la arregla.

## 3. La agregación

**Prueba decisiva** — MAX por lugar de un indicador real vs. de la nula reservada:

| Corrección | MAX indicador | MAX nula | brecha |
|---|---|---|---|
| **V0 producción** | 0.9989 | 0.9985 | **+0.0004** |
| combinada | 0.8862 | 0.3469 | +0.5393 |

Con el método actual, el radar es indistinguible de uno construido con
disparates. En Oicatá/étnicos la nula puntúa **más alto** que el indicador real.

### Señal entre lugares vs. artefacto por tamaño de corpus

Submuestreando Maicao a n = 20…1000 y midiendo cuánto se mueve el radar de la nula:

| Agregación | señal entre lugares | artefacto por tamaño | razón |
|---|---|---|---|
| PROP>0.5 | 0.1004 | 0.0012 | 83.7 |
| **P75** | **0.2007** | **0.0041** | **49.0** |
| MEDIA | 0.1057 | 0.0028 | 38.1 |
| P90 | 0.1879 | 0.0159 | 11.8 |
| TOP5 | 0.4838 | 0.3927 | 1.2 |
| TOP3 | 0.4270 | 0.3713 | 1.1 |
| **MAX** | 0.3156 | 0.3455 | **0.91** |

**Bajo MAX el artefacto por tamaño de corpus es mayor que la diferencia real
entre lugares.** TOP3 y TOP5 comparten el defecto: cualquier agregación
top-k premia tener más artículos. Los cuantiles y proporciones no.

Esto explica por qué la comparación MAX vs TOP3 de hace semanas dio idéntico
(0.9991 vs 0.9988): bajo V0 todo estaba saturado y ninguna agregación podía
distinguir nada.

---

## Resultado combinado

Radar por lugar aplicando las tres correcciones:

| Lugar | n art. | V0 (MAX) | V2 + P75 | nula V2+P75 |
|---|---|---|---|---|
| Antioquia (2023) | 494 | 0.9991 Alto | 0.3233 | 0.0000 |
| Municipio Maicao | 1.101 | 0.9989 Alto | 0.2807 | 0.0000 |
| Municipio Oicatá | 32 | 0.9923 Alto | 0.1226 | 0.0000 |
| Vereda Paraguachón | 20 | 0.9806 Alto | 0.2561 | 0.0000 |

Los cuatro lugares se separan y **el radar de la nula es exactamente 0**.
Oicatá queda claramente por debajo, lo que es sustantivamente correcto: Boyacá
es de los departamentos menos afectados por el conflicto.

---

## Pendientes

1. **Recalibrar los umbrales Bajo/Medio/Alto.** Los cortes 1/3–2/3 estaban
   pensados para una escala saturada; con P75 todo cae en "Bajo". Los umbrales
   no son transferibles entre agregaciones y hay que fijarlos de nuevo.
2. **Decidir si el pre-filtro sigue haciendo falta.** Con la escala corregida
   los artículos irrelevantes ya puntúan ~0 por sí solos. El pre-filtro V0
   anulaba el 33.6% de los positivos de plata; el V2 a 0.85 retiene el 92–95%
   pero solo filtra el 12%. Puede que su función ya esté cubierta.
3. **Ampliar el estándar de plata.** Solo cubre 2 de los 26 indicadores. Para
   los que no tienen marcadores léxicos hacen falta ~120–150 artículos anotados
   a mano.
4. **Validar sobre los 32 departamentos**, no solo estos 4 lugares.

## Limitaciones

- El estándar de plata es por palabras clave: alta precisión, recall imperfecto.
  Sirve para comparar variantes entre sí, no como verdad absoluta.
- El nivel absoluto del control absurdo depende del absurdo elegido (pingüinos
  20.5%, osos polares 8.6% en la misma configuración). Solo son comparables
  mediciones con la misma nula.
- Corpus dominado por Maicao (1.101 de 1.647).
- Paraguachón tiene 20 artículos y Oicatá 32: sus radares son frágiles.

## Lección metodológica

En tres ocasiones distintas la métrica agregada apuntó a la opción equivocada:

- El AUC habría elegido la variante "sin disyunción" (AUC 0.8355, la más alta),
  que afirma que hay pingüinos en el 83% de las noticias.
- El AUC daba por buena la normalización `ent/(ent+con)`, que triplica la
  inflación del control absurdo.
- El AUC y la separación elegían `P(ent)−P(neu)`, mediocre sobre el MAX real.

**Ninguna variante debería adoptarse sin pasar el control absurdo.** El AUC mide
orden; el control absurdo mide si el "sí" significa algo.
