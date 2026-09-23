# Informe — Reversión de la compuerta de grupos armados (fase 8)

Fecha: 2026-09-23 · Rama: `hipotesis-5ind-max` (commits locales, sin push ni merge) ·
Antecedentes: `informes/01_informe_5ind_MAX_fases_0-7.md` y
`informes/02_informe_fase_8_promocion_grupos_armados.md`.

## 1. Resumen

- Se fijó una regla nueva: **de cada indicador solo se puede cambiar la hipótesis**, es decir, la
  frase que evalúa el modelo NLI. No se puede cambiar el cálculo interno del indicador (por
  ejemplo, con reglas de palabras clave) ni agregar columnas a la salida.
- La compuerta de grupos armados que el informe 02 llevó a producción es una regla de palabras
  clave dentro del cálculo, así que **se revirtió**. Producción vuelve a ser exactamente la de la
  rama `radar-max_Septiembre` (la desplegada).
- El corte Bajo/Medio del radar vuelve de 0.7574 a **0.766** (el Medio/Alto sigue en 0.9233).
  **Ningún departamento cambia de clase** (6 Bajo / 19 Medio / 7 Alto), igual que con la
  compuerta.
- La segunda ronda de corrección se hará **solo reescribiendo hipótesis**, para los 5
  indicadores (grupos armados vuelve a la lista).

## 2. Qué se revirtió

| Elemento | Con la compuerta (informe 02) | Ahora |
|---|---|---|
| `presencia_grupos_armados` | score del NLI × 1 o 0 según una lista de nombres de grupos armados | score del NLI con la hipótesis vigente, sin regla |
| Columna auxiliar `compuerta_grupos_armados` | presente en la tabla procesada | eliminada |
| Cortes del radar | Bajo < 0.7574 ≤ Medio < 0.9233 ≤ Alto | Bajo < 0.766 ≤ Medio < 0.9233 ≤ Alto |
| Tests de integración | 15 | 10 (los 5 de la compuerta se retiran con ella) |
| Código de `src/` | modificado | idéntico al de `radar-max_Septiembre` |

## 3. Verificación (sin GPU)

- `python src/test_integracion.py`: 10/10.
- `experimentos/exp_5ind_max_f8_reversion.py`, sobre los 11.439 artículos de los 32
  departamentos y los puntajes nacionales ya calculados: el código ya no tiene compuerta; el
  radar por departamento coincide exactamente (diferencia máxima 0) con el de la versión
  vigente medida en la fase 7; la clasificación es 6 / 19 / 7; el procedimiento de cortes
  devuelve 0.766 / 0.9233 sin romper ninguna de las 12 anclas. Salida:
  `experimentos/resultados/juicio_5ind_holdout/f8_reversion.csv`.

## 4. Qué sigue valiendo del trabajo anterior

- La medición de las fases 0–7 no cambia: con dos jueces LLM ciegos, la compuerta subía la
  precisión de grupos armados entre los 10 artículos más altos de 0.17 a 0.93 (4 lugares) y de
  0.47 a 0.77 (holdout). Es un hallazgo medido, pero no se puede usar en producción con la regla
  nueva.
- Los Excel de lugares del informe 02 (`experimentos/resultados/excel_lugares_f8/`): los
  archivos «antes» coinciden con la producción actual; los «después» describen la versión
  revertida y quedan solo como registro.
- Las etiquetas de los jueces (565 artículos de los lugares y 94 del holdout) se reutilizan en
  la segunda ronda.

## 5. Segunda ronda: solo hipótesis

Para los 5 indicadores (exclusión de beneficios económicos, rechazo a proyecto, desplazamiento
forzado, conflicto territorial y presencia de grupos armados) se probarán frases nuevas, cada
una con su control absurdo (la misma frase con «osos polares» en lugar del objeto). Primero se
filtran en los 4 lugares de trabajo, reutilizando las etiquetas ya hechas; las que pasen van a
escala nacional, al holdout (Cauca, Chocó, Cundinamarca) y a la recalibración de cortes. El
criterio de adopción se fija antes de medir, en `experimentos/PREREG_5ind_MAX_r2.md`.

**Expectativa honesta:** en la primera ronda ninguna frase reescrita pasó el criterio. Con solo
cambiar la frase, la mejor precisión fue 0.38 (grupos armados), 0.17 (conflicto), 0.05
(desplazamiento) y 0.00 (rechazo y exclusión), frente a 0.60 exigido. El modelo tiende a
confirmar la forma de la frase sin mirar su objeto. Un resultado posible es que ninguna frase
pase; si así ocurre, se registra y el indicador queda como está.

## Anexo — Trazabilidad

| Elemento | Dónde |
|---|---|
| Decisión | `contexto/08_log_decisiones.md`, entrada [2026-09-23] «Regla del usuario… F8 REVERTIDA» |
| Regla | `CLAUDE.md`, regla 15 |
| Estado de `src/` restaurado | etiqueta local `base-26ind-f7` (705a557) = `base-26ind-radar-max` (71072a1) |
| Script de verificación | `experimentos/exp_5ind_max_f8_reversion.py` |
