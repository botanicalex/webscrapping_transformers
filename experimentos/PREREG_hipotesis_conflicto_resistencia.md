# PREREG — Frases de `conflicto_territorial` y `resistencia_territorial` (relevo 12)

Fecha: 2026-10-07. Rama `radar-18ind`. Escrito **antes de ver ningún número** de las candidatas.

## Pregunta

¿Existe, para cada indicador, una frase que se acerque a la intención del jefe sin saturar: que pase el control
absurdo (osos polares, mismo formato) y que distinga departamentos?

- conflicto: disputa entre dos o más actores identificables por control/uso/propiedad de tierra o territorio.
- resistencia: una comunidad actúa para defender su territorio frente a algo externo.

## Candidatas (ronda 1)

Fijadas en `experimentos/resultados/candidatas_conflicto_r1.json` (C01–C20) y
`experimentos/resultados/candidatas_resistencia_r1.json` (R01–R20): frase, nula del mismo formato (contenido
sustantivo → «colonias de osos polares»), eje mecanístico. Propuestas por dos subagentes independientes (Sonnet),
revisadas por el orquestador. Referencias sin GPU nueva: V2 (`scores_v2_32deptos.pkl`, nula = `V2.NULA_TEST`) y
jefe (`scores_hipotesis_jefe_18ind.pkl`, nula del mismo formato).

## Diseño

- Cola única de GPU: `experimentos/cola_gpu_conflicto_resistencia.py` (un pkl por candidata en
  `datos/scores/hip_conflicto_resistencia/<corpus>/`). Premisa = `texto`. Sesgo = columna `sesgo` de producción
  (nacional/submuestra) o media de `V2.NULAS_CALIBRACION` (lugares). `NULA_TEST` nunca en el sesgo.
- Submuestra de cribado: min(n, 50) artículos por departamento, semilla 20261007
  (`experimentos/resultados/submuestra_cribado.csv`, ≈1.500).
- Score corregido `clip(clip(ent − sesgo, 0)·(1 − neu), 0, 1)`; agregación MAX por departamento.

## Criterios del cribado (submuestra; referencias V2 y jefe medidas sobre la misma submuestra)

Puertas eliminatorias en orden:
- **P1** `prop(nula cruda > 0.9) ≤ 5 %` y `media(nula corregida) ≤ 0.10`.
- **P2** ambos valores ≤ los de V2 en la submuestra.
- **P3** brecha media (MAX real corr − MAX nula corr, por depto) ≥ la de V2 en la submuestra.
- **Saturación** (eliminatoria): MAX real por depto con mediana ≥ 0.98 **y** IQR < 0.05.

Ranking de supervivientes: brecha media (desc), luego IQR del MAX por depto (desc). Las 3–5 mejores por indicador
pasan a jueces. Si ninguna pasa P1, se diseña una ronda 2 a partir del patrón de la ronda 1 (no se relajan puertas).

## Jueces (proxy de plata)

Por indicador, para cada candidata de jueces y para V2 y jefe como referencias: el artículo top (MAX corregido) de
cada departamento de la submuestra. Dos jueces independientes (subagentes Sonnet), ciegos a la frase que lo eligió,
juzgan si el artículo cumple la intención del jefe (sí/no) viendo la premisa visible recortada. Se reporta precisión
por candidata (acuerdo de ambos = sí; desacuerdos aparte) y kappa de Cohen.
Criterio: precisión ≥ la de V2 (la candidata no puede ser menos fiel a la intención que V2).

## Finalistas (≤ 3 por indicador) → nacional completo + lugares

Pasan si en el nacional: P1–P3 contra V2 (brecha 0.520 conflicto, 0.347 resistencia), no saturada (criterio de
arriba). Recomendación: entre las que pasan, la de mayor precisión de jueces; empate → mayor brecha. Si ninguna pasa,
se reporta así y no se recomienda cambio de frase (el control autoriza a rechazar, nunca a adoptar solo).

## Ronda 2 — conflicto (registrada antes de puntuarla, tras ver la ronda 1 de conflicto)

Candidatas C21–C34 en `experimentos/resultados/candidatas_conflicto_r2.json`, diseñadas en la vecindad de C20
(«Hay una invasión de predios en disputa.») y C08 (actores antagónicos concretos), las únicas de la ronda 1 que
pasaron P1. Mismos criterios, misma submuestra, sin relajar puertas.

**Hallazgo registrado (no cambia las puertas):** la nula de C14 es exactamente la nula de V2 escrita en el formato de
V2 («Hay una disputa por el control, el uso o la propiedad de unas colonias de osos polares.») y da 21.7 % > 0.9 en
la submuestra: V2 de conflicto **no pasaría P1** con una nula de su propio formato (regla 3). Las referencias P2/P3
de V2 se miden con `NULA_TEST` (como en el relevo), que es más fácil de superar que una nula del mismo formato.

## Ronda 2 — resistencia (registrada antes de puntuarla, tras ver la ronda 1)

Candidatas R21–R35 en `experimentos/resultados/candidatas_resistencia_r2.json`: pares mínimos alrededor de R05
(«Los habitantes protestan para defender su territorio de una intervención externa.») y R12 («Los habitantes rechazan
una hidroeléctrica o un megaproyecto en su territorio.»), que aíslan actor, verbo, «de»/«frente a», objeto externo y la
disyunción del jefe. Mismos criterios y submuestra.

## Resultado del cribado y enmienda (2026-10-07, registrada antes de ver números del nacional)

Cribado (submuestra): pasan P1–P3 sin saturar C21 «Hay una invasión de predios.», R27 «Los habitantes protestan
contra una intervención externa en su territorio.», R30 y R29 (hidroeléctrica/megaproyecto). Salvedad de robustez:
con una nula más exigente (C21b conserva «predios», R27b conserva «intervención externa») dan 7.2 % y 6.5 % > 0.9:
fallarían P1. Jueces sobre el top por depto de la submuestra (kappa 0.92 / 0.91): precisión baja en todas
(conflicto V2 0.219, C20 0.250, C21 0.156, jefe 0.125; resistencia V2 0.125, R30 0.094, R27 0.031, jefe 0.031): el
criterio «precisión ≥ V2» **no lo cumple ninguna sobreviviente** en la submuestra. Lectura: con 50 artículos por
depto casi ningún depto tiene un artículo pertinente, y el top es ruido para todas las frases (n = 32, diferencias de
1–3 artículos); la medida tiene poca potencia.

**Enmienda (Fase 5):** finalistas al nacional: C21, C20 (mejor precisión en jueces, P3 a 0.024 en la submuestra),
R27, R30. Se repiten los jueces sobre el top por depto **del nacional** (mismos criterios y formato, V2 y jefe como
referencia). La recomendación se decide con los números del nacional; los de la submuestra se reportan tal cual.
