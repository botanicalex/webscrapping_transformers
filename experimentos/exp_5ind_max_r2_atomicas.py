"""
Fase A, paso 1, de la 2a ronda del plan 5ind MAX (experimentos/PREREG_5ind_MAX_r2.md §7.1):
puntua con NLI las 35 hipotesis de hipotesis_gpu() (15 candidatas N, sus 15 gemelas y las 5
vigentes como control de sanidad) sobre el corpus de los 4 lugares (1.647 articulos, premisa =
solo `texto`, max_length=512, igual que produccion).

Regla 8: guarda ent_, neu_, con_ SIN enmascarar; todo lo demas se calcula offline.
Checkpoint por hipotesis: si se corta, se retoma donde quedo.
Las 5 vigentes se puntuan primero: si no reproducen scores_5ind_atomicas_lugares.pkl con
max|dif| < 1e-4, se para ahi (sin gastar GPU en las otras 30).

Ejecutar desde la raiz del worktree:  python experimentos/exp_5ind_max_r2_atomicas.py
Salida: datos/scores/scores_5ind_r2_lugares.pkl
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_5ind_max_r2 as R2  # noqa: E402
from nli_core import NLIScorer  # noqa: E402

CORPUS = "datos/corpus/df_corpus_5lugares.pkl"
RONDA1 = "datos/scores/scores_5ind_atomicas_lugares.pkl"
SALIDA = "datos/scores/scores_5ind_r2_lugares.pkl"
CHECKPOINT = "datos/scores/scores_5ind_r2_lugares.parcial.pkl"
TOL = 1e-4


def sanidad(out: dict) -> float:
    """max|dif| de ent/neu/con de las 5 vigentes frente a la ronda 1."""
    r1 = pd.read_pickle(RONDA1)
    assert (r1["url"].values == out["url"]).all()
    dif = 0.0
    for ind in H.INDICADORES_5:
        c1 = H.columna(ind, "vig")
        for p in ("ent", "neu", "con"):
            dif = max(dif, float(np.abs(out[f"{p}_{ind}__vig"] - r1[f"{p}_{c1}"].values).max()))
    return dif


def main():
    df = pd.read_pickle(CORPUS).reset_index(drop=True)
    textos = df["texto"].fillna("").astype(str).tolist()
    hips = R2.hipotesis_gpu()
    # Vigentes primero, para la sanidad temprana.
    orden = sorted(hips, key=lambda k: (not k.endswith("__vig"), list(hips).index(k)))
    print(f"{len(textos)} articulos x {len(hips)} hipotesis")

    out = {"url": df["url"].values}
    if os.path.exists(CHECKPOINT):
        cp = pd.read_pickle(CHECKPOINT)
        if len(cp) == len(df) and (cp["url"].values == df["url"].values).all():
            out = {c: cp[c].values for c in cp.columns}
            print(f"checkpoint: {sum(c.startswith('ent_') for c in out)} hipotesis ya hechas")

    scorer = NLIScorer(verbose=False)
    print(f"tokens de la hipotesis mas larga: {R2.comprobar_tokens(scorer.tokenizer)} "
          f"(tope {R2.TOKENS_HIP_MAX})", flush=True)

    t0 = time.time()
    pendientes = [k for k in orden if f"ent_{k}" not in out]
    vig_hechas = False
    for i, k in enumerate(pendientes, 1):
        p = scorer.score(textos, hips[k], batch_size=32, max_length=512, devolver_todo=True)
        out[f"ent_{k}"] = np.asarray(p["entailment"], dtype=np.float32)
        out[f"neu_{k}"] = np.asarray(p["neutral"], dtype=np.float32)
        out[f"con_{k}"] = np.asarray(p["contradiction"], dtype=np.float32)
        pd.DataFrame(out).to_pickle(CHECKPOINT)
        dt = time.time() - t0
        print(f"[{i}/{len(pendientes)}] {k}  {dt/60:.1f} min, faltan ~{dt/i*(len(pendientes)-i)/60:.0f} min",
              flush=True)
        if not vig_hechas and all(f"ent_{ind}__vig" in out for ind in H.INDICADORES_5):
            vig_hechas = True
            d = sanidad(out)
            print(f"SANIDAD vigentes vs ronda 1: max|dif| = {d:.1e} {'OK' if d < TOL else 'FALLA'}", flush=True)
            if d >= TOL:
                sys.exit("PARADA: las vigentes no reproducen la ronda 1 (pre-registro r2 §7.1)")

    res = pd.DataFrame(out)
    d = sanidad(out)
    assert d < TOL, d
    res.to_pickle(SALIDA)
    os.remove(CHECKPOINT)
    print(f"SANIDAD final: max|dif| = {d:.1e} OK")
    print(f"OK -> {SALIDA} {res.shape}")


if __name__ == "__main__":
    main()
