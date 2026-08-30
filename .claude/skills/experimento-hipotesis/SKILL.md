---
name: experimento-hipotesis
description: Ciclo cerrado para probar variantes de redacción de una hipótesis NLI de un indicador. Define variantes que difieran en una sola cosa, las puntúa con nli_core, mide AUC contra el estándar de plata, corre el control absurdo con una nula del mismo formato y decide con el criterio conjunto — el AUC por sí solo nunca decide. Úsala cuando haya que reescribir, reformular, comparar, validar o descartar la formulación de cualquiera de las 26 hipótesis o del pre-filtro social; cuando un indicador no discrimine, dé scores saturados o parezca medir cualquier cosa; o cuando se pregunte si una redacción es mejor que otra. No es para la agregación por lugar (MAX/P75), ni para los cortes Bajo/Medio/Alto, ni para scraping.
---

# Experimento de hipótesis NLI

Ciclo: variantes → scoring → AUC → control absurdo → decisión → registro.
Todo se ejecuta **desde `experimentos/`**.

## Cuándo NO es este skill

- Se cambia la **agregación** por lugar o los **cortes** Bajo/Medio/Alto. Son decisiones
  separadas y mezclarlas es lo que ha venido confundiendo el análisis.
- No hay corpus puntuable, o `verificar_contra_produccion()` no da OK → arreglar eso primero.
- Se quiere cambiar de modelo NLI → no es una variante de hipótesis; leer
  `contexto/08_log_decisiones.md`.

## Paso 0 — Verificación bloqueante

```python
from nli_core import NLIScorer, verificar_contra_produccion
import hipotesis_base as HB

s = NLIScorer()   # imprime id2label; confirma el mapeo de etiquetas
assert verificar_contra_produccion(
    s, "../datos/scores/df_procesado_baseline.pkl",
    "presencia_grupos_armados", HB.TODAS["presencia_grupos_armados"])
```

Si no da `max|dif| = 0.00e+00`, **parar**: `nli_core` se desvió de producción y ninguna
medición sería comparable.

## Paso 1 — Declarar la pregunta antes de correr

En el docstring de `exp_<tema>.py`, y **antes de ver ningún número**:

- La pregunta, en una frase.
- El **par mínimo**: dos hipótesis que difieran en UNA sola cosa.
- Qué resultado la confirmaría y cuál la refutaría, ambos numéricos.

Si no se puede escribir el criterio de fracaso, el experimento no está diseñado.

## Paso 2 — Definir las variantes

Reglas heredadas de lo ya medido (detalle en `contexto/04_hallazgos_revision_nli.md`):

- **Sin marco metalingüístico.** La hipótesis describe *el territorio o el hecho*, no el
  documento. `"Este artículo reporta que X"` → `"X"`.
- Frase corta y declarativa (XNLI se entrenó con hipótesis de ~10 tokens).
- Sin `"explícitamente"`, `"verificable"`, `"documentada"`: son instrucciones para un
  anotador humano, no proposiciones evaluables. Medido: +0.03 de AUC, inertes.
- Tildes correctas.
- La disyunción se conserva cuando es sustantiva: quitarla sola **empeora** el control.

Incluir siempre la variante `actual` como referencia. Sin ella no hay comparación.

## Paso 3 — La nula del mismo formato

**El control absurdo se reescribe en el formato exacto de cada variante**, conservando el
contenido imposible. Si la variante cambia el formato y la nula no, el control ya no aísla
nada.

- Contenido imposible por defecto: `V2.NULA_TEST` (osos polares). **Reservado: no entra en
  la calibración del sesgo.**
- Sesgo por artículo: media de las 4 de `V2.NULAS_CALIBRACION`, cada una reescrita también
  en el formato de la variante.
- Solo son comparables mediciones con el **mismo contenido absurdo** (pingüinos 20.5%, osos
  polares 8.6% en la misma configuración).

## Paso 4 — Puntuar una vez y guardar todo

```python
import numpy as np, pandas as pd
import hipotesis_v2 as V2

IND  = "presencia_grupos_armados"
df   = pd.read_pickle("../datos/corpus/df_corpus_5lugares.pkl")
prem = df["texto"].fillna("").astype(str).tolist()   # premisa de produccion

VARIANTES = {"actual": V2.TODAS[IND], "va": "...", "vb": "..."}
NULAS     = {"actual": V2.NULA_TEST, "va": "...", "vb": "..."}   # mismo formato que su variante
CALIB     = {"actual": V2.NULAS_CALIBRACION, "va": [...], "vb": [...]}

out = {}
for k, hip in VARIANTES.items():
    p = s.score(prem, hip, devolver_todo=True)
    out[f"ent_{k}"] = np.asarray(p["entailment"], dtype=float)
    out[f"neu_{k}"] = np.asarray(p["neutral"],    dtype=float)
    n = s.score(prem, NULAS[k], devolver_todo=True)
    out[f"ent_nula_{k}"] = np.asarray(n["entailment"], dtype=float)
    out[f"neu_nula_{k}"] = np.asarray(n["neutral"],    dtype=float)
    out[f"sesgo_{k}"] = np.mean([np.asarray(s.score(prem, h), dtype=float)
                                 for h in CALIB[k]], axis=0)
out["departamento"] = df["departamento"].astype(str).str.strip().values
pd.DataFrame(out).to_pickle(f"resultados/scores_{IND}_variantes.pkl")
```

Guardar `ent` y `neu` **sin enmascarar por el pre-filtro**: así el A/B del pre-filtro se
hace después sobre el pkl, sin repetir GPU. Los pasos 5–7 corren sobre ese pkl, sin tocar la
tarjeta.

## Paso 5 — AUC contra el estándar de plata

```python
import silver
y = silver.etiquetar(df, HB.KEYWORDS_SILVER[IND])["label"].values   # 1 / 0 / NaN
for k in VARIANTES:
    print(k, silver.evaluar(out[f"ent_{k}"], y))
```

El AUC se calcula sobre `ent` **crudo**, sin corrección y sin enmascarar: mide ordenamiento
puro. La zona ambigua (exactamente 1 keyword) se descarta a propósito.

**Si el indicador no tiene estándar de plata** (24 de 26 no lo tienen), elegir:

- **A.** Anotar a mano 60–80 artículos muestreados de forma estratificada por score (no solo
  los del tope). Es lo único sólido.
- **B.** Usar como proxy un indicador vecino que sí tenga plata, y declarar que la
  conclusión es por transferencia.
- **C.** Declarar la variante **no medible** — y entonces **no se adopta**.

El control absurdo autoriza a *rechazar*, nunca a *adoptar*: es necesario, no suficiente.

## Paso 6 — Control absurdo

Reportar en las dos escalas:

- **Cruda:** `media(ent_nula_k)` y `prop(ent_nula_k > 0.9)`.
- **Corregida:** con `score = clip(clip(ent − sesgo, 0) * (1 − neu), 0, 1)`, y la prueba
  decisiva: el radar P75 por lugar del indicador real frente al de la nula.

Referencia de lo que significa "malo": bajo V0 el MAX de un indicador real y el de una
hipótesis absurda diferían en **0.0004**.

## Paso 7 — Decidir

Puertas eliminatorias, en orden. Falla una, se acabó:

1. `prop(nula cruda > 0.9) ≤ 5%` y `media(nula corregida) ≤ 0.10`.
2. El control absurdo no empeora respecto de `actual`.
3. La brecha por lugar (radar real − radar nula, P75) no baja.

Solo si pasa las tres:

| Control absurdo | AUC | Decisión |
|---|---|---|
| mejora o igual | sube | **Adoptar** |
| mejora | baja ≤ 0.04 | **Adoptar** si la brecha real−nula sube. Precedente: se sacrificó ~0.04 de AUC para arreglar la cola, y fue correcto |
| mejora | baja > 0.04 | No adoptar sin una razón mecanicista explícita |
| **empeora** | **sube** | **Rechazar.** Es el modo de fallo que ya ocurrió tres veces |
| empeora | baja | Rechazar |
| igual | igual | No adoptar — el empate favorece al statu quo |

**El AUC solo nunca decide.** Habría elegido "sin disyunción" (AUC 0.8355, la más alta), que
afirma que hay pingüinos en el 83% de las noticias.

## Paso 8 — Recalibrar lo que dependa de la escala

Si la variante se adopta, **todo umbral aguas abajo queda inválido**: el del pre-filtro y
los cortes Bajo/Medio/Alto se calibraron para otra distribución. Recalibrarlos, o dejar
constancia explícita de que quedan pendientes. Ya se olvidó dos veces.

## Paso 9 — Registrar, también los rechazos

Añadir la entrada a `contexto/08_log_decisiones.md` con su formato. Registrar los rechazos
es la mitad del valor: evita que se reintenten.

## Trampas conocidas

- **El umbral del pre-filtro pertenece a la hipótesis para la que se calibró.** Medir sin
  enmascarar y decidir el umbral después, sobre el pkl.
- **Los negativos de plata contienen falsos negativos** (un artículo de "hombres armados"
  sin nombrar el grupo). No invalida la comparación entre variantes, sí el nivel absoluto.
- **El corpus de 5 lugares está dominado por Maicao** (1.101 de 1.647). Los AUC son globales,
  no por lugar.
- **No comparar nulas de contenido distinto.**
- **Reportar `prop>0.9`, no solo la media.** La media puede mejorar mientras la cola —lo
  único que ve una agregación de extremos— sigue rota. Le pasó a `P(ent) − P(neu)`.
