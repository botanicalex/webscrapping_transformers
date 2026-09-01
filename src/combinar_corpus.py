"""
Actualiza el corpus nacional reemplazando departamentos por su version fresca.

Toma como base `datos/corpus/df_corpus_combinado_32deptos.pkl` (11.439 articulos,
32 departamentos) y, por cada `df_corpus_<depto>.pkl` que encuentre en
`datos/corpus/actualizados/`, elimina las filas viejas de ese departamento e
inserta las nuevas. Deduplica por URL y descarta filas sin texto.

Resultado: corpus unico con columnas base, listo para puntuar. NO corre
transformers.

Uso tipico: despues de re-scrapear uno o varios departamentos con
`python src/correr_grupo.py N --salida datos/corpus/actualizados`.

Nota historica: la version original de este script partia de un corpus "alexa"
que vivia en el repo hermano `webscrapping_transformers/`. Ese repo no forma
parte de `desarrollo/`; su aporte ya esta incorporado en el corpus combinado,
que es ahora la base.
"""
import glob
import os

import pandas as pd

DIR_SRC = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_SRC)   # raiz de desarrollo/

DIR_CORPUS = os.path.join(DIR_PROYECTO, "datos", "corpus")
RUTA_BIG = os.path.join(DIR_CORPUS, "df_corpus_combinado_32deptos.pkl")
DIR_ULTIMOS = os.path.join(DIR_CORPUS, "actualizados")
SALIDA = RUTA_BIG   # se reescribe en sitio; hacer copia antes si hace falta

COLS_BASE = ["periodico", "titulo", "fecha", "texto", "url", "departamento"]


def _solo_base(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva solo las columnas base requeridas por el pipeline."""
    faltantes = [c for c in COLS_BASE if c not in df.columns]
    for c in faltantes:
        df[c] = None
    return df[COLS_BASE].copy()


def main():
    # 1. Corpus grande (32 deptos) -> solo columnas base
    big = pd.read_pickle(RUTA_BIG)
    big = _solo_base(big)
    print(f"Corpus grande (alexa): {len(big)} articulos | {big['departamento'].nunique()} deptos")

    # 2. Cargar los PKL actualizados (excluyendo el archivo de salida)
    archivos = sorted(
        f for f in glob.glob(os.path.join(DIR_ULTIMOS, "*.pkl"))
        if os.path.abspath(f) != os.path.abspath(SALIDA)
    )
    partes_nuevas = []
    deptos_nuevos = set()
    for r in archivos:
        df = _solo_base(pd.read_pickle(r))
        deptos_nuevos |= set(df["departamento"].dropna().astype(str).str.strip().unique())
        partes_nuevas.append(df)
    df_nuevos = pd.concat(partes_nuevas, ignore_index=True)
    print(f"Ultimos_pkl: {len(df_nuevos)} articulos | {len(deptos_nuevos)} deptos | {len(archivos)} archivos")

    # 3. Eliminar del corpus grande los deptos que vienen actualizados
    big_dep = big["departamento"].astype(str).str.strip()
    mantener = big[~big_dep.isin(deptos_nuevos)].copy()
    deptos_mantenidos = sorted(mantener["departamento"].astype(str).str.strip().unique())
    print(f"Se mantienen del grande [{len(deptos_mantenidos)}]: {deptos_mantenidos}")

    # 4. Concatenar + limpiar
    combinado = pd.concat([mantener, df_nuevos], ignore_index=True)
    antes = len(combinado)
    combinado = combinado.drop_duplicates(subset=["url"]).reset_index(drop=True)
    sin_texto = combinado["texto"].isna() | (combinado["texto"].astype(str).str.strip() == "")
    combinado = combinado[~sin_texto].reset_index(drop=True)
    combinado["fecha"] = pd.to_datetime(combinado["fecha"], errors="coerce")
    print(f"Combinado: {antes} -> {len(combinado)} tras dedup url + filtrar sin texto")
    print(f"Total deptos: {combinado['departamento'].nunique()}")

    # 5. Guardar
    combinado.to_pickle(SALIDA)
    print(f"\nGuardado -> {SALIDA}  (shape={combinado.shape})")
    print("\nArticulos por departamento:")
    print(combinado["departamento"].astype(str).str.strip().value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
