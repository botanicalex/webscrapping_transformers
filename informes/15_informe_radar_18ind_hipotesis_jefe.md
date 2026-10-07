# Informe 15 — Radar de 18 indicadores con las hipótesis pedidas por el jefe

Fecha: 2026-10-07 · Rama: `radar-18ind` (solo local, sin push ni merge) · Antecedente: `informes/14_informe_prefiltro_etapa2_cierre.md`.

## 1. Qué se cambió

Se implementó lo pedido, sin modificar el cálculo interno de ningún indicador:

- **Dos indicadores retirados** (20 → 18): `movimientos_sociales` y `exclusion_servicios_derechos`. Los bloques de la salida quedan en 5/5/4/4 sin mover indicadores (`src/radar.py`).
- **Tres hipótesis nuevas** (solo la frase, `src/Transformer_optimo.py`):
  - `conflicto_territorial`: «Dos o más actores disputan el control, uso o propiedad de un territorio.»
  - `zonas_proteccion_alimentaria`: «El territorio tiene una figura de protección especial para la producción de alimentos.»
  - `resistencia_territorial`: «Una comunidad realiza acciones para defender su territorio frente a proyectos, intervenciones o decisiones externas.»
- **Blanqueo quitado:** antes, si un lugar salía Bajo, el Excel dejaba en blanco el valor y el título del artículo que fija el MAX; ahora se muestran siempre (`src/generar_max_articulos_por_departamento.py`, `src/pipeline_lugares.py`).
- **Cortes recalibrados** (regla 2) de 0.7138/0.905 a **0.6885/0.8916** (sección 4).
- Tests `python src/test_integracion.py`: 16/16.

## 2. Antioquia y los lugares, antes y después

Fuente: `experimentos/resultados/tabla_antioquia_lugares_18ind.md` (y `.xlsx`; script `experimentos/exp_tabla_antioquia_lugares_18ind.py`). Cortes 20 ind 0.7138/0.905; 18 ind 0.6885/0.8916.

| Lugar | Artículos | Radar 20 | Clase | Radar 18 | Clase |
|---|---:|---:|:--:|---:|:--:|
| Antioquia | 494 | 0.9192 | Alto | 0.9084 | Alto |
| Paraguachón | 20 | 0.5809 | Bajo | 0.6053 | Bajo |
| Maicao | 1101 | 0.9547 | Alto | 0.9544 | Alto |
| Güintiva | 0 | sin radar | — | sin radar | — |
| Oicatá | 32 | 0.5215 | Bajo | 0.4891 | Bajo |

**Ningún lugar cambia de clase.** Paraguachón y Oicatá son bases pequeñas (frágiles). En Antioquia, quitar los 2 indicadores baja el radar 0.0041 y las 3 frases nuevas lo bajan otros 0.0067.

## 3. Hallazgo: dos de las tres frases no distinguen nada

**La prueba.** Para cada frase se calcula el mismo puntaje con una frase «gemela» absurda, del mismo formato pero sobre osos polares. Si el modelo dice «sí» a la gemela casi tanto como a la frase real, el «sí» no significa nada: el modelo reconoce la forma de la oración, no su contenido. (Regla 1 del proyecto.) Resultado en el corpus nacional (`experimentos/resultados/exp_hipotesis_jefe_18ind.csv`; puntajes en `datos/scores/scores_hipotesis_jefe_18ind.pkl`):

| Indicador | Gemela absurda sobre 0.9 (nueva / antes) | Brecha real − gemela por departamento (nueva / antes) | Prueba |
|---|---|---|---|
| `conflicto_territorial` | 78.7 % / 5.7 % | 0.005 / 0.520 | Falla |
| `resistencia_territorial` | 44.8 % / 5.7 % | 0.041 / 0.347 | Falla |
| `zonas_proteccion_alimentaria` | 2.5 % / 5.7 % | 0.225 / 0.459 | Falla solo en brecha |

Con la frase de conflicto, la máxima por departamento está entre 0.909 y 0.998 (mediana 0.996): **todos los departamentos sacan casi el máximo**. Con la de resistencia, entre 0.948 y 0.999 (antes 0.000 a 0.992, mediana 0.822). Un indicador que da casi lo mismo en todas partes suma una constante y no ordena nada. La frase de zonas de protección es honesta (la gemela casi no la activa), pero la frase real casi no se activa tampoco en prensa (entailment medio 0.12 frente a 0.62 antes); su MAX por departamento va de 0.002 a 0.995 (mediana 0.622). No se pudo medir AUC: no hay estándar de plata para estos indicadores.

**Ejemplos (Excel de lugares, ahora con los títulos visibles):**

- Oicatá (lugar Bajo, 32 artículos): `conflicto_territorial` marca 0.975 por «Así fue la cadena de fallas que llevó al choque mortal del camión de gas…», un accidente de tránsito sin disputa territorial. `zonas_proteccion_alimentaria` marca 0.449 por una encuesta de intención de voto.
- Paraguachón: `resistencia_territorial` pasa de 0.000 a 0.995 y el artículo que la fija es «Migración Colombia expulsa a venezolana detectada durante trámite médico».
- Antioquia: `resistencia_territorial` pasa de 0.873 a 0.996 con «Disidencias de las Farc impusieron "manual de convivencia" en 14 municipios de Antioquia», y `zonas_proteccion_alimentaria` queda en 0.746 con «A Antioquia llegarán 490 policías para reforzar la lucha contra la inseguridad».

(Todos en `experimentos/resultados/tabla_antioquia_lugares_18ind.md`.)

## 4. Cortes y clases

Los cortes se recalibraron con el mismo procedimiento (`experimentos/exp_retiro_2ind_cortes.py`, salida `experimentos/resultados/exp_retiro_2ind_cortes.csv`). Con 20 indicadores el script reproduce 0.7138/0.905 (sanidad) y con 18 da 0.6885/0.8916, con las 12 anclas intactas. Clases 6/19/7 iguales; **ningún departamento cambia de clase**; accuracy contra el DANE 0.344 igual; Spearman contra el DANE −0.0861 → −0.0975; contra el número de artículos +0.875 → +0.879. Advertencia: la zona alta es densa (9 departamentos entre 0.8856 y 0.9521); el corte 0.8916 cae ahí y Antioquia queda a 0.017 de él.

## 5. Decisión pendiente para el jefe

El control absurdo se reporta y **no decide**: la implementación se hizo por orden del jefe. Opciones:

1. **Mantener las tres frases.** Producción queda como está. Hay que asumir que `conflicto_territorial` y `resistencia_territorial` aportan casi una constante.
2. **Pedir otra redacción** para conflicto y resistencia. Cualquier candidata debe pasar la misma prueba (gemela de osos polares, mismo formato) antes de entrar.
3. **Mantener `zonas_proteccion_alimentaria` y volver a la frase anterior en las otras dos**, que pasaban la prueba (brechas 0.520 y 0.347). Sin costo de recalibración mayor, pero se pierde parte de lo pedido.

Limitaciones: sin AUC (sin estándar de plata); prueba de una sola gemela; los lugares pequeños son frágiles.
