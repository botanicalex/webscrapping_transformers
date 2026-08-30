# Radar de riesgo territorial — entorno de desarrollo

Pipeline que calcula un radar de riesgo por departamento de Colombia a partir de prensa
regional. **Radar alto = zona difícil o inviable para implementar proyectos.**

Para el contexto completo, ver `CLAUDE.md` y la carpeta `contexto/`.

## Estructura

```
desarrollo/
├── CLAUDE.md            se carga solo en cada conversacion; reglas duras
├── contexto/            documentacion bajo demanda (00 a 08)
├── src/                 pipeline de produccion — ejecutar DESDE LA RAIZ
├── experimentos/        revision de indicadores — ejecutar DESDE experimentos/
├── datos/
│   ├── corpus/          texto crudo de noticias
│   ├── referencia/      radar oficial DANE
│   └── scores/          matrices ya calculadas — reutilizar antes de tocar la GPU
└── resultados/          salidas (fuera de git)
```

## Requisitos

Python con PyTorch + CUDA (probado en RTX 4050), `transformers`, `pandas`, `openpyxl`,
`scikit-learn`, `matplotlib`, `seaborn`. Para scraping: `playwright`, `aiohttp`,
`nest_asyncio`. Ver `requirements.txt`.

El modelo NLI se descarga a `~/.cache/huggingface/hub` la primera vez.

## Uso

### Scraping

```bash
python src/correr_grupo.py --listar     # ver la composicion de los 11 grupos
python src/correr_grupo.py 5            # un grupo
python src/correr_grupo.py --todos      # los 11, en secuencia
python src/monitor.py                   # que departamentos ya tienen pkl
```

Los grupos están armados para que dos departamentos que usan el mismo periódico no compitan
por el servidor. Leer el comentario de `GRUPOS_DEPARTAMENTOS` en `src/config_pipeline.py`
antes de reordenarlos.

**Trampa importante:** el filtro de relevancia usa solo la **primera palabra** del término
de búsqueda. Nunca pasar `"Vereda Paraguachón"` — contaría menciones de "vereda". Ver
`contexto/05_scraping.md`.

### Pipeline completo

```bash
python src/orquestador_pipeline.py --skip-scraping
```

### Lugares sub-departamentales (veredas, municipios)

```bash
python src/scrape_lugares.py            # edita LUGARES dentro del script
python src/pipeline_lugares.py          # corpus -> indicadores -> excels
```

### Tablas por departamento

```bash
python src/generar_tablas_por_departamento.py          # con GPU, ~2 h
python src/generar_max_articulos_por_departamento.py   # sin GPU, desde el pkl
```

### Tests

```bash
python src/test_integracion.py
```

Corpus sintético, sin cargar modelos. Es la única red de seguridad del repositorio: correrlo
tras cualquier cambio en el núcleo.

### Experimentos

```bash
cd experimentos
python exp_formato.py         # eje de formato de hipotesis
python exp_agregacion_v2.py   # agregacion y umbrales, sin GPU (lee el pkl de scores)
```

Antes de cualquier experimento, verificar que el motor reproduce producción:

```python
from nli_core import NLIScorer, verificar_contra_produccion
import hipotesis_base as HB
s = NLIScorer()
verificar_contra_produccion(s, "../datos/scores/df_procesado_baseline.pkl",
                            "presencia_grupos_armados",
                            HB.TODAS["presencia_grupos_armados"])
```

Debe dar `max|dif| = 0.00e+00`.

## Herramientas de Claude Code

- **Skill `experimento-hipotesis`** — el ciclo validado para probar variantes de hipótesis.
- **Agente `orquesta-lead`** — lee el contexto y propone el siguiente paso.

## Notas de rendimiento

- 11.439 artículos × 26 hipótesis ≈ 125 min de GPU.
- El pre-filtro social corre primero y solo se puntúan los artículos relevantes: ahorra ~38%.
- `datos/scores/scores_v2.pkl` permite recalcular correcciones, umbrales y agregaciones
  **sin GPU**. Mirar ahí antes de puntuar nada de nuevo.
- Los scripts que escriben `.xlsx` fallan con `PermissionError` si el archivo está abierto en
  Excel. Los que corren GPU guardan el `.pkl` antes de escribir los Excel, así que una
  interrupción no obliga a repetir la corrida.
