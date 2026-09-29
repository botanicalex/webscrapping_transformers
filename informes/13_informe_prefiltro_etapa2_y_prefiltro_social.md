# Informe 13 — Pre-filtro por indicador, etapa 2: resultado del primer tramo, y por qué no se reactiva el pre-filtro social

Fecha: 2026-09-29 · Rama: `hipotesis-5ind-max` (commits locales, sin push ni merge) ·
Commits: `da30a63` (pre-registro, congelado antes de calcular), `9e7a3cb` (confirmación de las listas), `6708fb8` (tasas de
apertura, GPU de controles, pool y lotes), `118e633` (juicio), `600c5d3` (análisis y veredicto), `95cf1ec` (registro) y el que
añade este informe · Antecedentes: `informes/11_informe_prefiltro_social_max.md`, `informes/12_informe_prefiltro_por_indicador.md`
y las entradas [2026-08-31], [2026-09-28] y [2026-09-29] de `contexto/08_log_decisiones.md`.

## 1. Resumen

- **Pedido de partida.** Se busca un pre-filtro que se aplique a **todos** los indicadores. Hay dos maneras de hacerlo: un filtro
  **social general** (una sola pregunta para los 26) o un filtro **por indicador** (cada indicador exige que su objeto aparezca en
  el texto). El general se midió dos veces y se rechazó las dos (sección 2). El por indicador es el mecanismo único que se adoptó:
  está en producción para 2 indicadores (informe 12) y este informe mide su extensión a 6 más.
- **Por qué no se reactiva el pre-filtro social:** con el umbral calibrado (0.85) no cambia la clase de ningún departamento, no mejora
  la cabeza del ranking con jueces, cuesta capacidad de ordenar (reproducido exacto) y empeora la correlación con el radar oficial.
  La causa es de fondo: el 87 % de los artículos erróneos que ocupan los primeros puestos **son** socialmente relevantes (mediana de
  puntaje social 0.998), así que una pregunta general de relevancia no puede sacarlos. Con umbrales más bajos (0.50, 0.65, 0.75)
  tampoco pasa.
- **Etapa 2, tramo 1 (6 indicadores):** amenaza a líderes, amenazas e intimidación, protesta social, violación de derechos
  humanos, reasentamiento y daños ambientales. Diseño y reglas fijados antes de calcular; listas escritas sin mirar datos y
  confirmadas por el usuario; juicio ciego por dos jueces nuevos sobre 356 artículos.
- **Resultado: no se adopta ninguna lista nueva.** Reasentamiento y daños ambientales no tienen casos suficientes para medirse
  (4 y 3 confirmados). De los otros 4, ninguno cumple las cuatro condiciones; el más cercano, amenazas e intimidación, mejora mucho
  la precisión (+0.43 en los lugares, +0.27 fuera de muestra) pero falla el control absurdo: el modelo sigue diciendo «sí» con la
  misma fuerza cuando el objeto de la frase es absurdo.
- **Producción no cambia:** sigue el pre-filtro por indicador en grupos armados y desplazamiento, cortes 0.7572/0.9233, 26
  indicadores, agregación MAX.
- **Trazabilidad del MAX** (el artículo que el radar muestra como evidencia de cada indicador): con las listas, el artículo que fija
  el máximo es un caso confirmado en 14 de 42 combinaciones lugar × indicador, frente a 8 sin ellas. Es un dato de reporte: no
  compensa el fallo del control absurdo.

## 2. Por qué no se vuelve a activar el pre-filtro social

### 2.1 Qué es

Antes de puntuar los 26 indicadores, cada artículo se somete a una pregunta general: *«Hay un conflicto, una afectación o un riesgo
que afecta a una comunidad»*. Si el modelo está seguro en menos de 0.85, el artículo se da por irrelevante y sus 26 puntajes pasan a
0. Es un único interruptor para todo el radar.

### 2.2 Cuántas veces se midió y con qué

| Fecha | Agregación | Evidencia | Resultado |
|---|---|---|---|
| 2026-08-31 | P75 | AUC contra el estándar de plata (2 indicadores) | Rechazado: el AUC baja en los dos |
| 2026-09-28 | MAX (la actual) | Pre-registro con 4 criterios; plata, jueces (940 artículos, 5 indicadores), control absurdo y radar nacional | Rechazado: fallan 3 de 4 criterios |

La segunda medición se hizo porque había hechos nuevos (el cambio a MAX y la referencia de jueces). El usuario había aceptado
incorporarlo como excepción a la regla 15 si ganaba; no ganó (informe 11; `experimentos/RESULTADOS_prefiltro_max.md`).

### 2.3 Los cuatro motivos, con sus números

Fuente: `experimentos/resultados/exp_prefiltro_max.xlsx` (hojas indicadas) y log [2026-09-28].

1. **No mejora el radar frente al oficial (criterio C2, falla).** La correlación de Spearman con el radar del DANE baja de
   −0.1653 a −0.1712 (`E_radar_nacional`). Con los cortes vigentes ningún departamento cambia de clase; con los recalculados solo
   cambia Meta, y por el corte, no por el filtro (su radar pasa de 0.9171 a 0.9169).
2. **Cuesta capacidad de ordenar (criterio C3, se dispara).** El AUC —la probabilidad de que un artículo que trata el tema quede por
   encima de uno que no— baja en grupos étnicos de 0.8323 a 0.7791 (−0.0531, IC95 % [−0.0662, −0.0402]) y en grupos armados de 0.8232
   a 0.7963 (−0.0269, [−0.0355, −0.0191]) (`A_auc_plata`). Es la misma pérdida medida el 2026-08-31, reproducida con una diferencia
   de 5.6e-17.
3. **No mejora la cabeza del ranking, que es lo único que ve el MAX (criterio C4, falla).** Con jueces, en grupos armados el artículo
   que fija el máximo es un caso confirmado en 5 de 7 celdas sin filtro y en 4 de 7 con filtro; la precisión entre los 10 primeros
   pasa de 0.3000 a 0.2857 (IC95 % [−0.0429, +0.0429]); en las 23 celdas con jueces, de 0.1130 a 0.1087 (`C_unidades`). El único caso
   que cambia es el primero de grupos armados en Chocó —un caso confirmado («Chocó: 79 % de los confinamientos…») con puntaje social
   0.049— que el filtro **elimina**.
4. **El control absurdo pasa solo con poca holgura (criterio C1).** La diferencia media entre el radar real y el de una frase sin
   sentido sube +0.0028 en los 32 departamentos, pero baja en 19 de ellos; la media la sostienen tres casos (Atlántico, Boyacá, Oicatá)
   (`D_brecha_dep`, `D_brecha_lugar`).

Regla del pre-registro: se reintegra solo si se cumplen los cuatro; un empate cuenta como no. Se cumple uno.

### 2.4 La causa de fondo: los errores del radar sí son «sociales»

El problema que se quería resolver son los artículos que ocupan los primeros puestos de un indicador sin tratar su tema. El
análisis de esos artículos (`experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx`, hoja `resumen_top10`) muestra que:

- De los 199 puestos de los diez primeros ocupados por artículos no confirmados, **173 (87 %) pasan el filtro social**, con una
  mediana de puntaje social de **0.998**. Para el modelo son noticias de conflicto o afectación a comunidades; lo que falla es que
  no tratan el hecho concreto del indicador en cuyo ranking aparecen.
- De los 225 puestos de los diez primeros, el filtro saca 27: 26 no confirmados y 1 confirmado. Los reemplazos son, a su vez, no
  confirmados, así que la precisión no sube.

Un filtro que pregunta «¿es esto social?» no puede distinguir «es social pero de otro tema». Por eso el error es **específico de cada
indicador**, y la respuesta es el pre-filtro por indicador (informe 12), no el general.

### 2.5 No hay umbral que lo salve

Con 0.50, 0.65 y 0.75 ninguno cumple los cuatro criterios: el control absurdo falla en los lugares (la diferencia baja 0.0007, 0.0021 y
0.0021) y la única mejora que aparece es trivial (AUC con jueces entre +0.0009 y +0.0043) (`G_sensibilidad`, `G_sens_B`, `G_sens_C`).

### 2.6 Qué aporta la etapa 2 a esta conclusión

La etapa 2 **no volvió a medir** el filtro social. Lo que muestra es coherente con el diagnóstico: incluso una lista de palabras
**propia de cada indicador**, mucho más específica que una pregunta general, no basta en 4 de los 4 indicadores medibles para que el
«sí» del modelo dependa del objeto (sección 4). Un filtro general, más grueso, tiene menos margen todavía.

### 2.7 Qué haría falta para reabrirlo

Por la regla 10 del proyecto, solo evidencia nueva medida: por ejemplo, otro modelo de lenguaje, otra frase social pre-registrada o
una referencia que cubra más indicadores. Repetir la misma medición con otro umbral ya está descartado (2.5).

## 3. Etapa 2: qué se hizo

- **Pre-registro** (`experimentos/PREREG_prefiltro_indicador_e2.md`), congelado antes de calcular. Decisiones del usuario: un primer
  tramo de 6 indicadores; como máximo 3 listas nuevas (con muchas pruebas, alguna pasaría por azar); techo de apertura del 50 %; sin
  lista placebo. Las 6 listas, escritas solo con el texto de cada hipótesis, se confirmaron una a una (excepción a la regla 15).
- **Tramo elegido sin datos:** indicadores con objeto concreto, vocabulario poco común en la prensa y relación con «cuánto estorba».
  Quedaron fuera grupos étnicos (su evaluación contra la plata sería circular), incentivos económicos (vocabulario como el de exclusión,
  que ya falló) y los de vocabulario muy común.
- **Techo de apertura:** una lista que aparece en más de la mitad de los 11.439 artículos no filtra nada. Ninguna lo superó
  (reasentamiento 0.5 %, daños ambientales 6.9 %, protesta 9.6 %, amenazas 10.6 %, violación de DDHH 20.5 %, amenaza a líderes 22.6 %;
  `experimentos/resultados/juicio_prefiltro_e2/aperturas.csv`).
- **Referencia:** dos jueces nuevos (`juez-c`, `juez-d`), ciegos, con un criterio escrito por indicador; un caso es confirmado si los
  dos dicen SÍ. Juzgaron los 356 artículos que ocupan los diez primeros puestos de cada indicador, con y sin filtro, en 7 lugares.
  Coincidencia entre jueces (kappa) de 0.75 a 0.95 (`consolidacion.csv`). Una instancia de un juez recortó 26 textos; esos dos lotes se
  volvieron a juzgar completos.
- **Muestra:** los 4 lugares (Antioquia, Maicao, Oicatá, Paraguachón) y, fuera de muestra, Cauca, Chocó y Cundinamarca.
- **GPU:** 11.7 minutos para las frases de control absurdo de los 6 indicadores; la verificación contra producción dio una diferencia
  de 9.8e-07.
- **Regla de inclusión** (la de la etapa 1), las cuatro a la vez: (a) la precisión de los diez primeros sube al menos 0.20 en los
  lugares; (b) sube al menos 0.10 fuera de muestra, con todo juzgado; (c) el control absurdo no empeora; (d) ninguna incoherencia
  nueva entre el máximo y los casos confirmados.

## 4. Resultados

Fuente: `experimentos/RESULTADOS_prefiltro_e2.md` y `experimentos/resultados/exp_prefiltro_e2.xlsx`.

**Indicadores sin casos suficientes:** reasentamiento (4 confirmados) y daños ambientales (3). Con menos de 5 se declaran «no medibles»
y pasan sin filtro.

**Los cuatro medibles:**

| Indicador | (a) precisión, lugares | (b) precisión, fuera de muestra | (c) control absurdo | (d) coherencia | Decisión |
|---|---|---|---|---|---|
| Amenaza a líderes | 0.03 → 0.08 (+0.05), no | +0.10, sí | falla | sí | no entra |
| Amenazas e intimidación | 0.28 → 0.70 (+0.43), sí | +0.27, sí | falla | sí | no entra |
| Protesta social | 0.74 → 0.78 (+0.04), no | +0.20, sí | sí | 1 incoherencia nueva | no entra |
| Violación de DDHH | 0.05 → 0.18 (+0.13), no | 0.00, no | falla | 1 incoherencia nueva | no entra |

**Qué significa el fallo del control absurdo.** Para cada indicador existe una frase gemela con el objeto cambiado por algo absurdo
(«Hubo amenazas, intimidación u hostigamiento contra osos polares»). Si la lista hiciera que el «sí» del modelo dependa del objeto, la
distancia entre el máximo real y el de la gemela tendría que crecer o, al menos, no bajar. En amenazas e intimidación **baja 0.114** de
media en los lugares: los artículos que quedan tras el filtro hablan de amenazas y el modelo afirma casi igual «amenazas contra
personas» que «amenazas contra osos polares». La lista mejora qué artículos llegan arriba, pero el puntaje sigue sin medir el objeto.
Es el mismo hallazgo de la ronda 1 («el modelo confirma la forma de la frase, no su objeto») y la misma razón por la que conflicto
territorial quedó fuera en la etapa 1.

**Radar nacional, cada lista sola** (informativo; ninguna llegó a este paso por la regla): las cuatro aumentan la dependencia del
radar respecto del número de artículos del departamento (de +0.8640 a entre +0.8658 y +0.8702) y tres de las cuatro bajan la correlación
con el radar oficial (hasta −0.1085). Ninguna rompe las anclas de validez.

## 5. Trazabilidad del MAX

El radar puede mostrar, para cada lugar e indicador, el artículo que fija el máximo (título, enlace, periódico, fecha). Producción ya lo
guarda. Se midió si ese artículo es un caso confirmado por los jueces:

| Indicador | Máximo fijado por un caso confirmado, sin filtro | con filtro |
|---|---|---|
| Reasentamiento | 0 de 7 | 1 de 7 |
| Amenaza a líderes | 2 de 7 | 2 de 7 |
| Amenazas e intimidación | 2 de 7 | 4 de 7 |
| Protesta social | 4 de 7 | 5 de 7 |
| Violación de DDHH | 0 de 7 | 1 de 7 |
| Daños ambientales | 0 de 7 | 1 de 7 |
| **Total** | **8 de 42** | **14 de 42** |

Lectura: sin filtro, en violación de DDHH, reasentamiento y daños ambientales el artículo que el radar mostraría como evidencia **nunca**
es un caso confirmado. Con las listas mejora, pero sigue siendo minoría. Este dato no decidía (pre-registro §7) y no cambia el veredicto:
una lista que mejora la evidencia mostrada pero cuyo puntaje sigue respondiendo a un objeto absurdo no cumple la regla del proyecto.

## 6. Decisión

**No se adopta ninguna lista del tramo 1.** Producción queda igual: hipótesis V2, sin pre-filtro social, con pre-filtro por indicador en
grupos armados y desplazamiento, sesgo descontado, MAX, cortes 0.7572/0.9233, 26 indicadores. Estas 6 listas, con esta redacción, no
se reintentan sin evidencia nueva medida (log [2026-09-29]).

## 7. Límites

- **Pocos casos.** Tres departamentos fuera de muestra y pocos casos confirmados por celda; en amenaza a líderes, la ganancia fuera de
  muestra (+0.10) queda justo en el umbral.
- **Jueces automáticos.** La referencia son dos modelos de lenguaje con criterio escrito, no personas; su coincidencia es alta (kappa
  0.75–0.95) pero no se contrastó con lectura humana.
- **Texto visible.** Los jueces leen el texto recortado con la hipótesis más larga; la lista, el de cada indicador.
- **n = 32.** En el radar nacional, solo una diferencia de Spearman de 0.15 o más se distingue del ruido.

## 8. Pendiente de decisión

1. **Los 11 indicadores restantes con lista posible** (y los 4 abstractos, que pasan sin filtro). El pre-registro solo contemplaba un
   segundo tramo si el primero dejaba alguna lista; no dejó ninguna. Con este resultado, más listas del mismo tipo tienen poca
   probabilidad de pasar el control absurdo.
2. **Qué mostrar en el front como evidencia del MAX.** Hoy se puede mostrar el artículo que fija el máximo; la sección 5 indica que en
   varios indicadores ese artículo no trata el tema. Decidir cómo se presenta es una decisión de producto, no técnica.
3. Siguen abiertos: la fusión de la rama, su push y qué hacer con exclusión de beneficios («no medible»).

## 9. Archivos de origen

- Pre-registro y listas: `experimentos/PREREG_prefiltro_indicador_e2.md`, `experimentos/hipotesis_prefiltro_e2.py`.
- Jueces: `.claude/agents/juez-c.md`, `.claude/agents/juez-d.md`; etiquetas y consolidación en
  `experimentos/resultados/juicio_prefiltro_e2/`.
- Scripts: `experimentos/exp_prefiltro_e2_{comun,apertura,gpu,pool,consolidar}.py`, `experimentos/exp_prefiltro_e2.py`.
- Resultados: `experimentos/RESULTADOS_prefiltro_e2.md`, `experimentos/resultados/exp_prefiltro_e2.xlsx`,
  `experimentos/resultados/exp_prefiltro_e2_gpu.log`.
- Pre-filtro social: `informes/11_informe_prefiltro_social_max.md`, `experimentos/RESULTADOS_prefiltro_max.md`,
  `experimentos/resultados/exp_prefiltro_max.xlsx`, `experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx`.
- Decisiones: `contexto/08_log_decisiones.md`, entradas [2026-08-31], [2026-09-28] y [2026-09-29].
