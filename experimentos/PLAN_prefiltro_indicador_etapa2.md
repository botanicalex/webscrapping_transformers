# Borrador — Etapa 2 del pre-filtro por indicador: los otros 21 indicadores

Fecha: 2026-09-29 · Rama: `hipotesis-5ind-max` · Estado: **borrador, no pre-registrado, sin cálculos.**

**Cómo se escribió.** Solo a partir del texto de cada hipótesis V2 (`src/Transformer_optimo.py`) y del sentido del indicador. No se
miró ningún puntaje, ningún juicio ni ningún artículo de estos 21 indicadores, ni se calculó cuántos artículos abriría cada lista.
Lo único que se sabe de fuera es el resultado de la etapa 1 (`experimentos/RESULTADOS_prefiltro_indicador.md`): entran grupos
armados y desplazamiento; conflicto, rechazo y exclusión de beneficios quedan sin filtro. Las listas de aquí son **propuestas para
discutir**: al pre-registrarlas quedarían congeladas, como las de la ronda 1, y no se retocarían después de ver datos.

## 1. Criterio de clasificación

- **Objeto concreto:** la hipótesis nombra una cosa, un acto o un actor que un artículo sobre ese hecho tiene que mencionar con
  un vocabulario razonablemente cerrado. Si ninguna de esas palabras aparece en la premisa visible, el artículo difícilmente
  reporta el hecho: la lista es una **condición necesaria** y quitar los que no la cumplen no debería costar casos verdaderos.
- **Abstracto:** el hecho puede decirse de muchas maneras (un juicio de valor, una carencia genérica, un estado). Ninguna lista corta
  es condición necesaria: filtrar sacaría casos verdaderos. **Pasa sin filtro.**
- **Riesgo de apertura (a priori):** cuánto es de esperar que la lista se abra en casi todos los artículos porque sus palabras son
  comunes en la prensa regional («consulta», «tierras», «agua»). Una lista que casi siempre está abierta no filtra nada.
  Es una estimación por el sentido de las palabras, no una medición.

## 2. Clasificación de los 21

| # | Indicador | Hipótesis V2 | Clase | Riesgo de apertura |
|---|---|---|---|---|
| 1 | `reasentamiento` | Se realizó un reasentamiento o reubicación de población. | concreto | bajo |
| 2 | `protesta_social` | Hubo una protesta, manifestación, bloqueo o paro. | concreto | medio |
| 3 | `amenaza_intimidacion` | Hubo amenazas, intimidación u hostigamiento contra personas. | concreto | medio |
| 4 | `resistencia_territorial` | Hay resistencia comunitaria en defensa del territorio o el medio ambiente. | concreto | bajo-medio |
| 5 | `exclusion_comunidades` | Las comunidades exigen ser consultadas o incluidas en las decisiones. | concreto | alto |
| 6 | `deficit_participacion_comunitaria` | No hubo consulta ni participación de la comunidad en un proyecto o decisión. | concreto | alto |
| 7 | `incentivos_economicos_inequitativos` | El reparto de compensaciones o regalías de un proyecto fue desigual. | concreto | bajo |
| 8 | `danos_ambientales` | Hubo daños ambientales, contaminación o pérdida de biodiversidad. | concreto | medio |
| 9 | `conflictos_socioambientales` | Hay un conflicto por el uso del territorio, el agua o los recursos naturales. | concreto | alto |
| 10 | `violacion_derechos_humanos` | Se denunciaron violaciones de derechos humanos. | concreto | medio |
| 11 | `exclusion_servicios_derechos` | Hay población sin acceso a servicios básicos o a sus derechos. | concreto | alto |
| 12 | `grupos_etnicos_existentes` | En este territorio hay comunidades étnicas o pueblos indígenas. | concreto | medio |
| 13 | `movimientos_sociales` | Hay movilizaciones u organizaciones sociales activas. | concreto | alto |
| 14 | `irregularidad_contractual` | Hubo irregularidades o corrupción en contratos públicos. | concreto | alto |
| 15 | `zonas_proteccion_alimentaria` | Hay cultivos, tierras de siembra o producción de alimentos. | concreto | medio |
| 16 | `dano_territorios` | Hubo destrucción, ocupación ilegal o despojo de territorios. | concreto | alto |
| 17 | `amenaza_lideres` | Hubo amenazas o agresiones contra líderes sociales. | concreto | bajo-medio |
| 18 | `derechos_vulnerados` | Se vulneraron los derechos de una comunidad. | **abstracto** | — |
| 19 | `conflicto_activo` | Hay un conflicto activo en este territorio. | **abstracto** | — |
| 20 | `debilidad_institucional` | Las instituciones carecen de recursos o de capacidad para cumplir su función. | **abstracto** | — |
| 21 | `poblacion_afectada` | Hay comunidades o familias afectadas. | **abstracto** | — |

Motivo de los cuatro abstractos: «derechos vulnerados» y «población afectada» se cumplen con cualquier daño; «conflicto activo» con cualquier
conflicto, armado o no; «debilidad institucional» es un juicio sobre capacidad que la prensa expresa sin vocabulario fijo.

## 3. Listas propuestas para los 17 concretos

Expresiones regulares sobre la premisa visible normalizada (minúsculas, sin tildes), en el mismo formato que `REGEX_F5`. Se comprobó
que compilan; no se probaron contra ningún dato.

| Indicador | Lista propuesta |
|---|---|
| `reasentamiento` | `reasent\|reubic\|relocaliz\|traslado de (familias\|comunidades\|poblacion)` |
| `protesta_social` | `protest\|manifestaci\|bloqueo\|\bparos?\b\|marcha\|asonada\|movilizaci\|huelga\|cacerolazo\|planton` |
| `amenaza_intimidacion` | `amenaz\|intimid\|hostig\|panfleto\|extorsi\|acoso\|coaccion` |
| `resistencia_territorial` | `resistencia\|defensa del (territorio\|agua\|ambiente\|medio ambiente)\|guardia (indigena\|cimarrona\|campesina)\|\bminga\b\|consulta popular\|zona de reserva campesina` |
| `exclusion_comunidades` y `deficit_participacion_comunitaria` (misma lista) | `consulta previa\|consult\|particip\|exig\w* (ser )?(escuchad\|incluid\|consultad)\|concertaci\|socializaci` |
| `incentivos_economicos_inequitativos` | `regalia\|compensaci\|reparto\|inequitativ\|desigual\|beneficios? econ\|contraprestaci\|inversion social` |
| `danos_ambientales` | `contaminaci\|derrame\|vertimiento\|deforestaci\|\btala\b\|erosi\|incendio forestal\|biodiversidad\|mineria ilegal\|mercurio\|sequia\|ecosistema\|fauna\|humedal\|paramo\|dano ambiental\|impacto ambiental\|residuos` |
| `conflictos_socioambientales` | `mineri\|hidroelectric\|represa\|fracking\|petrole\|hidrocarbur\|extractiv\|monocultivo\|palma de aceite\|licencia ambiental\|recursos? naturales\|\bagua\b\|\brio\b\|acueducto\|paramo\|humedal` |
| `violacion_derechos_humanos` | `derechos humanos\|\bddhh\b\|masacre\|homicidio\|asesinat\|desaparici\|tortura\|violaci\w* sexual\|ejecucion extrajudicial\|falsos positivos\|detencion arbitraria\|reclutamiento\|secuestro\|lesa humanidad\|defensoria del pueblo\|personeria` |
| `exclusion_servicios_derechos` | `acueducto\|agua potable\|alcantarillado\|energia electrica\|servicios? publicos?\|servicio de salud\|hospital\|puesto de salud\|escuela\|colegio\|educaci\|vivienda\|saneamiento\|sin (agua\|luz\|energia\|salud\|acceso)\|desnutrici\|hambre` |
| `grupos_etnicos_existentes` | `indigena\|\bafro\|raizal\|palenquer\|\brom\b\|gitan\|resguardo\|cabildo\|comunidades? negras?\|consejo comunitario\|etnic\|etnia\|wayuu\|embera\|\bnasa\b\|misak\|arhuaco\|kogui\|wiwa\|\bawa\b\|pijao\|zenu\|nukak\|tikuna\|kankuamo` |
| `movimientos_sociales` | `movilizaci\|organizaci\w* (social\|comunitaria\|campesina\|indigena\|de base)\|movimiento social\|sindicat\|junta de accion comunal\|colectivo\|plataforma\|veedur\|asociaci\w* de\|\bminga\b\|\bparo\b\|marcha` |
| `irregularidad_contractual` | `contrat\|licitaci\|corrupci\|sobrecosto\|peculado\|interventoria\|adjudicaci\|soborno\|cohecho\|detrimento patrimonial\|procuradur\|contralori\|elefante blanco\|obra inconclusa\|investigaci\w* (disciplinaria\|fiscal)` |
| `zonas_proteccion_alimentaria` | `cultiv\|siembra\|cosecha\|agricult\|agropecuari\|alimentari\|seguridad alimentaria\|campesin\|ganad\|pesca\|piscicult\|maiz\|arroz\|\bpapa\b\|\bcafe\b\|platano\|\byuca\b\|frijol\|\bfinca\|parcela\|huerta` |
| `dano_territorios` | `despojo\|usurpaci\|ocupaci\w* (ilegal\|de hecho)\|invasion\|desalojo\|destrucci\|deforest\|apropiaci\|acaparamiento\|baldio\|restituci\|predios?\|tierras` |
| `amenaza_lideres` | `\blider\|lideresa\|defensor(es\|a\|as)? (de\|del\|de la)\|dirigente\|vocero\|firmante de paz\|reclamante\|activista` |

(En las expresiones, `\|` es la barra de alternancia de la regex; está escapada solo por el formato de la tabla.)

## 4. Qué habría que pre-registrar para medirlo

1. **Techo de apertura.** Fijar antes de ver puntajes qué fracción de artículos puede abrir una lista para considerarla un filtro
   (propuesta: si abre en más de la mitad de los 11.439 artículos nacionales, pasa sin filtro). Es un cálculo sobre textos, no sobre
   puntajes ni juicios.
2. **Referencia.** No existe para estos 21 (la plata cubre grupos armados y grupos étnicos; los jueces, 5). Cada indicador necesita un
   codebook SÍ/NO congelado y un pool de jueces, o se declara «no medible» y **no se filtra**. Para `grupos_etnicos_existentes` la plata usa
   palabras clave muy parecidas a la lista propuesta: su AUC sería circular y no valdría como evidencia.
3. **Regla de inclusión.** La de la etapa 1, (a)–(d): ganancia de M2 en los lugares y en el holdout, control absurdo con gemela por
   indicador (con «osos polares» en el hueco del objeto) y M3 sin violaciones nuevas.
4. **Criterios del mecanismo combinado.** Los tres de la etapa 1, con cortes recalibrados por `elegir_cortes`, y retirada de listas en
   un orden declarado.
5. **Costo.** GPU para las gemelas de los 17 en los 4 lugares (17 × 1.647) y en el holdout (17 × 1.117): a razón de unos 1.3
   minutos por hipótesis en los lugares y 1 minuto en el holdout, unos 40 minutos; más los jueces de los pools de cada
   indicador, que son lo que más cuesta.
6. **Multiplicidad.** Con 17 listas, alguna pasará por azar. El pre-registro debe fijar cuántas se admiten como máximo y no
   corregir a posteriori.

## 5. Advertencias

- Las listas de exclusión de beneficios y rechazo de la etapa 1 no mejoraron el M2: el vocabulario de `incentivos_economicos_inequitativos` es
  parecido al de exclusión, así que puede pasar lo mismo.
- Las de riesgo de apertura alto (consulta y participación, servicios, tierras, agua, contratos) probablemente no filtran; conviene
  aplicar el techo del punto 4.1 antes de gastar jueces en ellas.
- La regla 15 sigue valiendo: cada lista es un cálculo interno del indicador y solo la excepción confirmada por el usuario la permite.
- Nada de esto cambia la agregación MAX ni el radar de 26 indicadores.
