# Informe 12 — Pre-filtro por indicador: qué es, qué se midió y qué quedó en producción

Fecha: 2026-09-29 · Rama: `hipotesis-5ind-max` (commits locales, sin push ni merge) ·
Commits: `12c494c` (pre-registro, congelado antes de calcular), `44f18f3` y `6ca52f8` (juicio y GPU acotada),
`3835672` (resultados y veredicto), `d249bba` (promoción a `src/`), `b73e8ec` (documentación), más los que añaden la recorrida
de los lugares, el registro en el log y este informe ·
Antecedentes: `informes/11_informe_prefiltro_social_max.md` y las entradas [2026-09-28] y [2026-09-29] de
`contexto/08_log_decisiones.md`.

## 1. Resumen

- **Qué es.** Para dos indicadores —presencia de grupos armados y desplazamiento forzado— se exige que las palabras de su objeto
  (ELN, disidencias, Clan del Golfo…; desplazamiento, huyeron, éxodo…) aparezcan en el texto que lee el modelo. Si no aparecen,
  el artículo puntúa 0 en ese indicador. Los otros 24 indicadores no cambian.
- **Por qué reemplaza al pre-filtro social general.** El informe 11 mostró que una sola pregunta para todos los indicadores no
  sirve: los falsos positivos de la cabeza del ranking son específicos de cada indicador, y el 87 % de ellos pasa el filtro general.
- **Qué se midió y qué entra.** Antes de calcular se fijaron cuatro condiciones por indicador y se juzgaron a ciegas artículos de
  Cauca, Chocó y Cundinamarca. Entran grupos armados y desplazamiento. Conflicto territorial queda fuera (falla el control
  absurdo y una regla de coherencia); rechazo de proyectos y exclusión de beneficios no ganaban lo suficiente.
- **Efecto en el radar.** Pequeño y sin cambios de clase: ningún departamento ni lugar cambia (6 Bajo / 19 Medio / 7 Alto). La
  correlación con el radar oficial pasa de −0.165 a −0.091 (una mejora menor que el ruido de 32 departamentos) y el MAX cambia
  en 27 de las 832 combinaciones departamento × indicador.
- **En producción.** El usuario aprobó la configuración y se implementó en `src/`: cortes del radar 0.7572/0.9233, 16 pruebas de
  integración y equivalencia exacta con el experimento.
- **Los cuatro lugares**, vueltos a correr con el `src/` nuevo (32 minutos de GPU), dan exactamente lo que el experimento había
  predicho: Antioquia (2023) 0.9354 Alto, Maicao 0.9623 Alto, Oicatá 0.6239 Bajo y Paraguachón 0.6523 Bajo. Ninguno cambia de clase
  y solo cambian 5 de los 104 máximos (grupos armados y desplazamiento en Maicao, Oicatá y Paraguachón).
- **Salvedad principal.** La lista de desplazamiento recorta artículos sin sus palabras, pero no distingue el objeto: su versión
  absurda («…por los osos polares») sigue puntuando alto. Queda pendiente la etapa 2 para cubrir los 26 indicadores.

## 2. Qué es el pre-filtro por indicador y por qué reemplaza al general

El radar toma, para cada indicador y lugar, el puntaje más alto entre todos los artículos (el MAX) y promedia los 26. Con esa
agregación, un solo artículo mal puntuado fija el indicador. La idea del pre-filtro por indicador es cortar los artículos que
puntúan alto sin nombrar el objeto del indicador: si la lista de palabras de un indicador no aparece en la parte del artículo que
lee el modelo (el cuerpo, recortado junto con la frase del indicador), el puntaje de ese artículo en ese indicador pasa a 0.

Ejemplo: en grupos armados, los artículos que más alto puntuaban sin nombrar ningún grupo eran de homicidios, porte ilegal de
armas, combos y hurtos. La lista (ELN, FARC, disidencias, Clan del Golfo, autodefensas, «frente 36»…) los deja en 0 y conserva los
que sí nombran un grupo organizado. La de desplazamiento pide, por ejemplo, «desplazamiento», «huyeron», «éxodo» o «abandonaron
sus hogares».

**Por qué no el general.** El informe 11 midió un pre-filtro único («¿hay un conflicto, una afectación o un riesgo que afecta a
una comunidad?», umbral 0.85) y lo rechazó: de los 225 puestos de los diez primeros artículos de cada indicador y lugar donde hay
jueces, sacaba 27 artículos, 26 no confirmados y 1 confirmado, y los reemplazos también eran no confirmados. La razón:
173 de los 199 puestos que ocupan artículos no confirmados (87 %) son artículos socialmente relevantes que pasan ese filtro
(`experimentos/resultados/exp_prefiltro_max_mecanismo.xlsx`). Un filtro por indicador ataca justo lo específico.

**No es nuevo.** Las listas son las que la ronda 1 congeló y midió (informes 01 y 02): en los cuatro lugares, la precisión de los
diez primeros de grupos armados subió de 0.17 a 0.93 y la de desplazamiento de 0.05 a 0.35. La de grupos armados se llevó a
producción el 2026-09-22 y se revirtió el 2026-09-23, porque la regla 15 solo permitía cambiar la hipótesis de cada indicador
(la de desplazamiento no había pasado los criterios absolutos de la ronda 1). El usuario admitió ahora una excepción a esa regla
para este diseño (una lista por indicador, calculada por dentro y sin columnas nuevas); cualquier otra lista o compuerta sigue
prohibida sin pre-registro y confirmación suya.

## 3. Qué se midió y qué entra

Las condiciones se escribieron **antes de calcular** (`experimentos/PREREG_prefiltro_indicador.md`, commit `12c494c`). Una lista
entra solo si cumple las cuatro:

| Condición | Qué exige |
|---|---|
| (a) Lugares | Que la precisión de los diez primeros (M2) suba al menos 0.20 en los cuatro lugares (dato de la ronda 1) |
| (b) Holdout | Que suba al menos 0.10 en Cauca, Chocó y Cundinamarca, con al menos el 90 % de esos artículos juzgados |
| (c) Control absurdo | Que la diferencia entre el indicador real y su versión absurda («…osos polares») no baje con el filtro, en los lugares y en el holdout |
| (d) Coherencia (M3) | Que el filtro no cree ninguna contradicción nueva: un lugar sin casos confirmados con MAX alto, o con casos y MAX bajo |

Resultado (fuente: `experimentos/resultados/exp_prefiltro_indicador.xlsx`, hojas `I_inclusion`, `I_holdout_b`, `I_control_c`, `I_m3_d`):

| Indicador | (a) ΔM2 lugares | (b) ΔM2 holdout | (c) control absurdo | (d) M3 nuevas | Entra |
|---|---|---|---|---|---|
| `presencia_grupos_armados` | +0.750 | +0.300 (0.467 → 0.767) | pasa | 0 | sí |
| `desplazamiento_forzado` | +0.300 | +0.200 (0.367 → 0.567) | pasa | 0 | sí |
| `conflicto_territorial` | +0.492 | +0.333 | **falla** (absurdo total, lugares −0.0089) | **1** (Paraguachón) | no |
| `rechazo_proyecto` | +0.025 | — | — | — | no |
| `exclusion_beneficios_economicos` | 0.000 | — | — | — | no |

El juicio del holdout lo hicieron dos jueces automáticos ciegos (`juez-a` y `juez-b`, con el codebook congelado) sobre 26
artículos nuevos y 10 de control: kappa 0.923 en desplazamiento, 1.000 en conflicto y 0.875 en grupos armados. La cobertura de
juicio de los diez primeros fue del 100 %.

**Salvedades de desplazamiento** (registradas en el log [2026-09-29]):

- **Pasa el control absurdo por no empeorar, no por mejorar.** Su versión absurda sigue con MAX entre 0.86 y 0.99 en los seis
  lugares con artículos, con y sin filtro; la diferencia con el indicador real cambia +0.0013 en los lugares y 0.0000 en el holdout.
  El filtro quita artículos sin las palabras, pero no distingue el objeto. En grupos armados, en cambio, la versión absurda baja
  (0.669 → 0.611 en Antioquia, 0.688 → 0.456 en Maicao) y queda bajo 0.766.
- **No cumple los criterios absolutos de la ronda 1** (precisión ≥ 0.60, MAX correcto en 3 de 4 lugares, versión absurda bajo
  0.766): su precisión es 0.35 en los lugares y 0.567 en el holdout. Entra por la regla de esta etapa, que mide ganancia.
- **La ganancia en el holdout la sostienen Cauca (0.30 → 0.80) y Chocó (0.80 → 0.90).** Cundinamarca no tiene casos confirmados de
  desplazamiento (0 → 0).

## 4. Efecto en el radar nacional

Con las dos listas y los cortes recalibrados (0.7572/0.9233, calculados sin mirar el radar oficial y sin romper ninguna de las 12
anclas de validez aparente) (hojas `R_configs`, `F_deptos`, `F_indicadores`, `F_celdas_MAX`):

| | Sin filtro | Con filtro |
|---|---|---|
| Cortes Bajo/Medio/Alto | 0.766 / 0.9233 | 0.7572 / 0.9233 |
| Clasificación de los 32 departamentos | 6 Bajo / 19 Medio / 7 Alto | 6 / 19 / 7 (ninguno cambia) |
| Correlación de Spearman con el radar oficial | −0.1653 | −0.0913 |
| Correlación del radar con el número de artículos | +0.884 | +0.864 |
| Anclas de validez aparente rotas | 0 | 0 |

- El radar baja en 20 de 32 departamentos (media −0.0048; la mayor caída, San Andrés y Providencia, −0.0407).
- Cambian 27 de las 832 combinaciones departamento × indicador (15 de desplazamiento y 12 de grupos armados), 14 en más de 0.05.
  Dos pasan a 0: grupos armados en San Andrés (0.861) y desplazamiento en Guainía (0.142, con 6 artículos). Otros movimientos
  grandes: grupos armados en Quindío 0.996 → 0.553 y en Guainía 0.640 → 0.011; desplazamiento en Caldas 0.947 → 0.446 y en
  Santander 0.969 → 0.654.
- La mejora del Spearman (+0.074) es menor que el +0.15 que se distingue del ruido con 32 departamentos: los criterios del radar
  eran de no empeorar, y se cumplen. La correlación con el radar oficial sigue siendo negativa.

## 5. Efecto en los cuatro lugares

Se volvieron a correr los indicadores y el radar de los 4 lugares con el `src/` nuevo (31.6 minutos de GPU), sobre
`datos/corpus/df_corpus_5lugares.pkl` **sin regenerarlo** (sha256 `b4ccb0e6122c91b7…` y fecha 2026-09-01T02:11:51 idénticos antes y
después; `experimentos/resultados/exp_prefiltro_indicador_correr_lugares.log`). Frente a la corrida anterior (la del 28 de septiembre,
idéntica a la del 1 de septiembre):

- las 24 columnas no filtradas y el sesgo son **idénticas** (diferencia 0);
- las dos filtradas son exactamente el puntaje anterior por la compuerta (diferencia 0). La compuerta deja abierto el objeto en el 7.7 %
  de los 1.647 artículos en desplazamiento y en el 9.7 % en grupos armados;
- los cuatro radares coinciden con la predicción del experimento (diferencia 0) y no cambia ninguna clase.

Fuente: `experimentos/resultados/exp_prefiltro_indicador_lugares.xlsx`, hojas `por_articulo`, `compuertas`, `max_lugar_x_indicador`,
`radar_clase`.

| Lugar | Artículos | Radar antes → después | Clase | MAX que cambian |
|---|---|---|---|---|
| Antioquia (2023) | 494 | 0.9354 → 0.9354 | Alto | ninguno |
| Maicao | 1.101 | 0.9625 → 0.9623 | Alto | grupos armados 0.985 → 0.982; desplazamiento 0.985 → 0.983 |
| Oicatá | 32 | 0.6688 → 0.6239 | Bajo | grupos armados 0.652 → 0; desplazamiento 0.517 → 0 |
| Paraguachón | 20 | 0.6801 → 0.6523 | Bajo | desplazamiento 0.723 → 0 |

**Qué artículos dejan de fijar el máximo** (fuentes: esa misma hoja y `experimentos/resultados/exp_prefiltro_lugares_recorrida.xlsx`, hoja
`indicadores_por_peso`, para la corrida anterior):

- **Oicatá:** el máximo de grupos armados (0.652) lo fijaba «Capturan a presunto responsable de millonario hurto en zona rural…» y el de
  desplazamiento (0.517) una nota sobre una encuesta de intención de voto. Ninguno abre la compuerta de su indicador: en el texto que
  lee el modelo, la nota del hurto no contiene ninguna palabra de la lista de grupos armados y la de la encuesta ninguna de la de
  desplazamiento; ahora ambos indicadores quedan en 0.
- **Paraguachón:** el máximo de desplazamiento (0.723) lo fijaba «Por presión de autoridades venezolanas, captores liberan secuestrados…»,
  que no contiene ninguna palabra de la lista de desplazamiento en el texto que lee el modelo; queda en 0.
- **Maicao:** el máximo de grupos armados pasaba de «Maicao fortalece su seguridad con inteligencia y presencia especializada…» (no
  abre la compuerta: ninguna palabra de la lista en el texto que lee el modelo) a «Autoridades redoblan acciones para esclarecer masacre en Maicao…». El de desplazamiento sigue alto (0.983), ahora
  fijado por una nota sobre una recompensa por la liberación de una persona («Ofrecen hasta $100 millones para lograr liberación de Angie
  Argáez»): que la lista se abra **no garantiza que el artículo sea un caso confirmado**, solo que nombra el objeto.
- **Antioquia (2023):** no cambia nada; el mismo artículo (la asonada de Briceño, «Nueva asonada en Antioquia: comunidad sacó a 80
  militares de Briceño») fija ambos máximos y pasa las dos compuertas.

**Indicadores que más pesan.** Los cinco de mayor máximo no cambian respecto del informe 11 porque ninguno de los dos indicadores
filtrados está entre ellos: Antioquia (2023) `derechos_vulnerados` 0.998, `conflicto_activo` 0.996, `conflicto_territorial` 0.996,
`poblacion_afectada` 0.996, `exclusion_beneficios_economicos` 0.996; Maicao `derechos_vulnerados` 0.998, `poblacion_afectada` 0.996,
`rechazo_proyecto` 0.996, `exclusion_beneficios_economicos` 0.996, `violacion_derechos_humanos` 0.996; Oicatá `derechos_vulnerados` 0.990,
`exclusion_beneficios_economicos` 0.989, `conflicto_activo` 0.985, `rechazo_proyecto` 0.979, `exclusion_comunidades` 0.953; Paraguachón
`derechos_vulnerados` 0.996, `exclusion_beneficios_economicos` 0.994, `conflicto_territorial` 0.993, `rechazo_proyecto` 0.989,
`conflicto_activo` 0.989 (hoja `indicadores_por_peso`). Lo que cambia es el fondo de la lista: los indicadores con máximo 0 pasan de 3
a 5 en Oicatá y de 3 a 4 en Paraguachón, y los que superan el corte Bajo/Medio (0.7572) son 24, 26, 14 y 14 de 26 en Antioquia (2023),
Maicao, Oicatá y Paraguachón (hoja `resumen_indicadores`). Sigue siendo el efecto de tamaño ya descrito: con cientos de artículos casi
todos los indicadores superan el corte; con 32 o 20 no.

## 6. Qué cambió en producción y cómo se verificó

- **`src/Transformer_optimo.py`:** un diccionario `PREFILTRO_OBJETO` con las dos listas (copias literales de las congeladas); para
  cada una, la compuerta se calcula sobre el texto que el modelo ve con la frase de **ese** indicador y multiplica su puntaje
  corregido, dentro de `procesar()`. No se agregan columnas a la salida.
- **`src/config_pipeline.py`:** el corte Bajo/Medio del radar pasa de 0.766 a 0.7572.
- **`src/test_integracion.py`:** 6 pruebas nuevas (16 en total, todas pasan): las listas son las congeladas, cada compuerta abre con su
  objeto y no sin él, solo mira el texto visible de su indicador, solo se multiplican esos dos indicadores y no aparecen columnas nuevas.
- **Equivalencia con el experimento** (`experimentos/exp_prefiltro_indicador_equivalencia.py`, sin GPU): la compuerta de `src/` es
  idéntica a la del experimento con la misma truncación, el MAX de los 26 indicadores en los 32 departamentos coincide exactamente
  (diferencia 0), la clasificación es 6/19/7 y el procedimiento de cortes devuelve 0.7572/0.9233 sin anclas rotas.
- **Tampoco cambia** la agregación MAX, el radar de 26 indicadores ni `ESTADO_DEL_PROYECTO.md`, que se actualiza al fusionar.

## 7. Límites

- **Cobertura.** El mecanismo cubre 2 de los 26 indicadores; la evidencia con jueces, 5 de 26; la plata, 2 de 26. Los otros 24
  indicadores no cambian.
- **Desplazamiento** no mejora su control absurdo (sección 3) y su precisión sigue siendo moderada.
- **Muestras pequeñas.** El holdout son 3 departamentos con pocos casos confirmados por indicador, y las listas se diseñaron con los
  lugares de la ronda 1: el holdout es la comprobación fuera de muestra. Oicatá (32 artículos) y Paraguachón (20) son bases pequeñas.
- **Ruido.** Con 32 departamentos, la mejora de la correlación con el radar oficial no se distingue del ruido.
- **Salidas antiguas.** Un `df_procesado` calculado antes del 2026-09-29 no trae el filtro y no debe clasificarse con los cortes nuevos.
  Como no se añaden columnas, nada en el archivo lo delata; hay que regenerarlo.
- **Texto visible.** La compuerta mira lo que el modelo ve; una mención más allá del corte de 512 unidades no cuenta. Con el recorte
  de producción de cada indicador, la lista difiere en 16 artículos (grupos armados) y 4 (desplazamiento) de 11.439 respecto del
  experimento y no cambia ningún MAX departamental.

## 8. Etapa 2: cubrir los 26 indicadores

El borrador (`experimentos/PLAN_prefiltro_indicador_etapa2.md`) se escribió solo a partir del texto de cada hipótesis, sin mirar puntajes
ni jueces. Clasifica los otros 21 indicadores en **17 de objeto concreto**, con una lista propuesta cada uno (por ejemplo, reasentamiento,
protesta social, amenazas, daños ambientales, irregularidad contractual, grupos étnicos, amenaza a líderes), y **4 abstractos** que pasan
sin filtro (derechos vulnerados, conflicto activo, debilidad institucional y población afectada), porque ninguna lista corta es condición
necesaria. Varias listas propuestas casi siempre estarían abiertas (consulta y participación, servicios, tierras, agua, contratos) y no
filtrarían nada.

Hacerlo exigiría, para cada indicador: un techo de apertura fijado antes de mirar puntajes, una referencia de jueces con un codebook por
indicador (hoy solo hay para 5), gemelas absurdas, la misma regla de inclusión (a)–(d) y un pre-registro. Por la regla 15, cada lista nueva
necesita además la confirmación expresa del usuario. Con 17 listas alguna pasaría por azar, así que el pre-registro debe fijar de antemano
cuántas se admiten. **Nada de esto se ha empezado.**

## 9. Archivos de origen

- Pre-registro y resultados: `experimentos/PREREG_prefiltro_indicador.md`, `experimentos/RESULTADOS_prefiltro_indicador.md`,
  `experimentos/resultados/exp_prefiltro_indicador.xlsx`, `experimentos/resultados/juicio_prefiltro_indicador/`.
- Plan de implementación y borrador de la etapa 2: `experimentos/PLAN_implementacion_prefiltro_indicador.md`,
  `experimentos/PLAN_prefiltro_indicador_etapa2.md`.
- Código: `src/Transformer_optimo.py`, `src/config_pipeline.py`, `src/test_integracion.py`; equivalencia
  `experimentos/exp_prefiltro_indicador_equivalencia.py` (`experimentos/resultados/exp_prefiltro_indicador_equivalencia.csv`).
- Lugares: `experimentos/exp_prefiltro_correr_lugares.py`, `experimentos/exp_prefiltro_indicador_lugares.py`,
  `experimentos/resultados/exp_prefiltro_indicador_lugares.xlsx`; datos locales `resultados/tablas_lugares_max_prefiltro_2026-09-29/`
  (nueva) y `resultados/tablas_lugares_max_2026-09-28/` (anterior, idéntica a la del 1-sep).
- Registro: `contexto/08_log_decisiones.md`, entradas [2026-09-28] y [2026-09-29].
