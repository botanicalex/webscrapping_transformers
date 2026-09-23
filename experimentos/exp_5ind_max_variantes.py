"""
F3 del plan 5ind MAX (experimentos/PREREG_5ind_MAX.md §3): construye OFFLINE, sobre
datos/scores/scores_5ind_atomicas_lugares.pkl, las 12 variantes por indicador, sus dos
controles absurdos (objeto absurdo y absurdo total), el MAX por lugar y el pool TREC
(top-15 por variante x indicador x lugar, excluyendo score 0).

Sin GPU. La agregacion por lugar es MAX, como en produccion.

Ejecutar desde la raiz del worktree:  python experimentos/exp_5ind_max_variantes.py
Salidas (experimentos/resultados/juicio_5ind/):
  premisas_visibles.pkl  url -> premisa visible (juez y compuerta F5)
  variantes_5ind.pkl     url + <ind>__<V>, <ind>__<V>__abs, <ind>__<V>__tot
  max_por_lugar.csv      indicador, variante, lugar, max, url_max, max_abs, max_tot
  pool.csv               url, indicador, lugar, variante, rango (top-15 con score > 0)
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402

SCORES = "datos/scores/scores_5ind_atomicas_lugares.pkl"
CORPUS = "datos/corpus/df_corpus_5lugares.pkl"
BASELINE = "datos/scores/df_procesado_baseline_v2.pkl"
DIR = "experimentos/resultados/juicio_5ind"
LUGARES = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]
VARIANTES = [f"V{i:02d}" for i in range(1, 13)]
TOP_POOL = 15


def premisas_visibles(df) -> pd.Series:
    ruta = os.path.join(DIR, "premisas_visibles.pkl")
    if os.path.exists(ruta):
        p = pd.read_pickle(ruta)
        if (p.index.values == df["url"].values).all():
            return p
    from transformers import AutoTokenizer
    from nli_core import MODELO_NLI, _ruta_modelo_local
    tok = AutoTokenizer.from_pretrained(_ruta_modelo_local(MODELO_NLI))
    textos = df["texto"].fillna("").astype(str).tolist()
    p = pd.Series(H.premisa_visible(textos, tok, H.hipotesis_unicas().values()),
                  index=df["url"].values)
    p.to_pickle(ruta)
    return p


def construir(sc: pd.DataFrame, gates: dict) -> pd.DataFrame:
    sesgo = sc["sesgo"].values

    def s(col):
        ent, neu = sc[f"ent_{col}"].values.astype(float), sc[f"neu_{col}"].values.astype(float)
        return np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)

    def resta(x, conf):
        return np.clip(x - conf, 0, 1)

    tot = s("ABSURDO_TOTAL")
    out = {"url": sc["url"].values}
    for ind in H.INDICADORES_5:
        a = lambda k: s(H.columna(ind, k))  # noqa: E731
        g = gates[ind]
        conf = np.max([a("c1"), a("c2"), a("c3")], axis=0)
        pieza = H.PIEZA_F2_ABS[ind]
        otra = "A2" if pieza == "A1" else "A1"
        f2 = np.minimum(a("A1"), a("A2"))
        f2_abs = np.minimum(a(otra), a(pieza + "_abs"))
        f2_tot = np.minimum(a(otra), tot)
        f3n = resta(a("nue"), conf)
        f3n_abs, f3n_tot = resta(a("nue_abs"), conf), resta(tot, conf)
        V = {
            "V01": (a("vig"), a("vig_abs"), tot),
            "V02": (a("gpt"), a("gpt_abs"), tot),
            "V03": (a("nue"), a("nue_abs"), tot),
            "V04": (np.min([a("nue"), a("p1"), a("p2")], axis=0),
                    np.min([a("nue_abs"), a("p1_abs"), a("p2_abs")], axis=0), tot),
            "V05": (f2, f2_abs, f2_tot),
            "V06": (resta(a("vig"), conf), resta(a("vig_abs"), conf), resta(tot, conf)),
            "V07": (f3n, f3n_abs, f3n_tot),
            "V08": (a("vig") * g, a("vig_abs") * g, tot * g),
            "V09": (a("nue") * g, a("nue_abs") * g, tot * g),
            "V10": (f2 * g, f2_abs * g, f2_tot * g),
            "V11": (f3n * g, f3n_abs * g, f3n_tot * g),
            "V12": (resta(f2, conf), resta(f2_abs, conf), resta(f2_tot, conf)),
        }
        for v, (x, xa, xt) in V.items():
            out[f"{ind}__{v}"] = x
            out[f"{ind}__{v}__abs"] = xa
            out[f"{ind}__{v}__tot"] = xt
    return pd.DataFrame(out)


def main():
    sc = pd.read_pickle(SCORES)
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    assert (sc["url"].values == corpus["url"].values).all()
    lug = pd.read_csv(os.path.join(DIR, "url_lugares.csv"))

    prem = premisas_visibles(corpus)
    gates = {i: np.asarray(H.compuerta(prem.values, i)) for i in H.INDICADORES_5}
    var = construir(sc, gates)
    var.to_pickle(os.path.join(DIR, "variantes_5ind.pkl"))

    # Sanidad: V01 debe reproducir el score vigente de produccion.
    base = pd.read_pickle(BASELINE).set_index("url").loc[var["url"]]
    dif = max(np.abs(var[f"{i}__V01"].values - base[i].values).max() for i in H.INDICADORES_5)
    print(f"V01 vs produccion (baseline_v2): max|dif| = {dif:.1e} {'OK' if dif < 1e-4 else 'DESVIACION'}")

    filas, pool = [], []
    for lugar in LUGARES:
        sub = var[var["url"].isin(lug.loc[lug["lugar"] == lugar, "url"])]
        for ind in H.INDICADORES_5:
            for v in VARIANTES:
                c = f"{ind}__{v}"
                orden = sub.sort_values([c, "url"], ascending=[False, True])
                filas.append({"indicador": ind, "variante": v, "lugar": lugar,
                              "max": orden[c].iloc[0], "url_max": orden["url"].iloc[0],
                              "max_abs": sub[c + "__abs"].max(), "max_tot": sub[c + "__tot"].max(),
                              "n_pos_score": int((sub[c] > 0).sum()),
                              "prop_abs_766": float((sub[c + "__abs"] > 0.766).mean())})
                top = orden[orden[c] > 0].head(TOP_POOL)
                for r, u in enumerate(top["url"], 1):
                    pool.append({"url": u, "indicador": ind, "lugar": lugar, "variante": v, "rango": r})
    mx = pd.DataFrame(filas)
    mx.to_csv(os.path.join(DIR, "max_por_lugar.csv"), index=False)
    pool = pd.DataFrame(pool)
    pool.to_csv(os.path.join(DIR, "pool.csv"), index=False)

    print(f"Pool: {pool['url'].nunique()} articulos unicos "
          f"({len(pool)} entradas variante x indicador x lugar)")
    # Resumen corto: nº de lugares (de 4) con MAX >= 0.766, por variante x indicador.
    mx["alto"] = mx["max"] >= 0.766
    t = mx.pivot_table(index="variante", columns="indicador", values="alto", aggfunc="sum")
    t.columns = [c[:12] for c in t.columns]
    print("Lugares con MAX >= 0.766 (de 4):")
    print(t.to_string())


if __name__ == "__main__":
    main()
