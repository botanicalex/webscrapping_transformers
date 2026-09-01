# 03 — Los 26 indicadores

**Las cadenas exactas viven en el código, no aquí**, para que no diverjan:

- `experimentos/hipotesis_base.py` → **V0**, las 26 hipótesis históricas (producción hasta
  el 2026-08-31). De solo lectura.
- `experimentos/hipotesis_v2.py` → **V2**, las 26 reescritas tras la revisión de agosto.
  Validadas en los 2 indicadores con estándar de plata. **En producción desde el
  2026-08-31** (`src/Transformer_optimo.py`, verificadas byte a byte antes de promover).
- `src/radar.py` → `CalculadorRadar.COLUMNAS_BINARIAS`, la lista canónica de nombres.

## Composición

**5 eventos** — hechos que ocurrieron: `desplazamiento_forzado`, `reasentamiento`,
`protesta_social`, `amenaza_intimidacion`, `conflicto_territorial`.

**5 posturas** — posición de actores: `rechazo_proyecto`, `derechos_vulnerados`,
`conflicto_activo`, `resistencia_territorial`, `exclusion_comunidades`.

**16 generales** — `deficit_participacion_comunitaria`,
`incentivos_economicos_inequitativos`, `debilidad_institucional`, `danos_ambientales`,
`conflictos_socioambientales`, `violacion_derechos_humanos`, `exclusion_servicios_derechos`,
`grupos_etnicos_existentes`, `movimientos_sociales`, `poblacion_afectada`,
`exclusion_beneficios_economicos`, `irregularidad_contractual`,
`zonas_proteccion_alimentaria`, `dano_territorios`, `presencia_grupos_armados`,
`amenaza_lideres`.

Todos son **NLI**. Cero NER, cero zero-shot.

## Historia

- Se partió de 36, luego 31.
- **Junio 2026:** se eliminaron 3 indicadores que medían la *ausencia* de eventos
  (`consulta_previa_omitida`, `audiencia_publica_omitida`, `taller_participativo_omitido`) —
  pedir a un modelo que infiera que algo *no* se hizo es poco fiable.
- `grupos_etnicos_existentes` se **migró de NER a NLI**, y con eso se eliminó el redundante
  `existencia_grupos_etnicos`. Igual con `grupos_armados_existentes`, cubierto por
  `presencia_grupos_armados`.
- Quedan **26**. `VARS_INVERTIR` está vacío: todos tienen hipótesis de déficit/riesgo, así
  que más alto siempre es peor.

## La transformación V0 → V2

**Regla:** quitar el marco metalingüístico. La hipótesis describe **el territorio o el
hecho**, no el documento.

```
V0: "Este artículo menciona explícitamente la presencia, acción, control o
     intervención de grupos armados ilegales en un territorio."
V2: "En este territorio hay presencia de grupos armados ilegales."

V0: "Este texto reporta que OCURRIÓ un desplazamiento forzado, expulsión o
     éxodo de comunidades"
V2: "Hubo un desplazamiento forzado o éxodo de comunidades."
```

Reglas secundarias: frase corta y declarativa (XNLI se entrenó con hipótesis de ~10 tokens);
sin `"explícitamente"` / `"verificable"` / `"documentada"` (instrucciones para un anotador,
no proposiciones); tildes correctas; la disyunción se conserva cuando es sustantiva.

El porqué y las mediciones están en `04_hallazgos_revision_nli.md`.

## Solapamientos conocidos

**`incentivos_economicos_inequitativos` vs `exclusion_beneficios_economicos`.** Eran casi el
mismo enunciado. Se diferenciaron a mano (agosto): el primero mide *reparto desigual*, el
segundo *exclusión total*. **El cambio no funcionó**: la correlación entre ambos pasó de
0.8017 a 0.7997 — siguen midiendo lo mismo, solo intercambiaron magnitudes.

**`exclusion_comunidades` vs `deficit_participacion_comunitaria`.** También se solapan. En
V2 se separaron: el primero es la *exigencia* de ser incluido, el segundo la *ausencia* de
proceso participativo. Sin medir todavía.

## Los tres indicadores muertos

`debilidad_institucional`, `danos_ambientales` e `irregularidad_contractual` dan **0.0000
incluso en el percentil 90**, en los cuatro lugares.

No es culpa de la agregación: ya eran los más débiles antes de la reescritura
(`prop_0.9` histórico de 0.043 y 0.057). Las causas candidatas son la redacción, que el
fenómeno sea genuinamente raro en prensa regional, o que el concepto sea demasiado abstracto
para inferencia textual.

Nota: `debilidad_institucional` es de los pocos indicadores que apuntan a la dimensión
*ausencia de Estado*, que es la que el índice oficial parece medir. Que no funcione es
doblemente costoso. Ver `07_backlog.md`.

> **Corrección [2026-09-01]:** la etiqueta "tres indicadores muertos" es inexacta a escala
> nacional. Sobre `scores_v2_32deptos.pkl` (P90 por rango cercano):
> `irregularidad_contractual` 21/32 departamentos > 0 (max 0.3586),
> `debilidad_institucional` 7/32 (max 0.1419), `danos_ambientales` 3/32 (max 0.0247). En
> P75 —lo que usa el radar— quedan casi mudos (1/32, 1/32, 0/32); el único en cero
> absoluto es `danos_ambientales`, junto con `deficit_participacion_comunitaria`.
> Diagnosticar sobre el corpus nacional, no el de 5 lugares. Ver `08_log_decisiones.md`
> [2026-08-31].

## Cuatro hipótesis sin tildes

`resistencia_territorial`, `exclusion_comunidades`, `danos_ambientales` y
`violacion_derechos_humanos` estaban escritas sin acentuación en V0 ("danos",
"contaminacion", "perdida", "reivindicacion"). "danos" no es una palabra española y tokeniza
distinto de "daños". Corregido en V2; el efecto aislado no se midió.

## Pre-filtro social

**CERRADO 2026-08-31: RECHAZADO y retirado de producción.** Con la escala V2 se probó el
umbral 0.85 (AUC por indicador + control absurdo): cuesta AUC de forma clara en los 2
indicadores con estándar de plata (−0.053 y −0.027, IC95% excluye cero). Hoy los 26
indicadores se puntúan sobre todos los artículos. Detalle en `08_log_decisiones.md`
[2026-08-31].

Histórico (V0): una hipótesis NLI aparte (`HIPOTESIS_SOCIAL`) con umbral 0.65; los
artículos que no la superaban quedaban con sus 26 indicadores en 0. En V0 tenía la
enfermedad de formato en forma extrema —metalingüística y con ocho disyuntos encadenados—
y **anulaba el 33.6% de los positivos de plata** de `grupos_etnicos_existentes` y el 17.7%
de `presencia_grupos_armados`. Reescrita en V2 a una sola frase. Su umbral 0.65 fue
calibrado para la distribución de la hipótesis vieja; con la hipótesis V2 dejaba pasar el
92.5% en vez del 65.5%.
