"""
Tramo 2, fase de jueces (PREREG_prefiltro_indicador_e2_t2.md §4 -> PREREG_prefiltro_indicador_e2.md §4): pool y lotes ciegos
para UN indicador, zonas_proteccion_alimentaria. Copia el procedimiento de exp_prefiltro_e2_pool.py. Solo CPU; no toca src/.

V01 = puntaje de produccion sin compuerta (lugares: corrida de produccion del 2026-09-29; holdout: scores_v2_32deptos.pkl con
clip(clip(ent - sesgo, 0) * (1 - neu), 0, 1), por posicion con el corpus nacional). V08 = V01 x compuerta (lista del indicador
sobre su premisa visible con SU hipotesis, normalizada). Pool por lugar (Antioquia, Maicao, Oicata, Paraguachon, Cauca, Choco,
Cundinamarca): top-k de V01 U top-k de V08, k = min(10, n con puntaje > 0), orden por puntaje desc y url asc. Union deduplicada,
barajada con default_rng(20260930) sobre las url ordenadas; ids t0000...; lotes JSONL de <= 40 con la premisa visible recortada
con la hipotesis del indicador (completa).

  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_e2_t2_pool.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_prefiltro_e2_comun as C  # noqa: E402
import hipotesis_prefiltro_e2_t2 as T2  # noqa: E402

IND = "zonas_proteccion_alimentaria"
CORPUS_L = "datos/corpus/df_corpus_5lugares.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
URL_LUGARES = "experimentos/resultados/juicio_5ind/url_lugares.csv"
PROC_PREF = "resultados/tablas_lugares_max_prefiltro_2026-09-29/df_procesado_5lugares.pkl"
DIR = "experimentos/resultados/juicio_prefiltro_e2_t2"
LUGARES = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]
HOLDOUT = ["Cauca", "Chocó", "Cundinamarca"]
TAM_LOTE, K, SEMILLA = 40, 10, 20260930


def topk(urls, x):
    d = pd.DataFrame({"url": urls, "x": x})
    d = d[d["x"] > 0].sort_values(["x", "url"], ascending=[False, True])
    return list(zip(d["url"].head(K), d["x"].head(K)))


def main():
    dl = os.path.join(DIR, "lotes")
    if os.path.isdir(dl) and os.listdir(dl):
        sys.exit(f"{dl} ya tiene contenido: no se sobrescribe")
    tok = C.cargar_tokenizer()
    rx, hip = T2.LISTAS[IND], T2.HIPOTESIS[IND]
    # ---- lugares
    cl = pd.read_pickle(CORPUS_L).reset_index(drop=True)
    a = pd.read_pickle(PROC_PREF).reset_index(drop=True)
    assert (a["url"].values == cl["url"].values).all()
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
    print("url en lugares y holdout a la vez:", len(set(cl["url"]) & set(ho["url"])))

    e, n = d[f"ent_{IND}"].values.astype(float), d[f"neu_{IND}"].values.astype(float)
    s_ho = np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)[m_ho]
    g_l = np.array(C.compuerta(C.premisa_visible_prod(txt_l, tok, hip), rx))
    g_h = np.array(C.compuerta(C.premisa_visible_prod(txt_h, tok, hip), rx))
    s_l = a[IND].astype(float).values
    print(f"{IND}: compuerta abre {g_l.mean():.1%} lugares, {g_h.mean():.1%} holdout")
    lugares = []
    for l in LUGARES:
        mk = cl["url"].isin(set(lug.loc[lug["lugar"] == l, "url"])).values
        lugares.append((l, cl["url"].values[mk], s_l[mk], g_l[mk]))
    for dep in HOLDOUT:
        mk = (ho["departamento"].values == dep)
        lugares.append((dep, ho["url"].values[mk], s_ho[mk], g_h[mk]))

    filas, kinfo = [], []
    for l, urls, s, g in lugares:
        t1 = {u: (r, x) for r, (u, x) in enumerate(topk(urls, s), 1)}
        t8 = {u: (r, x) for r, (u, x) in enumerate(topk(urls, s * g), 1)}
        sd, gd = dict(zip(urls, s)), dict(zip(urls, g))
        kinfo.append((l, len(t1), len(t8), len(set(t1) | set(t8))))
        for u in sorted(set(t1) | set(t8)):
            filas.append({"indicador": IND, "lugar": l, "url": u, "en_topk_v01": u in t1, "en_topk_v08": u in t8,
                          "puntaje_v01": sd[u], "puntaje_v08": sd[u] * gd[u],
                          "rango": min(t1.get(u, (99,))[0], t8.get(u, (99,))[0]),
                          "rango_v01": t1.get(u, (np.nan,))[0], "rango_v08": t8.get(u, (np.nan,))[0]})
    pool = pd.DataFrame(filas)
    os.makedirs(DIR, exist_ok=True)
    pool.to_csv(os.path.join(DIR, "pool.csv"), index=False)
    print("lugar, k_v01, k_v08, url aportadas:", kinfo)

    urls = np.array(sorted(set(pool["url"])))
    urls = urls[np.random.default_rng(SEMILLA).permutation(len(urls))]
    mapa = pd.DataFrame({"id": [f"t{i:04d}" for i in range(len(urls))], "url": urls})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)

    txt = dict(zip(cl["url"], txt_l))
    txt.update(dict(zip(ho["url"], txt_h)))
    prem = C.premisa_visible_prod([txt[u] for u in urls], tok, hip)
    os.makedirs(dl, exist_ok=True)
    nl, lineas = 0, 0
    for nl, ini in enumerate(range(0, len(mapa), TAM_LOTE), 1):
        with open(os.path.join(dl, f"lote_{nl:02d}.jsonl"), "w", encoding="utf-8") as f:
            for i in range(ini, min(ini + TAM_LOTE, len(mapa))):
                assert prem[i].strip(), mapa["url"].iloc[i]
                f.write(json.dumps({"id": mapa["id"].iloc[i], "premisa": prem[i]}, ensure_ascii=False) + "\n")
                lineas += 1
    for sub in ("etiquetas_e", "etiquetas_f"):
        os.makedirs(os.path.join(DIR, sub), exist_ok=True)
        open(os.path.join(DIR, sub, ".gitkeep"), "a").close()

    # ---- chequeos
    assert lineas == len(mapa) == len(set(pool["url"]))
    assert mapa["url"].is_unique and set(mapa["url"]) == set(pool["url"])
    assert all(p.strip() for p in prem)
    for l, urls_l, s, g in lugares[:4]:   # V01 de los 4 lugares == top-k de produccion (pkl), recalculado aparte
        ref = a[a["url"].isin(urls_l)].copy()
        ref = ref[ref[IND].astype(float) > 0].sort_values([IND, "url"], ascending=[False, True]).head(K)
        got = set(pool.loc[(pool["lugar"] == l) & pool["en_topk_v01"], "url"])
        assert got == set(ref["url"]), l
    print(f"CHEQUEOS OK: {len(mapa)} url unicas, {nl} lotes, {lineas} lineas")


if __name__ == "__main__":
    main()
