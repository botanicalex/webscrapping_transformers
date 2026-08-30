# 01 — Objetivo, radar oficial y métrica

## Qué mide el radar

Un valor **alto** significa **zona difícil o inviable para implementar proyectos**:
conflicto activo, presencia de grupos armados, ausencia de Estado, tensión con las
comunidades. No mide "cuánto pasa" sino "cuánto estorba" a una intervención.

De ahí la clasificación en tres clases: **Bajo** (viable), **Medio**, **Alto** (no viable).

## La referencia oficial

`datos/referencia/comparacion_radares_V3.xlsx` — 32 filas × 6 columnas:

| Columna | Contenido |
|---|---|
| `Departamento` | los 32 DANE |
| `radar_oficial_promedio` | valor de referencia (rango observado 18.8 – 46.4) |
| `radar_oficial_promedio_normalizado` | el anterior escalado a [0,1] |
| `Clasificacion_radar_oficial_promedio` | Bajo / Medio / Alto por terciles |

`comparacion_radares.xlsx` trae la misma columna oficial más 13 columnas
`EXPERIMENTO_*` de corridas viejas; es la que consume la ruta legado del orquestador.

### Cómo se ordena

```
Más alto : Vichada 46.4 · Guainía 46.0 · La Guajira 41.8 · Chocó 41.6 ·
           Amazonas 40.4 · Sucre 39.7 · Arauca 39.4 · Vaupés 36.6
Más bajo : Quindío 18.8 · Caldas 20.7 · San Andrés 21.9 · Cundinamarca 22.1 ·
           Risaralda 22.2 · Santander 23.0 · Valle del Cauca 23.3
```

**Antioquia sale "Bajo" (25.7)** y Cauca y Nariño quedan en "Medio".

Esto **no es un índice de conflicto armado**. Por conflicto, Antioquia y Cauca estarían
arriba y Vichada, Guainía y Amazonas no. El patrón —periferia amazónica y orinoquense
arriba, centros industriales abajo— es el de un índice de **vulnerabilidad socioeconómica y
ausencia de Estado**, coherente con que venga del DANE y con la definición de "difícil
implementar proyectos".

**Implicación:** los 26 indicadores cubren bien la dimensión *conflicto* y flojo la
dimensión *ausencia de Estado / vulnerabilidad*. Ahí está probablemente una parte de la
brecha de accuracy. Los pocos indicadores que sí apuntan a esa dimensión
(`exclusion_servicios_derechos`, `debilidad_institucional`, `zonas_proteccion_alimentaria`,
`deficit_participacion_comunitaria`) merecen atención — y `debilidad_institucional` es
justamente uno de los tres que no se activan nunca.

*(No se ha confirmado qué indicador exacto del DANE es. Vale la pena preguntarlo: cambia
cómo se interpretan los resultados.)*

## La métrica

**Accuracy de clasificación en terciles** contra el oficial. Se calcula en
`src/metricas_y_calculo_de_error.py`, junto con precision/recall/F1 macro, Cohen-kappa y la
matriz de confusión 3×3.

- **Objetivo del proyecto:** accuracy ≥ 0.70
- **Estado medido:** **0.312** (10 de 32 aciertos)
- **Azar con 3 clases:** 0.333

El radar está en el azar o por debajo. Ya **no** se calculan MAE, RMSE, R², Pearson ni MAPE;
cualquier documento que los mencione como criterio está obsoleto.

**Con n = 32, el error estándar de la accuracy es ~8 pp.** Diferencias menores a ~15 pp no
se distinguen del ruido: una mejora de 3 departamentos no es una mejora.

## La limitación estructural del insumo

La cobertura de prensa está **negativamente correlacionada** con el objetivo:

```
Correlación radar_oficial vs nº de artículos del corpus:  Spearman = -0.26
```

Los departamentos que el índice marca como más vulnerables son los que menos prensa tienen:

| Alto según el oficial | Artículos |
|---|---|
| Guainía | 6 |
| La Guajira | 11 |
| Vaupés | 32 |
| Sucre | 41 |
| Vichada | 62 |

**De los 11 departamentos clasificados como Alto, 5 tienen menos de 100 artículos.** Es la
clase que más importa detectar y es la que menos datos tiene. Mientras tanto Boyacá (Bajo)
tiene 380 y Cundinamarca (Bajo) 371.

**Consecuencia para interpretar resultados:** si el radar no reproduce el ranking esperado,
eso *no* prueba que los indicadores fallen — puede ser el reflejo fiel de un corpus mal
balanceado. Son dos afirmaciones distintas y no hay que mezclarlas:

- "los indicadores discriminan mejor" → demostrable con AUC y control absurdo
- "el radar predice mejor el índice oficial" → depende también del insumo

Reforzar `DEPARTAMENTO_PERIODICOS` para Norte de Santander, Chocó, La Guajira y Arauca
mejoraría el resultado más que cualquier ajuste de hipótesis. Exige re-scrapear.
