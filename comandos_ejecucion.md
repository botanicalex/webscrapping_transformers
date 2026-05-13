# Comandos de ejecución del pipeline

## Variables de entorno útiles

```powershell
# Ruta base del proyecto
$REPO = "C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\webscrapping_transformers"
```

---

## Solo transformers (sin scraping)

### Caso base — corpus en `resultados/`, salida en `resultados_pipeline/`

```powershell
python Transformer_optimo.py --skip-scraping
```

### Con carpeta de corpus personalizada

```powershell
python Transformer_optimo.py `
  --skip-scraping `
  --ruta-pkl "resultados" `
  --salida "resultados_pipeline"
```

---

## Transformers sobre corpus Alexa

Ejecutar desde el directorio del proyecto. Usa los pkl de `Alexa/` y guarda el CSV de indicadores con nombre propio.

> **Nota:** Si hay errores SSL al conectar con HuggingFace, anteponer `TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1` (Bash/Linux/Mac) o las variables de entorno equivalentes en PowerShell. Los modelos deben estar ya descargados en `~/.cache/huggingface/hub/`.

**Bash / Git Bash (recomendado si hay problemas SSL):**

```bash
TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 python Transformer_optimo.py \
  --skip-scraping \
  --ruta-pkl "C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\webscrapping_transformers\Alexa" \
  --salida "C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\webscrapping_transformers\alexa_resultados_pipeline" \
  --nombre-indicadores "alexa_indicadores_transformers_departamento.csv"
```

**PowerShell:**

```powershell
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
python Transformer_optimo.py `
  --skip-scraping `
  --ruta-pkl "C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\webscrapping_transformers\Alexa" `
  --salida "C:\Users\Usuario\Documents\REPOSITORIOS\Web_scrapping_2026\webscrapping_transformers\alexa_resultados_pipeline" `
  --nombre-indicadores "alexa_indicadores_transformers_departamento.csv"
```

**Salidas generadas en `alexa_resultados_pipeline/`:**

| Archivo | Descripción |
|---|---|
| `df_procesado.pkl` | DataFrame con scores NLP por artículo |
| `df_procesado.csv` | Idem en CSV |
| `alexa_indicadores_transformers_departamento.csv` | Media de indicadores por departamento |
| `radar_departamentos.pkl` | Base para cálculo de radar (bloques vacíos) |
| `radar_departamentos.csv` | Idem en CSV |

---

## Pipeline completo (scraping + transformers)

```powershell
python Transformer_optimo.py `
  --fecha-desde "2023-01-01" `
  --fecha-hasta "2023-12-31" `
  --ruta-pkl "resultados" `
  --salida "resultados_pipeline"
```

---

## Parámetros disponibles en `Transformer_optimo.py`

| Parámetro | Default | Descripción |
|---|---|---|
| `--skip-scraping` | `False` | Omite la etapa de scraping |
| `--ruta-pkl` | `resultados` | Carpeta con los `df_corpus_*.pkl` |
| `--salida` | `resultados_pipeline` | Carpeta de salida del pipeline NLP |
| `--nombre-indicadores` | `indicadores_transformers_departamento.csv` | Nombre del CSV de indicadores por departamento |
| `--fecha-desde` | `2023-01-01` | Fecha inicio del scraping |
| `--fecha-hasta` | `2023-12-31` | Fecha fin del scraping |

---

## Notas

- El script detecta automáticamente GPU (`torch.cuda.is_available()`); si no hay GPU usa CPU.
- Los modelos se descargan de HuggingFace la primera vez; en ejecuciones posteriores se usan desde caché local (`~/.cache/huggingface/hub/`).
- Con CPU, procesar ~30 departamentos puede tomar varias horas dependiendo del volumen de artículos.
- `--ruta-pkl` acepta rutas absolutas o relativas al directorio de ejecución.

---

## Radar sin pesos + métricas de clasificación (`comparar_radares_sin_pesos.py`)

Calcula radar como promedio simple de los 36 indicadores (sin invertir variables, sin pesos),
normaliza a 0-1, clasifica por quintiles en 5 categorías, agrega columnas al xlsx de comparación
y genera un xlsx con métricas de clasificación (accuracy, F1, kappa, matrices de confusión).

> **Importante:** cerrar `comparacion_radares_V2.xlsx` en Excel antes de ejecutar,
> de lo contrario Excel sobreescribe los cambios al guardarlo.

**Ejecutar desde la raíz del proyecto:**

```powershell
python comparar_radares_sin_pesos.py `
  --csv-viejo "Indicadores transformers\viejo_alexa_indicadores_transformers_departamento_completo.csv" `
  --csv-nuevo "Indicadores transformers\nuevo_alexa_indicadores_transformers_departamento.csv" `
  --xlsx-comparacion "comparacion_radares_V2.xlsx" `
  --salida-metricas "metricas_clasificacion_sin_pesos.xlsx"
```

**Salidas:**

| Archivo | Descripción |
|---|---|
| `comparacion_radares_V2.xlsx` | +4 columnas: `radar_viejo_promedio_normalizado`, `Clasificacion_radar_viejo`, `radar_nuevo_promedio_normalizado`, `Clasificacion_radar_nuevo` |
| `comparacion_radares_V2_backup.xlsx` | Backup automático (se crea solo si no existe) |
| `metricas_clasificacion_sin_pesos.xlsx` | Hojas: `resumen`, `detalle_por_clase`, `matrices_confusion` |

**Parámetros de `comparar_radares_sin_pesos.py`:**

| Parámetro | Descripción |
|---|---|
| `--csv-viejo` | CSV de indicadores "viejo" (ruta absoluta o relativa) |
| `--csv-nuevo` | CSV de indicadores "nuevo" |
| `--xlsx-comparacion` | xlsx destino donde se agregan las 4 columnas |
| `--salida-metricas` | xlsx de salida con métricas de clasificación |

**Comparaciones de clasificación que calcula:**

| Predicción | Referencia |
|---|---|
| `Clasificacion_radar_viejo` | `Clasificacion_radar_oficial_promedio` |
| `Clasificacion_radar_viejo` | `Clasificacion_IDIC` |
| `Clasificacion_radar_nuevo` | `Clasificacion_radar_oficial_promedio` |
| `Clasificacion_radar_nuevo` | `Clasificacion_IDIC` |

---

## Solución al error SSL con HuggingFace

En redes con certificados corporativos o proxies, `AutoTokenizer.from_pretrained()` puede fallar con:

```
SSLCertVerificationError: certificate verify failed: unable to get local issuer certificate
```

**Causa:** la librería `transformers` llama internamente a `model_info()` de HuggingFace Hub (para verificar si es un modelo Mistral), incluso cuando el modelo ya está en caché local.

**Solución implementada en el código:** la función `_ruta_modelo_local()` en `Transformer_optimo.py` resuelve la ruta del snapshot local desde `~/.cache/huggingface/hub/` y la pasa directamente a `from_pretrained()`. Al recibir un directorio local (`os.path.isdir() == True`), la librería omite la llamada a la API de HuggingFace.

**Verificar qué snapshots hay en caché:**

```powershell
# PowerShell
Get-Content "$env:USERPROFILE\.cache\huggingface\hub\models--MoritzLaurer--mDeBERTa-v3-base-xnli-multilingual-nli-2mil7\refs\main"
Get-Content "$env:USERPROFILE\.cache\huggingface\hub\models--finiteautomata--beto-sentiment-analysis\refs\main"
Get-Content "$env:USERPROFILE\.cache\huggingface\hub\models--dccuchile--bert-base-spanish-wwm-cased-finetuned-ner\refs\main"
```
