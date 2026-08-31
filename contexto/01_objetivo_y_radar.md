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

### Procedencia de la columna `radar_oficial_promedio`

Confirmado por el usuario (2026-08-29):

- **Es del DANE.**
- **La columna se pegó a mano** en el Excel, tomada de una página web donde el DANE publica
  el valor por departamento.
- **La URL de esa página está perdida** por ahora. No hay script, documento ni commit en el
  repositorio que la registre: el valor entra al proyecto ya consolidado.
- El DANE usa **sus propios indicadores, con otros nombres y otros cálculos**. Cuáles son
  exactamente no está documentado en ninguna parte del repositorio.

**Lo que sigue abierto no es si es del DANE, sino cuál de sus índices es.** Eso decide si
los 26 indicadores propios apuntan al constructo correcto. Es la tarea 0 del backlog.

Pista de nomenclatura: `radar_oficial_**promedio**` sugiere que el valor es el promedio de
varios ejes de un radar original. Si es así, la página fuente tendría las columnas por eje —
y esos ejes serían justamente los "indicadores con otros nombres" del DANE. Recuperar esa
página daría el mapa completo contra el que se está comparando.

> Nota histórica: hubo una columna `IDIC` (índice del DNP) en la versión anterior del
> archivo. **Se eliminó a propósito** porque comparar contra dos referencias a la vez no
> tenía sentido. No es una pista perdida: fue una decisión. No reintroducirla.

## La métrica

**Accuracy de clasificación en terciles** contra el oficial. Se calcula en
`src/metricas_y_calculo_de_error.py`, junto con precision/recall/F1 macro, Cohen-kappa y la
matriz de confusión 3×3.

### Líneas base — reportarlas SIEMPRE junto a la accuracy

Una accuracy sola no dice si el pipeline aporta algo. Medido el 2026-08-27:

```
Azar (3 clases)                        : 33.3%
Predecir siempre "Bajo"                : 34.4%
Predecir siempre "Alto"                : 34.4%
Predecir por nº de artículos solamente : 31.2%   <- modelo nulo
Radar propio actual                    : 31.2%
Objetivo del proyecto                  : 70.0%
```

**El radar V0 empata con el modelo nulo y pierde contra un predictor constante.** Y su
correlación con el objetivo es **+0.067 (Spearman): cero**.

**Actualización 2026-08-30 — radar V2, medido a escala nacional:**

```
Spearman(radar_V2, radar_oficial_promedio) = +0.384  (p=0.030, n=32)
Accuracy en terciles (V2, sin recalibrar cortes)      = 37.5%
```

El salto de +0.067 a +0.384 sobrevive el control de la nula reservada (que sigue dando
~0.0000 con P75 a escala nacional) y no rompe las anclas de validez aparente. La
accuracy (37.5%) sigue sin distinguirse de las líneas base con n=32 — pero el Spearman,
que es el indicador de trabajo, sí. Detalle en `08_log_decisiones.md` [2026-08-30].

Esto es lo primero que hay que mirar antes de invertir esfuerzo en optimizar indicadores.
El análisis completo, con los tres caminos posibles, está en `09_riesgos_y_limites.md`.

Ya **no** se calculan MAE, RMSE, R², Pearson ni MAPE; cualquier documento que los mencione
como criterio está obsoleto.

**Con n = 32, el error estándar de la accuracy es ~8 pp.** Diferencias menores a ~15 pp no
se distinguen del ruido: una mejora de 3 departamentos no es una mejora.

### Para iterar, usar Spearman — no la accuracy

La accuracy en terciles **tira a la basura casi toda la información**: convierte 32 valores
continuos en 3 clases y cuenta aciertos. Un cambio que mejore el orden de verdad puede no
moverla ni un punto, y con n = 32 el ruido se come las diferencias pequeñas.

Para trabajar hace falta una señal más fina: **correlación de Spearman contra
`radar_oficial_promedio`** (el valor continuo, no la clase). Hoy está en **+0.067**.

```
Optimizar mirando Spearman · Reportar la accuracy
```

La accuracy sigue siendo el entregable y el criterio de éxito del proyecto (≥ 0.70); Spearman
es el instrumento de trabajo, porque responde cuando algo mejora de verdad.

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
