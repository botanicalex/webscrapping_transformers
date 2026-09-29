"""
Compara la corrida de los 4 lugares del 2026-09-28 (resultados/tablas_lugares_max_2026-09-28/, hecha
con exp_prefiltro_correr_lugares.py y `src/` tal cual) con la del 1-sep (resultados/tablas_lugares_max/):

  1. por articulo: max|dif| y media|dif| de los 26 indicadores y del sesgo (mismo orden de urls);
  2. MAX por lugar x indicador (26 x 4) en las dos corridas y su diferencia, y si el articulo que fija
     el MAX (titulo) es el mismo;
  3. radar (media de los 26 MAX redondeados a 4 decimales, como en paso5_resumen) y clase por lugar, y
     los encabezados de los Excel de resumen.

Todo offline. Salida: experimentos/resultados/exp_prefiltro_lugares_recorrida.xlsx

  python experimentos/exp_prefiltro_comparar_lugares.py [carpeta_nueva]
"""
import os
import re
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "src"))
import hipotesis_v2 as V2  # noqa: E402
import config_pipeline as cfg  # noqa: E402

VIEJA = os.path.join(RAIZ, "resultados", "tablas_lugares_max")
NUEVA = os.path.join(RAIZ, sys.argv[1] if len(sys.argv) > 1 else os.path.join("resultados", "tablas_lugares_max_2026-09-28"))
SALIDA = os.path.join(RAIZ, "experimentos", "resultados", "exp_prefiltro_lugares_recorrida.xlsx")
PKL = "df_procesado_5lugares.pkl"
XLS = "resumen_indicadores_MAX_y_articulos_por_lugar.xlsx"
INDS26 = list(V2.TODAS)
TOL = 1e-4


def clase(v):
    return "Bajo" if v < cfg.CORTE_BAJO_MEDIO_RADAR else ("Medio" if v < cfg.CORTE_MEDIO_ALTO_RADAR else "Alto")


def maxes(df):
    mx = df.groupby("departamento")[INDS26].max()
    tit = {}
    for lugar, g in df.groupby("departamento"):
        g = g.reset_index(drop=True)
        tit[lugar] = {c: (g.loc[g[c].astype(float).idxmax(), "titulo"] if g[c].max() > 0 else "") for c in INDS26}
    return mx, pd.DataFrame(tit).T


def encabezados(ruta):
    x = pd.read_excel(ruta, header=[0, 1], index_col=0)
    return list(dict.fromkeys(c[0] for c in x.columns))


def main():
    a = pd.read_pickle(os.path.join(VIEJA, PKL))
    b = pd.read_pickle(os.path.join(NUEVA, PKL))
    print(f"1-sep : {VIEJA}\nnueva : {NUEVA}\nformas: {a.shape} / {b.shape}")
    assert (a["url"].values == b["url"].values).all(), "las corridas no tienen los mismos articulos en el mismo orden"

    # 1. por articulo
    filas = []
    for c in INDS26 + ["sesgo"]:
        d = np.abs(a[c].astype(float).values - b[c].astype(float).values)
        filas.append({"columna": c, "max_abs_dif": float(d.max()), "media_abs_dif": float(d.mean()),
                      "n_articulos_dif_gt_1e-4": int((d > TOL).sum())})
    por_art = pd.DataFrame(filas)
    dmax = float(por_art["max_abs_dif"].max())
    print(f"\n[1] por articulo: max|dif| global {dmax:.2e} (col {por_art.loc[por_art.max_abs_dif.idxmax(), 'columna']}); "
          f"articulos con |dif|>1e-4 en algun indicador: "
          f"{int((np.abs(a[INDS26].astype(float).values - b[INDS26].astype(float).values) > TOL).any(axis=1).sum())}")

    # 2. MAX por lugar x indicador
    ma, ta = maxes(a)
    mb, tb = maxes(b)
    largo = []
    for lugar in ma.index:
        for c in INDS26:
            largo.append({"lugar": lugar, "indicador": c, "MAX_1sep": ma.loc[lugar, c], "MAX_nueva": mb.loc[lugar, c],
                          "dif": mb.loc[lugar, c] - ma.loc[lugar, c], "mismo_articulo": ta.loc[lugar, c] == tb.loc[lugar, c]})
    max_li = pd.DataFrame(largo)
    print(f"[2] MAX por lugar x indicador: max|dif| {max_li['dif'].abs().max():.2e}; celdas con |dif|>1e-4: "
          f"{int((max_li['dif'].abs() > TOL).sum())} de {len(max_li)}; articulo distinto en {int((~max_li['mismo_articulo']).sum())}")

    # 3. radar y clase por lugar
    ra = ma.round(4).mean(axis=1)
    rb = mb.round(4).mean(axis=1)
    ha, hb = encabezados(os.path.join(VIEJA, XLS)), encabezados(os.path.join(NUEVA, XLS))
    rc = pd.DataFrame({"radar_1sep": ra, "clase_1sep": ra.map(clase), "radar_nueva": rb, "clase_nueva": rb.map(clase)})
    rc["dif"] = rc["radar_nueva"] - rc["radar_1sep"]
    rc["misma_clase"] = rc["clase_1sep"] == rc["clase_nueva"]
    rc["encabezado_1sep"] = ha
    rc["encabezado_nueva"] = hb
    rc["mismo_encabezado"] = rc["encabezado_1sep"] == rc["encabezado_nueva"]
    print("\n[3] radar y clase por lugar:")
    print(rc[["radar_1sep", "clase_1sep", "radar_nueva", "clase_nueva", "dif", "misma_clase", "mismo_encabezado"]]
          .round(6).to_string())
    print("\nencabezados nueva:", hb)

    # 4. indicadores que mas pesan en el radar de cada lugar (corrida nueva): cada MAX aporta MAX/26 al promedio
    n_art = b.groupby("departamento").size()
    filas = []
    for lugar in mb.index:
        orden = mb.loc[lugar].sort_values(ascending=False)
        for rango, (c, v) in enumerate(orden.items(), 1):
            filas.append({"lugar": lugar, "n_articulos": int(n_art[lugar]), "rango": rango, "indicador": c,
                          "MAX": float(v), "aporte_al_radar": float(round(v, 4) / len(INDS26)),
                          "MAX>=corte_bajo_medio": bool(v >= cfg.CORTE_BAJO_MEDIO_RADAR),
                          "MAX>=corte_medio_alto": bool(v >= cfg.CORTE_MEDIO_ALTO_RADAR), "articulo_del_MAX": tb.loc[lugar, c]})
    top = pd.DataFrame(filas)
    resumen = top.groupby("lugar").agg(n_articulos=("n_articulos", "first"),
                                       n_indicadores_MAX_ge_0766=("MAX>=corte_bajo_medio", "sum"),
                                       n_indicadores_MAX_ge_09233=("MAX>=corte_medio_alto", "sum"),
                                       n_indicadores_MAX_cero=("MAX", lambda s: int((s == 0).sum())))
    print("\n[4] indicadores con MAX >= 0.766 y >= 0.9233 por lugar:")
    print(resumen.to_string())
    for lugar in mb.index:
        print(f"    {lugar}: " + ", ".join(f"{r.indicador} {r.MAX:.3f}" for r in top[(top.lugar == lugar) & (top.rango <= 5)].itertuples()))

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with pd.ExcelWriter(SALIDA, engine="openpyxl") as w:
        por_art.to_excel(w, sheet_name="por_articulo", index=False)
        max_li.to_excel(w, sheet_name="max_lugar_x_indicador", index=False)
        rc.to_excel(w, sheet_name="radar_clase")
        resumen.to_excel(w, sheet_name="resumen_indicadores")
        top.to_excel(w, sheet_name="indicadores_por_peso", index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
