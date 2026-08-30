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
**Estado:** el script está listo y **guarda por checkpoint tras cada hipótesis**, así que
una interrupción ya no cuesta la corrida entera. Reanuda solo; `--reiniciar` empieza de
cero.
**Produce:** `datos/scores/scores_v2_32deptos.pkl` con `ent_` y `neu_` sin enmascarar, de
modo que después se puede analizar todo offline sin volver a la GPU.

**Lo primero que hay que medir con ese pkl:** la correlación del radar V2 corregido con el
oficial. El radar V0 daba +0.067 (cero), pero se midió sobre un radar que ya sabíamos roto.
Si el V2 tampoco correlaciona, el problema no está en los indicadores — ver
`09_riesgos_y_limites.md`.

## 2. Recalibrar los cortes Bajo/Medio/Alto

Con P75 los valores caen entre 0.12 y 0.32 y los cortes 1/3–2/3 mandan **todo** a "Bajo".
Los cortes se calibraron para una escala saturada y ya no significan lo mismo.

**Enfoque acordado:** cortes fijos recalibrados **una sola vez** sobre la distribución de
los 32 departamentos, y congelados. Respeta la restricción de "umbrales fijos, no terciles"
pero calibrados sobre datos. Dos anclajes lo hacen defendible: el suelo lo pone el radar de
la nula (con P75 da exactamente 0.0000), y los cortes salen de la distribución nacional, no
de 4 lugares.

**Depende de:** punto 1.

## 3. A/B del pre-filtro social — con y sin

**Hipótesis:** con la escala corregida puede ser prescindible, porque los artículos
irrelevantes ya puntúan ~0 por sí solos.

**Datos que la motivan:** el pre-filtro V0 anulaba el 33.6% de los positivos de plata de
`grupos_etnicos_existentes` y el 17.7% de `presencia_grupos_armados`, y costaba −0.074 y
−0.024 de AUC. El V2 con umbral 0.85 retiene 92.4% / 95.0% pero solo filtra el 12%.

**Costo:** minutos, si los scores están guardados sin enmascarar.
**Depende de:** punto 1.

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

## 6. Medir la accuracy de V2 contra el oficial

Comparar con el 31.2% histórico.

**Advertencia importante:** son dos afirmaciones distintas y no hay que mezclarlas.
"Los indicadores discriminan mejor" está demostrado (AUC, control absurdo). "El radar
predice mejor el índice oficial" no se ha medido, y hay razones estructurales para dudarlo
—el objetivo mide vulnerabilidad socioeconómica y los indicadores miden conflicto—.
Ver `01_objetivo_y_radar.md`.

Con n = 32 y error estándar ~8 pp, no perseguir mejoras menores a ~15 pp.

**Depende de:** puntos 1 y 2.

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
