# Informe 16 — Nuevas frases para conflicto territorial y resistencia territorial

Fecha: 2026-10-07 · Rama: `radar-18ind-c21-r30` (creada desde `radar-18ind`; solo local, sin push ni merge) ·
Antecedente: `informes/15_informe_radar_18ind_hipotesis_jefe.md`.

## 1. Qué se cambió

Solo el texto de dos hipótesis en `src/Transformer_optimo.py`. El cálculo de los indicadores, las columnas de salida y
los otros 16 indicadores no cambian (regla 15):

| Indicador | Frase anterior (pedida por el jefe, informe 15) | Frase nueva |
|---|---|---|
| `conflicto_territorial` | «Dos o más actores disputan el control, uso o propiedad de un territorio.» | **«Hay una invasión de predios.»** |
| `resistencia_territorial` | «Una comunidad realiza acciones para defender su territorio frente a proyectos, intervenciones o decisiones externas.» | **«Los habitantes rechazan una hidroeléctrica o un megaproyecto.»** |

`zonas_proteccion_alimentaria` conserva la frase del jefe (decisión del usuario).

También se recalibraron los cortes del radar (regla 2): de 0.6885/0.8916 a **0.6559/0.8839**
(`src/config_pipeline.py`). La prueba de integración `python src/test_integracion.py` da 16/16.

## 2. Por qué

En el informe 15 las dos frases del jefe fallaban el control absurdo. El control consiste en puntuar, junto a cada
frase, una frase «gemela» del mismo formato que habla de colonias de osos polares. El modelo decía «sí» a la gemela
en el 78.7 % (conflicto) y el 44.8 % (resistencia) de las noticias. Es decir, reconocía la forma de la oración, no su
contenido, y sumaba casi la misma constante (≈0.99) a todos los departamentos.

## 3. Cómo se eligieron

Pre-registro con los criterios fijados antes de medir: `experimentos/PREREG_hipotesis_conflicto_resistencia.md`.

1. **69 frases candidatas** en dos rondas (34 de conflicto y 35 de resistencia), cada una con su gemela absurda
   (`experimentos/resultados/candidatas_*_r{1,2}.json`).
2. **Cribado** en una muestra de 1.476 noticias (50 por departamento). Se exigía:
   - gemela absurda sobre 0.9 en como máximo el 5 % de las noticias;
   - separación entre frase real y gemela al menos igual a la de V2, la frase original del proyecto;
   - que no saturara.

   Resultado en `experimentos/resultados/cribado_conflicto_resistencia_submuestra.csv`.
3. **Corpus nacional completo** (11.439 noticias) para las finalistas.
4. **Dos jueces independientes**, que no sabían qué frase había elegido cada noticia, revisaron la noticia con el
   puntaje más alto de cada departamento. Coincidieron mucho entre sí: kappa 0.91 (conflicto) y 0.88 (resistencia).

Patrón encontrado:
- **Saturan:** «disputa/conflicto» con actores genéricos, la lista «control, uso o propiedad», y «una comunidad» con
  verbos abstractos (defiende, actúa, se moviliza).
- **No saturan:** un hecho concreto («invasión de predios») y «los habitantes» con un verbo de protesta
  (rechazan, protestan).

## 4. Resultados en el corpus nacional

Fuente: `experimentos/resultados/cribado_conflicto_resistencia_nacional.csv` y
`experimentos/resultados/juicio_conflicto_resistencia_nacional/precision_nacional.csv`.

| Frase | Gemela sobre 0.9 | Separación real − gemela | Puntaje más alto por depto: mediana / dispersión | Precisión de jueces |
|---|---:|---:|---|---:|
| Conflicto, jefe | 78.7 % | 0.005 | 0.996 / 0.003 | 10/32 |
| Conflicto, V2 (original) | 5.7 % | 0.520 | 0.989 / 0.017 | 13/32 |
| **Conflicto, nueva** | **2.9 %** | **0.571** | 0.979 / 0.044 | 10/32 |
| Resistencia, jefe | 44.8 % | 0.041 | 0.996 / 0.002 | 2/32 |
| Resistencia, V2 (original) | 5.7 % | 0.347 | 0.822 / 0.167 | 8/32 |
| **Resistencia, nueva** | **0.3 %** | **0.603** | 0.750 / 0.267 | 5/32 |

**Frente a las frases del jefe** (lo que estaba en producción), las nuevas son claramente mejores: pasan el control
absurdo, distinguen departamentos y tienen igual o mayor precisión.

**Frente a V2**, las nuevas pasan mejor el control y separan mejor los departamentos, pero los jueces les dan algo
menos de precisión. Con 32 departamentos esas diferencias (13 contra 10 y 8 contra 5 noticias) no se distinguen del
ruido.

## 5. Antioquia y los lugares

Fuente: `experimentos/resultados/tabla_antioquia_lugares_c21_r30.md` (y `.xlsx`; script
`experimentos/exp_tabla_antioquia_lugares_c21_r30.py`). Los valores de «hoy» reproducen los del informe 15.

| Lugar | Artículos | Radar hoy | Clase | Radar nuevo | Clase |
|---|---:|---:|:--:|---:|:--:|
| Antioquia | 494 | 0.9084 | Alto | 0.8974 | Alto |
| Paraguachón | 20 | 0.6053 | Bajo | 0.5465 | Bajo |
| Maicao | 1101 | 0.9544 | Alto | 0.9406 | Alto |
| Güintiva | 0 | sin radar | — | sin radar | — |
| Oicatá | 32 | 0.4891 | Bajo | 0.4181 | Bajo |

**Ningún lugar cambia de clase.** Los dos casos absurdos del informe 15 desaparecen:
- Oicatá: resistencia pasa de 0.988 (artículo sobre megaproyectos anunciados) a 0.025.
- Paraguachón: resistencia pasa de 0.995 (expulsión de una migrante) a 0.107.

Nacional (`experimentos/resultados/exp_c21_r30_cortes.csv`, script `experimentos/exp_c21_r30_cortes.py`):
- Clases de los 32 departamentos: 6 Bajo / 19 Medio / 7 Alto, sin cambios; ningún departamento cambia de clase.
- Accuracy contra el DANE: 0.344, igual que antes.
- Spearman contra el DANE: −0.0975 → −0.1162.

## 6. Limitaciones

- **Conflicto lee «invasión» también como llegada de migrantes.** En Antioquia y Maicao la noticia más alta trata de
  migrantes o de la reapertura de la frontera. Además, el puntaje más alto por departamento sigue cerca de la
  saturación (mediana 0.979).
- **Resistencia queda más estrecha de lo que pidió el jefe.** Detecta el rechazo a hidroeléctricas y megaproyectos,
  no cualquier defensa del territorio frente a algo externo. La frase más fiel a la intención del jefe («Los
  habitantes protestan contra una intervención externa en su territorio.») pasaba el control, pero los jueces la
  rechazaron: en 21 de 22 departamentos donde puntuaba alto, la noticia no era de resistencia.
- **El control depende de cómo se escriba la gemela absurda.** Con una gemela más exigente, la frase de conflicto
  sube a 7.2 % en la muestra (por encima del 5 %). V2 tampoco pasaría con una gemela escrita en su propio formato
  (21.7 %).
- **No se cumplió el criterio pre-registrado «precisión ≥ V2».** El cambio se adoptó por decisión del usuario, con
  esa salvedad explícita (`contexto/08_log_decisiones.md` [2026-10-07]).
- **No hay estándar de plata para estos indicadores.** La precisión descansa en jueces LLM sobre 32 noticias por
  frase.

## 7. Pendiente

- Que el jefe vea el cambio de alcance de resistencia.
- Una medición de precisión más amplia: 60–80 noticias por frase muestreadas a distintos niveles de puntaje. No
  necesita GPU porque los puntajes ya están guardados en `datos/scores/hip_conflicto_resistencia/`.
