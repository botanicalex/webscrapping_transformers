# 00 — Estado actual

*Última actualización: 2026-08-27*

Es el primer documento a leer al retomar. Responde: dónde estamos, qué corre, qué no.

## Dónde estamos

El pipeline funciona de extremo a extremo y produce un radar por departamento. **El
problema no es que falle: es que su salida no discrimina.** Una revisión de seis
experimentos (agosto 2026) midió que el radar de producción es indistinguible de uno
construido con hipótesis absurdas — la diferencia entre el MAX de un indicador real y el de
"hay osos polares en este territorio" es de **0.0004**.

Se identificaron tres defectos, todos con corrección propuesta y validada sobre un corpus de
1.647 artículos. **Ninguna de esas correcciones está aplicada a `src/` todavía.** Viven en
`experimentos/` y esperan la validación nacional.

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

## Qué NO está hecho

- **El scoring V2 sobre los 32 departamentos.** Es el insumo de todo lo demás. Se intentó,
  la corrida se perdió al apagar el equipo (el script guarda solo al final). Son ~4 h.
  Relanzar con `cd experimentos && python generar_scores_32deptos.py`.
- **Recalibrar los cortes Bajo/Medio/Alto.** Con P75 los valores caen entre 0.12 y 0.32 y
  los cortes 1/3–2/3 mandan todo a "Bajo".
- **Decidir la suerte del pre-filtro social.** Ver `07_backlog.md`.
- **Aplicar nada de V2 a `src/`.** Producción sigue con las hipótesis V0.

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
