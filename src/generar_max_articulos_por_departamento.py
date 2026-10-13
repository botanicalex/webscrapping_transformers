"""
Genera UN solo Excel para los 32 departamentos con, por cada indicador (fila),
el valor MAXIMO del indicador en el departamento y el articulo (titulo + url)
que produjo ese maximo. Sin GPU: lee un df_procesado ya calculado.

Reglas:
  - Clasificacion del depto = categoria por los CORTES FIJOS de esta rama
    (CORTE_BAJO_MEDIO_RADAR/CORTE_MEDIO_ALTO_RADAR en config_pipeline.py,
    calibrados sobre la escala MAX) sobre el radar MAX (promedio de los 18
    maximos del depto).
  - Valor, titulo y url se muestran SIEMPRE, tambien en deptos Bajo
    (2026-10-06: se quito el blanqueo de los Bajo) y tambien cuando el
    articulo no supera el umbral de activacion (ver "activo" abajo) -- el
    dato existe y sirve para verificar de donde sale el numero.
  - Por indicador se elige UN solo articulo: el del maximo absoluto.
  - Si el maximo de un indicador es 0, titulo y url quedan en blanco (no hay
    ningun articulo que destacar: todos empatan en 0).
  - Columna "activo": "Si" si ese maximo supera UMBRAL_INDICADOR_ACTIVO
    (config_pipeline.py, el mismo que usa api.py para marcar "real"/"arts"),
    "No" si no -- para distinguir un enlace con evidencia real de un enlace
    que solo es el mayor de un conjunto sin señal (2026-10-13).

Salida (4 columnas por depto: valor + titulo + url + activo, encabezado con
clasificacion):
  tablas_indicadores_departamentos/resumen_indicadores_MAX_y_articulos_por_departamento.xlsx
"""
import os
import sys

import pandas as pd

DIR_SRC = os.path.dirname(os.path.abspath(__file__))
DIR_PROYECTO = os.path.dirname(DIR_SRC)   # raiz de desarrollo/
sys.path.insert(0, DIR_SRC)

import config_pipeline as cfg
from radar import CalculadorRadar

DIR_TABLAS = os.path.join(DIR_PROYECTO, "resultados", "tablas_departamentos")
ENTRADA = os.path.join(DIR_TABLAS, "df_procesado_32deptos.pkl")
SALIDA = os.path.join(DIR_TABLAS, "resumen_indicadores_MAX_y_articulos_por_departamento.xlsx")


def categoria(valor: float) -> str:
    """Cortes fijos de esta rama (MAX), no terciles: ver config_pipeline.py."""
    if valor < cfg.CORTE_BAJO_MEDIO_RADAR:
        return "Bajo"
    if valor < cfg.CORTE_MEDIO_ALTO_RADAR:
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
        max_vals, max_tit, max_url, max_activo = {}, {}, {}, {}
        for c in indicadores:
            serie = g[c].astype(float)
            idx = serie.idxmax()
            v = float(serie.loc[idx])
            max_vals[c] = round(v, 4)
            max_tit[c] = g.loc[idx, "titulo"] if v > 0 else ""
            max_url[c] = g.loc[idx, "url"] if v > 0 else ""
            max_activo[c] = "Si" if v >= cfg.UMBRAL_INDICADOR_ACTIVO else "No"

        radar_max = sum(max_vals.values()) / len(indicadores)
        clas = categoria(radar_max)
        resumen_clasif.append((depto, round(radar_max, 4), clas, len(g)))

        encabezado = f"{depto} — {clas} ({radar_max:.4f})"
        cols_data[(encabezado, "valor")] = [max_vals[c] for c in indicadores]
        cols_data[(encabezado, "titulo")] = [max_tit[c] for c in indicadores]
        cols_data[(encabezado, "url")] = [max_url[c] for c in indicadores]
        cols_data[(encabezado, "activo")] = [max_activo[c] for c in indicadores]

    df_out = pd.DataFrame(cols_data, index=indicadores)
    df_out.index.name = "Indicador"
    df_out.columns = pd.MultiIndex.from_tuples(df_out.columns)

    os.makedirs(DIR_TABLAS, exist_ok=True)
    df_out.to_excel(SALIDA)
    print(f"\nGuardado -> {SALIDA} (shape={df_out.shape})")

    print(f"\nClasificacion por departamento (radar MAX, cortes fijos "
          f"{cfg.CORTE_BAJO_MEDIO_RADAR}/{cfg.CORTE_MEDIO_ALTO_RADAR}):")
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
