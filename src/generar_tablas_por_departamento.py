"""
Corre el pipeline NLI (26 hipótesis V2, sin pre-filtro social, sesgo
descontado, score corregido) sobre el corpus combinado de 32 departamentos y
genera UNA tabla de indicadores por articulo por cada departamento (mismo
formato que el Excel de Antioquia).

Salida:
  tablas_indicadores_departamentos/
    df_procesado_32deptos.pkl              (respaldo del trabajo GPU)
    tabla_indicadores_<departamento>.xlsx  (uno por depto)
"""
import os
import sys
import unicodedata

import pandas as pd

DIR_SRC = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_SRC)   # raiz de desarrollo/
sys.path.insert(0, DIR_SRC)

from Transformer_optimo import PipelineTransformers
from radar import CalculadorRadar

ENTRADA = os.path.join(DIR_PROYECTO, "datos", "corpus", "df_corpus_combinado_32deptos.pkl")
DIR_SALIDA = os.path.join(DIR_PROYECTO, "resultados", "tablas_departamentos")
PROCESADO_PKL = os.path.join(DIR_SALIDA, "df_procesado_32deptos.pkl")


def slug(nombre: str) -> str:
    """Nombre de archivo seguro: sin tildes, minusculas, guiones bajos."""
    txt = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode("ascii")
    txt = txt.strip().lower()
    return "".join(c if c.isalnum() else "_" for c in txt).strip("_")


def escribir_tablas(df_proc: pd.DataFrame) -> None:
    columnas = ["titulo"] + CalculadorRadar.COLUMNAS_BINARIAS

    os.makedirs(DIR_SALIDA, exist_ok=True)
    resumen = []
    for depto, grupo in df_proc.groupby("departamento"):
        df_tabla = grupo[columnas].copy()
        for c in CalculadorRadar.COLUMNAS_BINARIAS:
            if df_tabla[c].dtype == bool:
                df_tabla[c] = df_tabla[c].astype(int)
        ruta = os.path.join(DIR_SALIDA, f"tabla_indicadores_{slug(depto)}.xlsx")
        df_tabla.to_excel(ruta, index=False)
        resumen.append((str(depto), len(df_tabla), os.path.basename(ruta)))

    print(f"\n{'Departamento':<26} {'Articulos':>10}  Archivo")
    for depto, n, arch in sorted(resumen):
        print(f"{depto:<26} {n:>10}  {arch}")
    print(f"\nTotal: {len(resumen)} departamentos -> {DIR_SALIDA}")


def main():
    df_corpus = pd.read_pickle(ENTRADA)
    sin_texto = df_corpus["texto"].isna() | (df_corpus["texto"].astype(str).str.strip() == "")
    df_corpus = df_corpus[~sin_texto].reset_index(drop=True)
    print(f"Corpus combinado: {len(df_corpus)} articulos | {df_corpus['departamento'].nunique()} deptos")

    pipeline = PipelineTransformers()
    df_proc = pipeline.procesar(df_corpus)

    os.makedirs(DIR_SALIDA, exist_ok=True)
    df_proc.to_pickle(PROCESADO_PKL)
    print(f"\n[respaldo] df_procesado guardado -> {PROCESADO_PKL} (shape={df_proc.shape})")

    escribir_tablas(df_proc)


if __name__ == "__main__":
    main()
