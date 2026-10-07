"""
Cola única de GPU para las candidatas de conflicto_territorial y resistencia_territorial
(relevo 12, §6). Puntúa en serie cada candidata (frase + su nula del mismo formato) y GUARDA
CADA CANDIDATA EN CUANTO TERMINA (un pkl por candidata). Si el pkl ya existe, la salta (regla 8):
la cola se puede cortar y relanzar sin repetir GPU.

Corpus:
  submuestra  estratificada por departamento: min(n_depto, 50) artículos por departamento del
              nacional, semilla 20261007. Índices en experimentos/resultados/submuestra_cribado.csv
              (se crea la primera vez; después se lee, nunca se regenera).
  nacional    los 11.439 artículos.
  lugares     df_corpus_5lugares.pkl; el sesgo (media de V2.NULAS_CALIBRACION) se calcula una vez
              y se guarda en el mismo directorio (como producción). NULA_TEST jamás entra al sesgo.
Premisa = columna `texto` (la de producción). ent/neu sin enmascarar.

  python experimentos/cola_gpu_conflicto_resistencia.py <corpus> <candidatas.json> [<más.json> ...] [--ids C01,R03]
Salida: datos/scores/hip_conflicto_resistencia/<corpus>/<id>.pkl  (dict: id, frase, nula, ent, neu, ent_nula, neu_nula)
"""
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_v2 as V2  # noqa: E402

CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
CORPUS_LUG = "datos/corpus/df_corpus_5lugares.pkl"
BASE_LUG = "datos/scores/df_procesado_baseline_v2.pkl"
SUBMUESTRA = "experimentos/resultados/submuestra_cribado.csv"
SALIDA = "datos/scores/hip_conflicto_resistencia"
SEMILLA, POR_DEPTO = 20261007, 50


def submuestra(df):
    if os.path.exists(SUBMUESTRA):
        return pd.read_csv(SUBMUESTRA)["idx"].values
    dep = df["departamento"].astype(str).str.strip()
    idx = []
    for d in sorted(dep.unique()):
        ii = np.flatnonzero(dep.values == d)
        rng = np.random.default_rng(SEMILLA + sum(map(ord, d)))
        idx.extend(sorted(rng.choice(ii, size=min(len(ii), POR_DEPTO), replace=False)))
    out = pd.DataFrame({"idx": idx, "departamento": dep.values[idx], "titulo": df["titulo"].values[idx]})
    out.to_csv(SUBMUESTRA, index=False)
    return out["idx"].values


def main():
    corpus = sys.argv[1]
    assert corpus in ("submuestra", "nacional", "lugares"), corpus
    ids = None
    archivos = [a for a in sys.argv[2:] if a.endswith(".json")]
    if "--ids" in sys.argv:
        ids = set(sys.argv[sys.argv.index("--ids") + 1].split(","))
    cands = [c for a in archivos for c in json.load(open(a, encoding="utf-8"))]
    if ids:
        cands = [c for c in cands if c["id"] in ids]
    assert len({c["id"] for c in cands}) == len(cands), "ids repetidos"

    df = pd.read_pickle(CORPUS_LUG if corpus == "lugares" else CORPUS_NAC).reset_index(drop=True)
    if corpus == "submuestra":
        df = df.iloc[submuestra(df)].reset_index(drop=True)
    prem = df["texto"].fillna("").astype(str).tolist()
    carpeta = os.path.join(SALIDA, corpus)
    os.makedirs(carpeta, exist_ok=True)
    pendientes = [c for c in cands if not os.path.exists(os.path.join(carpeta, f"{c['id']}.pkl"))]
    print(f"corpus={corpus} n={len(prem)} candidatas={len(cands)} pendientes={len(pendientes)}", flush=True)
    if not pendientes and not (corpus == "lugares" and not os.path.exists(os.path.join(carpeta, "_sesgo.pkl"))):
        return

    from nli_core import NLIScorer, verificar_contra_produccion_v2
    s = NLIScorer()
    if not verificar_contra_produccion_v2(s, BASE_LUG, "presencia_grupos_armados",
                                          V2.TODAS["presencia_grupos_armados"]):
        sys.exit("Paso 0 FALLA: nli_core se desvió de producción. Se detiene.")

    if corpus == "lugares" and not os.path.exists(os.path.join(carpeta, "_sesgo.pkl")):
        sesgo = np.mean([np.asarray(s.score(prem, h), dtype=float) for h in V2.NULAS_CALIBRACION], axis=0)
        with open(os.path.join(carpeta, "_sesgo.pkl"), "wb") as f:
            pickle.dump({"sesgo": sesgo, "departamento": df["departamento"].astype(str).str.strip().values,
                         "titulo": df["titulo"].values}, f)

    for c in pendientes:
        t0 = time.time()
        p = s.score(prem, c["frase"], devolver_todo=True)
        n = s.score(prem, c["nula"], devolver_todo=True)
        r = {"id": c["id"], "frase": c["frase"], "nula": c["nula"], "corpus": corpus, "n": len(prem),
             "ent": np.asarray(p["entailment"], dtype=float), "neu": np.asarray(p["neutral"], dtype=float),
             "ent_nula": np.asarray(n["entailment"], dtype=float), "neu_nula": np.asarray(n["neutral"], dtype=float)}
        tmp = os.path.join(carpeta, f"{c['id']}.pkl.tmp")
        with open(tmp, "wb") as f:
            pickle.dump(r, f)
        os.replace(tmp, os.path.join(carpeta, f"{c['id']}.pkl"))
        print(f"[{corpus}] {c['id']} listo en {time.time() - t0:.0f}s | {c['frase']}", flush=True)


if __name__ == "__main__":
    main()
