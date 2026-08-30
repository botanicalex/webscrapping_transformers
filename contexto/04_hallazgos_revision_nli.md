# 04 — Hallazgos de la revisión NLI (agosto 2026)

Documento técnico central. **Leer antes de tocar hipótesis, calibración o agregación.**

Seis experimentos sobre 1.647 artículos. Resultados en `experimentos/resultados/*.xlsx`,
scripts en `experimentos/exp_*.py`.

---

## La prueba que resume todo

MAX por lugar de un indicador real frente al de una hipótesis absurda ("hay colonias de osos
polares en este territorio"):

| Corrección | MAX indicador | MAX nula | brecha |
|---|---|---|---|
| **V0 producción** | 0.9989 | 0.9985 | **+0.0004** |
| V2 + calibración | 0.8862 | 0.3469 | +0.5393 |

**El radar de producción es indistinguible de uno construido con disparates.** En
Oicatá/étnicos la nula puntúa *más alto* que el indicador real. El radar de los 32
departamentos habría salido prácticamente igual reemplazando las 26 hipótesis por absurdos.

---

## Defecto 1 — El marco metalingüístico infla los scores

Control absurdo: misma estructura de las hipótesis reales, contenido imposible
(pingüinos emperador).

| Formato | media | prop>0.9 |
|---|---|---|
| V0 producción | 0.9098 | **78.45%** |
| Sin metalenguaje | 0.4660 | 20.46% |
| Corta | 0.4337 | 14.88% |
| Sin disyunción (conserva metalenguaje) | 0.9231 | 83.24% |

El 78% de las noticias colombianas "implica" que menciona pingüinos emperador. El modelo
evalúa si el texto *es un artículo que menciona algo* —trivialmente cierto para cualquier
noticia— en vez de evaluar la subordinada.

**La causa es el marco, no la disyunción ni `"explícitamente"`.** Quitar la disyunción
sola **empeora** (83.24%).

AUC contra el estándar de plata:

| Indicador | V0 | Sin metalenguaje |
|---|---|---|
| `presencia_grupos_armados` | 0.7430 | **0.8261** |
| `grupos_etnicos_existentes` | 0.6303 | **0.8212** |

Étnicos sale de la zona de "casi una moneda al aire".

## Defecto 2 — Sesgo "sí-decidor" por artículo

Estimado con 4 hipótesis nulas de dominios variados; evaluado con una quinta **reservada**.

```
sesgo por artículo: media 0.3638 · mediana 0.3113 · p90 0.7610 · max 0.9990
artículos con sesgo > 0.9: 6.5%
```

El 6.5% de los artículos afirma con casi total confianza cualquier cosa que se le proponga.

Correcciones probadas (`presencia_grupos_armados`):

| Corrección | AUC | separación | media neg | ctrl>0.9 |
|---|---|---|---|---|
| raw (sin metalenguaje) | **0.8261** | +0.364 | 0.555 | 8.6% |
| resta_sesgo | 0.7830 | +0.410 | 0.187 | **0.0%** |
| `P(ent) − P(neu)` | 0.8257 | **+0.721** | 0.120 | 6.7% |
| **combinada** | 0.7880 | +0.344 | 0.251 | **0.0%** |

`P(ent) − P(neu)` conserva el AUC y duplica la separación, **pero no arregla la cola**, que
es lo único que ve una agregación de extremos. La combinada sacrifica ~0.04 de AUC y sí la
arregla. **La corrección óptima depende de la agregación.**

Fórmula en uso: `clip(clip(ent − sesgo, 0) * (1 − neu), 0, 1)`

### Resultado negativo: normalizar `ent/(ent+con)` NO funciona

Descartar la masa de *neutral* empeora mucho el control absurdo (0.466 → 0.830 de media;
prop>0.9 de 20% a 60%) y colapsa la separación (+0.364 → +0.042).

**La masa de neutral es la que carga la señal de "este texto no habla de eso".** Ante una
hipótesis que el texto no aborda, el modelo pone masa en neutral, que es lo correcto.
Eliminarla convierte ese "no aplica" en un "sí" parcial. Es información, no ruido.

## Defecto 3 — El MAX está dominado por el tamaño del corpus

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

**Bajo MAX el artefacto por tamaño de corpus es mayor que la diferencia real entre
lugares.** Cualquier agregación top-k premia tener más artículos: TOP3 y TOP5 comparten el
defecto. Los cuantiles y proporciones no, porque son posicionales.

Esto explica por qué la comparación MAX vs TOP3 de junio dio prácticamente idéntica
(0.9991 vs 0.9988): bajo V0 todo estaba saturado y ninguna agregación podía distinguir nada.

**Elegido: P75** (ver `08_log_decisiones.md` para el porqué y su costo).

## Eje de premisa: sin ganador

| Indicador | mejor premisa | AUC |
|---|---|---|
| `presencia_grupos_armados` | titular_lede | 0.8358 (cuerpo 0.8261) |
| `grupos_etnicos_existentes` | **cuerpo** | 0.8212 (titular_lede 0.7157) |

Se contradicen, y la razón es sustantiva: depende de si el indicador es sobre el *tema* del
artículo o sobre *menciones incidentales*. La presencia de grupos armados suele ser el
titular; una comunidad wayúu puede aparecer de pasada en el párrafo doce. **Se mantiene
`cuerpo`.**

Premisas cortas reducen la inflación (titular: control 0.346, prop>0.9 solo 2.4%) pero a
costa de demasiado AUC.

## Resultado combinado

| Lugar | n art. | V0 (MAX) | V2 + P75 | nula |
|---|---|---|---|---|
| Antioquia (2023) | 494 | 0.9991 Alto | 0.3233 | **0.0000** |
| Municipio Maicao | 1.101 | 0.9989 Alto | 0.2807 | **0.0000** |
| Municipio Oicatá | 32 | 0.9923 Alto | 0.1226 | **0.0000** |
| Vereda Paraguachón | 20 | 0.9806 Alto | 0.2561 | **0.0000** |

Los cuatro se separan y el radar de la nula es exactamente 0. Oicatá queda claramente por
debajo, lo que es sustantivamente correcto: es Boyacá.

---

## Lección metodológica

**En tres ocasiones distintas el AUC apuntó a la opción equivocada y solo el control absurdo
la delató:**

1. La variante "sin disyunción" tenía el AUC más alto de todas (0.8355) y afirma que hay
   pingüinos en el 83% de las noticias.
2. La normalización `ent/(ent+con)` era neutra en AUC y triplica la inflación.
3. `P(ent) − P(neu)` ganaba en AUC y separación, y es mediocre sobre el MAX real.

**Ninguna variante se adopta sin pasar el control absurdo.** El AUC mide orden; el control
absurdo mide si el "sí" significa algo. El control autoriza a *rechazar*, nunca a *adoptar*:
es necesario, no suficiente.

## Descartado con evidencia

**Las etiquetas NLI no están invertidas.** `id2label = {0: entailment, 1: neutral,
2: contradiction}`: el bucle de `_resolver_labels` las resuelve por texto, el fallback
`0,1,2` nunca se ejecuta, y aun si se ejecutara coincidiría con el orden real del modelo.
No volver a proponer revisarlo.

## Limitaciones declaradas

- **Las variantes se eligieron sobre el mismo conjunto con el que se evaluó.** Se probaron 6
  variantes por indicador y se escogió por AUC sobre los mismos 141 y 119 positivos de
  plata, sin conjunto reservado. Con esas muestras, diferencias de AUC de 0.03–0.08 pueden
  no sobrevivir a validación independiente.
  *Aguantan* las conclusiones grandes —el marco metalingüístico (78% vs 20% en el control
  absurdo, criterio independiente del AUC) y el problema del MAX (razón 0.91 vs 49.0)—;
  *no necesariamente* las comparaciones finas entre variantes cercanas.
  **Para futuras comparaciones:** reservar un tercio de los positivos como validación,
  elegir en los dos tercios restantes y reportar sobre el reservado.
- El estándar de plata es por palabras clave: alta precisión, recall imperfecto. Sirve para
  comparar variantes **entre sí**, no como verdad absoluta. Cubre 2 de 26 indicadores.
- Los negativos ("0 keywords") contienen falsos negativos —un artículo de "hombres armados"
  sin nombrar el grupo—. El sesgo es igual para todas las variantes, así que no invalida la
  comparación, pero sí el nivel absoluto.
- El nivel absoluto del control absurdo depende del absurdo elegido (pingüinos 20.5%, osos
  polares 8.6% en la misma configuración). Solo comparar mediciones con la misma nula.
- Corpus dominado por Maicao (1.101 de 1.647). Los AUC son globales, no por lugar.
- Paraguachón (20 artículos) y Oicatá (32) son bases muy pequeñas.
