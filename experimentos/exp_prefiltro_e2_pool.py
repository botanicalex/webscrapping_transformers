"""
F1-T3 (PREREG_prefiltro_indicador_e2.md §4): pool y lotes ciegos para los jueces. Solo CPU; no toca src/.

V01 = puntaje de produccion sin compuerta de los indicadores del tramo (lugares: corrida de produccion del
2026-09-29; holdout: scores_v2_32deptos.pkl con clip(clip(ent - sesgo, 0) * (1 - neu), 0, 1), por posicion con el
corpus nacional). V08 = V01 x compuerta (lista del indicador sobre su premisa visible con SU hipotesis, normalizada).
Pool: por indicador del tramo que no supere el techo (aperturas.csv) y por lugar (Antioquia, Maicao, Oicata,
Paraguachon, Cauca, Choco, Cundinamarca), top-k de V01 U top-k de V08, k = min(10, n con puntaje > 0), orden por
puntaje descendente y url ascendente. Union de url deduplicada, barajada con default_rng(20260929) sobre las url
ordenadas; ids e0000...; lotes JSONL de <= 40 con la premisa visible recortada con la mas larga de las 6 hipotesis.

  PYTHONIOENCODING=utf-8 python experimentos/exp_prefiltro_e2_pool.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_prefiltro_e2_comun as C  # noqa: E402

P = C.P
CORPUS_L = "datos/corpus/df_corpus_5lugares.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
URL_LUGARES = "experimentos/resultados/juicio_5ind/url_lugares.csv"
PROC_PREF = "resultados/tablas_lugares_max_prefiltro_2026-09-29/df_procesado_5lugares.pkl"
PROC_MAX = "resultados/tablas_lugares_max/df_procesado_5lugares.pkl"
DIR = "experimentos/resultados/juicio_prefiltro_e2"
LUGARES = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]
HOLDOUT = ["Cauca", "Chocó", "Cundinamarca"]
TAM_LOTE, K = 40, 10


def topk(urls, x):
    d = pd.DataFrame({"url": urls, "x": x})
    d = d[d["x"] > 0].sort_values(["x", "url"], ascending=[False, True])
    return list(zip(d["url"].head(K), d["x"].head(K)))


def main():
    dl = os.path.join(DIR, "lotes")
    if os.path.isdir(dl) and os.listdir(dl):
        sys.exit(f"{dl} ya tiene contenido: no se sobrescribe")
    ap = pd.read_csv(os.path.join(DIR, "aperturas.csv"))
    ap_t = ap[ap["grupo"] == "tramo"].set_index("indicador")
    inds = [i for i in P.TRAMO_1 if not ap_t.loc[i, "supera_techo"]]
    print("Indicadores al pool:", inds, "| pasan sin filtro:", [i for i in P.TRAMO_1 if i not in inds])

    tok = C.cargar_tokenizer()
    # ---- lugares
    cl = pd.read_pickle(CORPUS_L).reset_index(drop=True)
    a = pd.read_pickle(PROC_PREF).reset_index(drop=True)
    b = pd.read_pickle(PROC_MAX).reset_index(drop=True)
    assert (a["url"].values == cl["url"].values).all() and (b["url"].values == cl["url"].values).all()
    dif = max(float(np.abs(a[i].astype(float).values - b[i].astype(float).values).max()) for i in P.TRAMO_1)
    print(f"Sanidad lugares: max|prefiltro_2026-09-29 - tablas_lugares_max| en los 6 indicadores = {dif:.2e} "
          f"({'OK' if dif < 1e-6 else 'FALLA'})")
    assert dif < 1e-6
    lug = pd.read_csv(URL_LUGARES)
    txt_l = cl["texto"].fillna("").astype(str).tolist()
    # ---- holdout
    cn = pd.read_pickle(C.CORPUS_NAC).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(cn) == len(d) == 11439
    assert (cn["titulo"].values == d["titulo"].values).all() and (cn["departamento"].values == d["departamento"].values).all()
    sesgo = d["sesgo"].values.astype(float)
    m_ho = cn["departamento"].isin(HOLDOUT).values
    ho = cn[m_ho].reset_index(drop=True)
    assert len(ho) == 1117
    txt_h = ho["texto"].fillna("").astype(str).tolist()
    sol = set(cl["url"]) & set(ho["url"])
    print("url en lugares y holdout a la vez:", len(sol))

    filas = []
    for ind in inds:
        rx = P.LISTAS_TRAMO_1[ind]
        hip = C.V2.TODAS[ind]
        assert hip == P.HIPOTESIS[ind]
        e, n = d[f"ent_{ind}"].values.astype(float), d[f"neu_{ind}"].values.astype(float)
        s_ho = np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)[m_ho]
        g_l = np.array(C.compuerta(C.premisa_visible_prod(txt_l, tok, hip), rx))
        g_h = np.array(C.compuerta(C.premisa_visible_prod(txt_h, tok, hip), rx))
        s_l = a[ind].astype(float).values
        print(f"{ind}: compuerta abre {g_l.mean():.1%} lugares, {g_h.mean():.1%} holdout")
        lugares = []
        for l in LUGARES:
            u = set(lug.loc[lug["lugar"] == l, "url"])
            mk = cl["url"].isin(u).values
            lugares.append((l, cl["url"].values[mk], s_l[mk], g_l[mk]))
        for dep in HOLDOUT:
            mk = (ho["departamento"].values == dep)
            lugares.append((dep, ho["url"].values[mk], s_ho[mk], g_h[mk]))
        for l, urls, s, g in lugares:
            t1 = {u: (r, x) for r, (u, x) in enumerate(topk(urls, s), 1)}
            t8 = {u: (r, x) for r, (u, x) in enumerate(topk(urls, s * g), 1)}
            sd, gd = dict(zip(urls, s)), dict(zip(urls, g))
            for u in sorted(set(t1) | set(t8)):
                filas.append({"indicador": ind, "lugar": l, "url": u, "en_topk_v01": u in t1, "en_topk_v08": u in t8,
                              "puntaje_v01": sd[u], "puntaje_v08": sd[u] * gd[u],
                              "rango": min(t1.get(u, (99,))[0], t8.get(u, (99,))[0]),
                              "rango_v01": t1.get(u, (np.nan,))[0], "rango_v08": t8.get(u, (np.nan,))[0]})
    pool = pd.DataFrame(filas)
    os.makedirs(DIR, exist_ok=True)
    pool.to_csv(os.path.join(DIR, "pool.csv"), index=False)

    res = []
    for ind in inds:
        p = pool[pool["indicador"] == ind]
        pu, p1, p8 = set(p["url"]), set(p.loc[p["en_topk_v01"], "url"]), set(p.loc[p["en_topk_v08"], "url"])
        res.append({"indicador": ind, "entradas": len(p), "url_unicas": len(pu), "solo_v01": len(p1 - p8),
                    "solo_v08": len(p8 - p1), "nuevas_por_filtro": len(p8 - p1)})
    print("\nPool por indicador (url unicas; nuevas por el filtro = en top-k V08 y no en top-k V01):")
    print(pd.DataFrame(res).to_string(index=False))

    urls = np.array(sorted(set(pool["url"])))
    urls = urls[np.random.default_rng(P.SEMILLA).permutation(len(urls))]
    mapa = pd.DataFrame({"id": [f"e{i:04d}" for i in range(len(urls))], "url": urls})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)

    # premisa del juez: recortada con la mas larga de las 6 hipotesis, tal cual la ve el modelo
    hips = [P.HIPOTESIS[i] for i in P.TRAMO_1]
    larga = max(hips, key=lambda h: len(tok(h, add_special_tokens=False)["input_ids"]))
    print(f"\nHipotesis mas larga (tokens): {larga!r}")
    txt = dict(zip(cl["url"], txt_l))
    txt.update(dict(zip(ho["url"], txt_h)))
    prem = C.premisa_visible_prod([txt[u] for u in urls], tok, larga)
    os.makedirs(dl, exist_ok=True)
    n = 0
    for n, ini in enumerate(range(0, len(mapa), TAM_LOTE), 1):
        with open(os.path.join(dl, f"lote_{n:02d}.jsonl"), "w", encoding="utf-8") as f:
            for i in range(ini, min(ini + TAM_LOTE, len(mapa))):
                assert prem[i].strip(), mapa["url"].iloc[i]
                f.write(json.dumps({"id": mapa["id"].iloc[i], "premisa": prem[i]}, ensure_ascii=False) + "\n")
    for sub in ("etiquetas_c", "etiquetas_d"):
        os.makedirs(os.path.join(DIR, sub), exist_ok=True)
    print(f"{len(mapa)} url unicas -> {n} lotes de <= {TAM_LOTE} en {dl}")


if __name__ == "__main__":
    main()
