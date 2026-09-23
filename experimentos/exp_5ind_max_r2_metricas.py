"""
Fase A, paso 4, de la 2a ronda del plan 5ind MAX (experimentos/PREREG_5ind_MAX_r2.md §4, §5):
M1-M6 y M2+ por candidata e indicador sobre los 4 lugares, kappa, criterios 1-5 contra la
vigente, hasta 2 finalistas por indicador y recuento de exclusion. Todo offline.

Referencia = SI/SI de juez-a y juez-b: ronda 1 (565 lugares + 94 holdout) + ronda 2 (pool
nuevo y muestra de exclusion). Los 40 de control conservan su etiqueta de la ronda 1.

Ejecutar desde la raiz del worktree:  python experimentos/exp_5ind_max_r2_metricas.py
Salidas: experimentos/resultados/juicio_5ind_r2/metricas_r2.xlsx y
         experimentos/RESULTADOS_5ind_MAX_r2.md
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_5ind_max_r2 as R2  # noqa: E402
import hipotesis_base as HB  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import silver  # noqa: E402
from exp_5ind_max_juicio import kappa  # noqa: E402
from exp_5ind_max_r2_pool import CLAVES, DIR, DIR_R1, LUGARES, juzgados_r1  # noqa: E402

CORPUS = "datos/corpus/df_corpus_5lugares.pkl"
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
BASELINE = "datos/scores/df_procesado_baseline_v2.pkl"
CORTE = 0.766
MIN_EXCL = 5
MIN_POR_HIP_NAC = 7.3  # §6: ~7.3 min por hipotesis sobre los 11.439
ORDEN = {k: i for i, k in enumerate(R2.CANDIDATAS)}
GA, CT = "presencia_grupos_armados", "conflicto_territorial"


def argmax_url(sub: pd.DataFrame, col: str) -> str:
    return sub.sort_values([col, "url"], ascending=[False, True])["url"].iloc[0]


def referencia() -> pd.DataFrame:
    """Una fila por URL juzgada: r1 (lugares + holdout) y r2 sin el control."""
    r1 = juzgados_r1()
    r2 = pd.read_csv(os.path.join(DIR, "referencia.csv"))
    r2 = r2[r2["origen"] != "control"].assign(ronda="r2_" + r2["origen"])
    ref = pd.concat([r1, r2], ignore_index=True)
    assert ref["url"].is_unique
    return ref


def main():
    cand = pd.read_pickle(os.path.join(DIR, "candidatas_r2.pkl"))
    ref = referencia()
    lug = pd.read_csv(os.path.join(DIR_R1, "url_lugares.csv"))
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    nac = pd.read_pickle(CORPUS_NAC)
    base = pd.read_pickle(BASELINE)
    titulo = pd.concat([corpus.set_index("url")["titulo"], nac.set_index("url")["titulo"]])
    titulo = titulo[~titulo.index.duplicated()]
    assert (corpus["url"].values == cand["url"].values).all()

    urls_lugar = {l: set(lug.loc[lug["lugar"] == l, "url"]) for l in LUGARES}
    en_lug = set().union(*urls_lugar.values())
    ref_l = ref[ref["url"].isin(en_lug)]
    positivos = {ind: set(ref.loc[ref[ind] == 1, "url"]) for ind in H.INDICADORES_5}
    kap = {ind: kappa(ref_l[ind + "__a"] == "SI", ref_l[ind + "__b"] == "SI") for ind in H.INDICADORES_5}

    # §5: exclusion en total (todas las juzgadas de las dos rondas).
    ex = ref[ref["exclusion_beneficios_economicos"] == 1]
    n_excl = len(ex)
    excl_medible = n_excl >= MIN_EXCL

    # M5: argmax de los otros 25 (21 de produccion + los otros 4 vigentes).
    otros = [c for c in {**V2.EVENTOS, **V2.POSTURAS, **V2.INDICADORES} if c not in H.INDICADORES_5]
    assert len(otros) == 21, len(otros)
    arg_otros = {}
    for l in LUGARES:
        sb = base[base["url"].isin(urls_lugar[l])]
        sv = cand[cand["url"].isin(urls_lugar[l])]
        arg_otros[l] = {c: argmax_url(sb, c) for c in otros}
        arg_otros[l].update({ind: argmax_url(sv, f"{ind}__vig") for ind in H.INDICADORES_5})

    plata = silver.etiquetar(corpus, HB.KEYWORDS_SILVER[GA])["label"].values

    filas = []
    for ind in H.INDICADORES_5:
        for k in CLAVES:
            c = f"{ind}__{k}"
            f = {"indicador": ind, "candidata": k, "frase": R2.texto(ind, k)}
            m1, m2, m2p, m3v = [], [], [], []
            for l in LUGARES:
                sv = cand[cand["url"].isin(urls_lugar[l])]
                pos_l = positivos[ind] & urls_lugar[l]
                orden = sv[sv[c] > 0].sort_values([c, "url"], ascending=[False, True])
                am = argmax_url(sv, c)
                mx = float(sv[c].max())
                kk = min(10, len(orden))
                if kk == 0:
                    p, ok1 = (1.0 if not pos_l else 0.0), not pos_l
                else:
                    assert orden["url"].head(kk).isin(ref["url"]).all(), ("top-10 sin juzgar", c, l)
                    p = float(np.mean([u in pos_l for u in orden["url"].head(kk)]))
                    ok1 = am in pos_l
                viol = (not pos_l and mx >= CORTE) or (bool(pos_l) and mx < CORTE)
                m1.append(ok1); m2.append(p); m3v.append(viol)
                if pos_l:
                    m2p.append(p)
                mabs = float(sv[c + "__abs"].max())
                f.update({f"M1_{l}": ok1, f"M2_{l}": round(p, 3), f"M3viol_{l}": viol,
                          f"max_{l}": round(mx, 4), f"abs_{l}": round(mabs, 4),
                          f"tot_{l}": round(float(sv["ABSURDO_TOTAL"].max()), 4),
                          f"prop_abs_{l}": round(float((sv[c + "__abs"] > CORTE).mean()), 4),
                          f"razon_abs_{l}": round(mabs / mx, 3) if mx > 0 else np.nan,
                          f"npos_{l}": len(pos_l),
                          f"M5_{l}": sum(u == am for k2, u in arg_otros[l].items() if k2 != ind),
                          f"M5cg_{l}": (am == arg_otros[l][GA if ind == CT else CT]) if ind in (GA, CT) else np.nan,
                          f"top1_{l}": titulo.get(am, "")})
            f["M1_n"] = int(sum(m1))
            f["M2"] = round(float(np.mean(m2)), 3)
            f["M2mas"] = round(float(np.mean(m2p)), 3) if m2p else np.nan
            f["M3_viol"] = int(sum(m3v))
            f["abs_medio"] = round(float(np.mean([f[f"abs_{l}"] for l in LUGARES])), 4)
            f["M5_medio"] = round(float(np.mean([f[f"M5_{l}"] for l in LUGARES])), 2)
            f["M5cg_n"] = int(sum(bool(f[f"M5cg_{l}"]) for l in LUGARES)) if ind in (GA, CT) else np.nan
            f["M6_auc"] = round(silver.auc(cand[c].values, plata), 4) if ind == GA else np.nan
            f["kappa"] = round(kap[ind], 3)
            filas.append(f)
    M = pd.DataFrame(filas)

    # Criterios 1-5 contra la vigente del mismo indicador.
    for ind in H.INDICADORES_5:
        b = M[(M.indicador == ind) & (M.candidata == "vig")].iloc[0]
        for i in M.index[M.indicador == ind]:
            r = M.loc[i]
            con_pos = [l for l in LUGARES if r[f"npos_{l}"] > 0]
            c1 = r["M2"] >= max(0.60, b["M2"] + 0.20)
            c2 = r["M1_n"] >= 3 or (len(con_pos) > 0 and all(r[f"M1_{l}"] for l in con_pos))
            c3 = all(not r[f"M3viol_{l}"] or b[f"M3viol_{l}"] for l in LUGARES)
            c4 = all(r[f"abs_{l}"] < CORTE and r[f"abs_{l}"] <= b[f"abs_{l}"] + 0.05
                     and r[f"tot_{l}"] <= b[f"tot_{l}"] + 0.05 for l in LUGARES)
            c5 = (r["M6_auc"] >= b["M6_auc"] - 0.02) if ind == GA else True
            medible = excl_medible or ind != "exclusion_beneficios_economicos"
            M.loc[i, ["c1", "c2", "c3", "c4", "c5"]] = [c1, c2, c3, c4, c5]
            M.loc[i, "pasa_1a5"] = bool(c1 and c2 and c3 and c4 and c5 and r["kappa"] >= 0.4
                                        and medible and r["candidata"] != "vig")
    M["pasa_1a5"] = M["pasa_1a5"].astype(bool)

    fin = {}
    for ind in H.INDICADORES_5:
        p = M[(M.indicador == ind) & M.pasa_1a5].copy()
        p["_o"] = p["candidata"].map(ORDEN)
        p = p.sort_values(["M2", "M1_n", "abs_medio", "_o"], ascending=[False, False, True, True])
        fin[ind] = p["candidata"].head(2).tolist()
    M["finalista"] = [k in fin[i] for i, k in zip(M.indicador, M.candidata)]
    M.to_excel(os.path.join(DIR, "metricas_r2.xlsx"), index=False)

    n_fin = sum(len(v) for v in fin.values())
    gpu_b = n_fin * 2 * MIN_POR_HIP_NAC
    for ind in H.INDICADORES_5:
        s = M[M.indicador == ind]
        print(f"{ind[:26]:26s} kappa={kap[ind]:.2f} " + " ".join(
            f"{r.candidata}:{r.M2:.2f}{'*' if r.pasa_1a5 else ''}" for r in s.itertuples())
            + f"  finalistas={fin[ind] or 'ninguna'}")
    print(f"Exclusion SI/SI en total: {n_excl} ({'medible' if excl_medible else 'NO MEDIBLE'}); "
          f"por ronda {ex['ronda'].value_counts().to_dict()}")
    print(f"Finalistas: {n_fin}; GPU fase B estimada {gpu_b:.0f} min ({n_fin} x 2 x {MIN_POR_HIP_NAC} min)")
    escribir_md(M, fin, kap, ref, ex, excl_medible, titulo, gpu_b)


def escribir_md(M, fin, kap, ref, ex, excl_medible, titulo, gpu_b):
    ok = lambda x: "sí" if x else "no"  # noqa: E731
    r2 = pd.read_csv(os.path.join(DIR, "referencia.csv"))
    n_r2 = r2["origen"].value_counts().to_dict()
    L = ["# Resultados — 2a ronda 5ind MAX, fase A (4 lugares, solo hipótesis)", "",
         "Generado por `experimentos/exp_5ind_max_r2_metricas.py`; detalle en "
         "`experimentos/resultados/juicio_5ind_r2/metricas_r2.xlsx`. Pre-registro "
         "`experimentos/PREREG_5ind_MAX_r2.md`. Criterio 6 (holdout) pendiente de la fase B.", "",
         f"Referencia: {len(ref)} artículos juzgados (ronda 1: 565 lugares + 94 holdout; ronda 2: "
         f"{sum(v for k, v in n_r2.items() if k != 'control')} nuevos, por origen {n_r2}). "
         "Los 40 de control conservan su etiqueta de la ronda 1.", "",
         "M2 = precisión@10 media en los 4 lugares (A/M/O/P = Antioquia/Maicao/Oicatá/Paraguachón); "
         "M2+ = solo lugares con positivos; gemela = frase con «osos polares»; absurdo total idéntico "
         "para todas (no discrimina).", ""]
    for ind in H.INDICADORES_5:
        s = M[M.indicador == ind]
        b = s[s.candidata == "vig"].iloc[0]
        npos = "/".join(str(b[f"npos_{l}"]) for l in LUGARES)
        tot = "/".join(f"{b[f'tot_{l}']:.2f}" for l in LUGARES)
        nota = "" if (excl_medible or ind != "exclusion_beneficios_economicos") else " — NO MEDIBLE (§5)"
        L += [f"## `{ind}` — kappa {kap[ind]:.2f} — positivos {npos} — finalistas: "
              f"{', '.join(fin[ind]) or 'ninguna'}{nota}", "",
              f"Absurdo total, máx por lugar: {tot}.", "",
              "| cand | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | M5 | "
              "c1 | c2 | c3 | c4 | c5 | pasa |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in s.iterrows():
            mx = "/".join(f"{r[f'max_{l}']:.2f}" for l in LUGARES)
            ab = "/".join(f"{r[f'abs_{l}']:.2f}" for l in LUGARES)
            m2p = "—" if pd.isna(r.M2mas) else f"{r.M2mas:.2f}"
            L.append(f"| {r.candidata} | {r.M2:.2f} | {m2p} | {r.M1_n} | {r.M3_viol} | {mx} | {ab} | "
                     f"{r.M5_medio:.2f} | {ok(r.c1)} | {ok(r.c2)} | {ok(r.c3)} | {ok(r.c4)} | {ok(r.c5)} | "
                     f"{ok(r.pasa_1a5)} |")
        L.append("")
        if ind == GA:
            L.append("M6 (AUC contra la plata): " + ", ".join(f"{r.candidata} {r.M6_auc:.3f}" for r in s.itertuples()))
            L.append("")
        if ind in (GA, CT):
            L.append(f"Lugares (de 4) cuyo artículo del MAX coincide con el de la vigente de "
                     f"`{GA if ind == CT else CT}`: " + ", ".join(f"{r.candidata} {int(r.M5cg_n)}" for r in s.itertuples()))
            L.append("")
        for k in fin[ind]:
            r = s[s.candidata == k].iloc[0]
            L.append(f"Cambio de top-1, vig → {k} («{r.frase}»):")
            for l in LUGARES:
                if b[f"top1_{l}"] != r[f"top1_{l}"]:
                    L.append(f"- {l}: «{b[f'top1_{l}']}» ({b[f'max_{l}']:.2f}) → «{r[f'top1_{l}']}» ({r[f'max_{l}']:.2f})")
            L.append("")
    L += ["## Exclusión de beneficios económicos (§5)", "",
          f"SÍ/SÍ en total (las dos rondas): **{len(ex)}** → "
          f"{'medible, evaluada con los criterios 1–5' if excl_medible else 'NO MEDIBLE con este corpus (< 5): decide el usuario'}. "
          f"Por origen: {ex['ronda'].value_counts().to_dict()}.", ""]
    for u in ex["url"]:
        L.append(f"- «{titulo.get(u, '')}» ({u})")
    L += ["", "## Control entre rondas (40 artículos ya juzgados, solo reporte)", ""]
    ctl = r2[r2["origen"] == "control"]
    j1 = juzgados_r1().set_index("url").loc[ctl["url"]]
    L += ["| indicador | acuerdo SI/SI r2 vs r1 | SI/SI r1 | SI/SI r2 |", "|---|---|---|---|"]
    for ind in H.INDICADORES_5:
        L.append(f"| `{ind}` | {float((ctl[ind].values == j1[ind].values).mean()):.2f} | "
                 f"{int(j1[ind].sum())} | {int(ctl[ind].sum())} |")
    L += ["", f"GPU estimada de la fase B: {gpu_b:.0f} min (finalistas × 2 frases × {MIN_POR_HIP_NAC} min).", ""]
    with open("experimentos/RESULTADOS_5ind_MAX_r2.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
