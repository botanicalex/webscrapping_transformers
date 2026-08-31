# 07 — Backlog

En orden de valor. Cada entrada dice qué desbloquea y qué cuesta.

---

## 0. Confirmar qué mide exactamente el índice del DANE — minutos

**Lo primero, antes que las 4 h de GPU.** Es lo más barato y de mayor impacto de todo el
backlog.

**Lo que ya está confirmado** (usuario, 2026-08-29): la columna es del DANE, se pegó a mano
desde una página web donde el DANE publica el valor por departamento, y **esa URL está
perdida**. El DANE usa sus propios indicadores, con otros nombres y otros cálculos.

**Lo que falta:** cuál de sus índices es. Hoy solo hay una inferencia a partir de cómo
ordena los departamentos (Vichada, Guainía y Chocó arriba; Antioquia y Valle abajo →
vulnerabilidad socioeconómica y ausencia de Estado).

El nombre `radar_oficial_**promedio**` sugiere que es el promedio de varios ejes. Si se
recupera la página fuente, esos ejes son los "indicadores con otros nombres" del DANE — el
mapa completo del constructo contra el que se compara.

**Por qué bloquea todo lo demás:** el radar tiene correlación **+0.067** con ese objetivo,
o sea cero, y empata con el modelo nulo. Saber qué mide el índice decide cuál de los tres
caminos de `09_riesgos_y_limites.md` corresponde: cambiar el objetivo, cambiar los
indicadores o soltar la métrica. Es una decisión de diseño de la investigación, no técnica.

**Cómo:** preguntar a la profesora, o localizar la fuente original del archivo
`comparacion_radares_V3.xlsx`.

## 0b. Reportar líneas base junto a la accuracy — minutos

`src/metricas_y_calculo_de_error.py` compara contra un objetivo de 0.70 sin ninguna
referencia intermedia. Añadir siempre: azar (33.3%), clase mayoritaria (34.4%) y **modelo
nulo por número de artículos** (31.2%).

Sin eso, "31.2%" no dice si el pipeline aporta algo — y resulta que no. Los números ya están
en `01_objetivo_y_radar.md`; falta llevarlos al script.

## 1. Scoring V2 sobre los 32 departamentos — ~4 h GPU

```bash
cd experimentos && python generar_scores_32deptos.py
```

**Desbloquea:** todo lo demás. Los puntos 2, 3 y 6 dependen de este pkl.
**Estado:** en curso desde 2026-08-30 (sobre el corpus viejo, con el bug del punto 1b
sin corregir en los datos — ver ahí). El script **guarda por checkpoint tras cada
hipótesis**, así que una interrupción ya no cuesta la corrida entera. Reanuda solo;
`--reiniciar` empieza de cero.
**Produce:** `datos/scores/scores_v2_32deptos.pkl` con `ent_` y `neu_` sin enmascarar, de
modo que después se puede analizar todo offline sin volver a la GPU.

**Lo primero que hay que medir con ese pkl:** la correlación del radar V2 corregido con el
oficial. El radar V0 daba +0.067 (cero), pero se midió sobre un radar que ya sabíamos roto.
Si el V2 tampoco correlaciona, el problema no está en los indicadores — ver
`09_riesgos_y_limites.md`.

## 1b. Terminar de limpiar el corpus de los 4 departamentos de nombre compuesto

Al probar 3b se encontraron y corrigieron dos bugs reales en `src/scrappers.py` (ver
`08_log_decisiones.md` [2026-08-30]): el filtro de relevancia ignoraba el nombre completo
de los departamentos compuestos (`La Guajira`, `Norte de Santander`,
`San Andrés y Providencia`, `Valle del Cauca`), y ~20 de las ~29 clases de scraper no
tenían el workaround SSL/MITM (antivirus Norton local) que `ElTiempo` ya traía. Ambos
corregidos y verificados contra red real.

**Pendiente, sin relación con lo anterior — 3 fallas de scraper distintas:**
- El Tiempo devolvía `502 Bad Gateway` para cualquier búsqueda (afecta 100% a San
  Andrés y Providencia, que depende solo de `eltiempo`). Reintentar más tarde.
- `elpais.com.co` (Valle del Cauca) responde 200 pero el parser no extrae resultados —
  posible carga de resultados por JS/AJAX no capturada por el scraper actual.
- `Corrillos` / `Enlace Televisión` (Norte de Santander, Playwright) y
  `diariooccidente` (Valle del Cauca) acumulan timeouts.

**Estado del corpus:** `datos/corpus/df_corpus_combinado_32deptos.pkl` sigue con los
conteos viejos (11, 36, 79, 117) — no se fusionó nada todavía. El resultado parcial del
re-scraping (solo La Guajira: 1.561, Norte de Santander: 15) está en
`experimentos/resultados/re_scrape_bugfix_relevancia/`.
**Costo:** minutos-horas por scraper, más lo que tome esperar a El Tiempo.
**Depende de:** nada técnico; se frenó por decisión de priorizar el punto 1 (GPU).

## 2. Recalibrar los cortes Bajo/Medio/Alto — HECHO 2026-08-30

Con P75 nacional los valores caen entre 0.22 y 0.41 y los cortes 1/3–2/3 mandaban casi
todo a "Bajo"/"Medio".

**Cortes adoptados** (`experimentos/exp_cortes_fijos_v2.py`, ver
`08_log_decisiones.md` [2026-08-30]): `Bajo < 0.30 <= Medio < 0.35 <= Alto`, leídos de
huecos naturales en la distribución del radar V2 (sin mirar el oficial), verificados
después contra las anclas de validez aparente (ninguna rota) y la accuracy (31.2%,
dentro del ruido de la de terciles ad hoc 40.6%).

**Pendiente:** promover a `src/` (hoy `radar.py`/`metricas_y_calculo_de_error.py`
clasifican con terciles empíricos) — paso de promoción aparte, regla 9, no hecho
todavía. Recalibrar si cambia la decisión del pre-filtro (punto 3).

## 3. A/B del pre-filtro social — con y sin

**Hipótesis:** con la escala corregida puede ser prescindible, porque los artículos
irrelevantes ya puntúan ~0 por sí solos.

**Datos que la motivan:** el pre-filtro V0 anulaba el 33.6% de los positivos de plata de
`grupos_etnicos_existentes` y el 17.7% de `presencia_grupos_armados`, y costaba −0.074 y
−0.024 de AUC. El V2 con umbral 0.85 retiene 92.4% / 95.0% pero solo filtra el 12%.

**Medido 2026-08-30 (nivel radar, no por indicador):** con vs sin el umbral 0.85, sobre
los 32 departamentos, Spearman contra el oficial da +0.376 vs +0.384 — diferencia
dentro del ruido. Apunta a que es prescindible, pero esto es una medición agregada del
radar completo, no el AUC/control absurdo por indicador que pide la regla 1 antes de
tocar producción. **No cerrar la decisión solo con este número.**
**Depende de:** punto 1 — YA CUMPLIDO. Falta el AUC por indicador antes de decidir.

## 3b. Los términos de búsqueda apuntan a conflicto, el objetivo mide déficit

Hipótesis concreta, barata de probar, que puede explicar buena parte de la brecha.

`cfg.TEMAS_BUSQUEDA` es: `conflicto, comunidades, institucional, derechos, social`. **Cuatro
de los cinco tiran hacia conflicto.** Si el índice oficial mide déficit estructural y
ausencia de Estado, el corpus se está construyendo con las noticias equivocadas desde el
primer paso — antes de que ninguna hipótesis NLI intervenga.

La prensa regional **sí** reporta el otro tipo de señal: acueductos que fallan, vías
destapadas, hospitales sin insumos, colegios en ruinas, cortes de gas, desabastecimiento.
Términos como *servicios, acueducto, agua, vías, salud, educación, infraestructura* traerían
ese material.

Encaja con dos hechos ya medidos: el radar produce un ranking de conflicto defendible pero
no correlaciona con el objetivo, y los indicadores que apuntan a la dimensión de déficit
(`exclusion_servicios_derechos`, `debilidad_institucional`, `zonas_proteccion_alimentaria`)
son los más débiles — `debilidad_institucional` es directamente uno de los muertos.

**Prueba barata antes de re-scrapear todo:** correr un departamento con los términos nuevos
y ver cuántos artículos aparecen y si los indicadores de déficit se activan. Si sí, es la
palanca más grande del proyecto. Si no, se descarta por poco costo.

**Depende de:** la tarea 0 (saber qué mide el índice) para saber qué términos añadir.

### Términos candidatos

```
acueducto · agua potable · energía · alcantarillado · gas · salud · hospital ·
escuela · educación · docentes · vías · carretera · desnutrición · vivienda ·
servicios públicos · conectividad
```

## 3c. Bloque de indicadores de déficit estructural (propuesta)

Idea del usuario tras ver que el objetivo mide déficit y los indicadores miden conflicto:
**añadir indicadores de la dimensión faltante, y podar los que no aportan.**

Es legítimo: en un diseño de proxy, ajustar las variables al constructo que se quiere
predecir es ingeniería de características correcta, no trampa. Pero ver el freno más abajo.

### Candidatos a añadir — escritos en formato V2 (declarativos, sin marco metalingüístico)

| Clave | Hipótesis |
|---|---|
| `carencia_agua_potable` | "No hay acueducto ni agua potable." |
| `carencia_energia` | "Hay cortes de energía o falta de servicio eléctrico." |
| `carencia_saneamiento` | "No hay alcantarillado ni manejo de residuos." |
| `deficit_salud` | "El servicio de salud es insuficiente o no hay hospital." |
| `desnutricion` | "Hay desnutrición o hambre en la población." |
| `deficit_educacion` | "Las escuelas están en mal estado o faltan docentes." |
| `aislamiento_vial` | "Las vías están en mal estado o el territorio está incomunicado." |
| `ausencia_estatal` | "No hay presencia de instituciones del Estado en el territorio." |
| `vivienda_precaria` | "Hay viviendas precarias o hacinamiento." |

Junto con los ya existentes `exclusion_servicios_derechos` y `zonas_proteccion_alimentaria`
formarían un bloque de déficit real. `desnutricion` es especialmente pertinente para
La Guajira, que el oficial clasifica Alto y hoy tiene 11 artículos.

### Sobre podar

- **`debilidad_institucional` NO se elimina: se reescribe.** Su concepto —ausencia de
  Estado— es exactamente la dimensión que falta. Lo que falló es la redacción. Sería un
  error quitarlo justo ahora que sabemos que es el que más falta hace.
- `danos_ambientales` e `irregularidad_contractual` sí son de la dimensión conflicto/
  gobernanza y también están muertos. Ahí sí cabe preguntarse si valen la pena.
- `incentivos_economicos_inequitativos` y `exclusion_beneficios_economicos` correlacionan
  **0.80**: fusionarlos libera un espacio sin perder información.

### ⚠️ Freno metodológico — leer antes de empezar

Con **n = 32**, probar varios conjuntos de indicadores y quedarse con el de mejor número es
sobreajuste garantizado. Y lo peor: ese número **no se transferiría a las veredas**, que es
donde se quiere usar el radar.

Disciplina propuesta:

1. Decidir el conjunto **por razonamiento del dominio**, no por prueba y error.
2. Medir **una vez** y registrar el resultado salga como salga, en `08_log_decisiones.md`.
3. Usar las **anclas de validez aparente** (ver `09_riesgos_y_limites.md`) como criterio
   independiente: no se pueden sobreajustar.
4. Optimizar mirando **Spearman**, no accuracy (ver `01_objetivo_y_radar.md`).

**Orden correcto:** primero el corpus (3b), luego los indicadores (3c). Si la prensa no trae
el material, ninguna hipótesis lo va a encontrar.

## 4. Ampliar el estándar de plata

Hoy cubre **2 de 26** indicadores. **Es la mayor debilidad del informe**: todas las
conclusiones descansan en dos.

Dos caminos:
- **Keywords** para los indicadores con marcadores léxicos fiables (`protesta_social`,
  `desplazamiento_forzado`, `amenaza_lideres`...). Barato. Declarar honestamente cuáles
  **no** son viables en vez de inventar keywords malas.
- **Anotación manual** de 120–150 artículos para los conceptos abstractos
  (`debilidad_institucional`, `deficit_participacion_comunitaria`). Es lo único sólido, y
  hace falta antes de defender los resultados académicamente.

**No depende de nada.** Se puede hacer ya.

## 5. Los tres indicadores muertos

`debilidad_institucional`, `danos_ambientales`, `irregularidad_contractual` dan 0.0000
incluso en el percentil 90.

No es problema de agregación: ya eran los más débiles antes de la reescritura. Hipótesis a
distinguir: (a) redacción mala, (b) fenómeno genuinamente raro en prensa regional,
(c) concepto demasiado abstracto para inferencia textual.

**Importa doblemente** que `debilidad_institucional` sea uno de ellos: es de los pocos que
apuntan a la dimensión *ausencia de Estado*, que es la que el índice oficial parece medir.

**Herramienta:** el skill `experimento-hipotesis`.
**Bloqueo parcial:** ninguno de los tres tiene estándar de plata, así que el punto 4 debería
ir antes o en paralelo.

## 6. Medir la accuracy de V2 contra el oficial — MEDIDO 2026-08-30, ver matiz

Comparado con el 31.2% histórico del V0.

**Medido:** accuracy en terciles (sin recalibrar cortes, punto 2 todavía pendiente):
**37.5%** sin pre-filtro, **40.6%** con pre-filtro. Con n=32 y error estándar ~8 pp, la
diferencia frente a las líneas base (azar 33.3%, clase mayoritaria 34.4%) es **menor a
~15 pp — no concluyente por accuracy sola**, tal como advertía esta entrada.

**Lo que sí es concluyente:** el Spearman contra `radar_oficial_promedio` (el valor
continuo, la métrica de trabajo que pide `01_objetivo_y_radar.md`) subió de +0.067 a
+0.384 — un salto de +0.32, muy por encima del ruido, y que sobrevive el control de la
nula reservada (~0.0000) y las anclas de validez aparente (ninguna rota). Ver
`08_log_decisiones.md` [2026-08-30].

**Advertencia que sigue vigente:** "los indicadores discriminan mejor" (AUC, control
absurdo, ya demostrado) y "el radar predice mejor el índice oficial" (ahora con
evidencia real, +0.384) son afirmaciones distintas — pero ya no hay que tratarlas como
independientes: la segunda deja de ser dudosa a la luz de la primera. El desajuste de
constructo (conflicto vs vulnerabilidad) sigue siendo real — 0.38 no es 0.70 — pero es
menor de lo que el V0 hacía parecer.

**Depende de:** punto 1 (cumplido) y punto 2 (recalibrar cortes — pendiente, mejoraría
la accuracy en terciles aunque no cambie el Spearman).

## 7. Cobertura de prensa desbalanceada

De los 11 departamentos clasificados como Alto por el oficial, 5 tienen menos de 100
artículos (Guainía 6, La Guajira 11, Vaupés 32, Sucre 41, Vichada 62). Norte de Santander,
uno de los más golpeados del país, tiene 36.

Reforzar `DEPARTAMENTO_PERIODICOS` para Norte de Santander, Chocó, La Guajira y Arauca
mejoraría el insumo **más que cualquier ajuste de hipótesis**.

**Costo:** días (re-scraping). Es la mejora de mayor impacto y mayor costo.

---

## Trabajo perdido que conviene rehacer

Un workflow de 10 agentes quedó a medias al apagar el equipo. Cubría: propuestas de keywords
para ampliar el estándar de plata (punto 4), diagnóstico de los tres indicadores muertos
(punto 5), y una crítica adversarial del informe. No produjo resultados; se puede relanzar.
