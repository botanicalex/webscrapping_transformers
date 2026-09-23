# Informe — Fase 8: la compuerta de grupos armados pasa a producción

Fecha: 2026-09-22 (redactado el 2026-09-23) · Rama: `hipotesis-5ind-max` · Commits `062ab20` y
`50a553a` (locales: sin push ni merge a `radar-max_Septiembre`) · Antecedente:
`informes/01_informe_5ind_MAX_fases_0-7.md`.

## 1. Resumen

- El indicador **presencia de grupos armados** ahora solo puntúa un artículo si el texto que lee
  el modelo **nombra un grupo armado organizado** (ELN, FARC/disidencias, Clan del Golfo/AGC,
  autodefensas, paramilitares, guerrilla, "frente 36"…). Antes, con agregación MAX, el valor
  de un lugar lo fijaban a menudo homicidios, hurtos o "combos": delincuencia común.
- Es una regla de palabras clave encima del mismo modelo NLI. **No entra ningún LLM a
  producción.** Los otros 25 indicadores no cambian y **el radar sigue con 26**.
- El corte Bajo/Medio del radar se recalibró de **0.766 a 0.7574** (el Medio/Alto sigue en
  0.9233). **Ningún departamento cambia de clase** (6 Bajo / 19 Medio / 7 Alto).
- Verificado sin GPU: los tests pasan (15/15) y el código de producción reproduce exactamente
  el resultado del experimento en los 11.439 artículos de los 32 departamentos.
- Excel de Maicao, Oicatá y Paraguachón regenerados antes/después: solo cambia grupos armados
  (Oicatá baja de 65 a 0; Maicao queda en 98, pero ahora lo fija un artículo correcto).

## 2. Qué cambió en el código de producción

| Archivo | Cambio |
|---|---|
| `src/Transformer_optimo.py` | En `procesar()`: `presencia_grupos_armados = score corregido × compuerta`. La compuerta vale 1 si la lista de palabras clave (`REGEX_COMPUERTA_GRUPOS_ARMADOS`, copiada literal del experimento) aparece en el texto que ve el modelo con esa hipótesis, en minúsculas y sin tildes; 0 si no. Se guarda como columna auxiliar `compuerta_grupos_armados` (igual que `sesgo`), fuera de la lista de los 26 indicadores. |
| `src/config_pipeline.py` | `CORTE_BAJO_MEDIO_RADAR` 0.766 → **0.7574**; `CORTE_MEDIO_ALTO_RADAR` 0.9233 (igual). |
| `src/test_integracion.py` | 5 tests nuevos (15 en total), ver §5. |
| `src/generar_max_articulos_por_departamento.py` | Se niega a clasificar un `df_procesado_32deptos.pkl` generado antes de la compuerta (mezclaría la escala vieja con el corte nuevo). |

"El texto que ve el modelo" importa: el NLI solo lee los primeros ~500 tokens del cuerpo del
artículo (el 77% de los artículos es más largo). La compuerta mira exactamente ese mismo trozo,
no el artículo entero, para que un grupo armado mencionado al final no abra la compuerta de un
artículo cuyo comienzo habla de otra cosa.

Palabras que **no** abren la compuerta, a propósito (el codebook las define como delincuencia
común): "combo", "banda", "Los Costeños", "Tren de Aragua", porte ilegal de armas, sicariato.

## 3. Por qué se adoptó (evidencia de las fases 5 y 7)

La referencia la dan dos jueces LLM independientes y ciegos (Sonnet y Opus), solo en evaluación.
Un artículo cuenta como positivo si **ambos** dicen que reporta un grupo armado organizado.

| Medida | Antes (V01) | Después (V08) | Fuente |
|---|---|---|---|
| Precisión en los 10 artículos más altos, 4 lugares de trabajo | 0.17 | **0.93** | `experimentos/resultados/juicio_5ind/metricas_5ind.xlsx` |
| Lugares donde el artículo que fija el MAX es correcto | 2 de 4 | **4 de 4** | ídem |
| Precisión en los 10 más altos, holdout Cauca / Chocó / Cundinamarca | 0.70 / 0.50 / 0.20 (media 0.47) | **1.00 / 0.80 / 0.50 (media 0.77)** | `experimentos/resultados/juicio_5ind_holdout/metricas_holdout.csv` |
| Control absurdo ("presencia de osos polares"), MAX en el holdout | 0.67 / 0.52 / 0.71 | 0.61 / 0.42 / 0.71 | ídem |
| Departamentos con control absurdo > 0.766 (32, solo reporte) | 3 | 1 | `.../juicio_5ind_holdout/m4_nacional.csv` |
| AUC contra el estándar de plata (parcialmente circular) | 0.788 | 0.879 | `metricas_5ind.xlsx` |

Acuerdo entre jueces (kappa) en grupos armados: 0.94 en los lugares de trabajo y 0.81 en el
holdout. V08 cumplió los **6 criterios** fijados de antemano en `experimentos/PREREG_5ind_MAX.md`.
El holdout son tres departamentos que no se usaron para diseñar la regla.

## 4. Cortes del radar

Si cambia lo que se mide, hay que recalibrar el umbral (regla 2 del proyecto). Se repitió el
mismo procedimiento de la calibración original: huecos naturales en la distribución de los 32
departamentos, sin mirar la clasificación oficial, comprobando que no se rompa ninguna de las
12 anclas de validez aparente. Con la versión anterior el procedimiento devuelve exactamente
0.766 / 0.9233 (sanidad).

| | Antes | Después |
|---|---|---|
| Cortes | Bajo < 0.766 ≤ Medio < 0.9233 ≤ Alto | Bajo < **0.7574** ≤ Medio < 0.9233 ≤ Alto |
| Clasificación de los 32 | 6 / 19 / 7 | 6 / 19 / 7 (los mismos departamentos) |
| Anclas rotas | 0 | 0 |
| Accuracy contra el DANE (constancia) | 0.344 | 0.344 |
| Spearman contra el DANE (constancia) | −0.1653 | −0.1173 |

El corte bajo se mueve porque San Andrés baja de 0.7376 a 0.7045. El MAX de grupos armados baja
en Quindío (0.996 → 0.553), Caldas (0.978 → 0.725), San Andrés (0.861 → 0) y Guainía (0.640 →
0.011): los artículos que los fijaban no nombran un grupo armado. Fuente:
`experimentos/resultados/juicio_5ind_holdout/cortes_radar.xlsx`.

## 5. Verificación

- **Tests** (`python src/test_integracion.py`, sin GPU): 15/15. Los 5 nuevos comprueban que
  la compuerta abre con ELN, disidencias, Clan del Golfo, "frente 36" o autodefensas y no con
  combo, banda, porte ilegal, sicarios o Tren de Aragua; que solo mira el texto visible; que con
  el tokenizador real ese texto es el mismo que recibe el NLI (texto largo, corto y vacío); que
  `procesar()` la aplica solo a grupos armados; y que la columna auxiliar no altera el radar ni
  aparece en los exportadores.
- **Equivalencia con el experimento** (`experimentos/exp_5ind_max_f8_equivalencia.py`, sin
  GPU, sobre los 11.439 artículos y los scores nacionales ya calculados): la compuerta de
  producción es idéntica a la del experimento artículo por artículo (abre en el 12.2%); el MAX
  de grupos armados y el radar por departamento coinciden con diferencia máxima 0; la clase de
  los 32 coincide uno a uno; el procedimiento de cortes sobre ese radar devuelve 0.7574 /
  0.9233. Salida: `experimentos/resultados/juicio_5ind_holdout/f8_equivalencia.csv`.
- **Revisión independiente** (agente `orquesta-lead`, una vez): aprobado, sin bloqueantes. De 5
  observaciones menores se aplicaron 4; la quinta es una decisión de fusión (§8).

## 6. Excel de lugares antes / después

Carpeta `experimentos/resultados/excel_lugares_f8/` (script
`experimentos/exp_5ind_max_f8_excel_lugares.py`, sin GPU). Un archivo por lugar y versión:
`radar_resumen_<Lugar>_antes_V01.xlsx` y `radar_resumen_<Lugar>_despues_V08.xlsx`.

Formato: el de los `radar_resumen_*.xlsx` que vio la profesora (hoja `Resumen`: Dimensión,
Indicador, Score 0–100, URL del artículo que fija el máximo, 26 filas en el orden de los bloques
A–E). Se añadió una hoja `Radar` con el valor del radar, la clase y los cortes usados, que los
originales no traían.

| Lugar | Artículos | Radar antes | Clase (corte 0.766) | Radar después | Clase (corte 0.7574) | Grupos armados |
|---|---|---|---|---|---|---|
| Maicao | 1.101 | 0.9625 | Alto | 0.9624 | Alto | 98 → 98; el artículo pasa de "Maicao fortalece su seguridad… contra el crimen" a "…esclarecer masacre en Maicao que dejó cinco víctimas" |
| Oicatá | 32 | 0.6688 | Bajo | 0.6437 | Bajo | 65 → 0: el máximo era un hurto; Oicatá no tiene artículos sobre grupos armados |
| Paraguachón | 77 | 0.8188 | Medio | 0.8188 | Medio | 99 → 99, mismo artículo (un positivo) |

Solo cambia la fila de grupos armados; ningún lugar cambia de clase.

**Diferencia con los Excel de la profesora.** El "antes" regenerado no coincide con sus archivos
en 26 de 78 celdas (Maicao 9, Oicatá 3, Paraguachón 14), y en todas el valor regenerado es
mayor. Sus 69 artículos top están en nuestro corpus, y nuestro score para cada uno coincide con
el suyo (±0.5 por redondeo): sus Excel se generaron sobre **un subconjunto** de los artículos
que tenemos hoy (probablemente una descarga anterior de la aplicación). Además, sus archivos
dejan vacía la URL en algunos scores bajos (≤ 7); los regenerados la ponen siempre que el score
sea mayor que 0. Detalle celda a celda: `comparacion_antes_despues.csv` en la misma carpeta.

## 7. Limitaciones

- La compuerta depende de una lista fija de nombres. Un grupo armado que no esté en la lista (o
  que la prensa nombre de otra forma) no abre la compuerta y ese artículo puntúa 0.
- La compuerta decide si el artículo **nombra** un grupo; el NLI sigue decidiendo si habla de su
  presencia. Un artículo que nombra al ELN por otro motivo puede seguir puntuando alto.
- La referencia son jueces LLM, no personas; el acuerdo alto (kappa 0.81–0.94) la hace creíble,
  no infalible. El holdout son 3 departamentos y 94 artículos juzgados.
- Con 32 departamentos, la accuracy y el Spearman no distinguen esta versión de la anterior;
  se reportan solo como constancia.

## 8. Pendiente

1. **Revisión del usuario** de la rama `hipotesis-5ind-max`. Sin push ni merge sin aprobación.
2. **Decisión de fusión:** `CLAUDE.md` (reglas 5–6), `README.md` y `explicacion_alexa.md` dicen
   que la rama no tiene `experimentos/`, pero `hipotesis-5ind-max` sí lo tiene (los informes ya
   viven en `informes/`, fuera de `experimentos/`). Si `experimentos/` entra en
   `radar-max_Septiembre`, hay que corregir esas reglas; si no, hay que quitar las referencias a
   `experimentos/` de los documentos que se entregan.
3. **Segunda ronda** para conflicto territorial, desplazamiento forzado, rechazo a proyecto y
   exclusión de beneficios económicos (propuesta, no aprobada): compuertas de palabras clave y
   controles específicos antes que reescribir frases; nuevo muestreo para exclusión (0 casos
   reales en 659 artículos juzgados). Detalle en `contexto/11_relevo_5ind_MAX.md`.
4. Re-puntuar los 32 departamentos con el código de producción (pendiente desde antes; ~4 h GPU).

## Anexo — Trazabilidad

| Elemento | Dónde |
|---|---|
| Commits | `062ab20` (promoción, tests, equivalencia, Excel), `50a553a` (correcciones de la revisión) |
| Estado previo protegido | etiqueta local `base-26ind-f7` (705a557) |
| Registro de decisiones | `contexto/08_log_decisiones.md`, entradas [2026-09-22] F7, F8 y revisión de F8 |
| Scripts | `experimentos/exp_5ind_max_f8_equivalencia.py`, `experimentos/exp_5ind_max_f8_excel_lugares.py` |
| Resultados | `experimentos/resultados/juicio_5ind_holdout/f8_equivalencia.csv`, `experimentos/resultados/excel_lugares_f8/` |
