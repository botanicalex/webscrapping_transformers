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

Un matiz a favor del pipeline: la correlación con el número de artículos también es ~0, así
que el radar **no** es un medidor de cobertura de prensa disfrazado. Mide algo —
presumiblemente conflicto — pero ese algo no es lo que el índice oficial ordena.

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

## Los tres caminos

**La decisión es de diseño de la investigación, no técnica.** Corresponde a la profesora, no
a quien programe.

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
