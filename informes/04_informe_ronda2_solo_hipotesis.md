# Informe — Segunda ronda: reescritura de hipótesis de 5 indicadores (fase A)

Fecha: 2026-09-23 · Rama: `hipotesis-5ind-max` (commits locales, sin push ni merge) ·
Pre-registro congelado: 219ac1b · Fase A: 63364db · Antecedentes:
`informes/01_informe_5ind_MAX_fases_0-7.md` y `informes/03_informe_reversion_f8.md`.

## 1. Resumen

- Con la regla vigente (de cada indicador solo se puede cambiar la hipótesis, es decir, la
  frase que evalúa el modelo NLI), se probaron **25 frases candidatas** para 5 indicadores, 5
  por indicador: 15 nuevas y 10 paráfrasis de la primera ronda.
- **Ninguna pasa el criterio de adopción** fijado antes de medir. La mejor precisión fue 0.38
  (grupos armados), frente al 0.60 exigido.
- Los 5 indicadores **conservan su hipótesis vigente**. Producción no cambia: sigue siendo
  exactamente la rama `radar-max_Septiembre`, con los mismos cortes (Bajo < 0.766 ≤ Medio <
  0.9233 ≤ Alto) y la misma clasificación (6 Bajo / 19 Medio / 7 Alto). El radar sigue con
  los 26 indicadores.
- `exclusion_beneficios_economicos` **no se puede medir con este corpus**: en 940 artículos
  juzgados no hay ni un caso en que los dos jueces coincidan. Queda pendiente de decisión; no se
  retira.
- Como no hubo frases finalistas, la fase B prevista (escala nacional, departamentos de control
  y recalibración de cortes) no se ejecuta.

## 2. Qué se probó

Los 5 indicadores son exclusión de beneficios económicos, rechazo a proyecto, desplazamiento
forzado, conflicto territorial y presencia de grupos armados. Para cada uno se probó su frase
vigente y 5 alternativas: 3 nuevas y 2 paráfrasis de la primera ronda que nunca se habían
evaluado solas. Textos en `experimentos/hipotesis_5ind_max_r2.py`.

Cada frase llevó su **control absurdo**: la misma frase con «osos polares» en lugar del objeto.
Por ejemplo, «Familias fueron desplazadas de sus veredas **por los osos polares**». Una frase
útil debe puntuar alto en noticias que reportan el hecho y bajo en su versión absurda.

## 3. Cómo se midió

- **Datos:** los 4 lugares de trabajo de la primera ronda. Son 1.647 artículos: Antioquia 494,
  Maicao 1.101, Oicatá 32 y Paraguachón 77. El modelo NLI puntuó en 46 minutos de GPU 35
  frases: las 15 nuevas, sus 15 versiones absurdas y las 5 vigentes, que sirvieron para
  comprobar que se reproducía la primera ronda. Las paráfrasis ya estaban puntuadas.
- **Referencia:** dos jueces LLM (Claude Sonnet y Claude Opus) que leen cada artículo sin saber
  de dónde viene ni qué frase lo eligió. Un artículo cuenta como positivo solo si **los dos**
  dicen SÍ. Se reutilizaron las 659 etiquetas de la primera ronda y se juzgaron 281 artículos
  nuevos: 940 en total. Además se volvieron a juzgar 40 artículos de la primera ronda como
  control, y las etiquetas coinciden entre el 97 y el 100 % por indicador.
- **Criterio, fijado antes de medir** (`experimentos/PREREG_5ind_MAX_r2.md` §4). Una frase
  reemplaza a la vigente solo si cumple todo esto:
  - al menos 6 de los 10 artículos que más puntúa en cada lugar son positivos de verdad (en
    promedio), y eso supera en 0.20 a la vigente;
  - el artículo que fija el máximo del lugar es correcto en al menos 3 de los 4 lugares, o en
    todos los lugares que tienen algún positivo;
  - no empeora la coherencia con el corte del radar;
  - en cada lugar, su control absurdo queda por debajo de 0.766 y no supera en más de 0.05 al de
    la vigente;
  - en grupos armados, no pierde capacidad de separar artículos (AUC).

## 4. Resultados

Precisión = proporción de positivos entre los 10 artículos con score más alto por lugar,
promediada en los 4 lugares. Fuente: `experimentos/RESULTADOS_5ind_MAX_r2.md`.

| Indicador | Positivos (A/M/O/P) | Vigente | Mejor alternativa | Su control absurdo | Veredicto |
|---|---|---|---|---|---|
| Exclusión de beneficios | 0/0/0/0 | 0.00 | todas 0.00 | — | no medible |
| Rechazo a proyecto | 1/3/0/0 | 0.00 | 0.25 (*) | bajo (pasa) | no pasa |
| Desplazamiento forzado | 10/1/0/0 | 0.05 | 0.07 | 0.99 / 0.98 (falla) | no pasa |
| Conflicto territorial | 10/8/0/3 | 0.07 | 0.26 | 0.78–0.89 en 3 lugares (falla) | no pasa |
| Presencia de grupos armados | 42/45/0/5 | 0.17 | 0.38 | peor que la vigente (falla) | no pasa |

A/M/O/P = Antioquia / Maicao / Oicatá / Paraguachón. (*) Un lugar sin positivos vale 1 solo
si la frase no puntúa ningún artículo. El 0.25 de rechazo sale entero de Oicatá: en los lugares
que sí tienen positivos, su precisión es 0.00. Las mejores alternativas fueron:
- **Rechazo:** «La comunidad rechaza que construyan una mina, una represa o un parque eólico.»
- **Desplazamiento:** «Familias fueron desplazadas de sus veredas por la violencia armada.»
- **Conflicto:** «Grupos armados ilegales se enfrentan entre sí por el control de esta zona.»
- **Grupos armados:** «Hay presencia de guerrilla o paramilitares en este territorio.»

Ninguna de las 25 alcanza la precisión mínima de 0.60. Además, 20 de las 25 fallan el control
absurdo. En 18 de ellas, la versión con «osos polares» sigue superando 0.766, el corte
Bajo/Medio del radar; en las otras 2 (grupos armados), supera en más de 0.05 al control de la
vigente.

## 5. Exclusión de beneficios económicos

Como en la primera ronda no había aparecido ningún caso, esta vez se juzgaron **todos** los
artículos del corpus que mencionan regalías, compensaciones, consulta previa, indemnizaciones o
«no han recibido»: 237 artículos. El resultado sigue siendo 0 casos con acuerdo de los dos
jueces en 940 juzgados. En esta ronda hubo 8 casos dudosos o con un solo SÍ, todos fuera de los
4 lugares:
por ejemplo, pérdida de regalías de un municipio por la salida de una petrolera en Caquetá.
Con menos de 5 casos, el pre-registro declara el indicador **no medible con este corpus**. Qué
hacer con él lo decide el responsable del proyecto; mientras tanto sigue en el radar con su
frase vigente.

## 6. Qué significa

- En las dos rondas se probaron 12 variantes y 25 frases. Cuando solo se cambia la frase, la
  mejor precisión es 0.38. El modelo NLI tiende a **confirmar la forma de la frase sin mirar su
  objeto**: en desplazamiento, cambiar «por la violencia armada» por «por los osos polares» deja
  el máximo prácticamente igual (de 1.00 / 0.98 a 0.99 / 0.98 en Antioquia y Maicao).
- En la primera ronda, la única mejora que pasó todos los criterios fue una regla de palabras
  clave sobre grupos armados (precisión de 0.17 a 0.93), y la regla vigente no permite usarla
  (informe 03).
- **Conclusión:** con este modelo y este corpus, reescribir la hipótesis no mejora estos 5
  indicadores. El resultado negativo quedó registrado para no repetir la prueba.

## 7. Limitaciones

- Solo 4 lugares, y dos son pequeños. Oicatá no tiene ningún positivo en ningún indicador, así
  que ahí una frase solo suma si no puntúa nada. Por eso se reportó también la precisión contando
  solo los lugares con positivos: la mejor es 0.50, en grupos armados, y sigue por debajo del
  0.60 exigido.
- Pocos positivos en rechazo (4) y ninguno en exclusión.
- Los jueces son modelos de lenguaje, no personas. Su acuerdo es alto (kappa 0.87–0.94) en
  desplazamiento, conflicto y grupos armados, moderado en rechazo (0.44) y nulo en exclusión.
- Solo se juzgan los artículos que alguna frase pone entre sus 15 primeros. Un positivo que
  ninguna frase suba no se ve.

## 8. Pendientes (decisión del responsable)

1. Qué hacer con `exclusion_beneficios_economicos`, que resultó no medible.
2. Fusión de esta rama a `radar-max_Septiembre`, y si entra o no la carpeta `experimentos/`.
3. Push y merge de la rama.

## Anexo — Trazabilidad

| Elemento | Dónde |
|---|---|
| Pre-registro (criterios fijados antes de medir) | `experimentos/PREREG_5ind_MAX_r2.md` |
| Frases probadas | `experimentos/hipotesis_5ind_max_r2.py` |
| Tabla completa | `experimentos/RESULTADOS_5ind_MAX_r2.md`, `experimentos/resultados/juicio_5ind_r2/metricas_r2.xlsx` |
| Scripts | `experimentos/exp_5ind_max_r2_atomicas.py` (GPU), `exp_5ind_max_r2_pool.py`, `exp_5ind_max_r2_metricas.py` |
| Etiquetas de los jueces | `experimentos/resultados/juicio_5ind_r2/etiquetas_a/`, `etiquetas_b/`, `referencia.csv` |
| Decisión | `contexto/08_log_decisiones.md`, entradas [2026-09-23] «2a ronda, fase A» y siguientes |
