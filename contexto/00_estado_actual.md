# 00 — Estado actual

*Última actualización: 2026-09-01 (auditoría DSH: salvedades añadidas)*

Es el primer documento a leer al retomar. Responde: dónde estamos, qué corre, qué no.

## Dónde estamos

**Producción (`src/`) corre V2 desde el 2026-08-31** (antes V0). `python
src/orquestador_pipeline.py` (sin flags): hipótesis V2 (sin marco metalingüístico), sin
pre-filtro social, sesgo por artículo descontado, agregación P75 (no MAX), cortes fijos
Bajo/Medio/Alto (no terciles), clasificación oficial real del DANE (no re-tercilada).
Detalle completo de la promoción y de dos bugs no anticipados que se corrigieron de paso
(`radar.py` tenía 3 caminos de cálculo inconsistentes; `metricas_y_calculo_de_error.py`
no usaba la clasificación oficial real) en `08_log_decisiones.md` [2026-08-31].

V0 (la versión anterior) era indistinguible de un radar construido con hipótesis
absurdas (brecha 0.0004 en el MAX) y no correlacionaba con el oficial DANE (Spearman
+0.067, cero — salvedad: ese +0.067 proviene de una columna de procedencia no
identificada, ver `08_log_decisiones.md` [2026-08-31]). La receta V2 ya promovida
**sí lleva señal**: medida a escala nacional
sobre `scores_v2_32deptos.pkl` (todavía el único insumo de 32 departamentos —
**producción no se ha vuelto a correr sobre el corpus nacional completo**, ver "Qué NO
está hecho"), `Spearman(radar_V2, radar_oficial) = +0.384` a +0.42 según la variante
exacta de P75 (p<0.03, n=32), frente a +0.067 del V0 (misma salvedad), sin romper ninguna ancla de validez
aparente. No es una correlación fuerte y la accuracy en cortes fijos (25-31%, según la
entrada exacta) sigue lejos del 0.70 objetivo — con n=32 (regla 11) esas diferencias de
accuracy no son concluyentes por sí solas; el indicador de trabajo es el Spearman.
Detalle completo en `08_log_decisiones.md` [2026-08-30, 2026-08-31] y
`09_riesgos_y_limites.md`.

## Qué está hecho

- **26 indicadores NLI** (hipótesis V2 desde el 2026-08-31), cero NER, cero análisis de
  sentimiento (ambos desactivados y comentados en `Transformer_optimo.py`, junio 2026).
- **Sin pre-filtro social** (retirado el 2026-08-31, rechazado por AUC — ver abajo): los
  26 indicadores se puntúan sobre todos los artículos. En su lugar, sesgo por artículo
  (media de 4 hipótesis nulas) descontado de cada indicador.
- **Corpus nacional** de 11.439 artículos, 32 departamentos (`datos/corpus/`).
- **Corpus de trabajo** de 1.647 artículos (Antioquia 2023 + Maicao + Oicatá + Paraguachón).
- **Seis experimentos** con resultados en `experimentos/resultados/` y conclusiones en
  `experimentos/RESULTADOS.md`.
- **Las 26 hipótesis reescritas** (V2) en `experimentos/hipotesis_v2.py`, validadas en los
  dos indicadores que tienen estándar de plata.
- **Scoring V2 sobre los 32 departamentos** (`datos/scores/scores_v2_32deptos.pkl`,
  2026-08-30, ~4 h GPU). Es el insumo de la medición de correlación de arriba y de todo
  lo que sigue en el backlog (puntos 2, 3, 6).
- **Pre-filtro social V2 RECHAZADO y retirado de producción** (backlog punto 3, resuelto
  2026-08-31): cuesta AUC de forma clara en los 2 indicadores con estándar de plata
  (−0.053 y −0.027, IC95% excluye cero), y el control absurdo no lo explica. La
  correlación agregada del radar no lo detectaba (diferencia dentro del ruido) porque
  se diluye en la agregación P75. Ver `08_log_decisiones.md` [2026-08-31].
- **Cortes Bajo/Medio/Alto recalibrados sin pre-filtro y promovidos**: `Bajo < 0.2969 <=
  Medio < 0.3527 <= Alto` (backlog punto 2, ver `08_log_decisiones.md` [2026-08-31]).
  Una primera versión (0.3074/0.3524) se calibró sobre la distribución equivocada (P75
  interpolado en vez de rango cercano) y se corrigió el mismo día.
- **Agregación P75 (no MAX) promovida a `src/`**, por rango más cercano (conserva
  trazabilidad a un artículo real concreto para verificación manual).
- **4 fallas de scraper más corregidas** (backlog punto 1b, 2026-08-31): El País Cali
  (SSL/MITM en `newspaper.Article`, ajeno al fix del `self.session` de la entrada
  anterior — corregido en la clase base, beneficia a ~20 scrapers), Diario Occidente
  (paraba en el primer artículo viejo asumiendo orden cronológico que WordPress no
  garantiza), Corrillos/Enlace Televisión (timeout total contaba la espera en cola del
  pool de conexiones, no solo la descarga) y timeouts de listado/descarga de Diario
  Occidente por ser insuficientes para un sitio simplemente lento (no caído). Los 4
  verificados contra red real antes y después del fix. Ver `08_log_decisiones.md`
  [2026-08-31].
- **V2 promovido a `src/`** (backlog punto 2, 2026-08-31): `Transformer_optimo.py`,
  `radar.py`, `config_pipeline.py`, `orquestador_pipeline.py` y
  `metricas_y_calculo_de_error.py` tocados. Verificado offline (sin GPU, sobre
  `scores_v2_32deptos.pkl`) y con GPU (smoke test de `Transformer_optimo.py` real contra
  `nli_core`, corpus de 5 lugares, max\|dif\| ~5e-7). Nuevo baseline de verificación:
  `datos/scores/df_procesado_baseline_v2.pkl`. Ver `08_log_decisiones.md` [2026-08-31].

## Qué NO está hecho

- **Re-puntuar el corpus nacional completo (32 departamentos) con el código de `src/` ya
  promovido.** `scores_v2_32deptos.pkl` (de `experimentos/`, vía `nli_core`) sigue siendo
  el único insumo nacional — producción nunca corrió sobre los 32 departamentos con la
  receta V2. Costaría ~4h GPU; no se hizo esta sesión por pedido explícito del usuario de
  minimizar costo. Hasta entonces, todo número de correlación/accuracy "de producción"
  citado arriba en realidad viene de `experimentos/`, no de una corrida real de `src/`.
- **Fusionar el corpus re-scrapeado de 3 de los 4 departamentos de nombre compuesto.**
  Las 5 fallas de scraper originales (filtro de relevancia, SSL/MITM, El País, Diario
  Occidente, Corrillos/Enlace) ya están corregidas y verificadas contra red real
  (`08_log_decisiones.md` [2026-08-30] y [2026-08-31]). Re-scraping ya corrido: La
  Guajira 11→1553, Norte de Santander 36→352, Valle del Cauca 117→145. **San Andrés y
  Providencia sigue en 0** — depende 100% de El Tiempo, que tiene un 502 intermitente
  externo, no arreglable de este lado. El resultado vive en
  `experimentos/resultados/re_scrape_bugfix_relevancia/`, **todavía sin fusionar** con
  `datos/corpus/` (junction compartida con `desarrollo/`, decisión aparte). El scoring V2
  nacional (`datos/scores/scores_v2_32deptos.pkl`) sigue sobre el corpus viejo para estos
  departamentos — la medición de correlación (+0.384) y el AUC del pre-filtro
  subestiman si acaso, no inflan. Ver `07_backlog.md` punto 1b.

## Alcance actual

El proyecto se aplica a los 32 departamentos, pero el trabajo reciente se acotó a un
conjunto pequeño para iterar rápido: **Antioquia (2023)** más las veredas y municipios
**Maicao, Oicatá y Paraguachón** (agosto 2025 – agosto 2026). Güintiva se intentó y no
produjo artículos.

## Cómo se llegó hasta aquí

1. *Junio*: reducción de 31 a 26 indicadores, eliminación de los que medían "ausencia" de
   eventos, migración de `grupos_etnicos_existentes` de NER a NLI, desactivación de NER y
   sentimiento.
2. *Agosto (primera mitad)*: corpus de lugares sub-departamentales, `pipeline_lugares.py`,
   tablas por departamento.
3. *Agosto (segunda mitad)*: revisión de indicadores. Empezó con la sospecha de que las
   etiquetas NLI estaban invertidas — **descartada con evidencia** — y terminó encontrando
   tres defectos distintos y reales. Ver `04_hallazgos_revision_nli.md`.

## Aviso sobre carpetas antiguas

`Respaldo/Orquesta-v3_ultimo_commit/` es el directorio del que salió esta carpeta; queda
intacto como respaldo. `webscrapping_transformer_produccion/` está **congelada el
10-jun-2026** y le falta todo lo posterior: no usarla como referencia de nada salvo su
`radar.py` simplificado, que se copió aquí como `referencia_radar_simple.py`.
