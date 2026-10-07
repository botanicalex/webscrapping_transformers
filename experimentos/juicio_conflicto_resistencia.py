"""
Jueces (proxy de plata) para conflicto_territorial y resistencia_territorial (PREREG §Jueces).

  python experimentos/juicio_conflicto_resistencia.py lotes <corpus> C01,C05,...,R03,...   # V2 y JEFE siempre entran
  python experimentos/juicio_conflicto_resistencia.py consolidar <corpus>

Pool: el artículo MAX (corregido) de cada departamento para cada candidata elegida y para V2 y JEFE de cada
indicador (experimentos/resultados/top_por_depto_<corpus>.csv). Cada artículo único se juzga UNA vez para AMBOS
indicadores. Ceguera: el lote trae id opaco + premisa visible (recorte de src/Transformer_optimo.premisa_visible con la
frase más larga, la del jefe de resistencia: el recorte más corto). Ni candidata, ni score, ni departamento, ni título.
DIR lleva sufijo _<corpus> salvo en la submuestra. Mapa id -> idx_corpus en <DIR>/mapa_ids.csv, fuera de lotes/.
Etiquetas: <DIR>/etiquetas_a/*.jsonl y <DIR>/etiquetas_b/*.jsonl, una línea por artículo:
  {"id": "a0001", "conflicto": ["SI|NO|DUDOSO", "cita"], "resistencia": ["SI|NO|DUDOSO", "cita"]}
"""
import json
import os
import sys

import numpy as np
import pandas as pd

DIR = "experimentos/resultados/juicio_conflicto_resistencia"
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
SEMILLA, TAM_LOTE = 20261007, 30
FRASE_RECORTE = ("Una comunidad realiza acciones para defender su territorio frente a proyectos, "
                 "intervenciones o decisiones externas.")
IND = {"conflicto_territorial": "conflicto", "resistencia_territorial": "resistencia"}
VALORES = {"SI", "NO", "DUDOSO"}


def lotes(corpus, ids):
    top = pd.read_csv(f"experimentos/resultados/top_por_depto_{corpus}.csv")
    elegidos = set(ids) | {"V2", "JEFE"}
    pool = top[top["id"].isin(elegidos)]
    os.makedirs(os.path.join(DIR, "lotes"), exist_ok=True)
    pool.to_csv(os.path.join(DIR, "pool.csv"), index=False)
    idxs = np.array(sorted(pool["idx_corpus"].unique()))
    idxs = idxs[np.random.default_rng(SEMILLA).permutation(len(idxs))]
    mapa = pd.DataFrame({"id": [f"a{i:04d}" for i in range(len(idxs))], "idx_corpus": idxs})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)

    from transformers import AutoTokenizer
    sys.path.insert(0, "src")
    from Transformer_optimo import premisa_visible  # noqa: E402
    sys.path.insert(0, "experimentos")
    from nli_core import MODELO_NLI, _ruta_modelo_local  # noqa: E402
    tok = AutoTokenizer.from_pretrained(_ruta_modelo_local(MODELO_NLI))
    corp = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    prem = premisa_visible(corp["texto"].fillna("").astype(str).iloc[idxs].tolist(), tok, FRASE_RECORTE)
    n = 0
    for n, ini in enumerate(range(0, len(mapa), TAM_LOTE), 1):
        with open(os.path.join(DIR, "lotes", f"lote_{n:02d}.jsonl"), "w", encoding="utf-8") as f:
            for j in range(ini, min(ini + TAM_LOTE, len(mapa))):
                f.write(json.dumps({"id": mapa["id"][j], "premisa": prem[j]}, ensure_ascii=False) + "\n")
    print(f"{len(pool)} filas de pool, {len(mapa)} artículos únicos -> {n} lotes en {DIR}/lotes")


def _leer(carpeta):
    filas = []
    d = os.path.join(DIR, carpeta)
    for fn in sorted(os.listdir(d)):
        for linea in open(os.path.join(d, fn), encoding="utf-8"):
            if linea.strip():
                o = json.loads(linea)
                fila = {"id": o["id"]}
                for corto in IND.values():
                    v = o[corto][0].strip().upper().replace("SÍ", "SI")
                    assert v in VALORES, (fn, o["id"], corto, v)
                    fila[corto] = v
                filas.append(fila)
    return pd.DataFrame(filas).drop_duplicates("id").set_index("id")


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float("nan") if pe == 1 else float((po - pe) / (1 - pe))


def consolidar(corpus):
    mapa = pd.read_csv(os.path.join(DIR, "mapa_ids.csv"))
    A, B = _leer("etiquetas_a"), _leer("etiquetas_b")
    faltan = (set(mapa["id"]) - set(A.index)) | (set(mapa["id"]) - set(B.index))
    assert not faltan, f"faltan {len(faltan)} ids: {sorted(faltan)[:5]}"
    pool = pd.read_csv(os.path.join(DIR, "pool.csv")).merge(mapa, on="idx_corpus")
    filas = []
    for ind, corto in IND.items():
        a = A.loc[mapa["id"], corto] == "SI"
        b = B.loc[mapa["id"], corto] == "SI"
        print(f"{ind}: SI_a={a.sum()} SI_b={b.sum()} kappa={kappa(a, b):.2f} (n={len(mapa)})")
        g = pool[pool["indicador"] == ind].copy()
        g["a"] = A.loc[g["id_y"], corto].values
        g["b"] = B.loc[g["id_y"], corto].values
        g["ambos_si"] = (g["a"] == "SI") & (g["b"] == "SI")
        g["algun_si"] = (g["a"] == "SI") | (g["b"] == "SI")
        for cid, h in g.groupby("id_x"):
            filas.append({"indicador": ind, "id": cid, "n_deptos": len(h),
                          "precision_ambos": h["ambos_si"].mean(), "precision_alguno": h["algun_si"].mean(),
                          "desacuerdos": int((h["a"] != h["b"]).sum())})
    R = pd.DataFrame(filas).sort_values(["indicador", "precision_ambos"], ascending=[True, False])
    R.to_csv(os.path.join(DIR, f"precision_{corpus}.csv"), index=False)
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    if sys.argv[2] != "submuestra":
        DIR = f"{DIR}_{sys.argv[2]}"
    if sys.argv[1] == "lotes":
        lotes(sys.argv[2], sys.argv[3].split(","))
    else:
        consolidar(sys.argv[2])
