"""
Pipeline completo (post-scraping) para los 5 lugares del encargo.

Pasos:
  1. Combina los pkl de corpus_lugares/ + las filas de Antioquia (2023) que ya
     estan en Ultimos_pkl/df_corpus_combinado_32deptos.pkl
  2. Corre PipelineTransformers (26 indicadores NLI + pre-filtro social 0.65)
  3. Guarda df_procesado (respaldo del trabajo GPU)
  4. Escribe una tabla de indicadores por articulo por cada lugar
  5. Escribe el Excel resumen MAX + articulo de origen, por lugar

Requiere haber corrido antes: python scrape_lugares.py
"""
import glob
import os
import sys
import unicodedata

import pandas as pd

DIR_SRC = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_SRC)   # raiz de desarrollo/
sys.path.insert(0, DIR_SRC)

from Transformer_optimo import PipelineTransformers
from radar import CalculadorRadar

DIR_CORPUS = os.path.join(DIR_PROYECTO, "datos", "corpus")
# Carpeta de salida configurable: python pipeline_lugares.py <carpeta>
# Sin argumento usa la de siempre.
DIR_SALIDA = os.path.join(DIR_PROYECTO, sys.argv[1] if len(sys.argv) > 1 else os.path.join("resultados", "tablas_lugares"))

CORPUS_COMBINADO = os.path.join(DIR_CORPUS, "df_corpus_5lugares.pkl")
PROCESADO_PKL = os.path.join(DIR_SALIDA, "df_procesado_5lugares.pkl")
RESUMEN_XLSX = os.path.join(DIR_SALIDA, "resumen_indicadores_MAX_y_articulos_por_lugar.xlsx")

# Antioquia 2023 ya scrapeada: se reutiliza el texto crudo del corpus de 32 deptos
FUENTE_ANTIOQUIA = os.path.join(DIR_PROYECTO, "datos", "corpus", "df_corpus_combinado_32deptos.pkl")
ETIQUETA_ANTIOQUIA = "Antioquia (2023)"

COLS_BASE = ["periodico", "titulo", "fecha", "texto", "url", "departamento"]

UMBRAL_BAJO = 1 / 3
UMBRAL_ALTO = 2 / 3


def slug(txt: str) -> str:
    t = unicodedata.normalize("NFD", str(txt).lower()).encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() else "_" for c in t).strip("_")


def categoria(valor: float) -> str:
    if valor < UMBRAL_BAJO:
        return "Bajo"
    if valor <= UMBRAL_ALTO:
        return "Medio"
    return "Alto"


def _solo_base(df: pd.DataFrame) -> pd.DataFrame:
    for c in COLS_BASE:
        if c not in df.columns:
            df[c] = None
    return df[COLS_BASE].copy()


def paso1_combinar() -> pd.DataFrame:
    partes = []

    # Solo los pkl por lugar. datos/corpus/ tambien contiene el corpus nacional
    # de 32 departamentos y el combinado de 5 lugares; ninguno debe entrar aqui.
    archivos = sorted(
        f
        for patron in ("df_corpus_municipio_*.pkl", "df_corpus_vereda_*.pkl")
        for f in glob.glob(os.path.join(DIR_CORPUS, patron))
    )
    if not archivos:
        sys.exit(f"ERROR: no hay pkl por lugar en {DIR_CORPUS}. "
                 f"Corre primero: python src/scrape_lugares.py")
    for r in archivos:
        df = _solo_base(pd.read_pickle(r))
        partes.append(df)
        print(f"  {os.path.basename(r)}: {len(df)} articulos")

    # Antioquia 2023 desde el corpus ya existente
    if os.path.exists(FUENTE_ANTIOQUIA):
        big = pd.read_pickle(FUENTE_ANTIOQUIA)
        ant = big[big["departamento"].astype(str).str.strip() == "Antioquia"].copy()
        ant["departamento"] = ETIQUETA_ANTIOQUIA
        ant = _solo_base(ant)
        partes.append(ant)
        print(f"  {ETIQUETA_ANTIOQUIA}: {len(ant)} articulos (reutilizados)")
    else:
        print(f"  AVISO: no se encontro {FUENTE_ANTIOQUIA}; se omite Antioquia")

    combinado = pd.concat(partes, ignore_index=True)
    antes = len(combinado)
    combinado = combinado.drop_duplicates(subset=["url"]).reset_index(drop=True)
    sin_texto = combinado["texto"].isna() | (combinado["texto"].astype(str).str.strip() == "")
    combinado = combinado[~sin_texto].reset_index(drop=True)
    print(f"  Combinado: {antes} -> {len(combinado)} tras dedup url + filtrar sin texto")

    os.makedirs(DIR_CORPUS, exist_ok=True)
    combinado.to_pickle(CORPUS_COMBINADO)
    print(f"  Guardado -> {CORPUS_COMBINADO}")
    return combinado


def paso4_tablas(df_proc: pd.DataFrame) -> None:
    extra = ["score_social"] if "score_social" in df_proc.columns else []
    columnas = ["titulo"] + extra + CalculadorRadar.COLUMNAS_BINARIAS

    for lugar, grupo in df_proc.groupby("departamento"):
        df_tabla = grupo[columnas].copy()
        for c in CalculadorRadar.COLUMNAS_BINARIAS:
            if df_tabla[c].dtype == bool:
                df_tabla[c] = df_tabla[c].astype(int)
        ruta = os.path.join(DIR_SALIDA, f"tabla_indicadores_{slug(lugar)}.xlsx")
        df_tabla.to_excel(ruta, index=False)
        n_rel = int((grupo["score_social"] >= 0.65).sum())
        print(f"  {str(lugar):<26} {len(df_tabla):>5} articulos | {n_rel:>5} relevantes -> {os.path.basename(ruta)}")


def paso5_resumen(df_proc: pd.DataFrame) -> None:
    indicadores = [c for c in CalculadorRadar.COLUMNAS_BINARIAS if c in df_proc.columns]
    lugares = sorted(df_proc["departamento"].astype(str).unique())

    cols_data = {}
    clasif = []
    for lugar in lugares:
        g = df_proc[df_proc["departamento"].astype(str) == lugar]
        max_vals, max_tit = {}, {}
        for c in indicadores:
            serie = g[c].astype(float)
            idx = serie.idxmax()
            v = float(serie.loc[idx])
            max_vals[c] = round(v, 4)
            max_tit[c] = g.loc[idx, "titulo"] if v > 0 else ""

        radar_max = sum(max_vals.values()) / len(indicadores)
        clas = categoria(radar_max)
        clasif.append((lugar, round(radar_max, 4), clas, len(g)))

        enc = f"{lugar} — {clas} ({radar_max:.4f})"
        if clas == "Bajo":
            cols_data[(enc, "valor")] = ["" for _ in indicadores]
            cols_data[(enc, "titulo")] = ["" for _ in indicadores]
        else:
            cols_data[(enc, "valor")] = [max_vals[c] for c in indicadores]
            cols_data[(enc, "titulo")] = [max_tit[c] for c in indicadores]

    df_out = pd.DataFrame(cols_data, index=indicadores)
    df_out.index.name = "Indicador"
    df_out.columns = pd.MultiIndex.from_tuples(df_out.columns)
    df_out.to_excel(RESUMEN_XLSX)
    print(f"\n  Guardado -> {RESUMEN_XLSX} (shape={df_out.shape})")

    print(f"\n  {'Lugar':<26} {'radar_MAX':>10} {'Clasif':>8} {'Articulos':>10}")
    for lugar, rmax, clas, n in sorted(clasif, key=lambda x: -x[1]):
        print(f"  {lugar:<26} {rmax:>10.4f} {clas:>8} {n:>10}")


def main():
    os.makedirs(DIR_SALIDA, exist_ok=True)

    print("\n[1/5] Combinando corpus...")
    df_corpus = paso1_combinar()
    print(f"      Total: {len(df_corpus)} articulos | {df_corpus['departamento'].nunique()} lugares")

    print("\n[2/5] Corriendo pipeline NLI (26 indicadores + pre-filtro social)...")
    df_proc = PipelineTransformers().procesar(df_corpus)

    print("\n[3/5] Guardando respaldo...")
    df_proc.to_pickle(PROCESADO_PKL)
    print(f"      {PROCESADO_PKL} (shape={df_proc.shape})")

    print("\n[4/5] Escribiendo tabla por lugar...")
    paso4_tablas(df_proc)

    print("\n[5/5] Escribiendo resumen MAX + articulos...")
    paso5_resumen(df_proc)

    print(f"\nLISTO -> {DIR_SALIDA}")


if __name__ == "__main__":
    main()
