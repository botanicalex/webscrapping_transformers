# 08 — Log de decisiones

**Leer antes de proponer nada.** Lo marcado CERRADO no se relitiga sin evidencia nueva
medida. Los rechazos valen tanto como las adopciones: evitan reintentar lo que ya falló.

Formato para entradas nuevas:

```
## [fecha] <tema>
Pregunta:
Decisión:  ADOPTADA / RECHAZADA / NO MEDIBLE
Evidencia: <números y archivo de origen>
Cierra:    <qué no hace falta volver a probar>
Abre:      <qué sí>
```

---

## [2026-08-25] Mapeo de etiquetas NLI — CERRADO

**Pregunta:** ¿se está guardando `P(contradiction)` como si fuera `P(entailment)`? El
fallback `ent, neu, con = 0, 1, 2` de `_resolver_labels_nli` parecía peligroso.

**Decisión:** RECHAZADA la sospecha. No hay inversión.

**Evidencia:** `id2label = {0: 'entailment', 1: 'neutral', 2: 'contradiction'}`. El bucle
resuelve los tres índices por texto, así que el fallback **nunca se ejecuta**; y aunque se
ejecutara, `0,1,2` coincide con el orden real del modelo. Además `nli_core` reproduce
producción bit a bit (`max|dif| = 0.00e+00`).

**Cierra:** revisar el mapeo de etiquetas. No volver a proponerlo.
**Abre:** la anomalía que motivó la sospecha era real, pero su causa es otra — el marco
metalingüístico.

## [2026-08-25] El marco metalingüístico es la causa de la inflación — CERRADO

**Decisión:** ADOPTADA la reescritura sin marco metalingüístico (V2).

**Evidencia:** control absurdo con el formato de producción → media 0.9098, prop>0.9
**78.45%**. Sin metalenguaje → 0.4660 / 20.46%. AUC 0.7430→0.8261 (armados) y
0.6303→0.8212 (étnicos). Fuente: `experimentos/resultados/exp1_formato.xlsx`.

**Cierra:** que la disyunción múltiple sea la causa principal (quitarla sola **empeora**:
83.24%), y que `"explícitamente"` importe (+0.03 de AUC, inerte).
**Abre:** aplicar V2 a `src/`, pendiente de la validación nacional.

## [2026-08-26] Normalización `ent/(ent+con)` — CERRADO

**Decisión:** RECHAZADA.

**Evidencia:** empeora el control absurdo de 0.466 a 0.830 de media (prop>0.9 del 20% al
60%) y colapsa la separación de +0.364 a +0.042. Fuente: `exp2_premisa.xlsx`.

**Razón:** la masa de *neutral* es la que carga la señal de "este texto no habla de eso".
Descartarla convierte un "no aplica" en un "sí" parcial.

**Cierra:** no volver a proponer descartar neutral.

## [2026-08-26] Premisa: se mantiene el cuerpo del artículo — CERRADO

**Decisión:** ADOPTADA `cuerpo` (statu quo). No cambiar a titular ni titular+lede.

**Evidencia:** no hay ganador. `presencia_grupos_armados` prefiere titular_lede (0.8358 vs
0.8261) pero `grupos_etnicos_existentes` prefiere cuerpo por mucho (0.8212 vs 0.7157).
Ganar +0.010 en uno y perder −0.106 en el otro no compensa. Fuente: `exp2_premisa.xlsx`.

**Razón sustantiva:** depende de si el indicador es sobre el *tema* del artículo o sobre
*menciones incidentales* en el cuerpo.
**Abre:** una premisa distinta por tipo de indicador, si alguna vez compensa la complejidad.

## [2026-08-26] MAX y TOP-k descartados como agregación — CERRADO

**Decisión:** RECHAZADOS MAX, TOP3 y TOP5.

**Evidencia:** submuestreando Maicao a n = 20…1000, el artefacto por tamaño de corpus
supera la señal entre lugares. Razón señal/artefacto: MAX 0.91, TOP3 1.1, TOP5 1.2 frente a
P75 49.0 y P90 11.8. Fuente: `exp6_agregacion_v2.xlsx`.

**Razón:** toda agregación top-k premia tener más artículos; tomar los k mayores de una
muestra grande siempre da más alto. Los cuantiles son posicionales y no tienen ese sesgo.

**Cierra:** "probemos TOP3" — ya se probó y comparte el defecto. También explica por qué la
comparación MAX vs TOP3 de junio dio idéntica (0.9991 vs 0.9988): bajo V0 todo estaba
saturado.

## [2026-08-27] Agregación elegida: P75 — CERRADO (con costo asumido)

**Decisión:** ADOPTADO el percentil 75.

**Evidencia:** mejor combinación de separación entre lugares (0.2007) y estabilidad frente
al tamaño (artefacto 0.0041, razón 49.0). Con P75 el radar de la nula da **exactamente
0.0000** en los cuatro lugares.

**Costo asumido y medido:** frente a P90, P75 pierde 3 indicadores que tienen señal en el
percentil 90 pero no en el 75 (`reasentamiento`, `resistencia_territorial`,
`deficit_participacion_comunitaria`). Otros 3 quedan en cero bajo ambos, lo cual es un
problema del indicador, no de la agregación.

**Nota sobre el razonamiento original:** se justificó pensando que "si un hecho ocurre,
varios periódicos lo reportan". Eso es cierto pero **no sostiene P75**: P75 exige que el
indicador se active en el 25% de *todo* lo publicado sobre el lugar, y un hecho cubierto por
5 medios en Maicao es el 0.45% del corpus. P75 funciona porque los indicadores amplios son
frecuentes, no por redundancia entre medios. La decisión es correcta; el argumento inicial
no lo era.

**Abre:** si aparecen muchos indicadores raros pero válidos, reconsiderar P90.

## [2026-06] NER y análisis de sentimiento desactivados — CERRADO

**Decisión:** ADOPTADA la desactivación. Código comentado, no borrado.

**Razón:** no alimentaban ningún indicador ni el radar; solo consumían GPU y memoria.
`grupos_etnicos_existentes` se migró de NER a NLI y se eliminaron los indicadores
redundantes `existencia_grupos_etnicos` y `grupos_armados_existentes`.

**Cierra:** no reactivarlos.
**Nota útil:** las listas de keywords del NER sobreviven en
`experimentos/hipotesis_base.py` como `KEYWORDS_SILVER` y son la base del estándar de plata.

## [2026-06] Umbrales fijos, no terciles, para el radar propio — CERRADO por decisión externa

**Decisión:** cortes fijos 1/3 y 2/3, no terciles empíricos. Pedido del jefe del usuario.

**Nota:** con MAX esto hacía que los 32 departamentos salieran "Alto" (el mínimo fue Guainía
con 0.8907), o sea el filtro no discriminaba nada. Con P75 pasa lo contrario: todo cae en
"Bajo". La restricción se mantiene, pero los cortes deben **recalibrarse una vez** sobre la
distribución nacional y congelarse. Ver `07_backlog.md` punto 2.

## [2026-08-27] Reorganización a `desarrollo/` — ADOPTADA

**Decisión:** carpeta limpia en `Web_scrapping_2026/desarrollo`, con solo lo ejecutable y
los insumos.

**Evidencia:** el directorio original mezclaba ~190 MB de resultados superados con el
pipeline vivo; `webscrapping_transformer_produccion/` estaba congelada 2.5 meses atrás.

**Además:** `Transformer_optimo.py` ya no importa `scrappers` a nivel de módulo (import
diferido dentro de `correr_scraping()`), así que puntuar con GPU ya no arrastra
playwright/aiohttp. Los 11 `grupo_NN.py` idénticos se consolidaron en `correr_grupo.py`.

**Verificado:** `nli_core.verificar_contra_produccion()` sigue dando `max|dif| = 0.00e+00`
tras la migración.

## [2026-08-30] Bug en el filtro de relevancia para departamentos de nombre compuesto — CORREGIDO

**Contexto:** probando la tarea 3b del backlog (términos de búsqueda de déficit vs
conflicto) en La Guajira con `scrape_departamento(temas=TERMINOS_DEFICIT)`.

**Hallazgo:** `GestorScraper._es_relevante` (`src/scrappers.py:5721-5728`) deriva el
"territorio" a validar con `self.termino.split()[0]`, donde `self.termino` es la cadena
combinada `"{departamento} {tema}"`. Para un departamento de una sola palabra eso da el
nombre correcto. Para uno de varias, da solo la primera:

```
La Guajira               -> 'la'
Norte de Santander       -> 'norte'
San Andrés y Providencia -> 'san'
Valle del Cauca          -> 'valle'
```

Con `min_menciones=2` y "la" (o "san") contado en el cuerpo + título de cualquier
artículo en español, el filtro es esencialmente un no-op. Evidencia directa del log de
la prueba: **0 artículos descartados en absoluto**, en las ~30 llamadas al filtro para
La Guajira (`resultados/log_exp_terminos_deficit.txt`, líneas con
`Filtro relevancia (La, umbral=2): N → N artículos (0 descartados)`).

Efecto colateral en la propia prueba 3b: buscar con términos de déficit dio 3.121
artículos "únicos" para La Guajira contra 11 con los de conflicto (284x), pero al
inspeccionar muestras por término, salvo `desnutrición` (35, con señal real y
consistente: muertes infantiles Wayuu, urgencia de gobierno), el resto —incluidos
términos específicos como `acueducto`, `alcantarillado`, `servicios públicos`,
`conectividad`, `docentes`, no solo los genéricos `gas`/`salud`/`vías`— trae mayoría de
ruido (política local, sucesos, deportes, cultura) sin relación con el tema buscado.
El crecimiento de 284x no es evidencia confiable de que la prensa cubra más déficit: es,
en gran parte, artefacto de este filtro roto sumado a lo que sea que devuelva la
búsqueda interna de cada periódico para queries de una sola palabra común.

**Alcance:** afecta los 4 departamentos de nombre compuesto de los 32 — incluidos en el
corpus nacional ya scrapeado (`datos/corpus/df_corpus_combinado_32deptos.pkl`), no solo
a esta prueba. El filtro roto es más permisivo, no más estricto, así que no explica los
conteos bajos de artículos ya señalados en `07_backlog.md` punto 7 — pero sí pone en
duda si los artículos que SÍ pasaron el filtro para esos 4 departamentos son realmente
sobre ese territorio.

**Fix aplicado (2026-08-30, con autorización del usuario):** `_buscar_multi_termino` ya
tenía `territorio` como argumento propio; se propagó explícitamente a través de
`scrape_periodicos()` hasta `GestorScraping.__init__(..., territorio=None)`, que ahora
guarda `self.territorio` (el nombre completo, ej. `"la guajira"`) y `_es_relevante` lo
usa en vez de reconstruirlo con `.split()[0]`. Sin `territorio` explícito cae al
comportamiento viejo (retrocompatible). Verificado: un artículo real de escasez de agua
en La Guajira pasa el filtro; uno de reinado de belleza en Riohacha ya no.

**Decisión:** ADOPTADA. Se corrigió el filtro. El re-scraping de los 4 departamentos
para limpiar `datos/corpus/` se hizo junto con el fix de SSL de la entrada siguiente
(ambos bloqueaban la misma tarea) — ver esa entrada para el resultado.
**Cierra:** el bug del filtro en sí. No volver a proponer "usar `.split()[0]` para
derivar el territorio".
**Abre:** repetir la prueba 3b en un departamento de una sola palabra reveló un segundo
problema (SSL/MITM), ver entrada siguiente — 3b/3c siguen sin una lectura limpia.

## [2026-08-30] SSL/MITM local (Norton) sin parchar en ~20 de las ~29 clases de scraper — CORREGIDO

**Contexto:** al repetir 3b en Chocó (departamento de una sola palabra, para descartar
el bug anterior) el scraper local `choco7dias` falló en el 100% de las 16 búsquedas con
`SSLError: CERTIFICATE_VERIFY_FAILED`. Un diagnóstico directo (`requests.get` a
`choco7dias.com` y, por control, a `eltiempo.com`) mostró el mismo error en ambos —
incluido un dominio grande con certificado correctamente firmado. Eso descarta un
certificado roto del sitio: es el equipo local.

**Causa:** el código ya documentaba este problema — `ScraperElTiempo` y
`ScraperWordPressAPI` traen comentarios explícitos ("eltiempo.com verifica con un cert
MITM inyectado por el antivirus local (Norton SSL/TLS scanning)... curl funciona porque
usa el almacén de Windows") y ya ponían `self.session.verify = False` como workaround.
Pero ese fix nunca se generalizó: la clase base `ScraperPeriodico.__init__` sigue
creando `requests.Session()` sin `verify=False`, y por separado 8 clases reimplementan
la búsqueda con `aiohttp.ClientSession()` (sin conector) y otras 9 usan
`aiohttp.TCPConnector(limit=N)` para la descarga de artículos — ninguna de las 17
llamadas a aiohttp tenía `ssl=False`. En total, ~20 de las ~29 clases de scraper
dependían de que Norton no interceptara su dominio por pura suerte.

**Confirmado con red real, no solo en teoría:** antes del fix, `elpais.com.co` (Valle
del Cauca), `occidente.co` (Valle del Cauca) y `corrillos.com.co` (Norte de Santander)
fallaban al 100% en el re-scraping de los 4 departamentos del bug anterior — San Andrés
y Providencia y Valle del Cauca dieron **0 artículos** (antes: 79 y 117). Después del
fix, `s.session.get('https://www.elpais.com.co/')` y una llamada aiohttp directa a la
API de `choco7dias.com` devuelven `200` limpio.

**Fix aplicado:** `ScraperPeriodico.__init__` ahora pone `self.session.verify = False`
(hereda a las ~15 clases basadas en `requests.Session`, incluida `ScraperWordPressAPI`;
redundante pero inofensivo en `ScraperElTiempo`, que ya lo tenía). Los 8 sitios
`aiohttp.ClientSession()` sin conector y los 17 `aiohttp.TCPConnector(limit=N)` ahora
pasan `ssl=False`. 26 sitios en total. Verificado: `py_compile` limpio,
`GestorScraping` sigue funcionando, y las pruebas de red directas contra los dos sitios
que fallaban antes ahora responden `200`.

**No se investigó** por qué Norton empezó a interceptar más dominios que cuando se
scrapeó el corpus original (¿instalación/actualización reciente de Norton? ¿política de
inspección que cambió?) — se optó por generalizar el workaround ya aceptado en el
código en vez de perseguir la causa en Norton/Windows.

**Decisión:** ADOPTADA, con autorización del usuario (parchar las ~20 clases de una
vez, no solo las 4 necesarias para cerrar el bug del filtro).
**Cierra:** "por qué falla justo este departamento/scraper" cuando el error sea
`CERTIFICATE_VERIFY_FAILED` — es este problema, no el sitio.
**Abre:** el corpus histórico de los 32 departamentos se scrapeó ANTES de que este
problema apareciera (no está contaminado por esto), pero cualquier re-scraping futuro
sin este fix habría fallado silenciosamente en varios departamentos más allá de los 4
conocidos.

### Re-scraping post-fix (mismo día): 3 fallas más, no relacionadas con SSL ni con el filtro

Con los dos fixes aplicados, se repitió el re-scraping de los 4 departamentos
(`experimentos/exp_rescrape_fix_relevancia.py`, log en
`resultados/log_rescrape_bugfix_v2.txt`). Resultado: La Guajira 1.561 (sin cambio,
esperado — no dependía del fix SSL), Norte de Santander 143→**15**, San Andrés y
Providencia y Valle del Cauca **siguen en 0**. Tres causas nuevas, cada una distinta y
sin relación con lo ya corregido:

1. **El Tiempo devuelve 502 Bad Gateway ahora mismo**, para cualquier búsqueda —
   confirmado con una consulta de control ("Antioquia conflicto", nada que ver con San
   Andrés) que también da 502. Es una caída del sitio en este momento, no algo que el
   código pueda arreglar. San Andrés depende al 100% de `eltiempo`.
2. **`elpais.com.co` (Valle del Cauca) responde 200 con una página completa (61 KB)
   pero el parser no extrae resultados** — hipótesis: el buscador del sitio carga
   resultados por JS/AJAX, no en el HTML servido. No investigado a fondo. Distinto del
   problema de SSL (que sí estaba resuelto: la conexión funciona).
3. **`diariooccidente` (Valle del Cauca) y `Corrillos`/`Enlace Televisión` (Norte de
   Santander, Playwright) acumulan timeouts** — de ahí la caída de Norte de Santander
   de 143 a 15 artículos. Sitios lentos o que necesitan más tiempo de espera, no un
   problema de certificado.

**Decisión:** se frena aquí, con autorización del usuario. No se investigan estas 3
fallas ahora — cada una es una investigación aparte (parser de El País, timeouts de
Playwright, esperar a que El Tiempo vuelva) y el job de GPU (tarea 1 del backlog) sigue
siendo la prioridad activa.
**Cierra:** nada — quedan abiertas, documentadas para no re-descubrirlas de cero.
**Abre:**
- Backlog: investigar el parser de `elpais` (¿resultados vía AJAX?), ajustar timeouts
  de `Corrillos`/`Enlace Televisión`/`diariooccidente`, y reintentar San Andrés cuando
  El Tiempo vuelva a responder (probar primero con una petición suelta a
  `eltiempo.com/buscar/`, sin relanzar todo el departamento).
- **El corpus nacional (`datos/corpus/df_corpus_combinado_32deptos.pkl`) NO se
  actualizó.** Los 4 departamentos siguen con los conteos viejos (11, 36, 79, 117) y el
  bug del filtro de relevancia ya corregido en el código pero no reflejado en los datos
  guardados. `experimentos/resultados/re_scrape_bugfix_relevancia/` tiene el resultado
  parcial (solo La Guajira y Norte de Santander) para cuando se retome.

## [2026-08-30] Correlación del radar V2 con el oficial DANE, a escala nacional — MEDIDO

**Pregunta:** la más importante pendiente del proyecto (ver `09_riesgos_y_limites.md`):
con el radar V2 corregido (marco metalingüístico arreglado, sesgo por artículo
descontado, agregación P75) sobre los 32 departamentos, ¿aparece correlación con
`radar_oficial_promedio`? El V0 daba Spearman +0.067 (cero), pero medido sobre un radar
que ya sabíamos indistinguible de hipótesis absurdas.

**Insumo:** `datos/scores/scores_v2_32deptos.pkl` (11.439 artículos × 26 hipótesis,
`ent_`/`neu_` sin enmascarar), generado por `generar_scores_32deptos.py` (~4 h GPU,
2026-08-30). `nli_core.verificar_contra_produccion()` dio OK antes de correrlo. Análisis
en `experimentos/exp_correlacion_v2_nacional.py`
(`resultados/exp_correlacion_v2_nacional.xlsx`) — sin volver a tocar la GPU (regla 8).

**Evidencia:**

```
                     Spearman    p-valor   Accuracy terciles
V0 (historico)        +0.067       —              31.2%
V2, sin prefiltro     +0.384      0.030           37.5%
V2, con prefiltro 0.85 +0.376     0.034           40.6%
```

Control de sanidad — radar de la nula reservada (`NULA_TEST`) agregado con P75 a escala
nacional: **0.0000 en 31 de 32 departamentos** (Valle del Cauca 0.0067, despreciable),
`Spearman(radar_nula, n_articulos) = -0.146` (el MAX roto daba +0.87). P75 sigue
conteniendo el artefacto de tamaño de corpus a escala nacional — el +0.384 no es un
efecto del aggregation.

**Anclas de validez aparente** (`09_riesgos_y_limites.md`): **ninguna rota**, en ninguna
de las dos variantes. Cundinamarca, Quindío, Boyacá, San Andrés, Caldas y Risaralda
salen Bajo o Medio (nunca Alto); Cauca, Nariño, Chocó, Arauca, Norte de Santander y
Putumayo salen Medio o Alto (nunca Bajo).

**Lectura:** el V2 lleva señal real hacia el objetivo — el salto de +0.067 a +0.38 es
demasiado grande para ser ruido de n=32 (regla 11: diferencias >15 pp/0.15 en
proporción no son ruido; aquí el salto es de +0.32 en Spearman) y sobrevive el control
de la nula. No es una correlación fuerte (0.38 es moderada, no alta) y la accuracy en
terciles (37.5%/40.6%) sigue lejos del objetivo de 70% y dentro del margen de ruido
frente a las líneas base (azar 33.3%, clase mayoritaria 34.4% — diferencia <15 pp, no
concluyente por accuracy sola). **El indicador de trabajo es el Spearman, no la
accuracy** (así lo pide `01_objetivo_y_radar.md`), y ahí el cambio es claro y
sobrevive el control absurdo.

**Pre-filtro social (backlog punto 3):** con vs sin el umbral 0.85 da resultados casi
idénticos (+0.384 vs +0.376 Spearman, diferencia dentro del ruido). Consistente con la
hipótesis del backlog: a escala nacional, con la agregación P75, el pre-filtro parece
prescindible — el score de los artículos irrelevantes ya cae solo. No se recomienda
retirarlo todavía solo con esto (ver "Abre"), pero no está bloqueando nada.

**Decisión:** MEDIDO. No es una decisión de adoptar/rechazar una variante — es la
medición que faltaba para decidir el rumbo del proyecto (los tres caminos de
`09_riesgos_y_limites.md`). Con +0.38 y anclas intactas, el camino (B) "cambiar/ampliar
indicadores" (backlog 3b/3c) tiene ahora una base empírica más sólida que antes: los
indicadores actuales SÍ correlacionan, así que sumar los de déficit estructural es
extender algo que ya funciona parcialmente, no parchear algo que no lleva ninguna señal.
**Cierra:** "el V2 no va a correlacionar mejor que el V0, es el mismo problema
estructural" — no es cierto, medido. No volver a citar +0.067 como el estado actual del
radar V2.
**Abre:**
- Backlog punto 2 (recalibrar cortes Bajo/Medio/Alto sobre esta distribución nacional):
  ahora tiene sentido hacerlo, con un radar que sí lleva señal.
- Backlog punto 6 (accuracy V2 vs oficial): medido arriba (37.5%/40.6%); no concluyente
  por sí sola con n=32, pero ya no hace falta remedirla desde cero.
- Backlog punto 3 (A/B pre-filtro): apunta a que es prescindible, pero valdría
  confirmarlo mirando también el AUC/control absurdo por indicador antes de retirarlo
  de producción, no solo la correlación agregada.
- Sigue sin resolverse la pregunta de diseño de fondo (¿qué índice del DANE es
  exactamente? — tarea 0 del backlog, la trae el usuario): +0.38 es una mejora real,
  pero no alcanza el 0.70 objetivo, y sin saber qué mide el DANE no se puede juzgar si
  ese techo es de los indicadores o del desajuste de constructo.

## [2026-08-30] Cortes fijos Bajo/Medio/Alto recalibrados sobre el radar V2 nacional — ADOPTADA

**Pregunta:** backlog punto 2. Con P75 los valores del radar V2 caen entre 0.22 y 0.41;
los cortes viejos (1/3, 2/3 de la escala [0,1]) mandan casi todo a "Bajo"/"Medio" y ya
no significan nada. La restricción externa sigue en pie ([2026-06] "Umbrales fijos, no
terciles"): hacen falta dos valores de corte fijos, no terciles recalculados por lote,
porque el radar debe poder clasificar un lugar solo (una vereda), sin otros 31 lugares
con qué hacer terciles.

**Metodología (evita el riesgo de "seleccionar sobre el conjunto de evaluación" ya
señalado en `09_riesgos_y_limites.md`):** los cortes se leyeron de la forma de la
distribución del radar V2 en sí —huecos naturales entre valores consecutivos de los 32
departamentos— **sin mirar la clasificación oficial**. Solo después se verificaron
(no se ajustaron) contra las anclas de validez aparente y la accuracy resultante.
Script: `experimentos/exp_cortes_fijos_v2.py`
(`resultados/exp_cortes_fijos_v2.xlsx`). Configuración: radar V2, P75, **con** el
pre-filtro social 0.85 (la que coincide con el pipeline de producción actual — ver
nota al final sobre el pre-filtro).

**Cortes adoptados:**

```
Bajo   : radar_propio <  0.30
Medio  : 0.30 <= radar_propio < 0.35
Alto   : radar_propio >= 0.35
```

Caen en dos huecos genuinos de la distribución: 0.3513→0.3362 (hueco 0.0150) y
0.3117→0.2996 (hueco 0.0121) — no cortan un grupo de valores casi iguales por la mitad.
Da una distribución de clases 8 Alto / 13 Medio / 11 Bajo.

**Evidencia:**
- **Anclas de validez aparente: ninguna rota.** Cundinamarca (0.2486), Quindío (0.3117),
  Boyacá (0.2982), San Andrés (0.2257), Caldas (0.2161) y Risaralda (0.2996) salen Bajo
  o Medio, nunca Alto. Cauca (0.3927), Nariño (0.3513), Chocó (0.3895), Arauca (0.3994),
  Norte de Santander (0.3564) y Putumayo (0.3212) salen Medio o Alto, nunca Bajo.
- **Accuracy: 31.2%**, contra 40.6% de los terciles empíricos ad hoc usados como
  referencia en la medición de correlación del 2026-08-30. La diferencia (9.4 pp) está
  dentro del ruido de n=32 (regla 11, SE~8pp) — no es una señal de que los cortes fijos
  sean peores, es el costo esperado de no optimizar directamente contra el oficial.

**Nota sobre el pre-filtro:** estos cortes se calibraron con el pre-filtro puesto
(0.85), que es como corre producción hoy. El backlog punto 3 sigue abierto (A/B sugiere
que el pre-filtro es prescindible, pero falta el AUC por indicador antes de decidir
retirarlo). Si se retira, los valores de radar_propio cambian ligeramente
(+0.384 vs +0.376 de Spearman, diferencia chica) — **recalibrar estos cortes si cambia
esa decisión** (regla 2: si cambia lo que se mide, hay que recalibrar el umbral).

**Decisión:** ADOPTADA. Los cortes 0.30/0.35 quedan congelados para clasificar
`radar_propio` (V2, P75, con pre-filtro) en cualquier lugar futuro (departamento,
municipio, vereda), sin recalcular terciles por lote.
**Cierra:** "los cortes 1/3–2/3 mandan todo a Bajo" — ya no aplica con estos.
**Abre:** promover el cálculo a `src/radar.py`/`src/metricas_y_calculo_de_error.py`
(hoy clasifican con terciles empíricos, `_categoria_terciles`/`_clasificar`) es un paso
de promoción aparte (regla 9), pendiente de que el usuario lo pida — nada de V2 está en
`src/` todavía, ni las hipótesis ni la agregación ni estos cortes.
