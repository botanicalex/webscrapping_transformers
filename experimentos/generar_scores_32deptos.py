"""
Matriz de scores V2 sobre los 32 departamentos (11.439 articulos).

Reutiliza el corpus ya scrapeado — no vuelve a tocar el scraper.

Se puntua TODO sin enmascarar: asi el A/B del pre-filtro (con vs sin) se hace
despues sobre el pkl, sin repetir GPU. Los umbrales Bajo/Medio/Alto tambien se
calibraran sobre esta distribucion nacional, que es la poblacion correcta para
fijarlos (los 4 lugares no lo son).

~32 pases sobre 11.439 articulos: unas 4 horas.
Salida: resultados/scores_v2_32deptos.pkl
"""
import os

import numpy as np
import pandas as pd

import hipotesis_v2 as V2
from nli_core import NLIScorer

CORPUS = "../datos/corpus/df_corpus_combinado_32deptos.pkl"
SALIDA = "../datos/scores/scores_v2_32deptos.pkl"


def main():
    df = pd.read_pickle(CORPUS)
    sin_texto = df["texto"].isna() | (df["texto"].astype(str).str.strip() == "")
    df = df[~sin_texto].reset_index(drop=True)
    print(f"Corpus: {len(df)} articulos | {df['departamento'].nunique()} departamentos")

    prem = df["texto"].fillna("").astype(str).tolist()
    scorer = NLIScorer()

    out = {"departamento": df["departamento"].astype(str).str.strip().values,
           "titulo": df["titulo"].values}

    print("\n[1/3] Nulas de calibracion (4)...")
    nulas = []
    for i, h in enumerate(V2.NULAS_CALIBRACION, 1):
        nulas.append(np.asarray(scorer.score(prem, h), dtype=float))
        print(f"    {i}/4")
    out["sesgo"] = np.mean(nulas, axis=0)

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
        print(f"    {i}/26  {clave}")

    os.makedirs("resultados", exist_ok=True)
    d = pd.DataFrame(out)
    d.to_pickle(SALIDA)
    print(f"\nGuardado -> {SALIDA}  (shape={d.shape})")
    print(d["departamento"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
