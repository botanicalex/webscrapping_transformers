# 06 — Inventario de datos

**Antes de correr la GPU, mirar aquí.** Varias cosas ya están calculadas.

## `datos/corpus/` — texto crudo

Esquema: `periodico, titulo, fecha, texto, url, departamento`.

| Archivo | Filas | Contenido |
|---|---|---|
| `df_corpus_combinado_32deptos.pkl` | 11.439 | **Corpus maestro nacional**, los 32 departamentos DANE |
| `df_corpus_5lugares.pkl` | 1.647 | **Corpus de trabajo actual** |
| `df_corpus_municipio_maicao.pkl` | 1.101 | pieza |
| `df_corpus_municipio_oicata.pkl` | 32 | pieza |
| `df_corpus_vereda_paraguachon.pkl` | 77 | pieza (ojo, ver abajo) |

Composición de `df_corpus_5lugares.pkl`: Antioquia 2023 (494) · Maicao (1.101) ·
Oicatá (32) · Paraguachón (20).

### Advertencias

**Paraguachón tiene 20 artículos en el corpus combinado, no 77.** Su pkl individual trae 77,
pero **57 URLs (74%) se solapan con Maicao** —es corregimiento suyo— y el dedup por URL
(`keep='first'`, orden alfabético del glob) se las atribuyó a Maicao. El reparto entre
vereda y municipio lo decidió el orden de los archivos, no un criterio metodológico. Sus 26
indicadores salen de 10 artículos relevantes.

**Güintiva no existe en el corpus: 0 artículos.** Se intentó con `boyaca7dias` y `eltiempo`;
sin cobertura de prensa en 12 meses. Es un resultado plausible para una vereda, no un fallo.

**Oicatá (32) y Paraguachón (20) son bases muy pequeñas.** Sus radares son frágiles y no
sostienen conclusiones por lugar.

## `datos/referencia/`

| Archivo | Contenido |
|---|---|
| `comparacion_radares_V3.xlsx` | **El radar oficial DANE limpio.** 32 × 6. La verdad de referencia |
| `comparacion_radares.xlsx` | El mismo oficial + 13 columnas `EXPERIMENTO_*` viejas. Lo consume la ruta legado |

Ver `01_objetivo_y_radar.md`.

## `datos/scores/` — ya calculado, no repetir

| Archivo | Filas × cols | Qué es |
|---|---|---|
| `df_procesado_32deptos.pkl` | 11.439 × 38 | **Único resultado nacional vigente.** 26 indicadores V0 + `score_social` + dims. Junio 2026 |
| `df_procesado_baseline.pkl` | 1.647 × 38 | **Baseline de los experimentos.** V0 con los 4 cambios manuales. Agosto 2026 |
| `scores_v2.pkl` | 1.647 × 58 | **El más valioso.** `ent_*` y `neu_*` por indicador **sin enmascarar**, más `sesgo` y `score_social_v2`. Salida de las hipótesis V2 |

`scores_v2.pkl` permite recalcular offline cualquier corrección, umbral o agregación **sin
tocar la GPU**. Usarlo antes de puntuar nada de nuevo.

### Lo que falta

`scores_v2_32deptos.pkl` — el equivalente nacional. **No existe**: la corrida se perdió al
apagar el equipo. Son ~4 h:

```bash
cd experimentos && python generar_scores_32deptos.py
```

Ese script guarda **solo al final**. Si hay riesgo de interrupción, conviene modificarlo
para que guarde por lotes.

## `resultados/`

Salidas regenerables, fuera de git. Incluye
`resumen_indicadores_MAX_y_articulos_por_departamento.xlsx` de la corrida de junio.

## `experimentos/resultados/`

Los seis `exp*.xlsx` de la revisión de agosto. Pesan ~50 KB en total y **sí** están
versionados: son la evidencia de las conclusiones.

## Qué se dejó fuera al migrar

Del directorio original se descartaron ~190 MB: `Cambio_indicadores/`,
`alexa_resultados_pipeline/`, `resultados_pipeline/`, `Indicadores transformers/`,
`corpus_lugares_backup_prev/` (versión previa con 611 filas en vez de 1.647), duplicados de
tablas por departamento y por lugar, y varios Excel de métricas de variantes abandonadas
(P5, P8, sin-pesos).

Todo sigue existiendo en `Respaldo/Orquesta-v3_ultimo_commit/`, que **no se tocó**.

Nota: `webscrapping_transformer_produccion/` (5.4 GB, de los cuales 5.3 GB son `.venv`) está
congelada el 10-jun-2026 y le falta todo lo posterior. No usarla como referencia. Lo único
que se rescató de ahí es su `radar.py` simplificado, copiado como
`referencia_radar_simple.py`: no es una versión vieja sino una reescritura minimalista
deliberada para entrega final (promedio simple en [0,1], umbrales fijos, sin PCA ni z-score).
