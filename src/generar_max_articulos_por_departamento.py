"""
Genera UN solo Excel para los 32 departamentos con, por cada indicador (fila),
el valor MAXIMO del indicador en el departamento y el titulo del articulo que
produjo ese maximo.

Reglas:
  - Clasificacion del depto = categoria por UMBRALES FIJOS (1/3, 2/3) sobre el
    radar MAX (promedio de los 26 maximos del depto).
  - Solo se muestran los valores/titulos si el depto es Alto o Medio.
  - Si el depto es Bajo, sus 2 columnas quedan en blanco.
  - Por indicador se elige UN solo articulo: el del maximo absoluto.
  - Si el maximo de un indicador es 0, el titulo queda en blanco.

Salida (2 columnas por depto: valor + titulo, encabezado con clasificacion):
  tablas_indicadores_departamentos/resumen_indicadores_MAX_y_articulos_por_departamento.xlsx
"""
import os
import sys

import pandas as pd

DIR_SRC = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_SRC)   # raiz de desarrollo/
sys.path.insert(0, DIR_SRC)

from radar import CalculadorRadar

DIR_TABLAS = os.path.join(DIR_PROYECTO, "resultados", "tablas_departamentos")
ENTRADA = os.path.join(DIR_TABLAS, "df_procesado_32deptos.pkl")
SALIDA = os.path.join(DIR_TABLAS, "resumen_indicadores_MAX_y_articulos_por_departamento.xlsx")

UMBRAL_BAJO = 1 / 3
UMBRAL_ALTO = 2 / 3


def categoria(valor: float) -> str:
    if valor < UMBRAL_BAJO:
        return "Bajo"
    if valor <= UMBRAL_ALTO:
        return "Medio"
    return "Alto"


def main():
    df = pd.read_pickle(ENTRADA)
    df["departamento"] = df["departamento"].astype(str).str.strip()
    indicadores = [c for c in CalculadorRadar.COLUMNAS_BINARIAS if c in df.columns]
    deptos = sorted(df["departamento"].unique())
    print(f"Articulos: {len(df)} | Indicadores: {len(indicadores)} | Deptos: {len(deptos)}")

    cols_data = {}
    resumen_clasif = []

    for depto in deptos:
        g = df[df["departamento"] == depto]
        max_vals, max_tit = {}, {}
        for c in indicadores:
            serie = g[c].astype(float)
            idx = serie.idxmax()
            v = float(serie.loc[idx])
            max_vals[c] = round(v, 4)
            max_tit[c] = g.loc[idx, "titulo"] if v > 0 else ""

        radar_max = sum(max_vals.values()) / len(indicadores)
        clas = categoria(radar_max)
        resumen_clasif.append((depto, round(radar_max, 4), clas, len(g)))

        encabezado = f"{depto} — {clas} ({radar_max:.4f})"
        if clas == "Bajo":
            cols_data[(encabezado, "valor")] = ["" for _ in indicadores]
            cols_data[(encabezado, "titulo")] = ["" for _ in indicadores]
        else:
            cols_data[(encabezado, "valor")] = [max_vals[c] for c in indicadores]
            cols_data[(encabezado, "titulo")] = [max_tit[c] for c in indicadores]

    df_out = pd.DataFrame(cols_data, index=indicadores)
    df_out.index.name = "Indicador"
    df_out.columns = pd.MultiIndex.from_tuples(df_out.columns)

    os.makedirs(DIR_TABLAS, exist_ok=True)
    df_out.to_excel(SALIDA)
    print(f"\nGuardado -> {SALIDA} (shape={df_out.shape})")

    print("\nClasificacion por departamento (radar MAX, umbrales 1/3-2/3):")
    print(f"{'Departamento':<26} {'radar_MAX':>10} {'Clasif':>8} {'Articulos':>10}")
    n_alto = n_medio = n_bajo = 0
    for depto, rmax, clas, n in sorted(resumen_clasif, key=lambda x: -x[1]):
        print(f"{depto:<26} {rmax:>10.4f} {clas:>8} {n:>10}")
        n_alto += clas == "Alto"
        n_medio += clas == "Medio"
        n_bajo += clas == "Bajo"
    print(f"\nResumen: Alto={n_alto} | Medio={n_medio} | Bajo={n_bajo}")


if __name__ == "__main__":
    main()
