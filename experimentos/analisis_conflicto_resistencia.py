"""
Análisis (CPU, sin GPU) de las candidatas de conflicto_territorial y resistencia_territorial puntuadas por
cola_gpu_conflicto_resistencia.py. Criterios en experimentos/PREREG_hipotesis_conflicto_resistencia.md.

Referencias sin GPU nueva, medidas sobre el mismo corpus: V2 (scores_v2_32deptos.pkl, nula = V2.NULA_TEST
guardada como ent_nula_actual en scores_hipotesis_jefe_18ind.pkl) y JEFE (ent_nueva_* / ent_nula_nueva_*).

  python experimentos/analisis_conflicto_resistencia.py submuestra|nacional
Salida: experimentos/resultados/cribado_conflicto_resistencia_<corpus>.csv
        experimentos/resultados/top_por_depto_<corpus>.csv  (artículo MAX por depto y candidata, para jueces)
"""
import glob
import os
import pickle
import sys

import numpy as np
import pandas as pd

SCORES_NAC = "datos/scores/scores_v2_32deptos.pkl"
JEFE = "datos/scores/scores_hipotesis_jefe_18ind.pkl"
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
SUBMUESTRA = "experimentos/resultados/submuestra_cribado.csv"
CARPETA = "datos/scores/hip_conflicto_resistencia"
IND = {"C": "conflicto_territorial", "R": "resistencia_territorial"}


def corregido(ent, neu, sesgo):
    return np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)


def metricas(ent, neu, ent_n, neu_n, sesgo, dep):
    real = corregido(ent, neu, sesgo)
    nula = corregido(ent_n, neu_n, sesgo)
    mr = pd.Series(real).groupby(dep).max()
    mn = pd.Series(nula).groupby(dep).max()
    q1, q2, q3 = mr.quantile([0.25, 0.5, 0.75])
    return real, dict(
        nula_cruda_p09=(ent_n > 0.9).mean(), nula_corr_media=nula.mean(),
        real_corr_media=real.mean(), real_corr_p05=(real > 0.5).mean(),
        brecha_media=(mr - mn).mean(), brecha_min=(mr - mn).min(),
        max_min=mr.min(), max_q1=q1, max_med=q2, max_q3=q3, max_max=mr.max(), max_iqr=q3 - q1,
        nula_max_media=mn.mean())


def main():
    corpus = sys.argv[1]
    v2 = pd.read_pickle(SCORES_NAC).reset_index(drop=True)
    jf = pd.read_pickle(JEFE)
    jf = jf[jf["corpus"] == "nacional"].reset_index(drop=True)
    corp = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    assert (v2["titulo"].values == jf["titulo"].values).all()
    idx = pd.read_csv(SUBMUESTRA)["idx"].values if corpus == "submuestra" else np.arange(len(v2))
    v2, jf, corp = v2.iloc[idx].reset_index(drop=True), jf.iloc[idx].reset_index(drop=True), corp.iloc[idx].reset_index(drop=True)
    sesgo = v2["sesgo"].values.astype(float)
    dep = v2["departamento"].astype(str).str.strip().values

    filas, tops = [], []

    def registrar(letra, cid, frase, ent, neu, ent_n, neu_n):
        real, m = metricas(ent, neu, ent_n, neu_n, sesgo, dep)
        filas.append({"indicador": IND[letra], "id": cid, "frase": frase, **m})
        s = pd.Series(real)
        for d, i in s.groupby(dep).idxmax().items():
            tops.append({"indicador": IND[letra], "id": cid, "departamento": d, "idx_corpus": int(idx[i]),
                         "score": real[i], "titulo": corp["titulo"].iloc[i]})

    for letra, ind in IND.items():
        registrar(letra, "V2", "(V2)", v2[f"ent_{ind}"].values, v2[f"neu_{ind}"].values,
                  jf["ent_nula_actual"].values, jf["neu_nula_actual"].values)
        registrar(letra, "JEFE", "(jefe)", jf[f"ent_nueva_{ind}"].values, jf[f"neu_nueva_{ind}"].values,
                  jf[f"ent_nula_nueva_{ind}"].values, jf[f"neu_nula_nueva_{ind}"].values)
    for f in sorted(glob.glob(os.path.join(CARPETA, corpus, "[CR]*.pkl"))):
        r = pickle.load(open(f, "rb"))
        assert r["n"] == len(idx), f
        registrar(r["id"][0], r["id"], r["frase"], r["ent"], r["neu"], r["ent_nula"], r["neu_nula"])

    R = pd.DataFrame(filas)
    out = []
    for ind, g in R.groupby("indicador", sort=False):
        ref = g[g["id"] == "V2"].iloc[0]
        g = g.copy()
        g["P1"] = (g["nula_cruda_p09"] <= 0.05) & (g["nula_corr_media"] <= 0.10)
        g["P2"] = (g["nula_cruda_p09"] <= ref["nula_cruda_p09"]) & (g["nula_corr_media"] <= ref["nula_corr_media"])
        g["P3"] = g["brecha_media"] >= ref["brecha_media"]
        g["saturada"] = (g["max_med"] >= 0.98) & (g["max_iqr"] < 0.05)
        g["pasa"] = g["P1"] & g["P2"] & g["P3"] & ~g["saturada"]
        out.append(g.sort_values(["pasa", "brecha_media", "max_iqr"], ascending=False))
    R = pd.concat(out, ignore_index=True)
    R.to_csv(f"experimentos/resultados/cribado_conflicto_resistencia_{corpus}.csv", index=False)
    pd.DataFrame(tops).to_csv(f"experimentos/resultados/top_por_depto_{corpus}.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 60)
    cols = ["id", "nula_cruda_p09", "nula_corr_media", "brecha_media", "max_min", "max_med", "max_iqr",
            "real_corr_p05", "P1", "P2", "P3", "saturada", "pasa", "frase"]
    for ind, g in R.groupby("indicador", sort=False):
        print(f"\n=== {ind} ({corpus}, n={len(idx)}) ===")
        print(g[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
