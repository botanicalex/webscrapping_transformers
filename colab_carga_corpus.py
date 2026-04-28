# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE CORPUS — correr antes del pipeline NLP
# ══════════════════════════════════════════════════════════════════════════════

# ── Opción A: cargar desde Google Drive ───────────────────────────────────────
# from google.colab import drive
# drive.mount('/content/drive')
# RUTA_PKL = "/content/drive/MyDrive/fnce/resultados/"

# ── Opción B: subir pkl manualmente a Colab (o ruta local) ───────────────────
RUTA_PKL = "/content/resultados/"

# ── Dependencias ─────────────────────────────────────────────────────────────
import os
import glob
import pandas as pd
from datetime import datetime

# ── Cargar todos los pkl disponibles ─────────────────────────────────────────
archivos = sorted(glob.glob(os.path.join(RUTA_PKL, "df_corpus_*.pkl")))

if not archivos:
    raise FileNotFoundError(
        f"No se encontraron archivos df_corpus_*.pkl en '{RUTA_PKL}'.\n"
        "Verifica la ruta o sube los pkl antes de continuar."
    )

partes = []
cargados = []
fallidos = []

for ruta in archivos:
    nombre = os.path.basename(ruta)
    try:
        df_parte = pd.read_pickle(ruta)
        partes.append(df_parte)
        cargados.append((nombre, len(df_parte)))
    except Exception as e:
        fallidos.append((nombre, str(e)))

df_corpus_todos = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

# ── Verificar columnas necesarias para el pipeline ───────────────────────────
COLUMNAS_REQUERIDAS = ['periodico', 'titulo', 'fecha', 'texto', 'url', 'departamento']
COLUMNAS_OPCIONALES = ['terminos_encontrado']

faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df_corpus_todos.columns]
if faltantes:
    raise ValueError(
        f"El corpus cargado no tiene las columnas requeridas: {faltantes}\n"
        f"Columnas presentes: {list(df_corpus_todos.columns)}"
    )

# ── Limpieza básica ───────────────────────────────────────────────────────────
antes = len(df_corpus_todos)
df_corpus_todos = df_corpus_todos.drop_duplicates(subset=['url'])
duplicados = antes - len(df_corpus_todos)

# Asegurar tipo datetime en 'fecha'
df_corpus_todos['fecha'] = pd.to_datetime(df_corpus_todos['fecha'], errors='coerce')

# Descartar filas sin texto ni título
sin_contenido = df_corpus_todos['texto'].isna() | (df_corpus_todos['texto'].str.strip() == '')
df_corpus_todos = df_corpus_todos[~sin_contenido].reset_index(drop=True)

# ── Resumen ───────────────────────────────────────────────────────────────────
print("=" * 62)
print("  CORPUS CARGADO")
print("=" * 62)
print(f"  Archivos pkl leídos  : {len(cargados)}")
print(f"  Total artículos      : {len(df_corpus_todos):,}")
print(f"  Duplicados eliminados: {duplicados:,}")
if fallidos:
    print(f"  ⚠  Archivos con error: {len(fallidos)}")
    for nombre, err in fallidos:
        print(f"     {nombre}: {err}")

fecha_min = df_corpus_todos['fecha'].min()
fecha_max = df_corpus_todos['fecha'].max()
print(f"\n  Rango de fechas : {fecha_min:%Y-%m-%d}  →  {fecha_max:%Y-%m-%d}")
print(f"  Columnas        : {list(df_corpus_todos.columns)}")

print("\n  Artículos por departamento:")
conteo = (df_corpus_todos['departamento']
          .value_counts()
          .rename_axis('Departamento')
          .rename('Artículos'))
print(conteo.to_string())

print("\n  Archivos cargados:")
for nombre, n in cargados:
    print(f"    {nombre:<45} {n:>5} artículos")
print("=" * 62)
print("  ✓  df_corpus_todos listo para el pipeline NLP")
print("=" * 62)

# ── df_corpus_todos listo para pasar al pipeline ──────────────────────────────
# df_procesado = pipeline.procesar_dataframe(df_corpus_todos, columna_texto='texto')
