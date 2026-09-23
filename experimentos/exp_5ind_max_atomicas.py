"""
F2 del plan 5ind MAX (experimentos/PREREG_5ind_MAX.md): puntua con NLI todas las
hipotesis atomicas, gemelas absurdas, absurdo total y las 4 nulas de calibracion sobre el
corpus de trabajo (1.647 articulos, premisa = solo `texto`, max_length=512, igual que
produccion).

Regla 8: guarda ent_, neu_, con_ SIN enmascarar; todo lo demas se calcula offline.
Checkpoint por hipotesis: si se corta, se retoma donde quedo.

Ejecutar desde la raiz del worktree:  python experimentos/exp_5ind_max_atomicas.py
Salida: datos/scores/scores_5ind_atomicas_lugares.pkl
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipotesis_5ind_max as H  # noqa: E402
from nli_core import NLIScorer  # noqa: E402

CORPUS = "datos/corpus/df_corpus_5lugares.pkl"
SALIDA = "datos/scores/scores_5ind_atomicas_lugares.pkl"
CHECKPOINT = "datos/scores/scores_5ind_atomicas_lugares.parcial.pkl"


def main():
    df = pd.read_pickle(CORPUS).reset_index(drop=True)
    textos = df["texto"].fillna("").astype(str).tolist()
    hips = H.hipotesis_unicas()
    print(f"{len(textos)} articulos x {len(hips)} hipotesis")

    out = {"url": df["url"].values}
    if os.path.exists(CHECKPOINT):
        cp = pd.read_pickle(CHECKPOINT)
        if len(cp) == len(df) and (cp["url"].values == df["url"].values).all():
            out = {c: cp[c].values for c in cp.columns}
            print(f"checkpoint: {sum(c.startswith('ent_') for c in out)} hipotesis ya hechas")

    scorer = NLIScorer(verbose=False)
    t0 = time.time()
    pendientes = [k for k in hips if f"ent_{k}" not in out]
    for i, k in enumerate(pendientes, 1):
        p = scorer.score(textos, hips[k], batch_size=32, max_length=512, devolver_todo=True)
        out[f"ent_{k}"] = np.asarray(p["entailment"], dtype=np.float32)
        out[f"neu_{k}"] = np.asarray(p["neutral"], dtype=np.float32)
        out[f"con_{k}"] = np.asarray(p["contradiction"], dtype=np.float32)
        pd.DataFrame(out).to_pickle(CHECKPOINT)
        dt = time.time() - t0
        print(f"[{i}/{len(pendientes)}] {k}  {dt/60:.1f} min, faltan ~{dt/i*(len(pendientes)-i)/60:.0f} min",
              flush=True)

    res = pd.DataFrame(out)
    nulas = [f"ent_NULA_CAL_{i}" for i in range(len(H.NULAS_CALIBRACION))]
    res["sesgo"] = res[nulas].mean(axis=1)  # regla 4: solo las 4 de calibracion
    res.to_pickle(SALIDA)
    os.remove(CHECKPOINT)
    print(f"OK -> {SALIDA} {res.shape}")


if __name__ == "__main__":
    main()
