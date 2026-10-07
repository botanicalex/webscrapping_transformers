"""
Tabla para el jefe: radar de 18 indicadores HOY (frases del jefe en conflicto y resistencia, cortes 0.6885/0.8916)
contra NUEVO (C21 «Hay una invasión de predios.», R30 «Los habitantes rechazan una hidroeléctrica o un
megaproyecto.», cortes de config_pipeline al correr) para Antioquia y los lugares. Sin GPU.

Mismo cálculo que exp_tabla_antioquia_lugares_18ind.py (score corregido x compuerta PREFILTRO_OBJETO, MAX por lugar,
radar = media de los MAX redondeados a 4 decimales). Lo de HOY sale de esa misma construcción y se valida contra
experimentos/resultados/tabla_antioquia_lugares_18ind.md (radar 18). C21/R30: ent/neu de
datos/scores/hip_conflicto_resistencia/{nacional,lugares}/{C21,R30}.pkl (mismo orden que los corpus).

  python experimentos/exp_tabla_antioquia_lugares_c21_r30.py
Salida: experimentos/resultados/tabla_antioquia_lugares_c21_r30.{xlsx,md}
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
os.chdir(RAIZ)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "src"))
import config_pipeline as cfg  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import radar as R  # noqa: E402
import Transformer_optimo as T  # noqa: E402

MODELO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
CORPUS_LUG = "datos/corpus/df_corpus_5lugares.pkl"
PROC_LUG = "resultados/tablas_lugares_max_prefiltro_2026-09-29/df_procesado_5lugares.pkl"
JEFE = "datos/scores/scores_hipotesis_jefe_18ind.pkl"
NUEVAS = "datos/scores/hip_conflicto_resistencia"
SAL = "experimentos/resultados/tabla_antioquia_lugares_c21_r30"
CORTES_HOY = (0.6885, 0.8916)
HOY_ESPERADO = {"Antioquia": 0.9084, "Paraguachón": 0.6053, "Maicao": 0.9544, "Oicatá": 0.4891}  # informe 15
JEFE3 = ["conflicto_territorial", "zonas_proteccion_alimentaria", "resistencia_territorial"]
CAMBIAN = {"conflicto_territorial": "C21", "resistencia_territorial": "R30"}
I18 = list(R.CalculadorRadar.COLUMNAS_BINARIAS)
LUGARES = {"Antioquia": None, "Paraguachón": "Vereda Paraguach", "Maicao": "Municipio Maicao",
           "Güintiva": "Vereda G", "Oicatá": "Municipio Oicat"}


def clase(v, cb, ca):
    return "Bajo" if v < cb else ("Medio" if v < ca else "Alto")


def score(ent, neu, sesgo):
    return np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)


def main():
    cb, ca = cfg.CORTE_BAJO_MEDIO_RADAR, cfg.CORTE_MEDIO_ALTO_RADAR
    corpus = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    j = pd.read_pickle(JEFE)
    jn = j[j["corpus"] == "nacional"].reset_index(drop=True)
    jl = j[j["corpus"] == "lugares"].reset_index(drop=True)
    assert (jn["titulo"].values == corpus["titulo"].values).all()
    textos = corpus["texto"].fillna("").astype(str).tolist()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local(MODELO))
    sesgo = d["sesgo"].values
    hoy = pd.DataFrame({c: score(d[f"ent_{c}"].values, d[f"neu_{c}"].values, sesgo) for c in I18})
    for ind in T.PREFILTRO_OBJETO:
        hoy[ind] = hoy[ind] * T.compuerta_objeto(T.premisa_visible(textos, tok, V2.TODAS[ind]), ind)
    for c in JEFE3:
        hoy[c] = score(jn[f"ent_nueva_{c}"].values, jn[f"neu_nueva_{c}"].values, sesgo)
    nuevo = hoy.copy()
    for c, i in CAMBIAN.items():
        r = pickle.load(open(f"{NUEVAS}/nacional/{i}.pkl", "rb"))
        assert r["n"] == len(corpus)
        nuevo[c] = score(r["ent"], r["neu"], sesgo)

    cl = pd.read_pickle(CORPUS_LUG).reset_index(drop=True)
    pr = pd.read_pickle(PROC_LUG).reset_index(drop=True)
    assert (cl["url"].values == pr["url"].values).all() and (jl["titulo"].values == cl["titulo"].values).all()
    s_l = pr["sesgo"].values
    lhoy = pr[I18].astype(float).copy()
    for c in JEFE3:
        lhoy[c] = score(jl[f"ent_nueva_{c}"].values, jl[f"neu_nueva_{c}"].values, s_l)
    lnuevo = lhoy.copy()
    ses = pickle.load(open(f"{NUEVAS}/lugares/_sesgo.pkl", "rb"))
    assert np.allclose(ses["sesgo"], s_l, atol=1e-4) and (ses["titulo"] == cl["titulo"].values).all()
    for c, i in CAMBIAN.items():
        r = pickle.load(open(f"{NUEVAS}/lugares/{i}.pkl", "rb"))
        assert r["n"] == len(cl)
        lnuevo[c] = score(r["ent"], r["neu"], s_l)

    def agg(titulos, art, mask):
        g = art[mask].reset_index(drop=True)
        tt = titulos[mask].reset_index(drop=True)
        mx = g.max().round(4)
        ti = {c: (tt[g[c].idxmax()] if g[c].max() > 0 else "—") for c in g.columns}
        return mx, ti

    filas, detalle = [], {}
    for lug, pref in LUGARES.items():
        if lug == "Antioquia":
            mk, tit, a, b = (corpus["departamento"] == "Antioquia").values, corpus["titulo"], hoy, nuevo
        else:
            mk, tit, a, b = cl["departamento"].astype(str).str.startswith(pref).values, cl["titulo"], lhoy, lnuevo
        n = int(mk.sum())
        if n == 0:
            filas.append({"lugar": lug, "n_articulos": 0, "radar_hoy": np.nan, "clase_hoy": "sin datos",
                          "radar_nuevo": np.nan, "clase_nuevo": "sin datos", "dif": np.nan})
            continue
        (mh, th), (mn, tn) = agg(tit, a, mk), agg(tit, b, mk)
        rh, rn = round(float(mh.mean()), 4), round(float(mn.mean()), 4)
        if lug in HOY_ESPERADO and abs(rh - HOY_ESPERADO[lug]) > 1e-4:
            sys.exit(f"{lug}: radar hoy {rh} != informe 15 {HOY_ESPERADO[lug]}: PARA")
        filas.append({"lugar": lug, "n_articulos": n, "radar_hoy": rh, "clase_hoy": clase(rh, *CORTES_HOY),
                      "radar_nuevo": rn, "clase_nuevo": clase(rn, cb, ca), "dif": round(rn - rh, 4)})
        detalle[lug] = pd.DataFrame([{"indicador": c, "MAX_hoy": mh[c], "MAX_nuevo": mn[c],
                                      "articulo_MAX_hoy": th[c], "articulo_MAX_nuevo": tn[c]} for c in CAMBIAN])
    res = pd.DataFrame(filas)
    nota = f"Cortes hoy {CORTES_HOY[0]}/{CORTES_HOY[1]}; cortes nuevos {cb}/{ca}. Solo cambian conflicto_territorial y resistencia_territorial."
    with pd.ExcelWriter(SAL + ".xlsx") as xw:
        res.to_excel(xw, sheet_name="resumen", index=False)
        pd.DataFrame({"nota": [nota, "Güintiva: 0 artículos.", "Radar = media simple de los MAX redondeados a 4 decimales."]}).to_excel(
            xw, sheet_name="notas", index=False)
        for lug, df in detalle.items():
            df.to_excel(xw, sheet_name=lug[:30], index=False)

    def f(x):
        return "—" if pd.isna(x) else f"{x:.4f}"
    L = ["# Radar 18 indicadores: frases del jefe (hoy) contra C21/R30 — Antioquia y lugares", "", nota, "",
         "| Lugar | n art. | Radar hoy | Clase hoy | Radar nuevo | Clase nueva | Dif |", "|---|---:|---:|:--:|---:|:--:|---:|"]
    for r in res.itertuples():
        L.append(f"| {r.lugar} | {r.n_articulos} | {f(r.radar_hoy)} | {r.clase_hoy} | {f(r.radar_nuevo)} | {r.clase_nuevo} | {f(r.dif)} |")
    for lug, df in detalle.items():
        L += ["", f"## {lug}", "", "| Indicador | MAX hoy | MAX nuevo | Artículo MAX hoy | Artículo MAX nuevo |", "|---|---:|---:|---|---|"]
        for x in df.itertuples():
            L.append(f"| {x.indicador} | {f(x.MAX_hoy)} | {f(x.MAX_nuevo)} | {str(x.articulo_MAX_hoy).replace('|', '/')[:90]} | "
                     f"{str(x.articulo_MAX_nuevo).replace('|', '/')[:90]} |")
    open(SAL + ".md", "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(res.to_string(index=False))
    for lug, df in detalle.items():
        print(f"\n{lug}\n" + df.to_string(index=False, max_colwidth=60))
    print("->", SAL + ".xlsx", SAL + ".md")


if __name__ == "__main__":
    main()
