# Informe 14 — Pre-filtro por indicador, etapa 2: cierre con los 11 indicadores restantes

Fecha: 2026-09-29 · Rama: `hipotesis-5ind-max` (commits locales, sin push ni merge) ·
Commits: `26618f8` (pre-registro, congelado antes de calcular), `560fa9f` (cribado), `611a595` (jueces y codebook confirmado),
`eaba2ae` (pool), `226dea7` (juicio), `343db57` (análisis final) y los que añaden el registro y este informe ·
Antecedentes: `informes/12_informe_prefiltro_por_indicador.md`, `informes/13_informe_prefiltro_etapa2_y_prefiltro_social.md`.

## 1. Resumen

- **Pregunta.** Tras el primer tramo (informe 13: 6 indicadores, ninguna lista nueva), quedaban 11 indicadores con una lista de
  palabras propuesta y sin evaluar. ¿Alguna mejora el radar?
- **Método en dos pasos.** Primero un **cribado sin jueces** de las 11 con las dos condiciones que tumbaron al tramo 1 y que se
  calculan sin referencia: el control absurdo y el radar nacional. Solo las listas que pasaran las dos irían a jueces.
- **Cribado:** sobrevive 1 de 11, `zonas_proteccion_alimentaria` (cultivos y producción de alimentos). Nueve fallan el control
  absurdo; una lo pasa pero empeora la dependencia del radar respecto del tamaño del corpus.
- **Jueces:** la sobreviviente es medible (9 casos confirmados por los dos jueces, acuerdo kappa 0.72), pero **no cumple la regla**:
  la precisión de los diez primeros sube +0.14 en los lugares (se exige +0.20) y +0.07 fuera de muestra (se exige +0.10).
- **Decisión: se cierra la etapa 2.** Ninguna lista nueva entra. Producción no cambia: pre-filtro por indicador solo en grupos
  armados y desplazamiento, cortes 0.7572/0.9233, 26 indicadores, agregación MAX. Los otros 24 indicadores pasan sin filtro.

## 2. Por qué un cribado sin jueces

En el tramo 1, las 4 listas medibles cayeron por dos motivos: el **control absurdo** (el modelo afirma casi igual la frase real que
una gemela con el objeto cambiado por «osos polares») y el **radar nacional** (cada lista sola aumentaba la dependencia del radar
respecto del número de artículos del departamento). Las dos cosas se calculan sin jueces, que son la parte cara (unos 150 mil tokens
por juez y lote de trabajo). Aplicado al tramo 1, el cribado reproduce sus números y descarta sus 4 listas, como debía.

- **Condición C (control absurdo):** con el filtro, la distancia entre el máximo real y el de la gemela absurda, y entre el real y
  el de una frase absurda general, no puede bajar, en los 4 lugares y en los 3 departamentos de control (Cauca, Chocó,
  Cundinamarca).
- **Condición R (radar):** con la lista sola, recalculando los cortes, 0 anclas de validez rotas, correlación con el radar oficial
  ≥ −0.0913 y correlación con el tamaño ≤ +0.8640 (los valores de producción).

## 3. Resultado del cribado

Fuente: `experimentos/RESULTADOS_prefiltro_e2_t2.md`, `experimentos/resultados/exp_prefiltro_e2_t2.xlsx` (hojas `C_control`,
`R_radar`, `K_cribado`). GPU 20.8 minutos; verificación contra producción 9.8e-07; 17 de 17 chequeos de sanidad.

| Indicador | Control absurdo (C) | Radar (R) | Sobrevive |
|---|---|---|---|
| Resistencia territorial | falla | pasa (mejora: oficial −0.066, tamaño 0.855) | no |
| Exclusión de comunidades | falla | falla | no |
| Déficit de participación | falla | falla | no |
| Incentivos económicos inequitativos | falla | falla | no |
| Conflictos socioambientales | falla | pasa | no |
| Exclusión de servicios y derechos | pasa | falla (tamaño 0.868) | no |
| Grupos étnicos | falla | falla | no |
| Movimientos sociales | falla | falla | no |
| Irregularidad contractual | falla | falla | no |
| **Zonas de protección alimentaria** | **pasa** | **pasa (igual a producción)** | **sí** |
| Daño a territorios | falla | falla | no |

La sobreviviente pasa R por igualdad: las dos correlaciones son idénticas a las de producción (el orden de los 32 departamentos no
cambia), aunque el radar de algún departamento se mueva hasta 0.019.

## 4. Resultado con jueces (zonas de protección alimentaria)

Fuente: `experimentos/RESULTADOS_prefiltro_e2_t2_analisis.md`, `experimentos/resultados/exp_prefiltro_e2_t2_analisis.xlsx` (hojas
`I_inclusion`, `I_holdout_b`, `I_control_c`, `Z_trazabilidad`); 11 de 11 chequeos de sanidad.

- **Referencia:** dos jueces nuevos y ciegos (`juez-e`, `juez-f`) con un criterio escrito y confirmado por el usuario antes de
  formar la muestra; 105 artículos (los diez primeros con y sin filtro en 7 lugares). Caso confirmado = SÍ de los dos.
- **Regla de inclusión** (la misma de las etapas anteriores; se exigen las cuatro):

| Condición | Resultado | Cumple |
|---|---|---|
| (a) precisión de los diez primeros, 4 lugares | 0.05 → 0.19 (+0.14; se exige +0.20) | no |
| (b) precisión fuera de muestra, 3 departamentos | 0.07 → 0.13 (+0.07; se exige +0.10), todo juzgado | no |
| (c) control absurdo | las 4 comparaciones suben (+0.05 a +0.20) | sí |
| (d) coherencia entre máximo y casos confirmados | 1 → 1 incoherencias, 0 nuevas | sí |

- **Trazabilidad:** el artículo que fija el máximo es un caso confirmado en 2 de 7 lugares sin filtro y en 2 de 7 con filtro: la
  lista no cambia la evidencia que mostraría el radar.

Es la primera lista de la etapa 2 que pasa el control absurdo; lo que le falta es ganancia: con pocos casos confirmados (0 en
Cauca, 2 en Chocó, 2 en Cundinamarca), el filtro no sube lo suficiente la precisión de la cabeza del ranking.

## 5. Balance de la etapa 2

- 17 indicadores con lista propuesta: 6 en el tramo 1 (2 no medibles, 4 no cumplen) y 11 en este tramo (10 descartados en el
  cribado, 1 no cumple con jueces). **Ninguna lista nueva.** Los 4 indicadores abstractos pasan sin filtro por diseño.
- El motivo dominante es el mismo en las dos etapas: **el modelo confirma la forma de la frase, no su objeto.** Una lista de palabras
  cambia qué artículos llegan arriba, pero en 13 de las 18 listas a las que se aplicó el control absurdo (3 de la etapa 1, 4 del tramo
  1 y 11 de este tramo) el puntaje con filtro responde igual o más a un objeto absurdo.
- El pre-filtro por indicador queda, por tanto, en 2 de 26 indicadores (grupos armados y desplazamiento). Llegar a los 26 con este
  mecanismo no es posible con este modelo ni con esta referencia.

## 6. Decisión

**Se cierra la etapa 2 sin listas nuevas.** `src/` no cambia. Estas 11 listas, con esta redacción, no se reintentan sin evidencia nueva
medida (`contexto/08_log_decisiones.md`, [2026-09-29]).

## 7. Límites

- **Pocos casos.** 9 confirmados en total para la sobreviviente; 3 departamentos fuera de muestra.
- **Jueces automáticos**, no lectura humana (acuerdo kappa 0.72).
- **Once pruebas en el cribado:** que sobreviva una puede ser azar; por eso se exigió además la regla completa con jueces.
- **n = 32** en el radar: solo diferencias de correlación ≥ 0.15 se distinguen del ruido; las condiciones eran de no empeorar.

## 8. Pendiente de decisión

La fusión de la rama, su push y qué hacer con exclusión de beneficios («no medible»).

## 9. Archivos de origen

- Pre-registro y gemelas: `experimentos/PREREG_prefiltro_indicador_e2_t2.md`, `experimentos/hipotesis_prefiltro_e2_t2.py` (listas de
  `experimentos/hipotesis_prefiltro_e2.py`, congeladas en `da30a63`).
- Jueces: `.claude/agents/juez-e.md`, `.claude/agents/juez-f.md`; `experimentos/resultados/juicio_prefiltro_e2_t2/`.
- Scripts: `experimentos/exp_prefiltro_e2_t2_gpu.py`, `exp_prefiltro_e2_t2.py`, `exp_prefiltro_e2_t2_pool.py`,
  `exp_prefiltro_e2_t2_consolidar.py`, `exp_prefiltro_e2_t2_analisis.py`.
- Resultados: `experimentos/RESULTADOS_prefiltro_e2_t2.md`, `experimentos/RESULTADOS_prefiltro_e2_t2_analisis.md` y sus `.xlsx`.
