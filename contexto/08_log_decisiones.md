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
