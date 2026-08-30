# 09 — Riesgos y límites estructurales

*Medido el 2026-08-27. **Leer antes de invertir más trabajo en optimizar indicadores.***

Este documento existe para que nadie redescubra desde cero lo que ya está medido: hay un
techo estructural que ningún ajuste de hipótesis va a levantar.

---

## El hallazgo

Las líneas base que el proyecto nunca calculó, contra el radar oficial DANE:

```
Azar (3 clases)                        : 33.3%
Predecir siempre "Bajo"                : 34.4%
Predecir siempre "Alto"                : 34.4%
Predecir por nº de artículos solamente : 31.2%   <- modelo nulo
Radar propio actual                    : 31.2%
Objetivo del proyecto                  : 70.0%
```

**El radar empata exactamente con el modelo nulo y pierde contra un predictor constante.**
Decir "siempre Bajo" sin leer una sola noticia acierta más que todo el pipeline.

Y el dato que lo explica:

```
corr(radar_propio, radar_oficial)  Spearman = +0.067
corr(radar_propio, n_articulos)    Spearman = +0.062
corr(n_articulos,  radar_oficial)  Spearman = -0.260
```

**La correlación con el objetivo es cero.** No es que el radar mida mal el objetivo: es que
ambos constructos son prácticamente ortogonales.

### Pero el radar SÍ produce datos con sentido — mirar el ranking, no solo la correlación

Corrección importante, medida después de lo anterior. El ranking que produce el radar propio:

```
Más alto : Caquetá · Huila · Antioquia · Putumayo · Nariño · Tolima ·
           Arauca · Cesar · Norte de Santander · Casanare
Más bajo : Meta · Quindío · Boyacá · San Andrés · Sucre · Caldas · Guainía
```

**Por criterio de conflicto ese ranking es defendible.** Caquetá, Putumayo, Nariño, Arauca,
Norte de Santander y Antioquia arriba; Quindío, Boyacá, Caldas y San Andrés abajo. Y pasa la
prueba de sensatez: Cundinamarca no sale Alto.

Decir "el radar no lleva señal" sería incorrecto. **Lleva señal de conflicto; lo que no lleva
es señal de lo que el índice oficial ordena.** Son constructos distintos, no ruido.

### El MAX sí es un artefacto de cobertura — confirmado a escala nacional

```
corr(radar_MAX_crudo, nº de artículos)  Spearman = 0.87
```

Calculando el MAX de los 26 indicadores por departamento sobre `df_procesado_32deptos.pkl`,
los 5 más bajos son los 5 corpus más pequeños (Guainía 6 art., La Guajira 11, Vaupés 32,
Sucre 41, San Andrés 79) y los más altos los mayores (Magdalena 1.538, Cesar 1.075).

Es el artefacto del experimento 6 confirmado sobre los 32 departamentos. El cambio a **P75
ataca exactamente esto** (ver `04_hallazgos_revision_nli.md`).

### ⚠️ Discrepancia sin resolver — verificar antes de confiar en el 31.2%

Los dos cálculos anteriores **no dan el mismo ranking**:

| Fuente | corr con nº de artículos |
|---|---|
| Columna `Radar_completo_promedio_normalizado` del Excel de referencia | 0.062 |
| MAX de los 26 indicadores sobre `df_procesado_32deptos.pkl` | 0.87 |

`radar.py` aplica z-score (media 31.4, desv 7.6) y bloques A–E, pero **una calibración
z-score es monótona y no reordena**. Conclusión: la columna del Excel salió de un método o
de una corrida que **no es el pipeline actual**.

**Implicación:** no se sabe con certeza qué radar produjo la accuracy de 31.2%. Identificarlo
es barato y debe hacerse antes de interpretar esa cifra o de compararla con la de V2.

Reproducir con:

```python
import pandas as pd, unicodedata
norm = lambda s: unicodedata.normalize('NFKD', str(s).strip().lower()).encode('ascii','ignore').decode()
d = pd.read_excel('datos/referencia/comparacion_radares_V3.xlsx')
c = pd.read_pickle('datos/corpus/df_corpus_combinado_32deptos.pkl')
# unir por departamento normalizado y comparar clasificaciones
```

### Un matiz importante antes de sacar conclusiones

Esto se midió sobre un radar **que ya sabíamos roto**: la revisión demostró que era
indistinguible de uno construido con hipótesis absurdas (brecha 0.0004, ver
`04_hallazgos_revision_nli.md`).

Así que el 0.067 **no prueba** que un radar corregido no vaya a correlacionar. Prueba que el
actual no lleva ninguna señal. **Medir la correlación del radar V2 corregido es la pregunta
abierta más importante del proyecto** — y es barata una vez exista
`datos/scores/scores_v2_32deptos.pkl`.

---

## Por qué hay razones para temperar las expectativas

Tres factores estructurales, independientes de la calidad de los indicadores:

**1. Desajuste de constructo.** Los 26 indicadores miden conflicto y conflictividad social
reportada en prensa. El índice oficial parece medir vulnerabilidad socioeconómica y ausencia
de Estado (Vichada, Guainía, Amazonas arriba; Antioquia y Valle abajo). En Colombia esas dos
cosas se separan bastante: Antioquia tiene mucho conflicto y poca vulnerabilidad relativa;
Amazonas al revés.

**2. La cobertura del corpus va en contra del objetivo** (Spearman −0.26). Los departamentos
que el índice marca como más vulnerables son los que menos prensa tienen.

**3. Casi la mitad de la clase "Alto" es invisible.** De los 11 departamentos clasificados
como Alto, **5 tienen menos de 100 artículos**: Guainía 6, La Guajira 11, Vaupés 32,
Sucre 41, Vichada 62. Es la clase que más importa detectar y la que menos datos tiene.

**4. n = 32.** El error estándar de la accuracy es ~8 pp. Pasar de 0.312 a 0.70 significa ir
de 10 a 22 aciertos sobre 32. Diferencias menores a ~15 pp no se distinguen del ruido, y
optimizar directamente contra ese número arriesga sobreajustar a 32 puntos.

---

## Para qué existe el radar: el encuadre correcto

Antes de leer los tres caminos, hay que entender el diseño real del proyecto (confirmado por
el usuario, 2026-08-29):

> **Validar contra el DANE donde el DANE existe** (los 32 departamentos), **para poder
> aplicar el radar donde no existe**: veredas, municipios y otras ventanas temporales.

Es construir un proxy de alta frecuencia para una estadística oficial de baja frecuencia.
Diseño legítimo y común. Explica el ejercicio de Maicao, Oicatá y Paraguachón: el objetivo
final es bajar del nivel departamental, donde no hay referencia contra la cual contrastar.

No se busca reproducir la medida del DANE exactamente —podría ser mejor o peor— sino
**coincidir lo suficiente como para que el radar sea creíble donde no hay con qué
compararlo**.

**Consecuencia:** el acuerdo con el DANE no es un criterio más entre otros. Es **la licencia
para extrapolar**. Sin él no hay argumento para creerle al radar en una vereda.

**Asimetría a tener presente:** el DANE ordena por déficit estructural, el radar por
presencia de conflicto, y la cobertura de prensa está invertida respecto de ambos. Los
lugares donde más se quiere extrapolar (veredas remotas) son donde menos noticias hay —
Paraguachón tiene 20 artículos y Güintiva ninguno.

## Los tres caminos

**La decisión es de diseño de la investigación, no técnica.** Corresponde a la profesora, no
a quien programe.

Con el encuadre anterior, el camino (A) queda **debilitado**: el DANE no es un objetivo
intercambiable, es el ancla que da validez a la extrapolación. El debate real está entre
(B) y (C).

### A. Cambiar el objetivo

Validar el radar contra algo que sí deba predecir: un índice de conflicto armado (IICA del
DNP, informes de INDEPAZ, alertas tempranas de la Defensoría), y usar el DANE como contexto
descriptivo en vez de como verdad de referencia.

*A favor:* alinea la medición con lo que el instrumento realmente mide.
*En contra:* exige conseguir esa fuente y renegociar el criterio de éxito del proyecto.

### B. Cambiar los indicadores

Construir indicadores de la dimensión que el DANE mide: ausencia de servicios, debilidad
institucional, acceso a salud y educación, infraestructura.

*A favor:* mantiene el objetivo y el criterio de 0.70.
*En contra y hay que nombrarlo:* diseñar indicadores para acertarle al objetivo es
**legítimo en un modelo predictivo, pero discutible en un instrumento de medición**. Si el
radar se presenta como "medición de riesgo territorial", ajustarlo hasta que reproduzca otro
índice lo convierte en un estimador de ese índice, no en una medición independiente.

*Pista concreta:* de los 26, los que apuntan a esa dimensión son
`exclusion_servicios_derechos`, `debilidad_institucional`, `zonas_proteccion_alimentaria` y
`deficit_participacion_comunitaria`. Y **`debilidad_institucional` es uno de los tres
indicadores muertos** — el que más falta hace es el que no funciona.

### C. Soltar la métrica

Presentar el radar como instrumento propio con validez aparente, documentando qué mide y
qué no, sin accuracy contra el DANE.

*A favor:* honesto, y el trabajo de la revisión NLI lo respalda bien.
*En contra:* pierde el criterio de validación externa, que es lo que da credibilidad
académica.

---

## Antes de decidir: confirmar qué es el índice del DANE

**Es lo más barato y de mayor impacto de todo el backlog.** Hoy solo hay una inferencia a
partir de cómo ordena los departamentos. El DANE produce NBI, IPM, censo — no índices de
conflicto — lo que apoya la inferencia, pero no la confirma.

Saber exactamente qué indicador es decide cuál de los tres caminos corresponde. Si resulta
ser algo distinto de lo inferido, buena parte de este documento hay que reescribirla.

---

## Anclas de validez aparente — una prueba que la accuracy no da

Idea del usuario: *"sería imposible que en Cundinamarca nos arrojara un Alto"*. Es un juicio
externo, independiente del DANE, y detecta el disparate que una métrica agregada esconde.

Formalizado como test: departamentos donde el juicio externo es firme, con la clase que
**no** pueden tomar. Cualquier radar candidato debe respetarlas.

```
Nunca "Alto" : Cundinamarca · Quindío · Boyacá · San Andrés · Caldas · Risaralda
Nunca "Bajo" : Cauca · Nariño · Chocó · Arauca · Norte de Santander · Putumayo
```

**Ventajas sobre la accuracy:** es independiente del DANE, sobrevive a cambios de escala y
de agregación, y con n = 32 y error estándar de ~8 pp la accuracy sola no distingue un radar
bueno de uno mediocre — las anclas sí distinguen uno absurdo.

**Estado actual: el radar V0 las pasa.** Cundinamarca, Quindío, Boyacá y Caldas salen Bajo;
Nariño, Arauca, Putumayo y Norte de Santander salen Alto. Queda escrito **antes** de cambiar
la agregación, para poder comprobar que P75 no rompe lo que hoy funciona.

La lista es un juicio, no un dato: conviene revisarla con la profesora antes de usarla como
criterio formal. Implementar en `src/metricas_y_calculo_de_error.py` junto a la accuracy y
las líneas base.

## Riesgo metodológico: selección sobre el conjunto de evaluación

En la revisión de agosto se probaron **6 variantes por indicador** y se eligió la mejor por
AUC **sobre los mismos 141 y 119 positivos con los que se evalúa**. No hubo conjunto
reservado.

Con esas muestras, diferencias de AUC de 0.03–0.08 pueden no sobrevivir a validación
independiente.

**Qué aguanta y qué no:**

- *Aguantan* las conclusiones grandes: el marco metalingüístico (78% vs 20% en el control
  absurdo, una diferencia enorme y medida con un criterio independiente del AUC) y el
  problema del MAX (razón 0.91 vs 49.0).
- *No necesariamente aguantan* las comparaciones finas entre variantes cercanas.

**Para futuras comparaciones:** reservar un tercio de los positivos de plata como conjunto
de validación, elegir en los dos tercios restantes y reportar el resultado en el reservado.

---

## Qué NO es un riesgo

Para no reabrirlos: el mapeo de etiquetas NLI está verificado
(`id2label = {0: entailment, 1: neutral, 2: contradiction}`), y `nli_core` reproduce
producción bit a bit (`max|dif| = 0.00e+00`). Ver `08_log_decisiones.md`.
