# experimentos_claude

Workspace aislado para los experimentos de **formato de hipótesis NLI**.

No toca el pipeline de producción. Contiene solo lo necesario para responder una
pregunta: **¿el modelo ordena bien los artículos?** (medida con AUC, no con
`prop_0.9` ni con el MAX).

La agregación (MAX / TOP3 / umbrales) queda deliberadamente **fuera** de estos
experimentos. Mezclar ambas preguntas es lo que ha venido confundiendo el análisis.

## Contenido

| Archivo | Rol |
|---|---|
| `nli_core.py` | Motor NLI mínimo. Replica el scoring de producción sin importar `scrappers`. Permite variar `max_length` y devolver las 3 probabilidades. |
| `hipotesis_base.py` | Las 26 hipótesis actuales (V0), el pre-filtro social, el estándar de plata por keywords y el control absurdo. |
| `datos/df_corpus_5lugares.pkl` | 1.647 artículos (Antioquia 2023, Maicao, Oicatá, Paraguachón) con `titulo` **y** `texto`. |
| `datos/df_procesado_baseline.pkl` | Resultados de producción del 2026-08-25, para validar que `nli_core` reproduce los mismos scores. |
| `resultados/` | Salidas de los experimentos. |

## Antes de correr cualquier experimento

`nli_core.verificar_contra_produccion()` debe dar `OK`. Si no, este módulo se
desvió de producción y las comparaciones no serían válidas.

```python
from nli_core import NLIScorer, verificar_contra_produccion
from hipotesis_base import TODAS
s = NLIScorer()
verificar_contra_produccion(s, "../datos/scores/df_procesado_baseline.pkl",
                            "presencia_grupos_armados",
                            TODAS["presencia_grupos_armados"])
```

Ese mismo `NLIScorer()` imprime al cargar el `id2label` del modelo, lo que cierra
de paso la duda sobre el mapeo de etiquetas.

### Resultado de la verificación (2026-08-25)

```
id2label   : {0: 'entailment', 1: 'neutral', 2: 'contradiction'}
entailment=0  neutral=1  contradiction=2

Verificacion 'presencia_grupos_armados': max|dif| = 0.00e+00 -> OK
Verificacion 'danos_ambientales'       : max|dif| = 0.00e+00 -> OK
```

Dos conclusiones, ambas verificadas:

1. **El mapeo de etiquetas es correcto.** `id2label` trae las etiquetas
   textuales, así que el bucle de `_resolver_labels` las resuelve y el fallback
   `ent, neu, con = 0, 1, 2` **nunca se ejecuta** — y aun si se ejecutara,
   coincidiría con el orden real del modelo. La sospecha de que se estuviera
   guardando `P(contradiction)` como `P(entailment)` queda descartada.
2. **`nli_core` reproduce producción bit a bit** (diferencia máxima 0.00e+00),
   así que cualquier variante que se mida aquí es comparable con los resultados
   del pipeline real.

## Los 5 ejes a probar

Las hipótesis actuales se desvían de la distribución de entrenamiento de XNLI en
varios ejes a la vez. Cada uno se aísla con un par que difiera en **una sola cosa**:

1. **Marco metalingüístico** — `"Este artículo reporta que X"` vs `"X"`.
   XNLI entrena con hipótesis que describen el mundo, no que comentan el documento.
2. **Disyunción múltiple** — el pre-filtro encadena 8 alternativas.
3. **Calificadores de evidencialidad** — `"explícitamente"`, `"verificable"`,
   `"identificado"`. No tienen contenido veritativo evaluable.
4. **Premisa** — producción usa `df["texto"]` truncado a ~470 tokens y **excluye
   el titular**. XNLI usa premisas de una sola frase. Ver `PREMISAS` en `nli_core.py`.
5. **Tildes** — 4 hipótesis están escritas sin acentuación (`danos`, `contaminacion`,
   `perdida`, `reivindicacion`...). Ver `SIN_TILDES` en `hipotesis_base.py`.

## Etiquetas de referencia

Sin verdad de referencia un A/B solo dice que los scores *cambiaron*, no que
*mejoraron*. Dos caminos:

- **Estándar de plata (inmediato).** `KEYWORDS_SILVER` en `hipotesis_base.py`,
  recuperado del bloque NER que se desactivó el 2026-06-24. Cubre solo
  `presencia_grupos_armados` y `grupos_etnicos_existentes`. Alta precisión, no es
  verdad absoluta; sirve para comparar variantes **entre sí**.
- **Anotación manual (sólido).** ~120–150 artículos sobre 3–4 indicadores. Es lo
  único que permite afirmar algo con confianza para indicadores sin marcadores
  léxicos (`deficit_participacion_comunitaria`, `debilidad_institucional`).

## Control negativo

`HIPOTESIS_CONTROL_ABSURDO` usa el formato exacto de las hipótesis reales con
contenido imposible (pingüinos emperador). Si puntúa alto, el formato infla los
scores con independencia del contenido — y el diagnóstico queda cerrado sin
necesidad de etiquetas. Es el experimento más barato de todos.

## Advertencia sobre los datos

- **Güintiva no está**: 0 artículos, sin cobertura de prensa.
- **Paraguachón tiene 20 artículos**, no 77: las otras 57 URLs se solapan con
  Maicao (es corregimiento suyo) y el dedup por URL se las atribuyó a Maicao.
- Paraguachón (20) y Oicatá (32) son bases muy pequeñas; sirven para el corpus
  global de AUC, no para conclusiones por lugar.
