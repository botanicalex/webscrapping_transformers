"""
F7 del plan 5ind MAX (experimentos/PREREG_5ind_MAX.md §2, §4 criterio 6), paso 1.

  python experimentos/exp_5ind_max_nacional.py gpu        # gemela de objeto absurdo de grupos armados
  python experimentos/exp_5ind_max_nacional.py premisas   # premisas visibles nacionales (CPU)

Solo se puntua lo que falta a escala nacional: `presencia_grupos_armados__vig_abs`
(«En este territorio hay presencia de osos polares.»). La vigente, el sesgo (4 nulas de
calibracion) y el absurdo total (= NULA_TEST) se reutilizan de
datos/scores/scores_v2_32deptos.pkl, que no trae `url` y se une por posicion con
datos/corpus/df_corpus_combinado_32deptos.pkl (verificado en F0).

Regla 8: ent_, neu_, con_ SIN enmascarar. Checkpoint por bloques de articulos.
Salidas:
  datos/scores/scores_5ind_atomicas_nacional.pkl
  experimentos/resultados/juicio_5ind_holdout/premisas_visibles_nacional.pkl  (url -> premisa)
"""
import os
import sys
import time

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402

CORPUS = "datos/corpus/df_corpus_combinado_32deptos.pkl"
SALIDA = "datos/scores/scores_5ind_atomicas_nacional.pkl"
CHECKPOINT = "datos/scores/scores_5ind_atomicas_nacional.parcial.pkl"
DIR = "experimentos/resultados/juicio_5ind_holdout"
CLAVES = ["presencia_grupos_armados__vig_abs"]
BLOQUE = 1024


def gpu():
    from nli_core import NLIScorer
    df = pd.read_pickle(CORPUS).reset_index(drop=True)
    textos = df["texto"].fillna("").astype(str).tolist()
    hips = H.hipotesis_unicas()
    out = {"url": df["url"].values, "departamento": df["departamento"].values}
    hechos = 0
    if os.path.exists(CHECKPOINT):
        cp = pd.read_pickle(CHECKPOINT)
        out.update({c: cp[c].values.copy() for c in cp.columns if c not in out})
        hechos = int((~np.isnan(out[f"ent_{CLAVES[-1]}"])).sum())
        print(f"checkpoint: {hechos} articulos ya hechos")
    for k in CLAVES:
        for p in ("ent_", "neu_", "con_"):
            out.setdefault(p + k, np.full(len(df), np.nan, dtype=np.float32))
    print(f"{len(textos)} articulos x {len(CLAVES)} hipotesis: {[hips[k] for k in CLAVES]}")

    scorer = NLIScorer(verbose=False)
    t0 = time.time()
    for ini in range(hechos, len(textos), BLOQUE):
        fin = min(ini + BLOQUE, len(textos))
        for k in CLAVES:
            p = scorer.score(textos[ini:fin], hips[k], batch_size=32, max_length=512, devolver_todo=True)
            out[f"ent_{k}"][ini:fin] = p["entailment"]
            out[f"neu_{k}"][ini:fin] = p["neutral"]
            out[f"con_{k}"][ini:fin] = p["contradiction"]
        pd.DataFrame(out).to_pickle(CHECKPOINT)
        dt = time.time() - t0
        print(f"[{fin}/{len(textos)}] {dt/60:.1f} min, faltan ~{dt/(fin-hechos)*(len(textos)-fin)/60:.1f} min",
              flush=True)

    res = pd.DataFrame(out)
    assert not res.filter(like="ent_").isna().any().any()
    res.to_pickle(SALIDA)
    os.remove(CHECKPOINT)
    print(f"OK -> {SALIDA} {res.shape}")


def premisas():
    from transformers import AutoTokenizer
    from nli_core import MODELO_NLI, _ruta_modelo_local
    df = pd.read_pickle(CORPUS).reset_index(drop=True)
    tok = AutoTokenizer.from_pretrained(_ruta_modelo_local(MODELO_NLI))
    textos = df["texto"].fillna("").astype(str).tolist()
    t0 = time.time()
    p = pd.Series(H.premisa_visible(textos, tok, H.hipotesis_unicas().values()), index=df["url"].values)
    os.makedirs(DIR, exist_ok=True)
    p.to_pickle(os.path.join(DIR, "premisas_visibles_nacional.pkl"))
    # Sanidad: en las URL del corpus de lugares debe coincidir con la premisa visible de F3.
    f3 = pd.read_pickle("experimentos/resultados/juicio_5ind/premisas_visibles.pkl")
    comunes = f3.index.intersection(p.index)
    iguales = int((f3.loc[comunes].values == p.loc[comunes].values).sum())
    print(f"{len(p)} premisas en {(time.time()-t0)/60:.1f} min; "
          f"coinciden con F3 en {iguales}/{len(comunes)} URL comunes")


if __name__ == "__main__":
    {"gpu": gpu, "premisas": premisas}[sys.argv[1]]()
