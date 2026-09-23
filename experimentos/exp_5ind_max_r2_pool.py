"""
Fase A, paso 2, de la 2a ronda del plan 5ind MAX (experimentos/PREREG_5ind_MAX_r2.md §4, §5
y §7.2). Todo offline, sobre datos/scores/scores_5ind_r2_lugares.pkl (N1-N3 y gemelas) y
datos/scores/scores_5ind_atomicas_lugares.pkl (vigente, P1/P2 y gemelas, sesgo, absurdo total).

  python experimentos/exp_5ind_max_r2_pool.py lotes       # candidatas, pool, muestra, lotes
  python experimentos/exp_5ind_max_r2_pool.py consolidar  # etiquetas_a + etiquetas_b -> referencia

Score de cada frase = formula vigente s(h) = clip(clip(ent - sesgo, 0)*(1 - neu), 0, 1).
Pool TREC (§4): por indicador x lugar, top-15 (score > 0, desempate por URL) de la vigente y
las 5 candidatas; se juzga solo lo que no se juzgo en la ronda 1 (565 lugares + 94 holdout).
Muestra de exclusion (§5): premisa visible normalizada con REGEX_MUESTREO_EXCLUSION, en el
corpus nacional y en el de los 4 lugares; se juzgan las no juzgadas.
Control entre rondas (§7.2): 40 articulos ya juzgados en la ronda 1, al azar, ids nuevos.
Lotes ciegos: id opaco b0000... y premisa visible, barajados con semilla 20260923; el mapa
id -> url (mapa_ids.csv) queda fuera de la carpeta de lotes.

Salidas (experimentos/resultados/juicio_5ind_r2/): candidatas_r2.pkl, pool.csv,
muestra_exclusion.csv, mapa_ids.csv, lotes/lote_NN.jsonl; con `consolidar`, referencia.csv.
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_5ind_max_r2 as R2  # noqa: E402
from exp_5ind_max_juicio import VALORES, kappa  # noqa: E402

R1_SCORES = "datos/scores/scores_5ind_atomicas_lugares.pkl"
R2_SCORES = "datos/scores/scores_5ind_r2_lugares.pkl"
DIR_R1 = "experimentos/resultados/juicio_5ind"
DIR_HO = "experimentos/resultados/juicio_5ind_holdout"
DIR = "experimentos/resultados/juicio_5ind_r2"
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
LUGARES = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]
CLAVES = ["vig"] + R2.CANDIDATAS
SEMILLA = 20260923
TAM_LOTE = 40
TOP_POOL = 15
N_CONTROL = 40


def s(ent, neu, sesgo):
    return np.clip(np.clip(ent.astype(float) - sesgo, 0, None) * (1 - neu.astype(float)), 0, 1)


def candidatas() -> pd.DataFrame:
    """url + <ind>__<clave> y <ind>__<clave>__abs para vig, N1-N3, P1, P2; ABSURDO_TOTAL."""
    r1, r2 = pd.read_pickle(R1_SCORES), pd.read_pickle(R2_SCORES)
    assert (r1["url"].values == r2["url"].values).all()
    sesgo = r1["sesgo"].values
    f1 = lambda col: s(r1[f"ent_{col}"].values, r1[f"neu_{col}"].values, sesgo)  # noqa: E731
    f2 = lambda col: s(r2[f"ent_{col}"].values, r2[f"neu_{col}"].values, sesgo)  # noqa: E731
    out = {"url": r1["url"].values, "ABSURDO_TOTAL": f1("ABSURDO_TOTAL")}
    for ind in H.INDICADORES_5:
        for k in CLAVES:
            if k[0] == "N":
                x, xa = f2(f"{ind}__{k}"), f2(f"{ind}__{k}_abs")
            else:  # vig, P1, P2: ronda 1
                c = k.lower()
                x, xa = f1(H.columna(ind, c)), f1(H.columna(ind, c + "_abs"))
            out[f"{ind}__{k}"], out[f"{ind}__{k}__abs"] = x, xa
    return pd.DataFrame(out)


def juzgados_r1() -> pd.DataFrame:
    """Referencia de la ronda 1 (565 lugares + 94 holdout), una fila por URL."""
    a = pd.read_csv(os.path.join(DIR_R1, "referencia.csv")).assign(ronda="r1_lugares")
    b = pd.read_csv(os.path.join(DIR_HO, "referencia.csv")).assign(ronda="r1_holdout")
    j = pd.concat([a, b], ignore_index=True)
    assert j["url"].is_unique, "URL juzgada dos veces en la ronda 1"
    return j


def muestra_exclusion(prem_l: pd.Series, prem_n: pd.Series, juzg: set, lug: pd.DataFrame) -> pd.DataFrame:
    pat = re.compile(R2.REGEX_MUESTREO_EXCLUSION)
    hit = lambda p: {u for u, t in p.items() if pat.search(H.normalizar(t))}  # noqa: E731
    urls = sorted(hit(prem_l) | hit(prem_n))
    dep = pd.read_pickle(CORPUS_NAC).set_index("url")["departamento"]
    en_lug = set(lug["url"])
    m = pd.DataFrame({"url": urls})
    m["juzgada_r1"] = m["url"].isin(juzg)
    m["en_lugares"] = m["url"].isin(en_lug)
    m["departamento"] = m["url"].map(dep)
    return m


def lotes():
    os.makedirs(DIR, exist_ok=True)
    cand = candidatas()
    cand.to_pickle(os.path.join(DIR, "candidatas_r2.pkl"))
    lug = pd.read_csv(os.path.join(DIR_R1, "url_lugares.csv"))
    j1 = juzgados_r1()
    juzg = set(j1["url"])

    # Pool TREC (§4).
    pool = []
    for lugar in LUGARES:
        sub = cand[cand["url"].isin(lug.loc[lug["lugar"] == lugar, "url"])]
        for ind in H.INDICADORES_5:
            for k in CLAVES:
                c = f"{ind}__{k}"
                top = sub[sub[c] > 0].sort_values([c, "url"], ascending=[False, True]).head(TOP_POOL)
                for r, u in enumerate(top["url"], 1):
                    pool.append({"url": u, "indicador": ind, "lugar": lugar, "candidata": k, "rango": r})
    pool = pd.DataFrame(pool)
    pool.to_csv(os.path.join(DIR, "pool.csv"), index=False)
    pool_r1 = set(pd.read_csv(os.path.join(DIR_R1, "pool.csv"))["url"])
    u_pool = set(pool["url"])
    nuevos_pool = u_pool - juzg
    print(f"Pool r2: {len(u_pool)} URL unicas ({len(pool)} entradas); ya juzgadas {len(u_pool & juzg)} "
          f"(en pool r1 {len(u_pool & pool_r1)}); nuevas {len(nuevos_pool)}")

    # Muestra de exclusion (§5).
    prem_l = pd.read_pickle(os.path.join(DIR_R1, "premisas_visibles.pkl"))
    prem_n = pd.read_pickle(os.path.join(DIR_HO, "premisas_visibles_nacional.pkl"))
    m = muestra_exclusion(prem_l, prem_n, juzg, lug)
    m.to_csv(os.path.join(DIR, "muestra_exclusion.csv"), index=False)
    nuevos_m = set(m.loc[~m["juzgada_r1"], "url"])
    ho = m["departamento"].isin(["Cauca", "Choco", "Chocó", "Cundinamarca"])
    print(f"Muestra de exclusion: {len(m)} URL con la regex; {int(m['juzgada_r1'].sum())} ya juzgadas; "
          f"{len(nuevos_m)} sin juzgar (pre-registro: 237 / 206). Sin juzgar: en los 4 lugares "
          f"{int((~m['juzgada_r1'] & m['en_lugares']).sum())}, en el holdout {int((~m['juzgada_r1'] & ho).sum())}; "
          f"tambien en el pool r2 {len(nuevos_m & nuevos_pool)}")

    # Control entre rondas (§7.2) y lotes ciegos.
    rng = np.random.default_rng(SEMILLA)
    base = np.array(sorted(juzg))
    control = set(base[rng.permutation(len(base))[:N_CONTROL]])
    nuevos = nuevos_pool | nuevos_m
    urls = np.array(sorted(nuevos | control))
    urls = urls[rng.permutation(len(urls))]
    origen = lambda u: ("control" if u in control else  # noqa: E731
                        "+".join(o for o, S in (("pool", nuevos_pool), ("muestra", nuevos_m)) if u in S))
    mapa = pd.DataFrame({"id": [f"b{i:04d}" for i in range(len(urls))], "url": urls,
                         "origen": [origen(u) for u in urls]})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)
    d = os.path.join(DIR, "lotes")
    os.makedirs(d, exist_ok=True)
    n = 0
    for n, ini in enumerate(range(0, len(mapa), TAM_LOTE), 1):
        with open(os.path.join(d, f"lote_{n:02d}.jsonl"), "w", encoding="utf-8") as f:
            for u, i in zip(mapa["url"].iloc[ini: ini + TAM_LOTE], mapa["id"].iloc[ini: ini + TAM_LOTE]):
                p = prem_l[u] if u in prem_l.index else prem_n[u]
                f.write(json.dumps({"id": i, "premisa": p}, ensure_ascii=False) + "\n")
    print(f"{len(mapa)} articulos ({len(nuevos)} nuevos + {len(control)} control) -> {n} lotes de "
          f"<= {TAM_LOTE} en {d}")
    print(mapa["origen"].value_counts().to_string())


def _leer(carpeta: str) -> pd.DataFrame:
    filas = []
    d = os.path.join(DIR, carpeta)
    for fn in sorted(os.listdir(d)):
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    o = json.loads(linea)
                    fila = {"id": o["id"]}
                    for ind in H.INDICADORES_5:
                        v = o[ind][0].strip().upper().replace("SÍ", "SI")
                        assert v in VALORES, (fn, o["id"], ind, v)
                        fila[ind] = v
                    filas.append(fila)
    return pd.DataFrame(filas).drop_duplicates("id").set_index("id")


def consolidar():
    mapa = pd.read_csv(os.path.join(DIR, "mapa_ids.csv")).set_index("id")
    A, B = _leer("etiquetas_a"), _leer("etiquetas_b")
    faltan = set(mapa.index) - set(A.index) | set(mapa.index) - set(B.index)
    assert not faltan, f"faltan {len(faltan)} ids: {sorted(faltan)[:5]}"
    ref = pd.DataFrame({"url": mapa["url"], "origen": mapa["origen"]})
    for ind in H.INDICADORES_5:
        sa, sb = A.loc[mapa.index, ind] == "SI", B.loc[mapa.index, ind] == "SI"
        ref[ind] = (sa & sb).astype(int).values
        ref[ind + "__a"] = A.loc[mapa.index, ind].values
        ref[ind + "__b"] = B.loc[mapa.index, ind].values
    ref.reset_index().to_csv(os.path.join(DIR, "referencia.csv"), index=False)

    nuevos = ref[ref["origen"] != "control"]
    ctl = ref[ref["origen"] == "control"]
    j1 = juzgados_r1().set_index("url").loc[ctl["url"]]
    print(f"{len(nuevos)} nuevos + {len(ctl)} control -> {DIR}/referencia.csv")
    print(f"{'indicador':34s} {'SI_a':>5s} {'SI_b':>5s} {'SI/SI':>6s} {'kappa':>6s} | control: "
          f"{'acuerdo':>7s} {'SI/SI r1':>8s} {'SI/SI r2':>8s}")
    for ind in H.INDICADORES_5:
        sa, sb = nuevos[ind + "__a"] == "SI", nuevos[ind + "__b"] == "SI"
        acu = float((ctl[ind].values == j1[ind].values).mean())
        print(f"{ind:34s} {sa.sum():5d} {sb.sum():5d} {nuevos[ind].sum():6d} {kappa(sa, sb):6.2f} | "
              f"{acu:7.2f} {int(j1[ind].sum()):8d} {int(ctl[ind].sum()):8d}")


if __name__ == "__main__":
    {"lotes": lotes, "consolidar": consolidar}[sys.argv[1]]()
