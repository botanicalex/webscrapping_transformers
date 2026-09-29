# Pre-registro — Pre-filtro por indicador, etapa 2, tramo 2: cribado sin jueces de los 11 restantes

Fecha: 2026-09-29 · Rama: `hipotesis-5ind-max` · Base: `71c8aeb` · Gemelas y lista de indicadores:
`experimentos/hipotesis_prefiltro_e2_t2.py`; listas: `LISTAS_SOLO_APERTURA` de `experimentos/hipotesis_prefiltro_e2.py`
(congeladas en `da30a63`, sin retocar).

**A partir del commit que introduce este archivo, nada de §0–§9 cambia.** Toda desviación se registra en
`contexto/08_log_decisiones.md`. Antes de este commit no se calculó ninguna gemela, máscara nacional con puntajes, control
absurdo ni radar de estos 11 indicadores; lo único medido son sus tasas de apertura (`juicio_prefiltro_e2/aperturas.csv`, todas
≤ 0.2369, bajo el techo de 0.50). Decisión del usuario (2026-09-29): opción C, con las 11 listas sin retocar y la condición §6
con la lista sola como filtro previo (excepción a la regla 15 con el alcance de §8).

## 0. Pregunta y refutación

**Pregunta:** ¿alguna de las 11 listas restantes cumple las dos condiciones que tumbaron al tramo 1 (control absurdo y radar
nacional), de modo que valga la pena gastar jueces en ella?

**Refutación (cerrar la etapa 2):** ninguna lista pasa §2 y §3 a la vez. Entonces los 11 pasan sin filtro, la etapa 2 se cierra
y no se lanza ningún juez. Los 4 abstractos pasan sin filtro en cualquier caso.

## 1. Por qué un cribado sin jueces

En el tramo 1, 3 de las 4 listas medibles fallaron (c) y las 4 solas subieron el Spearman con el tamaño por encima de +0.8640
(§6.3). Las dos cosas se calculan sin referencia. Aplicado al tramo 1, este cribado habría descartado las 4 (sanidad S3). Ambas
condiciones son necesarias bajo la regla vigente; §3 con la lista **sola** es algo más estricta que la cadena de retirada del
tramo 1 (con una sola lista nueva son idénticas).

## 2. Condición C (control absurdo, sin jueces)

Mecanismo: `score' = s × 1[lista ∈ premisa visible normalizada]`, premisa recortada con la hipótesis de cada indicador
(`premisa_visible_prod`, como `PREFILTRO_OBJETO`). Igual que `inclusion()` de `experimentos/exp_prefiltro_e2.py`: por lugar,
brecha MAX real − MAX gemela y MAX real − MAX absurdo total (`NULA_TEST`), sin y con máscara. **Pasa** si, en las cuatro
comparaciones {gemela, total} × {media de los 4 lugares, media del holdout Cauca/Chocó/Cundinamarca},
con máscara ≥ sin máscara − 5e-5. Puntajes reales: lugares, corrida de producción del 2026-09-29
(`resultados/tablas_lugares_max_prefiltro_2026-09-29/`); holdout, `scores_v2_32deptos.pkl` con la fórmula de producción. Gemelas
y absurdo con la misma fórmula (sesgo descontado).

## 3. Condición R (radar nacional con la lista sola)

Radar MAX de los 32 departamentos con las 2 listas de producción más **solo** esta lista, cortes recalibrados por `elegir_cortes`
sobre el radar sin redondear. **Pasa** si: 0 anclas rotas (y hay cortes válidos); Spearman contra `radar_oficial_promedio`
≥ −0.0913; Spearman(radar, nº de artículos) ≤ +0.8640; desigualdades a 4 decimales. Igual que `criterios()` de
`exp_prefiltro_e2.py`.

## 4. Decisión del cribado

- **Sobrevive** una lista que pasa C y R. `exclusion_comunidades` y `deficit_participacion_comunitaria` comparten lista pero se
  evalúan por separado (hipótesis y gemela distintas).
- **0 sobrevivientes:** cierre de la etapa 2 (§0). Informe 14.
- **≥ 1 sobreviviente:** parada. Se reporta al usuario; luego una fase de jueces **solo** para las sobrevivientes, con el
  procedimiento de `PREREG_prefiltro_indicador_e2.md` §3–§6 tal cual: agentes nuevos `juez-e` (sonnet) y `juez-f` (opus) con un
  codebook SÍ/NO por indicador escrito **antes** de formar el pool y confirmado por el usuario; kappa < 0.4 → no se adopta;
  < 5 SÍ/SÍ → «no medible»; regla de inclusión (a)–(d); tope de **3** listas nuevas (orden de §5 del tramo 1); mecanismo combinado
  con retirada; empate = NO. Holdout y lugares, los mismos. Pool con semilla 20260930 e ids `t0000…`.
- `grupos_etnicos_existentes`: la plata no se usa como referencia (sería circular); si sobrevive, su referencia son los jueces.

## 5. Sanidad (bloqueante: si falla, se para sin decidir)

- S1: sin listas nuevas se reproduce producción: cortes 0.7572/0.9233, 6/19/7, Spearman DANE −0.0913, tamaño +0.8640, 0 anclas.
- S2: verificación de producción del NLI antes de la GPU (max|dif| < 1e-4).
- S3: con las 4 listas medibles del tramo 1 (gemelas de `scores_prefiltro_e2.pkl`), C y R reproducen `RESULTADOS_prefiltro_e2.md`
  (p. ej. `amenaza_intimidacion`: gemela lugares −0.11386; sola: Spearman DANE −0.1015, tamaño 0.8666) y ninguna sobrevive.
- S4: las tasas de apertura nacionales de los 11 coinciden con `aperturas.csv`.
- S5: los puntajes reales de los 11 en los lugares coinciden con la corrida de producción (máx |dif| < 1e-4 si se recalculan).

## 6. GPU (una sola vez)

Las 11 gemelas sobre los 1.647 artículos de los lugares y los 1.117 del holdout (premisa = `texto`, batch 32, max_length 512), en
un pkl nuevo `datos/scores/scores_prefiltro_e2_t2.pkl` (no versionado), `ent_`/`neu_` sin enmascarar. Unos 20–25 min. El absurdo
total ya existe (`scores_prefiltro_lugares.pkl`, `scores_v2_32deptos.pkl`). No se sobrescribe ningún pkl existente.

## 7. Salidas

`experimentos/exp_prefiltro_e2_t2_gpu.py`, `experimentos/exp_prefiltro_e2_t2.py` →
`experimentos/resultados/exp_prefiltro_e2_t2.xlsx` (hojas `S_sanidad`, `C_control`, `C_detalle`, `R_radar`, `K_cribado`) y
`experimentos/RESULTADOS_prefiltro_e2_t2.md`. Los scripts del tramo 1 no se modifican (se importan).

## 8. Alcance de la excepción a la regla 15

Las 11 listas solo se usan en `experimentos/`. Ninguna entra a `src/` sin pasar además la fase de jueces y sin nueva aprobación
del usuario. Si alguna entra: nuevas claves en `PREFILTRO_OBJETO` (`src/Transformer_optimo.py`), cortes en
`src/config_pipeline.py`, pruebas en `src/test_integracion.py`, equivalencia offline y recorrida de los 4 lugares con
`experimentos/exp_prefiltro_correr_lugares.py`. Sin columnas nuevas; MAX y 26 indicadores intactos.

## 9. Límites declarados

- Once pruebas: el cribado reduce la multiplicidad antes de los jueces, pero una lista puede sobrevivir por azar; por eso las
  sobrevivientes pasan aún por (a)–(d), el tope y el combinado.
- n = 32: los criterios R son de no empeorar; una mejora de Spearman < 0.15 no se distingue del ruido.
- El codebook de una sobreviviente se escribe tras ver el cribado (puntajes agregados, ningún artículo ni juicio); por eso exige
  la confirmación del usuario antes del pool.
- Las gemelas se escribieron sin datos, pero después de conocer el tramo 1.
