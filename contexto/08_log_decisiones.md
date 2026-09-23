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

## [2026-08-31] Backlog 1b — 3 fallas de scraper diagnosticadas y corregidas, re-scraping repetido

**Contexto:** las 3 fallas que quedaron abiertas en la entrada anterior (El Tiempo 502,
parser de El País sin resultados, timeouts de Corrillos/Enlace/diariooccidente). Cada
una se diagnosticó con pruebas directas contra la red real (no contra el HTML servido a
mano — eso fue lo que llevó a un diagnóstico impreciso la vez anterior) antes de tocar
`src/scrappers.py`.

**1. El País Cali — el diagnóstico anterior era impreciso.** La búsqueda (API Queryly)
**sí funcionaba**: 15-94 links encontrados por término en el log de la corrida anterior.
La falla real estaba en la descarga de artículos: 0% de éxito, mal etiquetado como
"timeouts" por el código (`_descargar_articulos` rotula CUALQUIER excepción como
"timeouts", regla general del código, no solo de El País). Reproducido directo:
`newspaper.Article(link).download()` da `CERTIFICATE_VERIFY_FAILED` — usa su propio
`requests.Session` interno, AJENO a `self.session`, así que el fix del 2026-08-30
(`self.session.verify = False`) nunca lo cubrió. `ScraperElTiempo` ya traía este mismo
fix aplicado a mano en su propio override; el resto de los ~20 scrapers que usan la
descarga por defecto de la clase base no. **Fix:** `Config` de `newspaper4k` con
`verify=False` (y de paso `timeout=20`, ver punto 4) en un objeto módulo
`_NEWSPAPER_CONFIG`, usado por `ScraperPeriodico._descargar_articulo_individual` — cubre
a los ~20 scrapers de una vez, no solo El País. Verificado: 2/2 artículos de prueba
descargados (antes: 0/2).

**2. Diario Occidente — el "parser" nunca fue el problema.** `_recolectar_links`
detiene la paginación en cuanto ve el PRIMER artículo con fecha anterior a
`fecha_desde`. Confirmado con la red real: la búsqueda de WordPress de `occidente.co`
ordena por relevancia, no por fecha — un artículo de 2020 aparece en la página 1
intercalado con otros de 2026 (ver ejemplo medido: query "institucional" trae
2026-07-17, 2026-02-27, **2020-09-15**, 2026-08-27... en ese orden). Parar en el primero
que se ve descarta páginas enteras con artículos en rango todavía por recorrer. **Fix:**
se ignora el artículo viejo (no se agrega, no se detiene) en vez de romper el bucle —
igual que ya hace `ScraperCorrillos`, que enfrenta el mismo problema de orden no
monótono en el mismo tipo de sitio (WordPress) y ya lo resolvía bien. La parada real
sigue siendo la de "3 páginas seguidas sin nada nuevo en rango", que no dependía del
bug.

**3. Corrillos / Enlace Televisión — el timeout medía la cola, no la red.** Reproducido
con datos reales (132 links de Corrillos de un scraping en vivo): con
`aiohttp.TCPConnector(limit=10, ssl=False)` y `session.get(link, timeout=15)` (entero,
timeout TOTAL) lanzando todos los links de una vez vía `asyncio.gather`, **68 de 132
(51%) fallaban por "TimeoutError"** — pero cada request individual tomaba 2-8s cuando sí
conseguía una conexión libre del pool; el resto del tiempo lo pasaba esperando en cola,
y esa espera cuenta contra el timeout total de 15s. A más links en el lote, más
artículos reales se pierden por pura cola, no por lentitud del sitio. **Fix:**
`aiohttp.ClientTimeout(total=None, sock_connect=20, sock_read=20)` en vez de un entero
— así la espera en cola no cuenta contra el timeout, solo la actividad real de socket.
Verificado con un lote simulado de 800 links (repitiendo los 132 reales): 51% de fallos
→ 784/792 (99%) éxitos, 8 fallos reales (`SocketTimeoutError` genuino).

**4. Hallazgo adicional durante la verificación de Diario Occidente — mismo patrón,
sitio simplemente lento.** Con el fix del punto 2 aplicado, `occidente.co` seguía
fallando la mayoría de sus páginas de listado (`Read timed out`, `timeout=10`).
Reproducido directo: el sitio responde consistentemente en 10-12s para búsquedas
paginadas, sin señal de estar caído ni de rate-limiting — el timeout de 10s era
simplemente insuficiente. **Fix:** `timeout=10 → 20` en el fetch de la página 1
(`ScraperPeriodico.scrape()`, clase base, beneficio de paso a cualquier scraper lento) y
`timeout=10 → 25` en el bucle de páginas de `ScraperDiarioOccidente._recolectar_links`
(igualando lo que `ScraperCorrillos` ya usa para el mismo tipo de sitio). Mismo problema
se repetía en la descarga de artículos individuales (7s por defecto de `newspaper4k`,
40% de fallos) — cubierto por el mismo `_NEWSPAPER_CONFIG` del punto 1
(`timeout: 20` agregado ahí). Verificado end-to-end: 0% → 100% de artículos descargados
en una búsqueda de prueba (35/35).

**El Tiempo (San Andrés y Providencia):** confirmado con la red real que el 502 **se
resolvió temporalmente** (200 OK en una prueba aislada) y **volvió a aparecer** en una
prueba posterior, minutos después, de forma consistente (4 intentos con 8s de espera,
502 en los 4). Es un problema externo intermitente del sitio, no del código — no hay fix
posible de nuestro lado. Sigue bloqueando San Andrés y Providencia, que depende al 100%
de este scraper.

**Verificación:** cada uno de los 4 fixes se probó de forma aislada contra la red real
(no solo `py_compile`) antes de correr el re-scraping completo — instanciando la clase
del scraper directamente con un rango de fechas corto y confirmando 100% de descargas
exitosas. `py_compile src/scrappers.py` limpio en cada paso.

**Re-scraping completo** (`experimentos/exp_rescrape_fix_relevancia.py`, log en
`resultados/log_rescrape_bugfix_v3.txt`), con los 4 fixes de esta entrada más los 2 de
la entrada anterior (filtro de relevancia, SSL/MITM base):

```
                              viejo   nuevo
La Guajira                      11    1553
Norte de Santander               36     352
San Andrés y Providencia         79       0   <- El Tiempo caído en el momento de la corrida
Valle del Cauca                 117     145
```

Norte de Santander pasó de 15 (corrida anterior, con Corrillos/Enlace rotos) a 352.
Valle del Cauca pasó de 0 (El País y Diario Occidente rotos) a 145. San Andrés sigue en
0 — no por un bug nuestro, sino porque El Tiempo estaba caído en el momento exacto de
esta corrida (confirmado con pruebas aisladas antes y después).

**Decisión:** ADOPTADOS los 4 fixes de `src/scrappers.py`. **NO se fusionó** el
resultado con `datos/corpus/df_corpus_combinado_32deptos.pkl` todavía — esa carpeta está
enlazada por junction con `desarrollo/` (ver `CLAUDE.md`), así que escribir ahí afecta a
los dos worktrees, y es una decisión aparte de si/cuándo hacerlo, no automática. El
resultado de esta corrida queda en
`experimentos/resultados/re_scrape_bugfix_relevancia/` (`df_corpus_la_guajira.pkl`,
`df_corpus_norte_de_santander.pkl`, `df_corpus_valle_del_cauca.pkl`).
**Cierra:** las 3 fallas de scraper que quedaron documentadas como abiertas en la
entrada anterior — diagnosticadas y corregidas (San Andrés queda bloqueado por una causa
externa distinta, no por las 3 fallas originales).
**Abre:**
- Fusionar estos 3 pkl con el corpus nacional (decisión pendiente, ver arriba).
- Si se fusiona: `datos/scores/scores_v2_32deptos.pkl` queda desactualizado para estos
  departamentos — la correlación V2 (+0.384, entrada del 2026-08-30) y el AUC del
  pre-filtro (entrada del 2026-08-31) se midieron sobre el corpus viejo de estos 3
  lugares. Re-medir es la tarea 3b/3c del backlog ("repetir con corpus limpio"), no algo
  automático — cuesta GPU (regla 8) y el propio `PROMPT_ARRANQUE.md` ya lo preveía como
  paso posterior a 1b, no parte de 1b.
- Reintentar San Andrés y Providencia cuando El Tiempo se estabilice — probar primero
  con una petición suelta a `eltiempo.com/buscar/` antes de relanzar el departamento
  completo (mismo consejo que la entrada anterior, sigue vigente).
- Se encontró y corrigió el mismo patrón de bug de timeout (`session.get(link,
  timeout=15)` total en vez de granular) en otros 10 scrapers del archivo, sin
  confirmar si también los afecta — fuera de alcance de esta tarea, queda como
  sugerencia aparte (chip `task_fa136510`).

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
**Nota (2026-08-31):** la entrada siguiente RECHAZA el pre-filtro a nivel de indicador.
Si esa decisión se confirma para producción, estos cortes (calibrados "con pre-filtro")
quedan invalidados por la regla 2 y hay que recalibrarlos sobre la distribución sin
pre-filtro antes de promover nada a `src/`.

## [2026-08-31] A/B del pre-filtro social V2, con AUC y control absurdo por indicador — RECHAZADO (umbral 0.85)

**Pregunta (backlog punto 3):** el A/B a nivel de radar agregado (entrada anterior,
2026-08-30) dio Spearman +0.376 con pre-filtro 0.85 vs +0.384 sin — "diferencia dentro
del ruido", y la propia entrada decía que no alcanzaba para decidir: faltaba el AUC y el
control absurdo por indicador, que es justo lo que pide la regla 1. Esta entrada mide eso.

**Método:** sobre `datos/scores/scores_v2_32deptos.pkl` (11.439 artículos, 32
departamentos, `ent_`/`neu_` sin enmascarar — sin volver a tocar la GPU, regla 8). Única
variable que cambia: aplicar o no `score_social_v2 >= 0.85` como máscara (forzar a 0 los
artículos que no pasan) antes de puntuar (regla 7). AUC contra estándar de plata en los 2
indicadores que lo tienen (`grupos_etnicos_existentes`, `presencia_grupos_armados`,
`experimentos/silver.py` + `hipotesis_base.KEYWORDS_SILVER`), en `ent` crudo y en score
corregido (`clip(clip(ent−sesgo,0)*(1−neu),0,1)`, la fórmula de producción V2). IC95% de
la diferencia por bootstrap (2.000 remuestreos, n=871–1.335 positivos de plata — mucha
más potencia que el n=32 departamental de la regla 11, que no aplica aquí). Control
absurdo por indicador: AUC de `NULA_TEST` (osos polares, reservada, nunca calibra el
sesgo — regla 4) contra los MISMOS silver labels, con y sin la máscara — para separar "el
pre-filtro discrimina el indicador real" de "el pre-filtro solo correlaciona con el tema
y por eso separa cualquier cosa, real o absurda, igual de bien". Script:
`experimentos/exp_prefiltro_auc_indicador.py`
(`resultados/exp_prefiltro_auc_indicador.xlsx`). Verificado con una revisión adversarial
de 3 lentes independientes (bugs de implementación, cumplimiento de reglas duras,
sensatez de la interpretación) antes de cerrar esta entrada; encontró un bug real menor
(la media corregida del control absurdo en escala completa se calculaba pero no se
guardaba en el Excel) — corregido y el script re-corrido; no cambió ningún número ya
reportado (ver el script, semilla de bootstrap fija).

**Evidencia:**

```
indicador                    escala            AUC sin   AUC con    delta        IC95%
grupos_etnicos_existentes    ent crudo          0.8413    0.7823   -0.0589   [-0.0734,-0.0450]
grupos_etnicos_existentes    score corregido    0.8323    0.7791   -0.0531   [-0.0662,-0.0402]
presencia_grupos_armados     ent crudo          0.8578    0.8210   -0.0369   [-0.0469,-0.0278]
presencia_grupos_armados     score corregido    0.8232    0.7963   -0.0269   [-0.0355,-0.0191]
```

Las 4 caídas tienen IC95% que excluye cero: el costo es real, no ruido de muestreo. El
pre-filtro retiene 89.1% / 92.7% de los positivos de plata a escala nacional (consistente
con el 92.4%/95.0% medido en `exp_agregacion_v2.py` sobre el corpus de 5 lugares, que fue
la única base con la que se eligió 0.85) — pero ese ~7-11% que SÍ se fuerza a 0 cae al
fondo del ranking y cuesta muchas comparaciones por pares en el AUC, mucho más de lo que
sugeriría la tasa de pérdida por sí sola.

**Control absurdo:** `NULA_TEST` contra los mismos silver labels gana algo de AUC con el
pre-filtro en `ent` crudo (+0.0117 y +0.0234, IC excluye cero en ambos — el pre-filtro sí
correlaciona algo con el tema), pero esa ganancia **casi desaparece en score corregido**
(+0.0019 y +0.0022, IC rozando cero) — la resta de sesgo ya neutraliza ese artefacto. Es
mucho menor que la caída de los indicadores reales en la misma escala (-0.0531 y -0.0269):
el costo del pre-filtro no se explica por ese artefacto. Control absurdo en escala
completa (sin condicionar a silver labels): prácticamente plano (media cruda 0.2142→
0.2034, prop>0.9 5.7%→5.5%, media corregida 0.0203→0.0193) — el pre-filtro no lo rompe,
tampoco lo mejora de forma que compense.

**Decisión:** RECHAZADO el pre-filtro social V2 con umbral 0.85, para los 2 indicadores
medidos. Caída de AUC clara y estadísticamente distinguible de cero en las 2 escalas y
los 2 indicadores; el control absurdo no la explica (gana mucho menos de lo que pierden
los indicadores reales, y nada en la escala que usa producción). No es la lectura que
sugería el A/B agregado del 2026-08-30 ("apunta a prescindible") — a nivel de radar por
P75 con 87% de artículos pasando el filtro, forzar a 0 el 7-11% de los positivos se
diluye; a nivel de AUC por artículo no.

**Alcance de la decisión — no sobregeneralizar:**
- Solo se probó el umbral **0.85** (regla 7, una variable). No dice nada sobre si algún
  otro umbral sí pasaría el control; recalibrar el umbral sería un experimento aparte.
- El estándar de plata cubre 2 de 26 indicadores. La generalización a los otros 24 es
  plausible (el pre-filtro es uniforme por artículo, no específico de un indicador) pero
  **no medida**.

**Cierra:** "el pre-filtro es prescindible" (no lo es: hace daño medible) y "hace falta
el AUC por indicador antes de decidir" (backlog punto 3, ya no está pendiente para estos
2 indicadores).
**Abre:**
- Si se decide sacar el pre-filtro de la receta V2 antes de promoverla a `src/` (regla 9,
  paso de promoción aparte, no hecho todavía): los cortes Bajo/Medio/Alto del
  2026-08-30 (entrada anterior) se calibraron "con pre-filtro" y quedan inválidos por la
  regla 2 — recalibrar sobre la distribución sin pre-filtro.
- Backlog punto 4 (ampliar el estándar de plata) ahora importa más: esta decisión
  descansa en 2 de 26 indicadores.

## [2026-08-31] Cortes fijos Bajo/Medio/Alto recalibrados SIN pre-filtro — ADOPTADA

**Pregunta:** el pre-filtro se rechazó (entrada anterior). Regla 2: si cambia lo que se
mide, recalibrar el umbral — los cortes 0.30/0.35 del 2026-08-30 se calibraron "con
pre-filtro" y ya no aplican.

**Método:** igual que `exp_cortes_fijos_v2.py` (huecos naturales en la distribución de
`radar_propio`, sin mirar el oficial; verificar después contra anclas y accuracy), pero
con `con_prefiltro=False`. Script nuevo:
`experimentos/exp_cortes_fijos_v2_sin_prefiltro.py`
(`resultados/exp_cortes_fijos_v2_sin_prefiltro.xlsx`). La primera pasada (los 2 huecos más
grandes sin más) rompió la ancla "Putumayo nunca Bajo" — se corrigió la selección para
buscar, entre los pares de huecos genuinos (>0.008) que no rompen ninguna ancla, el de
clasificación más balanceada (no solo el hueco más grande: maximizar el hueco a secas
eligió una combinación técnicamente válida pero degenerada, 25 Medio/4 Alto/3 Bajo).

**Cortes adoptados:**

```
Bajo   : radar_propio <  0.3074
Medio  : 0.3074 <= radar_propio < 0.3524
Alto   : radar_propio >= 0.3524
```

Distribución: 8 Bajo / 15 Medio / 9 Alto. Ninguna ancla rota.

**Accuracy: 25.0%**, contra 37.5% de los terciles ad hoc de la misma distribución. Es más
baja que el histórico V0 (31.2%) y que los cortes "con prefiltro" del 2026-08-30 (31.2%).
**Se registra tal como salió, sin buscar otro punto que mejore el número** — hacerlo sería
exactamente el sobreajuste contra el conjunto de evaluación que
`09_riesgos_y_limites.md` señala, y el propio precedente del 2026-08-30 ya estableció que
la diferencia con los terciles ad hoc es "el costo esperado de no optimizar directamente
contra el oficial", no una señal de que el corte esté mal. Con n=32 (regla 11, SE~8pp) la
diferencia entre 25.0% y 37.5% (12.5pp) no es concluyente por sí sola.

**Decisión:** ADOPTADA. Estos cortes (no los del 2026-08-30) son los que se promovieron a
`src/config_pipeline.py` (`CORTE_BAJO_MEDIO_RADAR`/`CORTE_MEDIO_ALTO_RADAR`) en la entrada
siguiente.
**Cierra:** qué cortes corresponden a la receta V2 sin pre-filtro.
**Abre:** si se fusiona el corpus re-scrapeado de la tarea 1b y se vuelve a puntuar con
GPU, estos cortes también quedan pendientes de recalibrar (regla 2).

## [2026-08-31] Promoción de V2 a `src/` — producción deja de ser V0

**Contexto:** con el radar V2 corregido (hipótesis sin marco metalingüístico, sesgo por
artículo descontado, P75 en vez de MAX, pre-filtro rechazado, cortes fijos recalibrados)
todo medido en `experimentos/` desde el 2026-08-27, nada se había promovido a `src/`
(regla 9). El usuario pidió avanzar en "radar, transformers e indicadores" evitando
scraping nuevo; autorizó GPU para transformers.

**Hallazgo antes de tocar nada — `radar.py` no tenía UN cálculo de radar, tenía tres,**
mutuamente inconsistentes, y ninguno coincidía con la fórmula P75+cortes fijos ya
validada:
1. `CalculadorRadar.calcular()` — promedio simple de scores crudos por artículo (usado
   por `test_integracion.py`).
2. El flujo por defecto de `orquestador_pipeline.py --only todo` — exporta el MÁXIMO por
   indicador a un CSV (`exportar_indicadores_transformers_por_departamento`) y lo
   re-agrega con la operación "bloques" (en la práctica, MAX + z-score + terciles).
3. La operación "indicadores_transformers" — pondera por bloques con pesos ALEATORIOS y
   un sistema de poda al top-N por accuracy contra el propio DANE
   (`ejecutar_experimentos_radar`), el mismo riesgo de sobreajuste que
   `09_riesgos_y_limites.md` señala para la revisión de indicadores de agosto. Era además
   el default de `orquestador_pipeline.py` sin flags (`--operaciones-radar` default
   incluía ambas operaciones, con `rng.choice` entre ellas).

**Segundo hallazgo — `metricas_y_calculo_de_error.py` no usaba la clasificación oficial
real del DANE.** `_leer_oficial_v3` lee `Clasificacion_radar_oficial_promedio` (la
columna oficial de `comparacion_radares_V3.xlsx`), pero tanto
`calcular_metricas_experimento` como el camino legado
`procesar_metricas_multi_experimento` la ignoraban y hacían
`cat_oficial = _clasificar(radar_oficial_promedio)` — re-tercilaban el número crudo del
DANE con una función propia, en vez de usar la columna que el DANE ya trae. Verificado
que para los departamentos comprobados a mano (Caquetá, Sucre, Putumayo) el resultado
coincidía por casualidad, pero nada en el código garantizaba eso — es distinto de lo que
hacen TODOS los scripts de `experimentos/`, que siempre usan la columna oficial
directamente.

**Decisión de arquitectura (confirmada con el usuario):** un solo camino limpio con P75 y
cortes fijos, sin pesos aleatorios. El sistema de pesos/poda-top-N se deja intacto pero
deja de ser el default — no se borra, no se toca su lógica interna, sigue disponible
pasando `--operaciones-radar indicadores_transformers` a mano.

**Cambios en `src/`:**

- **`Transformer_optimo.py`:** hipótesis V0 → V2 (verificado byte a byte idéntico a
  `experimentos/hipotesis_v2.py` antes de correr nada — ver script de verificación más
  abajo). Pre-filtro social retirado (`self.umbral_social`, `self.hipotesis_social`, el
  descarte de artículos en `procesar()`): se puntúan los 26 indicadores sobre TODOS los
  artículos. Se agregó la calibración de sesgo (4 `NULAS_CALIBRACION`, nunca la nula
  reservada) y la fórmula corregida `clip(clip(ent-sesgo,0)*(1-neu),0,1)` — antes no
  existían en producción. `_nli_batch` ahora puede devolver también `P(neutral)`
  (`devolver_neutral=True`), necesario para la fórmula. `exportar_indicadores_transformers_por_departamento`
  cambia de MAX (`idxmax`) a **P75 por rango más cercano** (no interpolado: el valor
  siempre es el de un artículo real, así que el CSV de "fuentes" para verificación manual
  sigue teniendo sentido).
- **`radar.py`:** `_calcular_bloques_desde_tasas` (el camino por defecto) y `calcular()`
  ya no llaman a `_calibrar_escala` (z-score hacia media=31.4/std=7.6 del DANE — monótona,
  no cambiaba el orden, pero los cortes fijos están calibrados sobre la escala P75
  natural, no sobre esa) ni a `_categoria_terciles`; usan la nueva
  `_categoria_cortes_fijos` con `CORTE_BAJO_MEDIO`/`CORTE_MEDIO_ALTO` (leídos de
  `config_pipeline.py`, ver abajo). `calcular()` además cambia su agregación de `.mean()`
  a P75 por rango más cercano (`_p75_rango_cercano`), consistente con
  `Transformer_optimo.py`. `_calcular_indicadores_transformers` (pesos aleatorios) **no
  se tocó** — sigue con terciles + z-score, es el camino legado.
- **`config_pipeline.py`:** nuevas `CORTE_BAJO_MEDIO_RADAR = 0.3074` /
  `CORTE_MEDIO_ALTO_RADAR = 0.3524` (entrada anterior) — viven aquí, no en `radar.py`,
  para que `metricas_y_calculo_de_error.py` los use sin crear un import circular
  (`radar.py` ya importa `metricas_y_calculo_de_error`).
- **`orquestador_pipeline.py`:** default de `--operaciones-radar` cambiado de
  `"bloques,indicadores_transformers"` a `"bloques"` — con una sola operación en la
  lista, `rng.choice` siempre la devuelve, así que el CLI sin flags queda determinista
  sin tocar `--desactivar-aleatoriedad`.
- **`metricas_y_calculo_de_error.py`:** `cat_oficial` ahora usa la columna
  `Clasificacion_radar_oficial_promedio` real (con fallback a `_clasificar` + aviso
  impreso si el Excel no la trae, solo en el camino legado de Excel ancho). `cat_exp`
  (nuestra clasificación) usa la nueva `_categoria_cortes_fijos` en vez de terciles, en
  los dos caminos (`calcular_metricas_experimento` y el legado
  `procesar_metricas_multi_experimento`).

**Verificación — dos niveles, siguiendo la regla 6 adaptada a un cambio de fórmula:**

1. **Offline, sin GPU** (`experimentos/exp_verificar_promocion_v2.py`): la receta completa
   traducida a `src/` (V2 + sesgo + P75 rango-más-cercano + cortes fijos + clasificación
   oficial real), recalculada sobre `scores_v2_32deptos.pkl` (ya existente).
   `Spearman(radar_V2_producción, radar_oficial) = +0.4208` (p=0.017) — no se aleja de
   +0.384 (P75 lineal, `exp_correlacion_v2_nacional.py`), la diferencia es consistente con
   el cambio de interpolación lineal a rango-más-cercano. Ninguna ancla rota. Accuracy
   25.0%, igual que la entrada anterior (mismos cortes, misma fuente).
2. **Con GPU, sobre el corpus de 5 lugares (1.647 artículos, ya existente — sin scraping
   nuevo)** (`experimentos/exp_smoke_test_produccion_v2.py`, log en
   `resultados/log_smoke_test_v2.txt`): se corrió `src/Transformer_optimo.py` REAL de
   punta a punta (32.3 min GPU) y se comparó contra `nli_core` calculando lo mismo de
   forma independiente — sesgo y los 2 indicadores con estándar de plata, max\|dif\| ~5e-7,
   muy por debajo de la tolerancia (1e-4). El resultado se guardó como el nuevo baseline
   de verificación, `datos/scores/df_procesado_baseline_v2.pkl` — el baseline V0
   (`df_procesado_baseline.pkl`) queda obsoleto para verificar producción, se conserva
   como referencia histórica. `nli_core.py` gana `verificar_contra_produccion_v2()`
   (aplica la fórmula corregida, sin la máscara del pre-filtro V0); el skill
   `experimento-hipotesis` (Paso 0) se actualizó para usarla.
3. `python -m py_compile` limpio en los 5 archivos tocados. `src/test_integracion.py`
   (10 tests, sin GPU) sigue pasando sin modificarlo — no afirma valores exactos de
   `radar_propio`/`categoria_riesgo`/`accuracy`, solo estructura y tipos.

**Decisión:** ADOPTADA. Producción (`src/`) deja de correr V0. `python src/orquestador_pipeline.py`
(sin flags) ahora corre: hipótesis V2, sin pre-filtro, P75, cortes fijos, clasificación
oficial real. El sistema de pesos aleatorios/poda sigue existiendo pero ya no es el
default de nada.
**Cierra:** "nada de V2 está en `src/`" (backlog punto 2 y toda la revisión de agosto,
regla 9 — se registra la promoción). El bug de clasificación oficial en
`metricas_y_calculo_de_error.py`.
**Abre:**
- **No se re-puntuó con GPU el corpus nacional completo** (32 departamentos): el pkl que
  produciría `src/` corriendo de verdad sobre los 32 departamentos todavía no existe;
  `scores_v2_32deptos.pkl` (de `experimentos/`, vía `nli_core`) sigue siendo el único
  insumo nacional. Correrlo con el código de `src/` ya promovido es un paso aparte, de
  ~4h GPU, no hecho — el usuario pidió minimizar costo esta sesión.
- La fusión del corpus re-scrapeado (backlog 1b) sigue pendiente y, cuando se decida,
  invalida de nuevo los cortes fijos (regla 2) y el baseline de verificación.
- El sistema de pesos aleatorios/poda-top-N sigue sin resolver como deuda técnica: es
  código funcional pero con un riesgo metodológico documentado, no usado por defecto,
  sin plan de retirarlo ni de arreglarlo.

## [2026-08-31] Revisión adversarial de la promoción — 5 defectos encontrados y corregidos

**Contexto:** al escribir un documento de orientación para el usuario
(`contexto/10_combinaciones_y_rumbo.md`) se lanzó una verificación con tres revisores
independientes (cifras, código, honestidad intelectual) contra el repositorio. Encontró
defectos reales **en la promoción del mismo día**, que la verificación original no detectó
porque comprobó la fórmula offline y el scorer con GPU, pero **nunca corrió el comando
end-to-end que se documentó**.

**Defectos corregidos:**

1. **Los cortes fijos se calibraron sobre la distribución equivocada.** 0.3074/0.3524
   salieron del P75 **interpolado** (`np.quantile` en `exp_correlacion_v2_nacional.py`),
   pero producción agrega con P75 por **rango más cercano** — otra distribución
   (max|dif| 0.0219). En la distribución real, 0.3074 caía en un hueco de 0.0071, **por
   debajo del umbral de 0.008 que el propio script exige** para considerarlo hueco. Es el
   caso literal de la regla 2. Recalibrados sobre la distribución correcta →
   **0.2969 / 0.3527**. Accuracy sin cambio (25.0%), anclas intactas.
2. **El camino legado de métricas aplicaba los cortes V2 a columnas en escala 0–100.** Al
   cambiar `_clasificar` por `_categoria_cortes_fijos` en
   `procesar_metricas_multi_experimento` se rompió: las 13 columnas `EXPERIMENTO_*` del
   Excel ancho van de 0 a 100, así que con corte 0.3527 caían casi todas en "Alto"
   (medido: 20 de 21 en `EXPERIMENTO_1`), y esas accuracies sin sentido eran las que se
   imprimían como RESUMEN FINAL. Revertido a terciles en ese camino; los cortes fijos
   quedan solo en `calcular_metricas_experimento`, que recibe el radar en su escala.
3. **El comando por defecto reventaba después de las ~4 h de GPU.** `--nombre-experimento`
   tenía default `experimento_1`, y esa columna ya existe en
   `datos/referencia/comparacion_radares.xlsx`: `_actualizar_excel_experimento` lanzaba
   `ValueError` y el orquestador moría con `sys.exit(1)` **después** de la etapa de
   transformers. Default cambiado a vacío → `radar.py` elige el siguiente índice libre con
   `_siguiente_indice_experimento`, que ya existía.
4. **`src/pipeline_lugares.py` reventaba con `KeyError`** al retirar el pre-filtro: leía
   `grupo["score_social"]` sin guarda y esa columna ya no se genera.
5. **La rama de scraping del orquestador era código muerto:** llamaba
   `tf.sc.FECHA_DESDE`, pero `Transformer_optimo` ya no tiene atributo `sc` (el import de
   `scrappers` se movió dentro de `correr_scraping`). Cambiado a `cfg.FECHA_DESDE`.

También se corrigió una inconsistencia menor: `generar_comparacion_experimento` escribía
la columna `Clasificacion_{EXP}` con terciles mientras la accuracy de la misma llamada se
calculaba con cortes fijos.

**Defectos NO corregidos, documentados como abiertos** (requieren una decisión, no un
parche):

- **`CargadorCorpus.cargar()` hace glob de TODOS los `df_corpus_*.pkl`.** Una corrida real
  levanta **12.592 artículos y 35 valores de `departamento`** (incluye "Municipio Maicao",
  "Vereda Paraguachón", "Antioquia (2023)"), no 11.439 / 32. Un re-puntuado nacional
  produciría 35 filas de radar. Hay que decidir qué corpus debe cargar producción.
- `src/pipeline_lugares.py` y `src/generar_max_articulos_por_departamento.py` siguen con
  cortes 1/3–2/3 y agregación MAX (rechazada). Fuera del camino por defecto.
- `experimentos_radar.jsonl` registra `"promedio_simple_36_indicadores"` y
  `"calibracion": "zscore_media31.4_std7.6"` para la operación "bloques": son 26
  indicadores y no hay z-score.

**Errores de documentación corregidos** (afectaban a `10_combinaciones_y_rumbo.md`,
`09_riesgos_y_limites.md` y `07_backlog.md`):

- **El modelo nulo da 28.1%, no 31.2%.** El 31.2% de `09_riesgos_y_limites.md` salió de
  re-tercilar el número crudo del DANE — el mismo bug corregido en `src/`.
- **La etiqueta "tres indicadores muertos" es inexacta a escala nacional.** El "0.0000
  incluso en P90" solo vale para el corpus de 5 lugares. Nacional, P90:
  `irregularidad_contractual` 21/32 deptos > 0 (max 0.3586), `debilidad_institucional`
  7/32 (max 0.1419), `danos_ambientales` 3/32. El único realmente en cero en P75 es
  `danos_ambientales`.
- **San Andrés y Providencia tiene 79 artículos en el corpus, no 0.** El 0 fue solo el
  resultado de la corrida de re-scraping del 31-08.
- **El Spearman +0.067 del V0 no es reproducible desde V0+MAX** (da −0.18): corresponde a
  la columna `Radar_completo_promedio_normalizado`, cuya procedencia
  `09_riesgos_y_limites.md` ya declaraba sin resolver. O sea, el punto de partida de la
  comparación "+0.067 → +0.42" es un radar no identificado.
- `Spearman(nº artículos, radar oficial)` recalculado da −0.31, no −0.26.
- El patrón de bug de timeout está en 15 clases de scraper, no en 10.

**Argumentos rechazados por no sostenerse** (estaban en el borrador del documento):

- *"E tiene el Spearman más alto"* como razón para preferir los cortes de E: el Spearman es
  **invariante a los cortes**, así que no puede justificar un juego de cortes sobre otro.
- *"E no rompe ninguna ancla"*: las cinco combinaciones pasan las anclas, y los cortes de E
  se eligieron filtrando por esa condición — la cumple por construcción.
- *Aplicar la regla 11 solo cuando conviene*: B (40.6%) menos E (25.0%) son **15.6 pp, por
  encima** del umbral de ~15 pp del propio proyecto. B le gana a E en la métrica oficial de
  forma distinguible, y hay que decirlo. La defensa de E se sostiene en que los terciles no
  son desplegables y en la decisión sobre el pre-filtro, no en que E sea "mejor".
- *"evidencia más fuerte que la accuracy"* para el AUC: son ejes distintos (discriminación
  del indicador vs acuerdo del radar con el DANE), no una comparación de potencia.

**Decisión:** ADOPTADAS las 5 correcciones de código y las correcciones de documentación.
`py_compile` limpio y `test_integracion.py` (10 tests) pasa.
**Cierra:** la idea de que la promoción del 2026-08-31 estaba verificada de punta a punta —
no lo estaba: faltaba correr el comando documentado.
**Abre:** decidir qué corpus debe cargar producción (punto 1 de los no corregidos), que
bloquea el re-puntuado nacional.

## [2026-09-08] Reescritura de `rechazo_proyecto`, `exclusion_beneficios_economicos` y
`derechos_vulnerados` (rama `prueba_radar_max`) — RECHAZADA

**Pregunta:** una revisión cualitativa externa señaló falsos positivos en
`rechazo_proyecto` y `exclusion_beneficios_economicos`, y solapamiento/exceso de
positivos en `derechos_vulnerados`. Se propuso una reescritura más específica para
las tres:

```
rechazo_proyecto
  vieja: "Hay oposición de comunidades o autoridades a un proyecto."
  nueva: "Una comunidad o autoridad se opuso a la ejecución de un proyecto específico."
exclusion_beneficios_economicos
  vieja: "Una comunidad quedó excluida de los beneficios económicos de un proyecto."
  nueva: "Una comunidad no recibió compensaciones o beneficios económicos de un proyecto."
derechos_vulnerados
  vieja: "Se vulneraron los derechos de una comunidad."
  nueva: "Una comunidad denunció la vulneración de sus derechos."
```

¿La reescritura reduce los falsos positivos sin perder los positivos reales, y sobrevive
el control absurdo?

**Método:** ninguno de los tres indicadores tiene estándar de plata (solo lo tienen
`grupos_etnicos_existentes` y `presencia_grupos_armados`). Se generó plata por keywords
para los tres (candidato) y se descartó: los términos sueltos (`rechazo`, `oposición`,
`derechos humanos`) resultaron demasiado polisémicos (4.1%, 2.4% y 10.4% de 11.439
artículos nacionales) y las frases completas dieron 0 positivos por ser matching literal
sin variación sintáctica. Se optó por anotación manual: se leyeron a mano los 102
artículos de una muestra estratificada de Antioquia (494 artículos totales, corpus
`df_corpus_combinado_32deptos.pkl` filtrado por departamento), con candidatos
preseleccionados por keywords laxas más negativos aleatorios. Positivos encontrados:
`derechos_vulnerados` 12/102, `rechazo_proyecto` 2/102, `exclusion_beneficios_economicos`
0/102. Verificado antes de puntuar: `nli_core.verificar_contra_produccion_v2()` OK
(max\|dif\| ~9.7e-07) para las tres hipótesis vigentes contra
`datos/scores/df_procesado_baseline_v2.pkl`.

Se puntuaron los 102 artículos (texto completo, sin enmascarar — regla 8) con vieja y
nueva hipótesis, sesgo descontado con las 4 `NULAS_CALIBRACION` estándar, y control
absurdo con `NULA_TEST` reescrita en el formato de cada variante nueva (regla 3) —
`nula_test_rechazo_nueva`, `nula_test_exclusion_nueva`, `nula_test_derechos_nueva`.
Script: `experimentos/exp_variantes_3indicadores_antioquia.py`. Resultado guardado sin
enmascarar en `datos/scores/scores_variantes_3indicadores_antioquia.pkl`. Etiquetas manuales en
`resultados/muestra_manual_antioquia_3indicadores.xlsx`.

**Evidencia:**

| Indicador | AUC vieja→nueva | Separación vieja→nueva | Control absurdo vieja→nueva |
|---|---|---|---|
| `derechos_vulnerados` (n_pos=12) | 0.6435→0.7593 | 0.1152→0.2557 | 0.0224→**0.1347** |
| `rechazo_proyecto` (n_pos=2, AUC no confiable) | — | media_neg 0.3522→0.5271 | 0.0224→**0.4776** |
| `exclusion_beneficios_economicos` (n_pos=0, sin AUC) | — | media_neg 0.5541→0.2144 | 0.0224→**0.2578** |

El control absurdo empeoró en los tres, en un caso de forma extrema
(`rechazo_proyecto`: 2.2%→47.8%). En `derechos_vulnerados` el AUC y la separación
mejoraron, pero coincide con el patrón exacto de la regla 1: el AUC sube y el control
empeora. Se interpreta como un efecto de formato: las tres reescrituras alargan la
hipótesis con sustantivos concretos («la ejecución de un proyecto específico»,
«compensaciones o beneficios económicos», «denunció la vulneración de sus derechos») que
calzan con una plantilla narrativa («alguien se opuso a algo», «alguien denunció algo»)
muy común en prensa, y el modelo tiende a confirmarla por la forma, no por el contenido
— igual que ya pasó tres veces antes con el marco metalingüístico (regla 1).

**Decisión:** RECHAZADAS las tres reescrituras. Se conserva el texto vigente de las 26
hipótesis en `src/Transformer_optimo.py` sin cambios.

**Cierra:** esta redacción puntual de las tres hipótesis, con este método de plata
(anotación manual sobre Antioquia). No se reintenta sin evidencia nueva.
**Abre:** el problema real que motivó el cambio (falsos positivos observados en
`rechazo_proyecto`/`exclusion_beneficios_economicos`, solapamiento en
`derechos_vulnerados`) sigue sin resolver — una reformulación futura debería evitar
sustantivos concretos tipo "proyecto específico"/"compensaciones" que parecen inflar el
control absurdo, y probarse con el mismo método (plata manual + control absurdo en el
formato de la variante) antes de mirar el AUC. Ampliar el estándar de plata manual más
allá de Antioquia (backlog punto 4) ayudaría a que `exclusion_beneficios_economicos`
deje de depender de n=0.

## [2026-09-22] Fase 0 del plan de 5 indicadores bajo MAX (`experimentos/PLAN_5ind_MAX.md`) — verificación de entorno

Rama `hipotesis-5ind-max` desde `radar-max_Septiembre` (71072a1). Cherry-pick de a9c84a0 y
2a0a01d sin conflictos (no tocan `src/`). Agregación MAX sin cambios.

- `nli_core.verificar_contra_produccion_v2()` sobre `datos/scores/df_procesado_baseline_v2.pkl`:
  OK en los 5 indicadores (max|dif| entre 9.2e-07 y 9.8e-07). `src/test_integracion.py`: 10/10.
- `resultados/tablas_lugares_max/df_procesado_5lugares.pkl` es idéntico a
  `df_procesado_baseline_v2.pkl` en los 5 indicadores (max|dif| = 0).
- MAX actual reproducido; coincide con `resumen_indicadores_MAX_y_articulos_por_lugar.xlsx`
  para Antioquia y Maicao. Los `radar_resumen_*.xlsx` de la profesora no están en el repo.
- Paraguachón (pkl individual, 77): las 77 URL ya están en `df_corpus_5lugares.pkl`
  (57 asignadas a Maicao, 20 a Paraguachón). Corpus de trabajo deduplicado = **1.647**
  artículos (no ~1.704). Tabla `url → lugares` en `experimentos/resultados/juicio_5ind/url_lugares.csv`.
  MAX Paraguachón-77 difiere del de 20 en `desplazamiento_forzado` (0.985 vs 0.723).
- Premisa de producción = **solo `texto`** (`procesar()` usa `df["texto"]`), no título+texto
  como dice §3 del plan. El juez verá exactamente eso (cuerpo truncado a 512 tokens con la hipótesis).
- `datos/scores/df_procesado_32deptos.pkl` es V0 sin corregir (sin `sesgo`, trae
  `score_social`, medianas crudas ~0.83–0.99), pero **el nacional V2 sí existe**:
  `scores_v2_32deptos.pkl` (11.439 × 58: `sesgo`, `score_social_v2` y pares `ent_`/`neu_` de
  las 26 + `NULA_TEST`, 2026-08-30). Faltaba en `datos/scores/`; estaba en
  `C:\Users\Usuario\Documents\Datos_alexa\Datos\scores\`. Copiado a `datos/scores/`.
  Verificado: filas alineadas 1:1 con `df_corpus_combinado_32deptos.pkl` (título y
  departamento 100%, no trae `url`: se une por posición); las 26 hipótesis de
  `hipotesis_v2.py` están en `src/Transformer_optimo.py`; re-puntuación GPU de 300 filas al
  azar (semilla 0): `sesgo` max|dif| 4.2e-06, `ent_`/`neu_` ≤ 2.9e-05 en `rechazo_proyecto`,
  `presencia_grupos_armados` y `exclusion_beneficios_economicos`.
  **Consecuencia para F7:** los 21 indicadores no tocados y el sesgo se reutilizan; solo se
  puntúan las hipótesis atómicas nuevas de los finalistas (+ piezas/confusores y gemelas).
- Decisión del usuario (2026-09-22): el juez ve **solo el cuerpo** (`texto`), como el NLI.

## [2026-09-22] Fase 1 — pre-registro `experimentos/PREREG_5ind_MAX.md` congelado tras revisión de `orquesta-lead`

`orquesta-lead` (invocado con su definición de `.claude/agents/orquesta-lead.md`; no está
registrado como subagente en la sesión) devolvió 10 correcciones. **Adoptadas 9 + media:**
etiqueta de REAPERTURA de [2026-09-08] con sus defectos de método (y la nota de que aquel
registro dice «NULA_TEST» cuando las gemelas nuevas usaron pingüinos); gemelas de objeto
absurdo con **una sola operación por indicador** (mismo hueco, solo «osos polares»; se
quitaron «focas/morsas», «invasión», «obra de cría»); absurdo total exigido solo como
≤ V01 + 0.05 (en F1 es idéntico entre variantes); artículos con score 0 fuera del pool; M1/M2
definidos en los 4 lugares con denominador min(10, n>0) y regla para lugares sin artículos;
criterio 4 por lugar; kappa sobre SÍ vs {NO, DUDOSO} y kappa < 0.4 ⇒ no se adopta; positivo
de X en L = cualquier artículo del pool de L con SÍ/SÍ en X; regex de desplazamiento con
«huyó/huye/huyen», compuerta sobre la premisa visible truncada; regex de exclusión sin «Caja
de Compensación», de conflicto con `disput` y `combate` acotados.
**No adoptada:** sustituir 0.766 por un umbral por indicador. 0.766 lo fija el plan aprobado
(§5/§7); se declara como límite y se añade como reporte la razón MAX(control)/MAX(variante),
independiente de escala. M3 ya penaliza a las variantes que solo encogen la escala.

## [2026-09-22] Fases 2–5 del plan 5ind MAX — resultado sobre los 4 lugares (criterios 1–5)

F2: 83 hipótesis × 1.647 artículos (87 min GPU) → `datos/scores/scores_5ind_atomicas_lugares.pkl`
(`ent_`/`neu_`/`con_` sin enmascarar). V01 reproduce producción (max|dif| 5.4e-07). Pool TREC:
565 artículos, 15 lotes; juez-a (sonnet) y juez-b (opus), ciegos. Detalle:
`experimentos/RESULTADOS_5ind_MAX.md`, `experimentos/resultados/juicio_5ind/metricas_5ind.xlsx`.

| Indicador | kappa | Positivos SÍ/SÍ (A/M/O/P) | Resultado |
|---|---|---|---|
| `presencia_grupos_armados` | 0.94 | 38/43/0/5 | **V08 (F5: vigente × compuerta léxica) pasa 1–5**: M2 0.17→0.93, M1 2→4 de 4, 0 violaciones M3, AUC plata 0.788→0.879, objeto absurdo ≤ V01 en los 4 lugares. Finalista único; pasa a F7 (holdout). V09/V10 fallan c3, V11 c3 y c5 |
| `conflicto_territorial` | 0.87 | 9/8/0/3 | **RECHAZADAS las 11.** Las mejores (V08/V09/V10, M2 0.57–0.59) no llegan a 0.60 y su gemela de objeto absurdo supera 0.766 en Antioquia |
| `desplazamiento_forzado` | 0.88 | 10/1/0/0 | **RECHAZADAS las 11.** Mejor M2 0.40 (V10). Con 2 lugares sin positivos, M2 medio ≥ 0.60 exige MAX = 0 en Oicatá y Paraguachón |
| `rechazo_proyecto` | 0.46 | 1/3/0/0 | **RECHAZADAS las 11.** M2 ≤ 0.03; solo 4 positivos en todo el pool |
| `exclusion_beneficios_economicos` | −0.00 | 0/0/0/0 | **No adoptable (referencia débil).** Ningún SÍ/SÍ en el pool (A: 1 SÍ, B: 2 SÍ). Aplica la cláusula del §4: se informa al usuario la opción de fusionar con `incentivos_economicos_inequitativos` o retirar, pendiente del holdout |

Hallazgos de método (no cambian el criterio congelado, se registran para no repetir):
- El control de objeto absurdo en F1 es altísimo: «oposición … a un criadero de osos polares»
  da MAX 0.96–0.99 en los 4 lugares con la hipótesis vigente de rechazo; lo mismo en
  desplazamiento y conflicto. **La vigente misma falla el criterio 4** en esos tres. El NLI
  confirma el marco («alguien se opone a algo») con independencia del objeto (regla 1, cuarta vez).
- El 77% de los artículos supera los 512 tokens: el NLI (y por diseño el juez) ve solo el comienzo.
- M2 en lugares sin positivos vale 0 si la variante puntúa algo > 0: con pocos positivos el
  criterio 1 es casi inalcanzable salvo con variantes que anulan el lugar entero (compuerta).

## [2026-09-22] F6 — visto bueno del usuario y recomendación sobre `exclusion_beneficios_economicos`

El usuario **aprobó la Fase 7**. Sobre exclusión delegó la decisión en una recomendación
justificada. **Recomendación adoptada (condicional al holdout):** retirar el indicador del
cálculo del radar, **no** fusionarlo con `incentivos_economicos_inequitativos`. Evidencia: 0
positivos SÍ/SÍ en 565 artículos juzgados; a escala nacional (`scores_v2_32deptos.pkl`, fórmula
V2) su MAX por departamento va de 0.950 a 0.999 (mediana 0.994, std 0.012, la segunda menor de
26): suma una constante sin discriminar. Fusionarlo por MAX sobrescribiría a `incentivos` (std
0.113) con esa constante. Si el holdout (Cauca, Chocó, Cundinamarca) trae algún SÍ/SÍ, no se
retira y se informa. Retirarlo exige recalibrar cortes (regla 2), ya previsto en F7.
Informe del experimento: `experimentos/INFORME_5ind_MAX.md`.

## [2026-09-22] Corrección: `exclusion_beneficios_economicos` NO se retira

El usuario revoca la recomendación de retirar exclusión: **no se quita ningún indicador**; el
radar sigue con 26. El orden es primero corregir los problemáticos (conflicto territorial,
desplazamiento, rechazo a proyecto, exclusión) y solo después discutir retiros. Retirar un
indicador ni siquiera de forma temporal ayuda a corregir los otros (cada uno se puntúa por
separado; solo cambiaría la media y los cortes), así que no se retira. La F7 recalibra cortes
con 26 indicadores (solo cambia grupos armados si V08 pasa el holdout).
Protección: etiquetas locales `base-26ind-radar-max` (71072a1 = `radar-max_Septiembre`) y
`base-26ind-f5` (cb336fa). `src/` no se ha tocado en el experimento.

## [2026-09-22] F7 del plan 5ind MAX — holdout nacional y recalibración de cortes: V08 de `presencia_grupos_armados` ADOPTADA (pendiente de promover en F8)

Scripts: `experimentos/exp_5ind_max_{nacional,holdout,cortes}.py`. Resultados:
`experimentos/resultados/juicio_5ind_holdout/`. Solo se puntuó en GPU lo que faltaba.

**Paso 1 (GPU, 7.3 min).** `presencia_grupos_armados__vig_abs` («En este territorio hay
presencia de osos polares.») sobre los 11.439 artículos → `datos/scores/scores_5ind_atomicas_nacional.pkl`
(`ent_`/`neu_`/`con_` sin enmascarar). Coincide con el pkl de lugares en las 494 URL comunes
(max|dif| 6.4e-06). Vigente, sesgo y absurdo total (= `NULA_TEST`) reutilizados de
`scores_v2_32deptos.pkl` (unión por posición). Premisas visibles nacionales (CPU, 0.5 min):
idénticas a las de F3 en las 494 URL comunes. M4 nacional (solo reporte,
`m4_nacional.csv`): departamentos con MAX de la gemela de objeto absurdo > 0.766: V01 3/32
(Boyacá 0.893, Cesar 0.853, San Andrés 0.790) → V08 1/32 (Cesar 0.853, su artículo pasa la
compuerta); V08 nunca sube el MAX de la gemela en ningún departamento (máx. Δ = 0). Absurdo
total > 0.766 en 1/32 con ambas.

**Paso 2 (holdout Cauca 598, Chocó 148, Cundinamarca 371).** Pool TREC: top-15 (score > 0,
desempate por URL) de V01 y V08 de grupos armados y de V01 de exclusión → 94 artículos, 3
lotes ciegos (semilla 20260922, ids `h0000…`). `juez-a` (sonnet) y `juez-b` (opus), ciegos.

| Indicador | SÍ A | SÍ B | SÍ/SÍ | kappa |
|---|---|---|---|---|
| `presencia_grupos_armados` | 49 | 40 | 40 | 0.81 |
| `desplazamiento_forzado` | 20 | 18 | 18 | 0.93 |
| `conflicto_territorial` | 21 | 19 | 16 | 0.75 |
| `rechazo_proyecto` | 3 | 3 | 3 | 1.00 |
| `exclusion_beneficios_economicos` | 0 | 0 | 0 | indefinida (ningún SÍ) |

Criterio 6 (grupos armados, `metricas_holdout.csv`): M2 Cauca/Chocó/Cundinamarca V01
0.70/0.50/0.20 (media **0.467**) → V08 1.00/0.80/0.50 (media **0.767**). **Cumple** (≥ 0.50 y
≥ V01). M1 verdadero en los 3 con ambas; 0 violaciones M3; gemela de objeto absurdo por
departamento V08 ≤ V01 (0.61/0.42/0.71 vs 0.67/0.52/0.71), todas < 0.766. Con los criterios
1–5 de F5, **V08 pasa los 6 criterios del pre-registro → se adopta** para
`presencia_grupos_armados` (score = s(vigente) · compuerta léxica).

Cláusula de exclusión: **0 SÍ/SÍ** también en el holdout (ningún juez dijo SÍ en 94 artículos,
15 por departamento elegidos por el propio V01 de exclusión). Por decisión del usuario no se
retira (radar con 26); queda para la segunda ronda, que debe buscar positivos con otra
estrategia de muestreo. Positivos SÍ/SÍ del holdout en los otros indicadores (insumo de la
2a ronda): desplazamiento Cauca 5 / Chocó 13 / Cund. 0; conflicto 7/8/1; rechazo 1/0/2.

**Paso 3 (cortes, regla 2).** Procedimiento de `b060b3b` (huecos > 0.008, sin extremos, par
que no rompe anclas y más balanceado; oficial no mirado), 26 indicadores, MAX. Sanidad: con
V01 devuelve exactamente 0.766 / 0.9233. Con V08 en grupos armados: **`CORTE_BAJO_MEDIO_RADAR`
0.766 → 0.7574**, `CORTE_MEDIO_ALTO_RADAR` 0.9233 (igual). La clasificación de los 32 no cambia
(Bajo 6 / Medio 19 / Alto 7, tanto con los cortes nuevos como con los viejos); el corte bajo
se mueve porque San Andrés cae de 0.7376 a 0.7045 y el hueco pasa a estar entre Norte de
Santander (0.7927) y el siguiente. **Ninguna de las 12 anclas se rompe** (se comprueba además
que las 12 existen en los datos; el script original las ignoraba en silencio si el nombre no
coincidía). Constancia: accuracy 0.344 → 0.344; Spearman −0.1653 → −0.1173. MAX de grupos
armados que cambia: Quindío 0.996→0.553, Caldas 0.978→0.725, San Andrés 0.861→0.000, Guainía
0.640→0.011 (los artículos que fijaban esos MAX no nombran un grupo armado en la premisa
visible; no se juzgaron: están fuera del holdout).
Compuerta con la truncación de producción (premisa con la hipótesis vigente de grupos, no la
más larga del experimento): difiere en 16 de 11.439 artículos y no cambia ningún MAX
departamental (max|dif| radar 0) → en F8 se puede implementar con la truncación propia de
la hipótesis.

## [2026-09-22] F8 del plan 5ind MAX — V08 de `presencia_grupos_armados` promovida a `src/`; cortes 0.7574 / 0.9233

Etiqueta local previa: `base-26ind-f7` (705a557, último commit con `src/` intacto).

**Adoptado (promovido):**
- `src/Transformer_optimo.py`: `procesar()` multiplica el score corregido de
  `presencia_grupos_armados` por la compuerta léxica (V08). Regex (`REGEX_COMPUERTA_GRUPOS_ARMADOS`)
  y `normalizar()` copiadas literal de `experimentos/hipotesis_5ind_max.py`; la compuerta mira la
  premisa que ve el NLI con la hipótesis vigente de grupos (`texto` tokenizado sin especiales,
  cortado a 512 − 3 − tokens(hipótesis), decodificado). `src/` no importa de `experimentos/`.
  Columna auxiliar `compuerta_grupos_armados` (como `sesgo`), fuera de `COLUMNAS_BINARIAS`: no
  entra al radar ni a los exportadores (todos filtran por esa lista; comprobado). NLI y los
  otros 25 sin cambios; el radar sigue con 26.
- `src/config_pipeline.py`: `CORTE_BAJO_MEDIO_RADAR` 0.766 → **0.7574**, `CORTE_MEDIO_ALTO_RADAR`
  0.9233 (F7). Actualizados también `CLAUDE.md` (Estado técnico), `README.md`,
  `explicacion_alexa.md` y `ESTADO_DEL_PROYECTO.md`. Los 0.766 que quedan en `experimentos/`
  (plan, pre-registro, scripts) son el umbral congelado del experimento, no el corte del radar.

**Verificación:**
- `python src/test_integracion.py`: 14/14 (4 nuevos: la compuerta abre con ELN, disidencias,
  Clan del Golfo, "frente 36", autodefensas y no con combo, banda, porte ilegal, sicarios, Tren
  de Aragua; solo mira la premisa visible; `procesar()` con NLI simulado la aplica solo a
  grupos; la columna auxiliar no cambia el radar ni aparece en los exportadores).
- Equivalencia offline (`experimentos/exp_5ind_max_f8_equivalencia.py`, sin GPU, corpus
  nacional + `scores_v2_32deptos.pkl`): compuerta de `src/` idéntica a la de F7 con truncación
  de producción en los 11.439 (0 distintos; 16 respecto de la truncación del experimento, como
  midió F7); MAX de grupos por departamento max|dif| 0; `radar_propio` de `CalculadorRadar` vs
  F7 max|dif| 0; clase igual a F7 en los 32 (6/19/7); el procedimiento de `b060b3b` sobre ese
  radar devuelve 0.7574/0.9233 sin romper anclas. (Aplicado sobre `radar_propio` ya redondeado
  a 4 decimales daría 0.9234 — punto medio 0.92335 —; se aplica sin redondear, como en F7.)

**Excel de lugares** (`experimentos/exp_5ind_max_f8_excel_lugares.py`, sin GPU; salida
`experimentos/resultados/excel_lugares_f8/`). Formato tomado de los `radar_resumen_*.xlsx` de la
profesora, que no están en el repo sino en Descargas del usuario (hoja `Resumen`: Dimensión |
Indicador | Score (0-100) | URL artículo top, orden de bloques A–E); no hay script que los
genere en ningún repo local (probablemente salieron de la app desplegada). Se añade una hoja
`Radar` (valor, clase, cortes). Antes = V01 con 0.766; después = V08 (función de `src/`) con
0.7574. Radar: Maicao 0.9625 Alto → 0.9624 Alto; Oicatá 0.6688 Bajo → 0.6437 Bajo; Paraguachón
0.8188 Medio → 0.8188 Medio. Solo cambia grupos armados: Oicatá 65 → 0 (el máximo era un hurto);
Maicao 98 → 98 con otro artículo (masacre en Maicao en vez de "fortalece su seguridad… contra
el crimen"); Paraguachón 99 igual. Coincide con el MAX de V08 de F5 en los 3.
**Hallazgo:** el "antes" regenerado difiere de los Excel de la profesora en 26 de 78 celdas
(Maicao 9, Oicatá 3, Paraguachón 14), siempre con el nuestro mayor; todas sus URL top están en
nuestro corpus con el mismo score (±0.5): sus Excel se hicieron sobre un subconjunto de los
artículos actuales. Sus archivos dejan vacía la URL en scores bajos (≤ 7); los nuestros la
ponen siempre que el score sea > 0.

## [2026-09-22] F8 — revisión final de `orquesta-lead` (una vez, sobre 062ab20): APROBADO, 0 bloqueantes, 5 menores

**Adoptadas (4):**
1. Test que contrasta `premisa_visible` con la premisa que de verdad queda en el par tokenizado
   del NLI (`tokenizer_nli(texto, hip, truncation=True, max_length=512)`) con el tokenizador
   real, para un texto largo, uno corto y uno vacío; se salta si el tokenizador no está
   descargado (`test_12b`). `test_integracion.py`: **15/15**, sin saltos. (El revisor lo
   comprobó además a mano: 0 diferencias en 402 textos.)
2. Trazabilidad del hallazgo sobre los Excel de la profesora: `comparacion_antes_despues.csv`
   trae `score_nuestro_url_profesora` y el script imprime el conteo: sus URL top están en
   nuestro corpus del lugar **69/69**, con |score nuestro ×100 − suyo| ≤ 0.5 en **69/69**.
3. `src/generar_max_articulos_por_departamento.py` aborta si el `df_procesado_32deptos.pkl`
   no trae `compuerta_grupos_armados` (sería anterior a F8 y mezclaría V01 con el corte
   0.7574, calibrado con compuerta).
4. `ESTADO_DEL_PROYECTO.md`: "reemplaza únicamente la agregación por MAX" contradecía la
   sección nueva; ahora menciona la compuerta.

**No aplicada — decisión del usuario al fusionar (5):** `CLAUDE.md` (reglas 5–6, Convenciones),
`README.md` y `explicacion_alexa.md` ("Qué se eliminó") dicen que en la rama no existen
`experimentos/` ni `nli_core`, pero en `hipotesis-5ind-max` sí existen y los documentos nuevos
remiten a `experimentos/INFORME_5ind_MAX.md`. Al fusionar a `radar-max_Septiembre` una de las
dos versiones quedará falsa: si `experimentos/` entra, hay que corregir esas reglas; si no, hay
que sacar el informe de `experimentos/` y cambiar las referencias. No se decide aquí porque
depende de cómo quiera el usuario fusionar.

## [2026-09-23] Informes en `informes/` y relevo de conversación — ADOPTADO (pedido del usuario)

- Nueva carpeta `informes/` para todo informe dirigido al jefe o la profesora, numerado
  (`NN_informe_<tema>.md`), con índice y convención en `informes/README.md`. Un informe entregado
  no se reescribe; los cambios van en el siguiente.
- `experimentos/INFORME_5ind_MAX.md` → `informes/01_informe_5ind_MAX_fases_0-7.md` (git mv),
  recortado a F0–F7; la F8 pasa al informe nuevo `informes/02_informe_fase_8_promocion_grupos_armados.md`.
  Las entradas anteriores de este log citan la ruta vieja; la vigente es la de `informes/`.
  Referencias actualizadas en `ESTADO_DEL_PROYECTO.md` y `explicacion_alexa.md`.
- Relevo para una conversación nueva: `contexto/11_relevo_5ind_MAX.md` (estado, innegociables,
  decisiones cerradas y pendientes, propuesta de 2a ronda, detalles operativos, siguiente paso).
  Punteros en `CLAUDE.md`, `contexto/00_estado_actual.md` y `contexto/07_backlog.md` (item 00).
- Con los informes fuera de `experimentos/`, la corrección 5 de la revisión de F8 se reduce a las
  reglas 5–6 de `CLAUDE.md`, `README.md` y "Qué se eliminó" de `explicacion_alexa.md`; sigue
  pendiente de la decisión de fusión del usuario.

## [2026-09-23] Regla del usuario: de cada indicador solo se cambia la hipótesis — F8 REVERTIDA

**Regla (usuario, 2026-09-23):** de cada indicador solo se puede cambiar la hipótesis (la frase
que evalúa el NLI). No se cambia el cálculo interno (nada de compuertas de palabras clave, `min`
de varias frases, restas de confusores) ni se agregan columnas a la salida. Sustituye al «NLI +
reglas de palabras clave» de `experimentos/PLAN_5ind_MAX.md` §1 y del relevo. Queda como regla 15
de `CLAUDE.md`.

**Revertido:** la promoción de la F8 (commits 062ab20 y 50a553a) aplicaba a
`presencia_grupos_armados` el score × compuerta léxica (V08) y guardaba la columna auxiliar
`compuerta_grupos_armados`: viola la regla. `src/` vuelve al estado de `base-26ind-f7` (idéntico
a `base-26ind-radar-max` = `radar-max_Septiembre`, `git diff` vacío): sin compuerta, cortes
`CORTE_BAJO_MEDIO_RADAR` 0.7574 → **0.766**, `CORTE_MEDIO_ALTO_RADAR` 0.9233. `README.md`,
`explicacion_alexa.md` y `ESTADO_DEL_PROYECTO.md` vuelven a su versión de F7 (describen
`radar-max_Septiembre`); `CLAUDE.md`, `00_estado_actual.md` y `07_backlog.md` se corrigen.

**Verificación (sin GPU):** `python src/test_integracion.py` 10/10.
`experimentos/exp_5ind_max_f8_reversion.py` (corpus nacional + `scores_v2_32deptos.pkl`): `src/`
sin compuerta; `radar_propio` de `CalculadorRadar` = radar V01 de F7 (max|dif| 0); cortes
0.766/0.9233; clasificación 6 Bajo / 19 Medio / 7 Alto; el procedimiento de `b060b3b` devuelve
0.766/0.9233 sin romper anclas. Salida `experimentos/resultados/juicio_5ind_holdout/f8_reversion.csv`.

**Lo que queda como registro (no se borra):** el resultado de F5/F7 (V08 pasó los 6 criterios
del pre-registro congelado) sigue siendo un hallazgo medido, pero **no es promovible** bajo la
regla. `exp_5ind_max_f8_equivalencia.py` y los Excel «después» de
`experimentos/resultados/excel_lugares_f8/` describen la versión revertida (históricos); los
«antes» (V01, corte 0.766) coinciden con producción. Informe: `informes/03_informe_reversion_f8.md`.

**Segunda ronda — redefinida.** La propuesta del relevo §5 (compuertas léxicas) y las cuatro
recomendaciones que el usuario aprobó antes de fijar la regla (pool en 29 departamentos con
top-5, excepción de c4, dos variantes con compuerta en desplazamiento, umbral 0.7574) quedan
**sin efecto**: todas suponían compuertas. El usuario aprobó (2026-09-23) la versión solo-F1:
reescritura de hipótesis de los **5** indicadores (grupos armados vuelve a la lista), filtro en
los 4 lugares reutilizando las etiquetas de F5, finalistas a escala nacional, holdout Cauca /
Chocó / Cundinamarca y recalibración de cortes. Pre-registro: `experimentos/PREREG_5ind_MAX_r2.md`.
