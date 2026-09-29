"""
Promocion del pre-filtro por indicador a src/ (log [2026-09-29]): compara la recorrida de los 4 lugares con el src/ nuevo
(resultados/tablas_lugares_max_prefiltro_2026-09-29/) con la anterior (resultados/tablas_lugares_max_2026-09-28/, identica a
la del 1-sep) y con lo que predijo el experimento (experimentos/resultados/exp_prefiltro_indicador.xlsx, hoja F_lugares).

  1. por articulo: solo pueden cambiar `presencia_grupos_armados` y `desplazamiento_forzado`; los otros 24 indicadores y el
     sesgo deben ser identicos;
  2. para esos dos, el score nuevo debe ser el anterior x la compuerta (premisa visible del par con la hipotesis de cada
     indicador, calculada aqui con las funciones de src/): diferencia maxima 0;
  3. MAX por lugar x indicador, radar (media de los 26 MAX redondeados a 4 decimales, como paso5_resumen) y clase con
     los cortes nuevos (0.7572/0.9233) frente a la prediccion del experimento;
  4. los indicadores que mas pesan en cada lugar (cinco de mayor MAX, tres de menor) con el articulo que fija el MAX.

  python experimentos/exp_prefiltro_indicador_lugares.py [carpeta_nueva] [carpeta_anterior]
Salida: experimentos/resultados/exp_prefiltro_indicador_lugares.xlsx
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
import config_pipeline as cfg  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import Transformer_optimo as T  # noqa: E402

NUEVA = os.path.join(RAIZ, sys.argv[1] if len(sys.argv) > 1 else os.path.join("resultados", "tablas_lugares_max_prefiltro_2026-09-29"))
ANTERIOR = os.path.join(RAIZ, sys.argv[2] if len(sys.argv) > 2 else os.path.join("resultados", "tablas_lugares_max_2026-09-28"))
CORPUS = os.path.join(RAIZ, "datos", "corpus", "df_corpus_5lugares.pkl")
PREDICCION = os.path.join(RAIZ, "experimentos", "resultados", "exp_prefiltro_indicador.xlsx")
SALIDA = os.path.join(RAIZ, "experimentos", "resultados", "exp_prefiltro_indicador_lugares.xlsx")
PKL, XLS = "df_procesado_5lugares.pkl", "resumen_indicadores_MAX_y_articulos_por_lugar.xlsx"
MODELO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
INDS26 = list(V2.TODAS)
GATED = list(T.PREFILTRO_OBJETO)
TOL = 1e-6


def clase(v):
    return "Bajo" if v < cfg.CORTE_BAJO_MEDIO_RADAR else ("Medio" if v < cfg.CORTE_MEDIO_ALTO_RADAR else "Alto")


def maxes(df):
    mx = df.groupby("departamento")[INDS26].max()
    tit = {}
    for lugar, g in df.groupby("departamento"):
        g = g.reset_index(drop=True)
        tit[lugar] = {c: (g.loc[g[c].astype(float).idxmax(), "titulo"] if g[c].max() > 0 else "") for c in INDS26}
    return mx, pd.DataFrame(tit).T


def main():
    a = pd.read_pickle(os.path.join(ANTERIOR, PKL))
    b = pd.read_pickle(os.path.join(NUEVA, PKL))
    cl = pd.read_pickle(CORPUS).reset_index(drop=True)
    print(f"anterior: {ANTERIOR}\nnueva   : {NUEVA}\nformas  : {a.shape} / {b.shape}")
    assert (a["url"].values == b["url"].values).all() and (b["url"].values == cl["url"].values).all()
    ok = True

    # 1. por articulo
    filas = []
    for c in INDS26 + ["sesgo"]:
        d = np.abs(a[c].astype(float).values - b[c].astype(float).values)
        filas.append({"columna": c, "filtrada": c in GATED, "max_abs_dif": float(d.max()), "media_abs_dif": float(d.mean()),
                      "articulos_distintos": int((d > TOL).sum())})
    por_art = pd.DataFrame(filas)
    no_filtradas = por_art[~por_art["filtrada"]]
    ok &= bool((no_filtradas["max_abs_dif"] < TOL).all())
    print(f"\n[1] las 24 no filtradas y el sesgo: max|dif| {no_filtradas['max_abs_dif'].max():.1e} "
          f"({'identicas' if (no_filtradas['max_abs_dif'] < TOL).all() else 'HAY DIFERENCIAS'}); "
          f"filtradas: " + ", ".join(f"{r.columna} {r.articulos_distintos} articulos distintos"
                                      for r in por_art[por_art['filtrada']].itertuples()))

    # 2. score nuevo = score anterior x compuerta (src/, premisa visible del par con la hipotesis de cada indicador)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local(MODELO))
    textos = cl["texto"].fillna("").astype(str).tolist()
    filas = []
    for ind in GATED:
        g = T.compuerta_objeto(T.premisa_visible(textos, tok, V2.TODAS[ind]), ind)
        pred = a[ind].astype(float).values * g
        d = float(np.abs(b[ind].astype(float).values - pred).max())
        ok &= d < TOL
        filas.append({"indicador": ind, "compuerta_abre_pct": float(g.mean()), "articulos_cerrados_con_score_previo_gt0":
                      int(((g == 0) & (a[ind].values > 0)).sum()), "max_abs_dif_nuevo_vs_anterior_x_compuerta": d})
        print(f"[2] {ind}: la compuerta abre en {g.mean():.1%}; cierra {filas[-1]['articulos_cerrados_con_score_previo_gt0']} articulos con score previo > 0; "
              f"max|nuevo - anterior x compuerta| = {d:.1e}")
    comp = pd.DataFrame(filas)

    # 3. MAX por lugar x indicador, radar y clase frente a la prediccion del experimento
    ma, ta = maxes(a)
    mb, tb = maxes(b)
    largo = []
    for lugar in ma.index:
        for c in INDS26:
            largo.append({"lugar": lugar, "indicador": c, "MAX_anterior": ma.loc[lugar, c], "MAX_nuevo": mb.loc[lugar, c],
                          "dif": mb.loc[lugar, c] - ma.loc[lugar, c], "mismo_articulo": ta.loc[lugar, c] == tb.loc[lugar, c]})
    max_li = pd.DataFrame(largo)
    cambian = max_li[max_li["dif"].abs() > TOL]
    print(f"[3] MAX que cambian: {len(cambian)} de {len(max_li)} (solo filtradas: {bool(cambian['indicador'].isin(GATED).all())}); "
          + ", ".join(f"{r.lugar.split()[-1]}/{r.indicador[:6]} {r.MAX_anterior:.3f}->{r.MAX_nuevo:.3f}" for r in cambian.itertuples()))
    ok &= bool(cambian["indicador"].isin(GATED).all())
    ra, rb = ma.round(4).mean(axis=1), mb.round(4).mean(axis=1)
    pred = pd.read_excel(PREDICCION, sheet_name="F_lugares")
    pred = pred[pred["configuracion"] == "incluidas por (a)-(d)"].set_index("lugar")
    rc = pd.DataFrame({"radar_anterior": ra, "radar_nuevo": rb, "radar_predicho_experimento": pred["radar_con"].reindex(rb.index)})
    rc["dif_vs_prediccion"] = rc["radar_nuevo"].round(4) - rc["radar_predicho_experimento"].round(4)
    rc["clase_anterior_cortes_viejos"] = ra.map(lambda v: "Bajo" if v < 0.766 else ("Medio" if v < 0.9233 else "Alto"))
    rc["clase_nueva_cortes_nuevos"] = rb.map(clase)
    rc["misma_clase"] = rc["clase_anterior_cortes_viejos"] == rc["clase_nueva_cortes_nuevos"]
    ok &= bool((rc["dif_vs_prediccion"].abs() < 1e-9).all())
    # encabezados del Excel de resumen (paso5_resumen con los cortes nuevos)
    x = pd.read_excel(os.path.join(NUEVA, XLS), header=[0, 1], index_col=0)
    enc = list(dict.fromkeys(c[0] for c in x.columns))
    pat = re.compile(r"^(.*) — (Bajo|Medio|Alto) \((\d+\.\d+)\)$")
    for e in enc:
        g = pat.match(e)
        ok &= (f"{rb[g.group(1)]:.4f}" == g.group(3)) and (clase(rb[g.group(1)]) == g.group(2))
    rc["encabezado_excel"] = enc
    print("[3] radar y clase por lugar (nuevo frente a la prediccion del experimento):")
    print(rc[["radar_anterior", "radar_nuevo", "radar_predicho_experimento", "dif_vs_prediccion", "clase_nueva_cortes_nuevos", "misma_clase"]]
          .round(4).to_string())

    # 4. indicadores que mas pesan
    n_art = b.groupby("departamento").size()
    top = []
    for lugar in mb.index:
        orden = mb.loc[lugar].sort_values(ascending=False)
        for rango, (c, v) in enumerate(orden.items(), 1):
            top.append({"lugar": lugar, "n_articulos": int(n_art[lugar]), "rango": rango, "indicador": c, "MAX": float(v),
                        "aporte_al_radar": float(round(v, 4) / len(INDS26)), "articulo_del_MAX": tb.loc[lugar, c]})
    top = pd.DataFrame(top)
    resumen = top.groupby("lugar").agg(n_articulos=("n_articulos", "first"),
                                       n_MAX_ge_corte_bajo_medio=("MAX", lambda s: int((s >= cfg.CORTE_BAJO_MEDIO_RADAR).sum())),
                                       n_MAX_ge_corte_medio_alto=("MAX", lambda s: int((s >= cfg.CORTE_MEDIO_ALTO_RADAR).sum())),
                                       n_MAX_cero=("MAX", lambda s: int((s == 0).sum())))
    print("\n[4] indicadores con MAX >= 0.7572 y >= 0.9233, y con MAX 0:")
    print(resumen.to_string())
    for lugar in mb.index:
        print(f"    {lugar}: " + ", ".join(f"{r.indicador} {r.MAX:.3f}" for r in top[(top.lugar == lugar) & (top.rango <= 5)].itertuples()))
    print(f"\nCOINCIDE CON LO PREDICHO Y SOLO CAMBIAN LAS DOS FILTRADAS: {'SI' if ok else 'NO'}")

    with pd.ExcelWriter(SALIDA, engine="openpyxl") as w:
        por_art.to_excel(w, sheet_name="por_articulo", index=False)
        comp.to_excel(w, sheet_name="compuertas", index=False)
        max_li.to_excel(w, sheet_name="max_lugar_x_indicador", index=False)
        rc.to_excel(w, sheet_name="radar_clase")
        resumen.to_excel(w, sheet_name="resumen_indicadores")
        top.to_excel(w, sheet_name="indicadores_por_peso", index=False)
    print(f"Guardado -> {SALIDA}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
