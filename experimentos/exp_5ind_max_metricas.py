"""
F5 del plan 5ind MAX (experimentos/PREREG_5ind_MAX.md §4): M1-M6 por variante e
indicador sobre los 4 lugares, criterio de adopcion 1-5 (el 6 es el holdout de F7) y
<= 2 finalistas por indicador. Todo offline.

Ejecutar desde la raiz del worktree:  python experimentos/exp_5ind_max_metricas.py
Salidas: experimentos/resultados/juicio_5ind/metricas_5ind.xlsx y
         experimentos/RESULTADOS_5ind_MAX.md (tabla + ejemplos de cambio de top)
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_base as HB  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import silver  # noqa: E402

DIR = "experimentos/resultados/juicio_5ind"
CORPUS = "datos/corpus/df_corpus_5lugares.pkl"
BASELINE = "datos/scores/df_procesado_baseline_v2.pkl"
LUGARES = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]
VARIANTES = [f"V{i:02d}" for i in range(1, 13)]
CORTE = 0.766
FAMILIA = {"V01": "F1", "V02": "F1", "V03": "F1", "V04": "F4", "V05": "F2", "V06": "F3",
           "V07": "F3", "V08": "F5", "V09": "F5", "V10": "F5+F2", "V11": "F5+F3", "V12": "F2+F3"}
ORDEN_FAMILIA = {"F1": 0, "F5": 1, "F2": 2, "F3": 3, "F4": 4, "F5+F2": 5, "F5+F3": 5, "F2+F3": 5}


def argmax_url(sub: pd.DataFrame, col: str) -> str:
    return sub.sort_values([col, "url"], ascending=[False, True])["url"].iloc[0]


def main():
    var = pd.read_pickle(os.path.join(DIR, "variantes_5ind.pkl"))
    mx = pd.read_csv(os.path.join(DIR, "max_por_lugar.csv"))
    ref = pd.read_csv(os.path.join(DIR, "referencia.csv"))
    lug = pd.read_csv(os.path.join(DIR, "url_lugares.csv"))
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    base = pd.read_pickle(BASELINE)
    titulo = corpus.set_index("url")["titulo"]

    # Kappa por indicador (recalculado igual que en la consolidacion).
    kap = {}
    for ind in H.INDICADORES_5:
        a, b = ref[ind + "__a"] == "SI", ref[ind + "__b"] == "SI"
        po = (a == b).mean()
        pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
        kap[ind] = (po - pe) / (1 - pe) if pe < 1 else np.nan

    positivos = {ind: set(ref.loc[ref[ind] == 1, "url"]) for ind in H.INDICADORES_5}
    urls_lugar = {l: set(lug.loc[lug["lugar"] == l, "url"]) for l in LUGARES}

    # M5: argmax de los otros indicadores (21 vigentes de produccion + los otros 4 en V01).
    otros = [c for c in {**V2.EVENTOS, **V2.POSTURAS, **V2.INDICADORES} if c not in H.INDICADORES_5]
    assert len(otros) == 21, len(otros)
    arg_otros = {}
    for l in LUGARES:
        sb = base[base["url"].isin(urls_lugar[l])]
        sv = var[var["url"].isin(urls_lugar[l])]
        arg_otros[l] = {c: argmax_url(sb, c) for c in otros}
        for ind in H.INDICADORES_5:
            arg_otros[l][ind] = argmax_url(sv, f"{ind}__V01")

    # M6: plata de grupos armados sobre el corpus de trabajo.
    plata = silver.etiquetar(corpus, HB.KEYWORDS_SILVER["presencia_grupos_armados"])["label"].values
    assert (corpus["url"].values == var["url"].values).all()

    filas = []
    for ind in H.INDICADORES_5:
        for v in VARIANTES:
            c = f"{ind}__{v}"
            f = {"indicador": ind, "variante": v, "familia": FAMILIA[v]}
            m1, m2, m3v = [], [], []
            for l in LUGARES:
                sv = var[var["url"].isin(urls_lugar[l])]
                pos_l = positivos[ind] & urls_lugar[l]
                r = mx[(mx.indicador == ind) & (mx.variante == v) & (mx.lugar == l)].iloc[0]
                orden = sv[sv[c] > 0].sort_values([c, "url"], ascending=[False, True])
                k = min(10, len(orden))
                if k == 0:
                    p = 1.0 if not pos_l else 0.0
                    ok1 = not pos_l
                else:
                    p = float(np.mean([u in pos_l for u in orden["url"].head(k)]))
                    ok1 = r["url_max"] in pos_l
                viol = (not pos_l and r["max"] >= CORTE) or (bool(pos_l) and r["max"] < CORTE)
                m1.append(ok1); m2.append(p); m3v.append(viol)
                am = argmax_url(sv, c)
                f[f"M1_{l}"] = ok1
                f[f"M2_{l}"] = round(p, 3)
                f[f"M3viol_{l}"] = viol
                f[f"max_{l}"] = round(r["max"], 4)
                f[f"abs_{l}"] = round(r["max_abs"], 4)
                f[f"tot_{l}"] = round(r["max_tot"], 4)
                f[f"razon_abs_{l}"] = round(r["max_abs"] / r["max"], 3) if r["max"] > 0 else np.nan
                f[f"npos_{l}"] = len(pos_l)
                f[f"M5_{l}"] = sum(u == am for k2, u in arg_otros[l].items() if k2 != ind)
                f[f"top1_{l}"] = titulo.get(r["url_max"], "")
            f["M1_n"] = int(sum(m1))
            f["M2"] = round(float(np.mean(m2)), 3)
            f["M3_viol"] = int(sum(m3v))
            f["M5_medio"] = round(np.mean([f[f"M5_{l}"] for l in LUGARES]), 2)
            f["M6_auc"] = (round(silver.auc(var[c].values, plata), 4)
                           if ind == "presencia_grupos_armados" else np.nan)
            f["kappa"] = round(kap[ind], 3)
            filas.append(f)
    M = pd.DataFrame(filas)

    # Criterio de adopcion 1-5 contra V01 del mismo indicador.
    for ind in H.INDICADORES_5:
        b = M[(M.indicador == ind) & (M.variante == "V01")].iloc[0]
        for i in M.index[M.indicador == ind]:
            r = M.loc[i]
            con_pos = [l for l in LUGARES if r[f"npos_{l}"] > 0]
            c1 = r["M2"] >= max(0.60, b["M2"] + 0.20)
            c2 = r["M1_n"] >= 3 or (len(con_pos) > 0 and all(r[f"M1_{l}"] for l in con_pos))
            c3 = all(not r[f"M3viol_{l}"] or b[f"M3viol_{l}"] for l in LUGARES)
            c4 = all(r[f"abs_{l}"] < CORTE and r[f"abs_{l}"] <= b[f"abs_{l}"] + 0.05
                     and r[f"tot_{l}"] <= b[f"tot_{l}"] + 0.05 for l in LUGARES)
            c5 = (r["M6_auc"] >= b["M6_auc"] - 0.02) if ind == "presencia_grupos_armados" else True
            M.loc[i, ["c1", "c2", "c3", "c4", "c5"]] = [c1, c2, c3, c4, c5]
            M.loc[i, "pasa_1a5"] = bool(c1 and c2 and c3 and c4 and c5 and r["kappa"] >= 0.4
                                        and r["variante"] != "V01")

    M["pasa_1a5"] = M["pasa_1a5"].astype(bool)
    fin = {}
    for ind in H.INDICADORES_5:
        p = M[(M.indicador == ind) & (M.pasa_1a5 == True)].copy()  # noqa: E712
        p["_o"] = p["familia"].map(ORDEN_FAMILIA)
        fin[ind] = p.sort_values(["_o", "M2"], ascending=[True, False])["variante"].head(2).tolist()
    M["finalista"] = [v in fin[i] for i, v in zip(M.indicador, M.variante)]
    M.to_excel(os.path.join(DIR, "metricas_5ind.xlsx"), index=False)

    cols = ["variante", "familia", "M2", "M1_n", "M3_viol", "c1", "c2", "c3", "c4", "c5", "pasa_1a5"]
    for ind in H.INDICADORES_5:
        s = M[M.indicador == ind]
        print(f"{ind}  kappa={kap[ind]:.2f}  finalistas={fin[ind] or 'ninguna'}")
        print("  " + s[s.variante.isin(["V01"] + fin[ind]) | s.pasa_1a5][cols]
              .to_string(index=False).replace("\n", "\n  "))
    escribir_md(M, fin, kap)


def escribir_md(M, fin, kap):
    L = ["# Resultados — 5 indicadores bajo MAX (F5, lugares)", "",
         "Generado por `experimentos/exp_5ind_max_metricas.py`; detalle completo en "
         "`experimentos/resultados/juicio_5ind/metricas_5ind.xlsx`. Criterio 6 (holdout) pendiente de F7.", ""]
    for ind in H.INDICADORES_5:
        s = M[M.indicador == ind]
        L += [f"## `{ind}` — kappa {kap[ind]:.2f} — finalistas: {', '.join(fin[ind]) or 'ninguna'}", "",
              "| V | fam | M2 | M1 (de 4) | M3 viol | máx abs (A/M/O/P) | máx tot (A/M/O/P) | c1 | c2 | c3 | c4 | c5 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in s.iterrows():
            ab = "/".join(f"{r[f'abs_{l}']:.2f}" for l in LUGARES)
            tt = "/".join(f"{r[f'tot_{l}']:.2f}" for l in LUGARES)
            ok = lambda x: "sí" if x else "no"  # noqa: E731
            L.append(f"| {r.variante} | {r.familia} | {r.M2:.2f} | {r.M1_n} | {r.M3_viol} | {ab} | {tt} | "
                     f"{ok(r.c1)} | {ok(r.c2)} | {ok(r.c3)} | {ok(r.c4)} | {ok(r.c5)} |")
        L.append("")
        b = s[s.variante == "V01"].iloc[0]
        for v in fin[ind]:
            r = s[s.variante == v].iloc[0]
            L.append(f"Cambio de top-1, V01 → {v}:")
            for l in LUGARES:
                if b[f"top1_{l}"] != r[f"top1_{l}"]:
                    L.append(f"- {l}: «{b[f'top1_{l}']}» ({b[f'max_{l}']:.2f}) → «{r[f'top1_{l}']}» ({r[f'max_{l}']:.2f})")
            L.append("")
    with open("experimentos/RESULTADOS_5ind_MAX.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
