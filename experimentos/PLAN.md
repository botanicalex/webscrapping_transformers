# Plan de experimentos — formato de hipótesis NLI

Estado: **Plan completado (2026-08-31) — instantánea histórica.** Los experimentos 1–6
se corrieron y la receta V2 se promovió a producción. Para el estado actual, ver
`contexto/10_combinaciones_y_rumbo.md` y `contexto/08_log_decisiones.md`.

---

## Diagnóstico (cerrado)

**El marco metalingüístico `"Este artículo menciona/reporta que X"` infla los
scores con independencia del contenido.**

Prueba directa — control absurdo (pingüinos emperador) sobre 1.647 artículos:

| Formato | media | prop>0.9 |
|---|---|---|
| V0 producción | 0.9098 | 78.45% |
| V1 sin metalenguaje | 0.4660 | 20.46% |
| V2 corta | 0.4337 | 14.88% |
| V4 sin disyunción (conserva metalenguaje) | 0.9231 | 83.24% |

El modelo evalúa si el texto *es un artículo que menciona algo* — trivialmente
cierto para cualquier noticia — en vez de evaluar la subordinada.

Descartado, con evidencia:
- **Inversión de etiquetas**: `id2label = {0: entailment, 1: neutral, 2: contradiction}`.
  El fallback nunca se ejecuta y coincidiría con el orden real.
- **La disyunción múltiple como causa principal**: V4 la elimina y empeora.
- **`"explícitamente"` como causa**: +0.03 de AUC, inerte.

## Lección metodológica

El AUC por sí solo habría elegido V4 (AUC 0.8355, la más alta), que es la peor
hipótesis del conjunto. **Toda variante candidata debe pasar el control absurdo
antes de considerarse.** AUC mide orden; el control absurdo mide si el "sí"
significa algo.

---

## Experimento 2 — eje de premisa (siguiente)

**Motivo:** aun sin metalenguaje queda inflación residual (V1 dice "sí" a los
pingüinos en el 20% de los casos). La hipótesis es que viene de la premisa:
producción usa `df["texto"]` truncado a ~470 tokens y **excluye el titular**,
mientras XNLI se entrenó con premisas de una sola frase.

**Diseño:** 4 premisas (`PREMISAS` en `nli_core.py`) × 2 hipótesis (V0, V1)
× 2 indicadores, más el control absurdo en cada premisa.

- `cuerpo` (producción)
- `titular`
- `titular_lede`
- `primeras_frases`

**Métricas:** AUC + separación + control absurdo. Una premisa solo es mejor si
sube AUC **y** baja el control absurdo.

**Costo:** ~20 min. Las premisas cortas corren mucho más rápido que `cuerpo`.

**Predicción:** `titular` y `titular_lede` suben AUC y bajan el control absurdo
de forma sustancial.

---

## Experimento 3 — combinación y verificación

Mejor formato × mejor premisa, con el control absurdo como criterio de aceptación.
Criterio de éxito propuesto: **AUC ≥ 0.85 y control absurdo con media ≤ 0.10.**

---

## Experimento 4 — extensión a las 26 + pre-filtro

Reescribir las 26 siguiendo el patrón ganador (sin marco metalingüístico,
declarativa, describiendo el territorio y no el documento). Ejemplos:

```
antes : "Este artículo menciona explícitamente la presencia... de grupos armados ilegales en un territorio."
después: "En este territorio hay presencia de grupos armados ilegales."
```

**El pre-filtro social necesita la misma corrección** — tiene la enfermedad en
forma extrema (metalingüístico + 8 disyuntos) y ya medimos su daño:

| Indicador | Positivos de plata anulados por `score_social < 0.65` |
|---|---|
| `grupos_etnicos_existentes` | 40/119 (33.6%) |
| `presencia_grupos_armados` | 25/141 (17.7%) |

Coste en AUC del enmascarado: −0.074 (étnicos) y −0.024 (armados).

Incluir también las 4 hipótesis escritas sin tildes (`SIN_TILDES`), que son una
variante gratis por probar.

---

## Experimento 5 — validación en producción

Correr el pipeline completo con las 26 reescritas sobre los mismos 1.647
artículos y comparar contra `datos/df_procesado_baseline.pkl`.

**Qué mirar:** si la media de los negativos baja de ~0.97 a ~0.5, el MAX vuelve
a discriminar y los departamentos dejan de salir todos "Alto". Ésta es la
conexión entre los dos problemas que veníamos tratando por separado: con
negativos en 0.969, el MAX da ~0.999 por construcción.

---

## Pendiente — anotación manual

El estándar de plata solo cubre 2 de los 26 indicadores. Para los que no tienen
marcadores léxicos (`deficit_participacion_comunitaria`, `debilidad_institucional`,
`poblacion_afectada`...) hace falta anotar ~120–150 artículos a mano. No bloquea
los experimentos 2–5, pero sí hace falta antes de defender los resultados.

---

## Limitaciones a declarar

- El estándar de plata es keyword-based: alta precisión, recall imperfecto.
  Sirve para comparar variantes **entre sí**, no como verdad absoluta.
- Los negativos ("0 keywords") pueden contener falsos negativos — un artículo
  sobre "hombres armados" sin nombrar el grupo. El sesgo es igual para todas las
  variantes, así que no invalida la comparación.
- Corpus dominado por Maicao (1.101 de 1.647). Los AUC son globales, no por lugar.
