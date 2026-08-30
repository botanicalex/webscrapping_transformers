"""
Calcula UNA vez la matriz completa de scores V2 y la guarda.

Cada experimento posterior sobre agregacion, umbrales o correcciones lee este
pkl en vez de repetir ~30 pases de GPU. Guarda las tres probabilidades crudas,
sin correccion ni enmascarado, para poder derivar cualquier variante offline.

Salida: resultados/scores_v2.pkl
  ent_<indicador>, neu_<indicador>  para las 26
  ent_NULA_TEST, neu_NULA_TEST      la nula reservada
  sesgo                             media de las 4 nulas de calibracion
  score_social_v2                   pre-filtro V2 (crudo)
  departamento, titulo
"""
import os

import numpy as np
import pandas as pd

import hipotesis_v2 as V2
from nli_core import NLIScorer

CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
SALIDA = "../datos/scores/scores_v2.pkl"


def main():
    df = pd.read_pickle(CORPUS)
    prem = df["texto"].fillna("").astype(str).tolist()
    scorer = NLIScorer()

    out = {"departamento": df["departamento"].astype(str).values,
           "titulo": df["titulo"].values}

    print("[1/3] Nulas de calibracion...")
    out["sesgo"] = np.mean([np.asarray(scorer.score(prem, h), dtype=float)
                            for h in V2.NULAS_CALIBRACION], axis=0)

    print("[2/3] Pre-filtro V2 + nula reservada...")
    out["score_social_v2"] = np.asarray(scorer.score(prem, V2.HIPOTESIS_SOCIAL), dtype=float)
    p = scorer.score(prem, V2.NULA_TEST, devolver_todo=True)
    out["ent_NULA_TEST"] = np.asarray(p["entailment"], dtype=float)
    out["neu_NULA_TEST"] = np.asarray(p["neutral"], dtype=float)

    print("[3/3] Las 26 hipotesis V2...")
    for i, (clave, hip) in enumerate(V2.TODAS.items(), 1):
        p = scorer.score(prem, hip, devolver_todo=True)
        out[f"ent_{clave}"] = np.asarray(p["entailment"], dtype=float)
        out[f"neu_{clave}"] = np.asarray(p["neutral"], dtype=float)
        if i % 5 == 0 or i == 26:
            print(f"    {i}/26")

    os.makedirs("resultados", exist_ok=True)
    d = pd.DataFrame(out)
    d.to_pickle(SALIDA)
    print(f"\nGuardado -> {SALIDA}  (shape={d.shape})")


if __name__ == "__main__":
    main()
