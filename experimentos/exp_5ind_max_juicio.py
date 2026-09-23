"""
F4 del plan 5ind MAX (experimentos/PREREG_5ind_MAX.md §4): lotes ciegos para los jueces
LLM y consolidacion de sus etiquetas.

  python experimentos/exp_5ind_max_juicio.py lotes       # arma lotes/lote_NN.jsonl
  python experimentos/exp_5ind_max_juicio.py consolidar  # etiquetas_a + etiquetas_b -> referencia

Ceguera: el lote solo trae un id opaco y la premisa visible, en orden barajado con semilla
fija. El mapa id -> url vive en mapa_ids.csv, fuera de la carpeta de lotes; los jueces no
lo leen. Ni variante, ni score, ni lugar, ni titulo.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402

DIR = "experimentos/resultados/juicio_5ind"
SEMILLA = 20260922
TAM_LOTE = 40
VALORES = {"SI", "NO", "DUDOSO"}


def lotes():
    pool = pd.read_csv(os.path.join(DIR, "pool.csv"))
    prem = pd.read_pickle(os.path.join(DIR, "premisas_visibles.pkl"))
    urls = np.array(sorted(pool["url"].unique()))
    rng = np.random.default_rng(SEMILLA)
    urls = urls[rng.permutation(len(urls))]
    mapa = pd.DataFrame({"id": [f"a{i:04d}" for i in range(len(urls))], "url": urls})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)
    d = os.path.join(DIR, "lotes")
    os.makedirs(d, exist_ok=True)
    n = 0
    for n, ini in enumerate(range(0, len(mapa), TAM_LOTE), 1):
        with open(os.path.join(d, f"lote_{n:02d}.jsonl"), "w", encoding="utf-8") as f:
            for _, r in mapa.iloc[ini: ini + TAM_LOTE].iterrows():
                f.write(json.dumps({"id": r["id"], "premisa": prem[r["url"]]}, ensure_ascii=False) + "\n")
    print(f"{len(mapa)} articulos -> {n} lotes de <= {TAM_LOTE} en {d}")


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
                        fila[ind + "__cita"] = o[ind][1]
                    filas.append(fila)
    return pd.DataFrame(filas).drop_duplicates("id").set_index("id")


def kappa(a, b) -> float:
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float("nan") if pe == 1 else float((po - pe) / (1 - pe))


def consolidar():
    mapa = pd.read_csv(os.path.join(DIR, "mapa_ids.csv")).set_index("id")
    A, B = _leer("etiquetas_a"), _leer("etiquetas_b")
    faltan = set(mapa.index) - set(A.index) | set(mapa.index) - set(B.index)
    assert not faltan, f"faltan {len(faltan)} ids: {sorted(faltan)[:5]}"
    ref = pd.DataFrame({"url": mapa["url"]})
    print(f"{'indicador':34s} {'SI_a':>5s} {'SI_b':>5s} {'SI/SI':>6s} {'kappa':>6s}")
    for ind in H.INDICADORES_5:
        sa, sb = A.loc[mapa.index, ind] == "SI", B.loc[mapa.index, ind] == "SI"
        ref[ind] = (sa & sb).astype(int).values
        ref[ind + "__a"] = A.loc[mapa.index, ind].values
        ref[ind + "__b"] = B.loc[mapa.index, ind].values
        k = kappa(sa, sb)
        print(f"{ind:34s} {sa.sum():5d} {sb.sum():5d} {ref[ind].sum():6d} {k:6.2f}"
              f"{'  REFERENCIA DEBIL' if k < 0.4 else ''}")
    ref.reset_index().to_csv(os.path.join(DIR, "referencia.csv"), index=False)
    print(f"-> {DIR}/referencia.csv ({len(ref)} articulos)")


if __name__ == "__main__":
    {"lotes": lotes, "consolidar": consolidar}[sys.argv[1]]()
