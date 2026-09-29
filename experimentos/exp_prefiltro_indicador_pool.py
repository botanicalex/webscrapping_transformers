"""
Fase 2 del pre-filtro por indicador (experimentos/PREREG_prefiltro_indicador.md §7): pool del holdout y
lotes ciegos para los jueces. Solo CPU; no toca src/ ni sobrescribe nada existente.

Pool: para `conflicto_territorial` y `desplazamiento_forzado` y cada departamento del holdout (Cauca, Choco,
Cundinamarca), el top-k de V01 (sin filtro) y el top-k de V08 (V01 x compuerta REGEX_F5 del indicador sobre la
premisa visible nacional), k = min(10, nº con puntaje > 0), orden por puntaje descendente y url ascendente,
sobre TODOS los articulos del departamento. Se juzgan solo los no juzgados todavia (fuera de los 940 de la
referencia) mas 10 ya juzgados del holdout como control entre rondas.

Lotes: url unicas de pool nuevo + control, barajadas con numpy.random.default_rng(20260928) (el mismo
generador elige antes el control), ids opacos p0000..., JSONL de <= 40 lineas {"id","premisa"} con la premisa
de juicio_5ind_holdout/premisas_visibles_nacional.pkl, en experimentos/resultados/juicio_prefiltro_indicador/lotes/.
El mapa id -> url (con el origen) y el pool quedan fuera de esa carpeta: los jueces no los leen.

  PYTHONIOENCODING=utf-8 python experimentos/exp_prefiltro_indicador_pool.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
from exp_5ind_max_r2_metricas import referencia  # noqa: E402

CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
PREM_NAC = "experimentos/resultados/juicio_5ind_holdout/premisas_visibles_nacional.pkl"
DIR = "experimentos/resultados/juicio_prefiltro_indicador"
HOLDOUT = ["Cauca", "Chocó", "Cundinamarca"]
INDS = ["conflicto_territorial", "desplazamiento_forzado"]
SEMILLA = 20260928
TAM_LOTE = 40
N_CONTROL = 10
K = 10


def main():
    if os.path.exists(os.path.join(DIR, "lotes")) and os.listdir(os.path.join(DIR, "lotes")):
        sys.exit(f"{DIR}/lotes ya tiene contenido: no se sobrescribe")
    corpus = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(corpus) == len(d) == 11439
    assert (corpus["titulo"].values == d["titulo"].values).all() and (corpus["departamento"].values == d["departamento"].values).all()
    prem = pd.read_pickle(PREM_NAC)
    assert prem.index.is_unique and set(corpus["url"]) <= set(prem.index)
    prem_c = prem.loc[corpus["url"]].values
    sesgo = d["sesgo"].values.astype(float)

    juzg = set(referencia()["url"])
    print(f"referencia: {len(juzg)} juzgados")

    filas = []
    for ind in INDS:
        e, n = d[f"ent_{ind}"].values.astype(float), d[f"neu_{ind}"].values.astype(float)
        s = np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)
        g = np.asarray(H.compuerta(prem_c, ind))
        print(f"{ind}: la compuerta abre en {g.mean():.1%} de los 11.439")
        for dep in HOLDOUT:
            m = (corpus["departamento"].values == dep)
            assert m.sum() > 0, dep
            for var, x in (("V01", s), ("V08", s * g)):
                sub = pd.DataFrame({"url": corpus["url"].values[m], "x": x[m]})
                sub = sub[sub["x"] > 0].sort_values(["x", "url"], ascending=[False, True])
                top = sub.head(K)
                for r, u in enumerate(top["url"], 1):
                    filas.append({"url": u, "indicador": ind, "departamento": dep, "variante": var, "rango": r,
                                  "juzgado_previo": u in juzg})
    pool = pd.DataFrame(filas)
    os.makedirs(DIR, exist_ok=True)
    pool.to_csv(os.path.join(DIR, "pool.csv"), index=False)

    resumen = (pool.groupby(["indicador", "departamento", "variante"])
               .agg(k=("url", "size"), ya_juzgados=("juzgado_previo", "sum")).reset_index())
    resumen["nuevos"] = resumen["k"] - resumen["ya_juzgados"]
    print("\nTop-k por indicador x departamento x variante (k, ya juzgados, sin juzgar):")
    print(resumen.assign(indicador=resumen["indicador"].str[:14]).to_string(index=False))

    u_pool = set(pool["url"])
    nuevos = u_pool - juzg
    print(f"\nPool: {len(pool)} entradas, {len(u_pool)} url unicas; ya juzgadas {len(u_pool & juzg)}; "
          f"SIN JUZGAR {len(nuevos)}")

    # Control entre rondas: 10 ya juzgados de los departamentos del holdout (mismo generador que el barajado)
    en_holdout = set(corpus.loc[corpus["departamento"].isin(HOLDOUT), "url"])
    base = np.array(sorted(juzg & en_holdout))
    rng = np.random.default_rng(SEMILLA)
    control = set(base[rng.permutation(len(base))[:N_CONTROL]])
    print(f"Control: {len(control)} de {len(base)} juzgados del holdout")

    urls = np.array(sorted(nuevos | control))
    urls = urls[rng.permutation(len(urls))]
    mapa = pd.DataFrame({"id": [f"p{i:04d}" for i in range(len(urls))], "url": urls,
                         "origen": ["control" if u in control else "pool" for u in urls]})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)

    dl = os.path.join(DIR, "lotes")
    os.makedirs(dl, exist_ok=True)
    n = 0
    for n, ini in enumerate(range(0, len(mapa), TAM_LOTE), 1):
        with open(os.path.join(dl, f"lote_{n:02d}.jsonl"), "w", encoding="utf-8") as f:
            for i, u in zip(mapa["id"].iloc[ini: ini + TAM_LOTE], mapa["url"].iloc[ini: ini + TAM_LOTE]):
                p = prem[u]
                assert isinstance(p, str) and p.strip(), u
                f.write(json.dumps({"id": i, "premisa": p}, ensure_ascii=False) + "\n")
    for sub in ("etiquetas_a", "etiquetas_b"):
        os.makedirs(os.path.join(DIR, sub), exist_ok=True)
    print(f"\n{len(mapa)} articulos ({len(nuevos)} nuevos + {len(control)} control) -> {n} lotes de <= {TAM_LOTE} en {dl}")
    print(mapa["origen"].value_counts().to_string())


if __name__ == "__main__":
    main()
