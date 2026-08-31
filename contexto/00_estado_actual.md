# 00 — Estado actual

*Última actualización: 2026-08-30*

Es el primer documento a leer al retomar. Responde: dónde estamos, qué corre, qué no.

## Dónde estamos

El pipeline funciona de extremo a extremo y produce un radar por departamento.
Producción (`src/`) sigue con las hipótesis **V0**, que son indistinguibles de un radar
construido con hipótesis absurdas (brecha 0.0004 en el MAX) y no correlacionan con el
oficial DANE (Spearman +0.067, cero).

Las correcciones (V2) ya se midieron a escala nacional el 2026-08-30, y **sí llevan
señal**: `Spearman(radar_V2, radar_oficial) = +0.384` (p=0.030, n=32), frente a +0.067
del V0, con el control de la nula reservada dando ~0.0000 y ninguna ancla de validez
rota. No es una correlación fuerte y la accuracy en terciles (37.5%) sigue lejos del
0.70 objetivo, pero es la primera evidencia de que el problema no es solo el radar V0:
los indicadores V2 apuntan, al menos parcialmente, al constructo correcto. Detalle
completo en `08_log_decisiones.md` [2026-08-30] y `09_riesgos_y_limites.md`.

**Ninguna corrección V2 está aplicada a `src/` todavía.** Viven en `experimentos/`.

## Qué está hecho

- **26 indicadores NLI**, cero NER, cero análisis de sentimiento (ambos desactivados y
  comentados en `Transformer_optimo.py`, junio 2026).
- **Pre-filtro social primero**: se calcula `score_social` antes de los indicadores y las 26
  hipótesis solo se corren sobre los artículos que pasan. Ahorra ~38% de GPU.
- **Corpus nacional** de 11.439 artículos, 32 departamentos (`datos/corpus/`).
- **Corpus de trabajo** de 1.647 artículos (Antioquia 2023 + Maicao + Oicatá + Paraguachón).
- **Seis experimentos** con resultados en `experimentos/resultados/` y conclusiones en
  `experimentos/RESULTADOS.md`.
- **Las 26 hipótesis reescritas** (V2) en `experimentos/hipotesis_v2.py`, validadas en los
  dos indicadores que tienen estándar de plata.
- **Scoring V2 sobre los 32 departamentos** (`datos/scores/scores_v2_32deptos.pkl`,
  2026-08-30, ~4 h GPU). Es el insumo de la medición de correlación de arriba y de todo
  lo que sigue en el backlog (puntos 2, 3, 6).
- **Cortes Bajo/Medio/Alto recalibrados** sobre el radar V2 nacional: `Bajo < 0.30 <=
  Medio < 0.35 <= Alto` (backlog punto 2, ver `08_log_decisiones.md` [2026-08-30]).

## Qué NO está hecho

- **Decidir la suerte del pre-filtro social.** El A/B (con vs sin umbral 0.85) dio
  +0.384 vs +0.376 de Spearman — diferencia dentro del ruido, apunta a que es
  prescindible pero falta confirmar con AUC/control absurdo por indicador antes de
  tocar producción. Ver `07_backlog.md` punto 3.
- **Aplicar nada de V2 a `src/`.** Producción sigue con las hipótesis V0.
- **Re-scrapear del todo los 4 departamentos de nombre compuesto** (La Guajira, Norte de
  Santander, San Andrés y Providencia, Valle del Cauca): dos bugs de scraping ya se
  corrigieron (filtro de relevancia, SSL/MITM), pero quedan 3 fallas de scraper sin
  resolver (El Tiempo caído, parser de El País, timeouts de Corrillos/Enlace). Ver
  `07_backlog.md` punto 1b. El scoring V2 nacional ya corrido usa el corpus viejo para
  esos 4 (11/36/79/117 artículos), así que la medición de correlación de arriba
  subestima si acaso — no la infla.

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
