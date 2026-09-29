# Informe 11 — ¿Conviene reintegrar el pre-filtro de relevancia social al radar?

Fecha: 2026-09-28 · Rama: `hipotesis-5ind-max` (commits locales, sin push ni merge) ·
Commits: `3849793` (pre-registro, congelado antes de calcular), `374cb90` (resultados y registro),
`1d81a30` (scripts de la recorrida de los lugares), `0426e22` (recorrida de los 4 lugares) y el que
añade este informe · Antecedentes: `informes/09_informe_avances_rama_hipotesis_5ind_max.md`,
`informes/10_informe_resumen_consolidado_01-09.md` y las entradas [2026-08-31] y [2026-09-28] de
`contexto/08_log_decisiones.md`.

## 1. Resumen

- Se midió si conviene volver a poner, antes de calcular los 26 indicadores, un filtro de
  **relevancia social**: si un artículo obtiene menos de 0.85 en la frase «Hay un conflicto, una
  afectación o un riesgo que afecta a una comunidad», se trata como irrelevante y queda en 0 en los
  26 indicadores. Se había rechazado el 2026-08-31; se reabrió porque desde entonces la agregación es
  MAX y hay jueces que permiten medir la cabeza del ranking.
- **Decisión: no se reintegra.** De los cuatro criterios fijados antes de medir, fallan tres (el radar
  nacional no mejora frente al oficial, la pérdida de capacidad de ordenar del 2026-08-31 se reproduce
  exacta y la cabeza del ranking no mejora con los jueces) y pasa uno, con poca holgura.
- **El radar casi no cambia.** El filtro deja en 0 el 12.6 % de los 11.439 artículos, pero el MAX solo
  cambia en 51 de las 832 combinaciones departamento × indicador, 10 de ellas en más de 0.05 y ninguna
  llega a 0. Con los cortes vigentes no cambia la clase de ningún departamento (6 Bajo / 19 Medio / 7 Alto).
- **Por qué no ayuda.** De los 225 puestos de los diez primeros artículos de cada indicador y lugar donde
  hay jueces, el filtro saca 27: 26 que no son casos confirmados y 1 que sí lo es (el primero de grupos
  armados en Chocó, con puntaje social 0.049). Como los reemplazos tampoco son casos confirmados, la
  precisión no sube; y el filtro cuesta capacidad de ordenar.
- **Los cuatro lugares**, vueltos a correr con la producción tal cual, dan exactamente lo mismo que el 1 de
  septiembre: Antioquia (2023) 0.9354 Alto, Maicao 0.9625 Alto, Oicatá 0.6688 Bajo y Paraguachón 0.6801 Bajo.
  Los tests de integración pasan 10/10.
- **No cambia nada de producción:** ni `src/`, ni los cortes 0.766 / 0.9233, ni la agregación MAX, ni los
  26 indicadores.

## 2. La pregunta y por qué se volvió a abrir

El 2026-08-31 se rechazó el filtro (log [2026-08-31]): con el umbral 0.85, el AUC —la probabilidad de que
un artículo que sí trata el tema quede por encima de uno que no— bajaba en los dos indicadores que tienen
«estándar de plata» (etiquetas por palabras clave): −0.053 en grupos étnicos y −0.027 en grupos armados.

Se reabre porque hay dos hechos nuevos (regla 10 del proyecto: solo se reabre con evidencia nueva):

1. La agregación pasó de P75 a **MAX** (el radar toma, para cada indicador y lugar, el puntaje más alto
   entre todos los artículos y promedia los 26 máximos). Bajo MAX solo cuenta la cabeza del ranking, y el
   efecto del filtro sobre el radar bajo MAX nunca se había medido.
2. Hay una **referencia nueva de jueces**: 940 artículos que dos modelos de lenguaje (`juez-a`, `juez-b`)
   leyeron a ciegas, sin ver ningún puntaje; el caso es «confirmado» si los dos dicen SÍ. Cubre 5 de los
   26 indicadores y permite medir si los primeros artículos de cada ranking son casos reales.

La regla 15 («de cada indicador solo se cambia la hipótesis») prohibiría añadir este cálculo. El usuario
decidió el 2026-09-28 admitir el filtro como **excepción si ganaba**, calculando el puntaje social por dentro
y sin columna nueva en la salida; la regla sigue valiendo para los 26 indicadores. Si el veredicto hubiera
sido reintegrar, no se habría tocado `src/` sin su aprobación.

## 3. Qué es el pre-filtro, en lenguaje llano

Cada artículo se compara con 26 frases (una por indicador) con un modelo de inferencia de lenguaje (NLI) que
devuelve qué tan seguro está de que el artículo «implica» la frase. El filtro añade una pregunta general antes
de todo eso: *«¿Hay un conflicto, una afectación o un riesgo que afecta a una comunidad?»*. Si la seguridad es
menor de 0.85, el artículo se considera irrelevante y sus 26 puntajes pasan a 0.

La idea es que un artículo sin relación con el tema (deportes, farándula) no fije el máximo de ningún
indicador. El riesgo es el contrario: descartar artículos que sí importan porque su texto no «suena» a
conflicto. Ejemplo medido: *«Chocó: 79 % de los confinamientos y el segundo con más desplazamientos»* es un caso
confirmado de presencia de grupos armados (el primero del ranking en Chocó), pero tiene puntaje social 0.049 y
el filtro lo elimina (fuente: `experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx`, hoja `choco_GA_top10`).

## 4. Cómo se decidió

El diseño y los criterios se escribieron **antes de calcular** (`experimentos/PREREG_prefiltro_max.md`,
commit `3849793`). Todo se hizo sin volver a puntuar el corpus nacional; la única GPU fue para dar a los 4 lugares
el puntaje social y el de la frase sin sentido (`experimentos/exp_prefiltro_gpu_lugares.py`). Se comparó siempre
**con y sin filtro**, con el umbral 0.85 como única variable. Se reprodujo primero el resultado del 2026-08-31
(exacto, diferencia máxima 5.6e-17) y se comprobó que, sin filtro, se recupera la producción (21 de 21
chequeos; fuente: `experimentos/resultados/exp_prefiltro_max.xlsx`, hojas `S_sanidad` y `A_reproduccion`).

Se reintegra solo si se cumplen los cuatro criterios; **un empate cuenta como no**:

| Criterio | Qué exige |
|---|---|
| C1 Control absurdo | Que con el filtro no baje la diferencia entre el radar real y el de una frase sin sentido («En este territorio hay colonias de osos polares»), en los 32 departamentos ni en los 4 lugares. Es el control que ya sirvió para rechazar variantes cuyo AUC subía. |
| C2 Radar nacional | Con los cortes Bajo/Medio/Alto recalculados para la distribución con filtro: ninguna de las 12 anclas de validez aparente rota (6 departamentos que nunca deben salir Alto y 6 que nunca deben salir Bajo) y correlación de Spearman con el radar oficial del DANE no menor que sin filtro. |
| C3 Capacidad de ordenar | Si el AUC cae más de 0.04 en algún indicador con referencia, la mejora tiene que venir de la cabeza del ranking medida con jueces (cota inferior: un artículo sin juzgar cuenta como no confirmado). |
| C4 Mejora distinguible | Al menos una métrica cuyo intervalo de confianza del 95 % quede por encima de cero, y que supere lo que el mismo filtro «mejora» en la frase sin sentido. Una subida del Spearman menor de 0.15 no cuenta (con 32 departamentos es ruido). |

## 5. Cuánto cambian el radar y los indicadores

**Artículos que el filtro deja en 0** (fuente: `experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx`, hoja
`enmascarados_por_ambito`):

| Ámbito | Artículos | Enmascarados | % |
|---|---|---|---|
| Nacional (32 departamentos) | 11.439 | 1.442 | 12.6 % |
| Antioquia (2023) | 494 | 65 | 13.2 % |
| Maicao | 1.101 | 113 | 10.3 % |
| Oicatá | 32 | 13 | 40.6 % |
| Paraguachón | 20 | 5 | 25.0 % |

**Radar nacional** (fuente: `exp_prefiltro_max.xlsx`, hojas `F_deptos`, `F_celdas_005`, `F_indicadores`,
`E_radar_nacional`):

- Con los cortes vigentes, **ningún departamento cambia de clase**. El radar baja en 23 de 32 departamentos
  (media −0.0023; la mayor caída, San Andrés y Providencia, −0.0161).
- Con los cortes recalculados para la distribución con filtro (0.7582 / 0.9105, 0 anclas rotas), solo cambia
  Meta (Medio → Alto), y no por el filtro (su radar pasa de 0.9171 a 0.9169) sino porque el corte de arriba baja
  de 0.9233 a 0.9105.
- La correlación con el radar oficial es negativa con y sin filtro: −0.1653 → −0.1712 (la accuracy queda en
  0.3438 en las tres configuraciones). Que sea negativa es una propiedad ya conocida del radar bajo MAX, que crece
  con el número de artículos del departamento (Spearman con el tamaño: +0.884 → +0.889); este experimento ni la
  causa ni la corrige.

**Indicadores.** De 832 combinaciones departamento × indicador, el MAX cambia en 51, en más de 0.05 en 10 y
en ninguna llega a 0. Los tres indicadores más afectados, por la media de |ΔMAX| entre departamentos:

| Indicador | Media de \|ΔMAX\| | Celdas con cambio > 0.05 | Celdas que pasan a 0 |
|---|---|---|---|
| `irregularidad_contractual` | 0.0168 | 2 (Valle del Cauca 0.917 → 0.553; Guaviare 0.885 → 0.712) | 0 |
| `debilidad_institucional` | 0.0093 | 2 (San Andrés 0.844 → 0.601; Amazonas 0.576 → 0.522) | 0 |
| `zonas_proteccion_alimentaria` | 0.0057 | 1 (Risaralda 0.913 → 0.781) | 0 |

## 6. La decisión y su justificación

**No se reintegra el pre-filtro con umbral 0.85.** Resultado por criterio (fuente: `exp_prefiltro_max.xlsx`,
hoja `H_decision` y las indicadas):

| Criterio | Resultado | Número clave | Hoja |
|---|---|---|---|
| C1 Control absurdo | **Pasa**, con poca holgura | Δ de la brecha media: +0.0028 (32 departamentos) y +0.0302 (4 lugares). Por departamento la brecha baja en 19 de 32 (mediana −0.0003) y en 2 de 4 lugares; la media la sostienen Atlántico (+0.0840), Boyacá (+0.0770) y Oicatá (+0.1227), donde el filtro sacó el artículo que fijaba el máximo de la frase sin sentido | `D_brecha_dep`, `D_brecha_lugar` |
| C2 Radar nacional | **Falla** | 0 anclas rotas, pero el Spearman baja de −0.1653 a −0.1712 | `E_radar_nacional` |
| C3 Capacidad de ordenar | **Se dispara** y la cabeza del ranking no compensa | AUC corregido con plata: grupos étnicos 0.8323 → 0.7791 (−0.0531, IC95 % [−0.0662, −0.0402]); grupos armados 0.8232 → 0.7963 (−0.0269, [−0.0355, −0.0191]); con jueces, grupos armados −0.0168 ([−0.0435, +0.0049]) | `A_auc_plata`, `B_auc_jueces` |
| C4 Mejora distinguible | **Falla** | Con jueces (cota inferior, cobertura 100 %): grupos armados en 7 celdas, M1 (¿el artículo que fija el máximo es un caso confirmado?) 5/7 → 4/7 y M2 (precisión entre los 10 primeros) 0.3000 → 0.2857, IC95 % [−0.0429, +0.0429]; en las 23 celdas, M2 0.1130 → 0.1087, IC95 % [−0.0130, +0.0130] | `C_unidades` |

Por qué el filtro no mejora la cabeza del ranking (exploratorio, posterior al pre-registro, no decide;
`experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx`):

- De los 225 puestos de los diez primeros artículos de las 23 celdas con jueces, el filtro saca 27 artículos:
  26 no confirmados y 1 confirmado. Limpia algo de ruido, pero los reemplazos también son no confirmados (la
  referencia tiene pocos casos por celda), así que la precisión no sube; y el único caso que se lleva es el nº 1
  de grupos armados en Chocó.
- En los 759 artículos juzgados de los lugares y del holdout, el filtro enmascara el 13.2 % de los negativos y el
  3.9 % de los positivos de grupos armados (5 de 128), y ninguno de los positivos de rechazo, desplazamiento y
  conflicto. Esa selectividad explica que el AUC contra jueces suba un poco en esos tres (+0.0070, +0.0041 y
  +0.0064). Pero la frase sin sentido también sube (+0.002) y, restada, la mejora no se distingue de cero
  (límites inferiores −0.0008, −0.0014 y −0.0003); en todo caso, con C3 disparada esa vía no cuenta.
- Los puestos que ocupan artículos no confirmados en la cabeza del ranking son, casi todos, artículos socialmente
  relevantes: de 199 puestos, 173 (87 %) pasan el filtro, con una mediana de puntaje social de 0.998 (hoja
  `resumen_top10`). Un filtro general de relevancia no puede corregirlos; es coherente con lo hallado en la ronda 1
  de los 5 indicadores, donde el NLI confirma la forma de la frase más que su objeto.

**Sensibilidad** (descriptiva, no decide; `exp_prefiltro_max.xlsx`, hojas `G_sensibilidad`, `G_sens_B`,
`G_sens_C`): con los umbrales 0.50, 0.65 y 0.75 ninguno pasa los cuatro criterios. C1 falla (la brecha de los
lugares baja 0.0007, 0.0021 y 0.0021) y C4 solo pasa por la vía del AUC con jueces, con mejoras triviales (entre
+0.0009 y +0.0043). No se registra ningún candidato para otro experimento.

## 7. Resultados de los cuatro lugares con la producción actual

Se volvieron a correr los indicadores y el radar de los 4 lugares con `src/` tal cual (hipótesis V2, sin
filtro, sesgo descontado, MAX, cortes 0.766 / 0.9233), sobre `datos/corpus/df_corpus_5lugares.pkl` **sin
regenerarlo** (sha256 `b4ccb0e6122c91b7…` y fecha 2026-09-01T02:11:51 idénticos antes y después; 32.1 min de GPU;
fuente: `experimentos/resultados/exp_prefiltro_correr_lugares.log` y
`resultados/tablas_lugares_max_2026-09-28/corpus_sha256.json`). Comparadas con la corrida del 1 de septiembre
(`resultados/tablas_lugares_max/`), la diferencia es **0** por artículo en los 26 indicadores, en los 104 máximos
por lugar × indicador (con el mismo artículo detrás) y en radar y clase de cada lugar
(`experimentos/resultados/exp_prefiltro_lugares_recorrida.xlsx`, hojas `por_articulo`, `max_lugar_x_indicador`,
`radar_clase`). `python src/test_integracion.py`: 10/10.

| Lugar | Artículos | Radar | Clase | Indicadores con máximo ≥ 0.766 | con máximo ≥ 0.9233 | con máximo 0 | Radar si se aplicara el filtro |
|---|---|---|---|---|---|---|---|
| Antioquia (2023) | 494 | 0.9354 | Alto | 24 de 26 | 21 | 0 | 0.9354 (Alto) |
| Maicao | 1.101 | 0.9625 | Alto | 26 de 26 | 23 | 0 | 0.9614 (Alto) |
| Oicatá | 32 | 0.6688 | Bajo | 14 de 26 | 6 | 3 | 0.6458 (Bajo) |
| Paraguachón | 20 | 0.6801 | Bajo | 13 de 26 | 9 | 3 | 0.6793 (Bajo) |

Fuente de las cuatro primeras columnas: `exp_prefiltro_lugares_recorrida.xlsx`, hojas `radar_clase` y
`resumen_indicadores`; la última: `exp_prefiltro_max.xlsx`, hoja `F_lugares`.

**Indicadores que más pesan.** El radar es el promedio de los 26 máximos, así que cada indicador aporta su máximo
dividido entre 26; pesan más los de máximo más alto (hoja `indicadores_por_peso`).

| Lugar | Cinco de mayor máximo | Tres de menor máximo | Artículos que fijan los tres primeros |
|---|---|---|---|
| Antioquia (2023) | `derechos_vulnerados` 0.998; `conflicto_activo` 0.996; `conflicto_territorial` 0.996; `poblacion_afectada` 0.996; `exclusion_beneficios_economicos` 0.996 | `danos_ambientales` 0.322; `debilidad_institucional` 0.707; `resistencia_territorial` 0.873 | «Medellín aumentó a extremo su nivel de riesgo electoral: MOE»; «Nueva asonada en Antioquia: comunidad sacó a 80 militares de Briceño» (los dos siguientes) |
| Maicao | `derechos_vulnerados` 0.998; `poblacion_afectada` 0.996; `rechazo_proyecto` 0.996; `exclusion_beneficios_economicos` 0.996; `violacion_derechos_humanos` 0.996 | `danos_ambientales` 0.802; `irregularidad_contractual` 0.814; `deficit_participacion_comunitaria` 0.835 | «World Vision entrega agua y formación comunitaria en La Guajira»; «Unidad de Búsqueda recupera 25 cuerpos en cementerio de Riohacha»; «Comunidad bloquea la vía Maicao – Paradero por falta de agua potable y servicio eléctrico» |
| Oicatá | `derechos_vulnerados` 0.990; `exclusion_beneficios_economicos` 0.989; `conflicto_activo` 0.985; `rechazo_proyecto` 0.979; `exclusion_comunidades` 0.953 | `danos_ambientales`, `irregularidad_contractual`, `dano_territorios` (los tres en 0) | «Estos fueron los compromisos acordados tras las protestas en el peaje de Tuta» (1.º y 3.º); «La Unidad de Búsqueda de Personas recuperó diez cuerpos en el cementerio de Oicatá» |
| Paraguachón | `derechos_vulnerados` 0.996; `exclusion_beneficios_economicos` 0.994; `conflicto_territorial` 0.993; `rechazo_proyecto` 0.989; `conflicto_activo` 0.989 | `resistencia_territorial`, `debilidad_institucional`, `danos_ambientales` (los tres en 0) | «Migración Colombia expulsa a venezolana detectada durante trámite médico»; «Tensión del lado venezolano por caso judicial afecta comercio binacional» (2.º y 3.º) |

Dos lecturas, sin ánimo de discutir la agregación:

- Bajo MAX, casi todos los indicadores de Antioquia (24 de 26) y de Maicao (26 de 26) superan el corte Bajo/Medio
  (0.766) por tener cientos de artículos; en Oicatá y Paraguachón, con 32 y 20, hay 3 indicadores en 0 y el radar
  queda en Bajo. Es el efecto de tamaño ya descrito en los informes anteriores, no algo nuevo de este experimento.
- Este cuadro dice qué mueve el radar, no si el artículo que fija cada máximo es un caso real del concepto. En este
  mismo experimento, con jueces, el artículo que fija el máximo es un caso confirmado en solo 6 de las 23 celdas
  (M1 = 0.2609, hoja `C_unidades`), y los informes 01–05 y 08 ya lo habían documentado. Aquí se ve, por ejemplo,
  que el máximo de `exclusion_beneficios_economicos` en Oicatá lo fija un artículo sobre cuerpos recuperados en un
  cementerio y el de Paraguachón uno sobre comercio binacional.

## 8. Limitaciones

- **Cobertura de la referencia.** La plata cubre 2 de los 26 indicadores y los jueces 5 de 26; uno de ellos,
  `exclusion_beneficios_economicos`, no tiene ningún caso confirmado (no medible). En los otros 21 indicadores el
  efecto del filtro solo se ve como un cambio en el radar, sin poder decir si es mejor o peor.
- **Bases pequeñas.** Oicatá tiene 32 artículos (sin casos confirmados de ningún indicador) y Paraguachón 20 (77 en
  la convención del plan, que repite artículos de Maicao). Con jueces hay solo 13 celdas (indicador × lugar) con algún
  caso confirmado; un cambio de 0.14 en M1 equivale a una sola celda.
- **La referencia favorece a la producción actual.** Los 940 juzgados se eligieron, en su mayor parte, entre los
  primeros de cada indicador sin filtro. Con filtro pueden entrar artículos sin juzgar; por eso se reportan dos cotas. Coincidieron (la
  cobertura fue 100 %), pero el pool sigue siendo un subconjunto del corpus.
- **Estadística.** Los intervalos son bootstrap por artículo y no consideran la dependencia entre artículos del
  mismo medio o hecho. Con 32 departamentos solo una diferencia de Spearman de 0.15 o más se distingue del ruido.
  No se corrigió por comparaciones múltiples: el criterio del encargo es «al menos una métrica».
- **C1 pasa por la media, no por unidad.** Como se explicó en la sección 6, la brecha baja en la mayoría de los
  departamentos; no debe leerse como «el filtro mejora el control absurdo».
- **Un solo umbral decide** (0.85); los demás son sensibilidad.
- Los 22 artículos juzgados en la prueba del modelo NLI no se usaron (no estaban en las fuentes del encargo).

## 9. Qué sigue

- **Nada que implementar.** Producción no cambia. El pre-filtro social queda cerrado también bajo MAX; no se
  reintenta sin evidencia nueva medida (log [2026-09-28]).
- **Propuesta menor, no aplicada:** añadir una línea al comentario de `src/Transformer_optimo.py:168-175`
  («reevaluado bajo MAX el 2026-09-28: sigue rechazado, ver `contexto/08_log_decisiones.md`»). Solo se hace si el
  usuario lo pide; `src/` no se tocó.
- **Lo que sigue abierto** (no lo resuelve este experimento): ampliar la referencia, con más casos confirmados y más
  indicadores con estándar. El efecto del tamaño del corpus sobre el radar es una propiedad conocida de la
  agregación MAX elegida; no se reabre aquí.

## 10. Archivos de origen

- Pre-registro: `experimentos/PREREG_prefiltro_max.md`. Resultados y lectura: `experimentos/RESULTADOS_prefiltro_max.md`.
- Scripts: `experimentos/exp_prefiltro_gpu_lugares.py`, `exp_prefiltro_max.py`, `exp_prefiltro_max_mecanismo.py`,
  `exp_prefiltro_correr_lugares.py`, `exp_prefiltro_comparar_lugares.py`.
- Resultados: `experimentos/resultados/exp_prefiltro_max.xlsx` (hojas A–H), `exp_prefiltro_max_mecanismo.xlsx`,
  `exp_prefiltro_lugares_recorrida.xlsx` y los logs `exp_prefiltro_*.log`.
- Datos (locales, no versionados): `datos/scores/scores_prefiltro_lugares.pkl` (nuevo),
  `resultados/tablas_lugares_max_2026-09-28/` (corrida nueva) y `resultados/tablas_lugares_max/` (1-sep).
- Registro de la decisión: `contexto/08_log_decisiones.md`, entrada [2026-09-28].
