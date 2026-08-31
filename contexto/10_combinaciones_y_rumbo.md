# 10 — Combinaciones probadas y hacia dónde seguir

*Escrito el 2026-08-31. Responde tres preguntas de golpe: cuál combinación funciona mejor,
qué se probó ya, y qué está corriendo hoy en esta rama.*

*Verificado con tres revisores independientes contra el repositorio. La primera versión de
este documento tenía varias afirmaciones que no resistieron el escrutinio; están corregidas
y las correcciones se señalan donde importan.*

Todo número lleva el archivo del que sale. Si algo no está medido, dice "no medido".

---

## 1. La mejor combinación hasta ahora

El pipeline tiene tres etapas y **en cada una hay decisiones independientes**:

| Etapa | Qué se decide |
|---|---|
| **1. Scraper** | Qué términos de búsqueda, qué periódicos, qué filtro de relevancia |
| **2. Transformers** | Redacción de las 26 hipótesis, si hay pre-filtro social, si se descuenta el sesgo por artículo |
| **3. Radar** | Cómo se agregan los artículos por lugar (MAX / P75), dónde se cortan las clases |

### Las 5 combinaciones medidas

Todas sobre el mismo corpus (11.439 artículos, 32 departamentos) y los mismos términos de
búsqueda de conflicto. **La etapa 1 nunca se ha variado en una medición completa** — solo
cambian las etapas 2 y 3.

| id | Hipótesis | Pre-filtro | Agregación | Cortes | Accuracy | Spearman |
|---|---|---|---|---|---|---|
| **A** | V0 (viejas) | sí (0.65) | MAX | terciles | 31.2% | +0.067 (ver aviso) |
| **B** | V2 (nuevas) | sí (0.85) | P75 interpolado | terciles ad hoc | **40.6%** | +0.376 |
| **C** | V2 | no | P75 interpolado | terciles ad hoc | 37.5% | +0.384 |
| **D** | V2 | sí (0.85) | P75 interpolado | fijos 0.30 / 0.35 | 31.2% | +0.376 |
| **E** | V2 | no | P75 rango cercano | fijos 0.2969 / 0.3527 | 25.0% | +0.4208 |

**E es la receta que está en `src/`.** Pero ojo: **los números de la fila E son un recálculo
offline sobre `scores_v2_32deptos.pkl`, no la salida de una corrida de producción.**
Producción nunca ha corrido sobre los 32 departamentos con la receta V2 (ver sección 3).

Fuentes: A → `09_riesgos_y_limites.md` (histórico). B y C →
`experimentos/resultados/exp_correlacion_v2_nacional.xlsx`. D →
`experimentos/resultados/exp_cortes_fijos_v2.xlsx`. E →
`experimentos/resultados/exp_verificar_promocion_v2.xlsx`; sus cortes salen de
`experimentos/resultados/exp_cortes_fijos_v2_sin_prefiltro.xlsx`.

**Aviso sobre la fila A.** El +0.067 **no es reproducible desde la receta que la fila
declara**. Recalculando V0 + MAX sobre `datos/scores/df_procesado_32deptos.pkl` da −0.18.
El +0.067 corresponde a la columna `Radar_completo_promedio_normalizado` del Excel de
referencia, **cuya procedencia `09_riesgos_y_limites.md` declara sin resolver** ("salió de
un método o de una corrida que no es el pipeline actual"). O sea: el punto de partida de la
comparación es un radar no identificado. La accuracy de 31.2% de esa fila sí se sostiene.

### Las líneas base — sin esto los números de arriba no significan nada

Recalculadas el 2026-08-31 contra la clasificación oficial real del DANE
(`datos/referencia/comparacion_radares_V3.xlsx`; conteos por departamento desde
`datos/corpus/df_corpus_combinado_32deptos.pkl`):

```
Azar (3 clases)                          33.3%
Predecir siempre "Bajo"                  34.4%
Predecir siempre "Alto"                  34.4%
Predecir siempre "Medio"                 31.2%
Predecir por nº de artículos (nulo)      28.1%
Objetivo del proyecto                    70.0%
```

**El modelo nulo da 28.1%, no 31.2%.** El 31.2% que figura en `09_riesgos_y_limites.md` y
en `07_backlog.md` punto 0b se calculó re-tercilando el número crudo del DANE en vez de
usar su columna de clasificación. Esos dos documentos están desactualizados en ese punto.

### La lectura honesta

**Por accuracy pura, la mejor es B (40.6%).** Y hay que decir algo que la primera versión
de este documento se saltaba: **B le saca 15.6 puntos a E (25.0%), y 15.6 pp está POR
ENCIMA del umbral de ~15 pp que el propio proyecto fija como límite del ruido (regla 11).**
Por su propia regla, B le gana a E de forma distinguible en la métrica oficial. No sirve
invocar la regla 11 solo cuando conviene.

Aun así, B no puede ser producción, y la razón es **una sola y es fuerte**:

> **Los "terciles ad hoc" no son un método desplegable.** Calculan los cortes dividiendo
> los 32 departamentos en tres grupos iguales. El objetivo del proyecto es clasificar
> *una vereda sola*, donde no hay otros 31 lugares con qué hacer terciles. B existe como
> número de referencia, no como radar utilizable.

A eso se suma una **decisión** (no una comparación de potencia): el pre-filtro que usa B se
rechazó por su efecto en el AUC por indicador. Conviene ser preciso, porque el proyecto
insiste en no confundir los dos ejes: el AUC mide **discriminación del indicador** contra el
estándar de plata; la accuracy mide **acuerdo del radar departamental** con el DANE. No son
la misma escala y la primera no "gana" a la segunda por potencia estadística. Lo que pasó es
que el proyecto decidió que la validez del indicador manda sobre la accuracy a n=32. Es
defendible, pero es una decisión.

**Dos razones que la primera versión de este documento daba y que NO se sostienen:**

- *"E tiene el Spearman más alto"* — el Spearman es **invariante a los cortes**, que es
  justamente lo único que distingue a E de B/C. No puede justificar un juego de cortes
  sobre otro. Además +0.4208 vs +0.384 es diferencia de ruido, y se debe al cambio de P75
  interpolado a rango cercano, no a la receta.
- *"E no rompe ninguna ancla de validez aparente"* — **las cinco combinaciones pasan las
  anclas**, así que no distingue nada; y en el caso de E los cortes se eligieron filtrando
  por esa condición, o sea que la cumple por construcción.

**Matiz sobre "los cortes se leyeron sin mirar el objetivo":** es cierto que el script nunca
consulta la columna del DANE. Pero su criterio **primario** es el balance de clases
(maximizar la clase más pequeña) y el tamaño del hueco es solo el desempate. Y preferir la
partición más balanceada no es del todo neutral: la clasificación oficial es 11 Alto / 11
Bajo / 10 Medio, casi perfectamente balanceada. Es mucho más débil que mirar el objetivo,
pero no es información cero.

**Y lo incómodo, sin rodeos: ninguna de las 5 combinaciones supera las líneas base de forma
concluyente, y la que quedó en producción (E, 25.0%) está por debajo de las cinco,
incluido el modelo nulo.** Después de tres días de correcciones reales y medidas, la
accuracy contra el DANE no mejoró.

**Lo que sí se movió, y es real:**

- **Validez del instrumento.** El radar V0 era indistinguible de uno construido con
  hipótesis absurdas (brecha 0.0004 en el control absurdo). El V2 no. Eso no aparece en la
  accuracy, pero es la diferencia entre medir algo y no medir nada. *Advertencia:* esa
  validación se hizo eligiendo la mejor de 6 variantes por AUC **sobre los mismos positivos
  con los que se evalúa**, sin conjunto reservado (`09_riesgos_y_limites.md`). Las
  conclusiones grandes aguantan; las comparaciones finas entre variantes cercanas, no
  necesariamente.
- **Spearman más alto que el punto de partida.** Con la salvedad del aviso sobre la fila A:
  el punto de partida (+0.067) es un radar no identificado.

---

## 2. Qué se probó y qué falta

### Cerrado con evidencia medida — no relitigar

Detalle y evidencia en `08_log_decisiones.md`.

| Qué se probó | Resultado |
|---|---|
| ¿Las etiquetas NLI están invertidas? | **No.** Sospecha descartada con evidencia |
| Marco metalingüístico ("Este texto reporta que X") | **Es la causa de la inflación.** 78% de las noticias "implicaba" hipótesis absurdas → reescritas (V2) |
| Quitar la disyunción múltiple de las hipótesis | **Rechazado** — empeora (83% en control absurdo) |
| Normalizar `ent/(ent+con)` (descartar neutral) | **Rechazado** — triplica la inflación |
| Premisa: cuerpo vs titular vs titular+lede | **Empate** — se mantiene el cuerpo |
| Agregación MAX / TOP3 / TOP5 | **Rechazadas** — premian tener más artículos, no más riesgo |
| Agregación P75 vs P90 | **P75 adoptado** (cuesta 3 indicadores que solo viven en P90) |
| Descontar sesgo por artículo (4 hipótesis nulas) | **Adoptado** |
| NER y análisis de sentimiento | **Desactivados** (junio) — no alimentaban nada |
| Cortes: terciles empíricos vs fijos | **Fijos** (restricción externa: clasificar una vereda sola) |
| Pre-filtro social, **umbral 0.85** | **Rechazado** — cuesta AUC. *Alcance:* solo ese umbral, solo 2 de 26 indicadores. Otro umbral no está descartado |
| Correlación del V2 a escala nacional | **Medida** |
| Promover V2 a `src/` | **Hecho** (2026-08-31) |
| 6 bugs de scraping | **Corregidos y verificados contra red real** (2 el 30-08, 4 el 31-08) |

### Pendiente — ordenado por lo que desbloquea

**Bloqueante y barato (no es técnico):**

- **Identificar qué índice del DANE es exactamente el de referencia.** La columna se copió a
  mano de una página web cuya dirección se perdió. **Lo trae el usuario.** Decide cuál de
  los tres caminos de `09_riesgos_y_limites.md` corresponde. Se vuelve más urgente a la luz
  del aviso sobre la fila A: hoy ni siquiera está claro qué radar produjo el histórico.

**No depende de nada — se puede hacer ya:**

- **Ampliar el estándar de plata.** Hoy cubre **2 de 26** indicadores. Es la mayor debilidad
  del informe: todas las conclusiones de calidad —incluido el rechazo del pre-filtro—
  descansan en dos. Conviene además **reservar un tercio de los positivos** como conjunto de
  validación, que es la recomendación pendiente de `09_riesgos_y_limites.md`.
- **Los indicadores débiles.** `danos_ambientales` es el único que queda en 0.0000 en P75 a
  escala nacional (junto con `deficit_participacion_comunitaria`). Ver el aviso de abajo:
  la etiqueta "tres indicadores muertos" del backlog es inexacta a escala nacional.
- **Fusionar `incentivos_economicos_inequitativos` con `exclusion_beneficios_economicos`**
  (correlacionan 0.80). Y **`debilidad_institucional` se reescribe, no se elimina**: apunta
  a la dimensión que el DANE parece medir.

**Depende de decisiones o de datos:**

- **Decidir si se fusiona el corpus re-scrapeado** (La Guajira 11→1.553, Norte de Santander
  36→352, Valle del Cauca 117→145). Está sin fusionar porque `datos/corpus/` es compartida
  con `desarrollo/` por junction. **Esta decisión va ANTES de re-puntuar**: al revés obliga
  a repetir las ~4 h de GPU, que es lo que prohíbe la regla 8.
- **Re-puntuar los 32 departamentos con el código de `src/`** (~4 h GPU). Ver el problema
  del cargador de corpus en la sección 3 antes de lanzarlo: tal como está produce 35 filas,
  no 32.
- **San Andrés y Providencia:** el corpus tiene **79 artículos** (no 0 — el 0 fue solo el
  resultado de la corrida de re-scraping del 31-08, con El Tiempo caído). Reintentable:
  probar primero una petición suelta a `eltiempo.com/buscar/` antes de relanzar el
  departamento entero. Importa porque San Andrés es una de las anclas ("nunca Alto").
- **Términos de búsqueda: conflicto vs déficit** (etapa 1, la única nunca variada). Cuatro
  de los cinco términos actuales tiran hacia conflicto. Depende de saber qué mide el DANE.
- **Bloque de indicadores de déficit estructural** (9 hipótesis candidatas ya redactadas en
  `07_backlog.md`). Va después de los términos: si la prensa no trae el material, ninguna
  hipótesis lo encuentra.
- **Cobertura de prensa desbalanceada** — la mejora de mayor impacto y mayor costo.

**Deuda técnica conocida:**

- El bug de timeout corregido en Corrillos/Enlace tiene el mismo patrón estructural en
  **15 clases de scraper** más (10 con `timeout=15` literal, 5 con `timeout=30`), sin
  confirmar si las afecta.
- El camino legado de pesos aleatorios con poda por accuracy sigue en `radar.py`. Ver
  sección 3.

### Nunca probado

- Ponderar los 26 indicadores **por razonamiento de dominio** (no aleatoriamente). Hoy el
  radar es un promedio simple.
- Reconsiderar P90 si aparecen muchos indicadores raros pero válidos.
- Los caminos (A) y (C) de `09_riesgos_y_limites.md`: cambiar el objetivo contra el que se
  valida, o soltar la métrica. **No son decisiones técnicas.**

---

## 3. Qué corre hoy en esta rama (`pruebas`)

### Las hipótesis son las NUEVAS (V2)

Desde el 2026-08-31, `src/Transformer_optimo.py` tiene las 26 hipótesis **V2**, verificadas
byte a byte idénticas a `experimentos/hipotesis_v2.py`.

```
V0 (vieja) : "Este artículo menciona explícitamente la presencia, acción, control o
              intervención de grupos armados ilegales en un territorio."
V2 (nueva) : "En este territorio hay presencia de grupos armados ilegales."
```

Las 26 **claves** son idénticas entre V0 y V2; solo cambia el texto. Las viejas sobreviven
en `experimentos/hipotesis_base.py`, que es de **solo lectura**.

### El cálculo del radar, paso a paso

```
1. Por cada artículo y cada una de las 26 hipótesis:
      ent = P(entailment)      neu = P(neutral)

2. Sesgo del artículo (mide si es un artículo "sí-decidor"):
      sesgo = media de P(entailment) contra 4 hipótesis IMPOSIBLES
              (pingüinos emperador, helio-3 lunar, caligrafía medieval, glaciares de metano)

3. Score corregido del indicador:
      score = clip( clip(ent - sesgo, 0) * (1 - neu), 0, 1 )

4. Agregación por departamento (por cada indicador):
      P75 por RANGO MÁS CERCANO  (no el MAX, no interpolado)

5. Radar del departamento:
      promedio simple de los 26 valores P75   -> radar_propio

6. Clasificación:
      Bajo   si radar_propio <  0.2969
      Medio  si 0.2969 <= radar_propio < 0.3527
      Alto   si radar_propio >= 0.3527
```

**No hay pre-filtro social. No hay calibración z-score.** Los cortes son fijos, no terciles.
La clasificación oficial del DANE se lee de su columna, ya no se recalcula.

**Sobre los cortes:** su primera versión (0.3074/0.3524) se calibró por error sobre la
distribución del P75 **interpolado**, mientras que producción usa **rango más cercano** —
otra distribución (max|dif| 0.0219). En la distribución buena, 0.3074 caía en un hueco de
0.0071, por debajo del umbral de 0.008 que el propio script exige. Es el caso literal de la
regla 2. Recalibrados el mismo día sobre la distribución correcta → **0.2969 / 0.3527**. La
accuracy no cambió (25.0%) y las anclas siguen intactas.

### Dónde vive cada cosa

| Archivo | Qué hace |
|---|---|
| `src/Transformer_optimo.py` | Hipótesis V2, sesgo, score corregido, P75 por departamento |
| `src/radar.py` | Promedio de los 26, cortes fijos. Contiene también el camino legado de pesos aleatorios, **fuera del default** |
| `src/config_pipeline.py` | `CORTE_BAJO_MEDIO_RADAR` / `CORTE_MEDIO_ALTO_RADAR` |
| `src/metricas_y_calculo_de_error.py` | Accuracy contra el DANE, con líneas base |
| `src/orquestador_pipeline.py` | Orquesta todo |

Se ejecuta desde la raíz:

```bash
python src/orquestador_pipeline.py --only transformers --skip-scraping
```

### Cómo se verificó la promoción

- **Sin GPU:** la receta recalculada sobre `scores_v2_32deptos.pkl` da Spearman +0.4208 y no
  rompe ninguna ancla (`experimentos/exp_verificar_promocion_v2.py`).
- **Con GPU:** se corrió el `Transformer_optimo.py` real sobre el corpus de 5 lugares
  (32 min) contra `nli_core` independiente: **max|dif| ~5e-7**
  (`experimentos/exp_smoke_test_produccion_v2.py`).
- `src/test_integracion.py` (10 tests) pasa.
- Baseline de verificación vigente: `datos/scores/df_procesado_baseline_v2.pkl`.

### Lo que está roto o pendiente en `src/` — leer antes de lanzar una corrida larga

Encontrado en la revisión del 2026-08-31, **después** de la promoción:

1. **`CargadorCorpus` carga TODOS los `df_corpus_*.pkl`**, no solo el nacional. Una corrida
   real levanta **12.592 artículos y 35 valores de `departamento`** (incluye "Municipio
   Maicao", "Vereda Paraguachón", "Antioquia (2023)"), no 11.439 / 32. **Un re-puntuado
   nacional produciría 35 filas de radar.** Hay que decidir qué corpus debe cargar
   producción antes de gastar las 4 h.
2. **Dos scripts sueltos siguen con la receta vieja:** `src/pipeline_lugares.py` y
   `src/generar_max_articulos_por_departamento.py` usan cortes 1/3–2/3 y agregación MAX
   (rechazada). No están en el camino por defecto.
3. **El registro `experimentos_radar.jsonl` miente** para la operación "bloques": anota
   `"promedio_simple_36_indicadores"` y `"calibracion": "zscore..."`. Son 26 indicadores y
   no hay z-score.
4. **El camino legado de pesos aleatorios** (`--operaciones-radar indicadores_transformers`)
   sigue invocable. Tiene un riesgo de sobreajuste documentado: poda al top-N por accuracy
   contra el propio DANE. **No usarlo.**

Corregidos el mismo día, después de la revisión: el comando por defecto reventaba con
`ValueError` *después* de las 4 h de GPU (colisión de `EXPERIMENTO_1`); el camino legado de
métricas aplicaba los cortes V2 a columnas en escala 0–100 y las mandaba casi todas a
"Alto"; `pipeline_lugares.py` reventaba con `KeyError` por la columna `score_social` ya
retirada; y la rama de scraping del orquestador era código muerto (`tf.sc`).

### Lo que NO se ha hecho en esta rama

- **Producción nunca corrió sobre los 32 departamentos con la receta V2.** Todos los números
  nacionales vienen de `experimentos/`, vía `nli_core`.
- Nada se fusionó a `master`, y `ESTADO_DEL_PROYECTO.md` **sigue describiendo el estado del
  2026-08-30** (V0 en producción). Está desactualizado.

---

## 4. El techo estructural — por qué la accuracy no se mueve

Detalle en `09_riesgos_y_limites.md`:

1. **Desajuste de constructo.** Los 26 indicadores miden conflicto. El índice oficial parece
   medir vulnerabilidad socioeconómica y ausencia de Estado.
2. **La cobertura del corpus va en contra del objetivo.** `Spearman(nº artículos, radar
   oficial) = −0.31` (recalculado 2026-08-31; `09_riesgos_y_limites.md` dice −0.26).
3. **Casi la mitad de la clase "Alto" es invisible.** De los 11 departamentos Alto, 5 tenían
   menos de 100 artículos: Guainía 6, La Guajira 11, Vaupés 32, Sucre 41, Vichada 62.
   **La Guajira ya tiene 1.553 esperando la decisión de fusión** — ese límite no es del todo
   inamovible.
4. **n = 32.** Diferencias de accuracy menores a ~15 pp no se distinguen del ruido.

Ninguno de los cuatro se arregla ajustando la redacción de una hipótesis.

---

## Aviso: la etiqueta "tres indicadores muertos" es inexacta

`07_backlog.md` punto 5 dice que `debilidad_institucional`, `danos_ambientales` e
`irregularidad_contractual` "dan 0.0000 incluso en el percentil 90". **Eso solo es cierto
sobre el corpus de 5 lugares.** A escala nacional (`scores_v2_32deptos.pkl`, P90 por rango
más cercano):

```
irregularidad_contractual   21/32 departamentos > 0   (max 0.3586)
debilidad_institucional      7/32 departamentos > 0   (max 0.1419)
danos_ambientales            3/32 departamentos > 0   (max 0.0247)
```

En P75 (lo que usa el radar) sí quedan casi mudos: 1/32, 1/32 y 0/32. El que está
verdaderamente en cero a escala nacional es `danos_ambientales`, junto con
`deficit_participacion_comunitaria`. Antes de diagnosticar "por qué están muertos", conviene
mirar el corpus nacional y no el de 5 lugares.
