"""
Matriz de scores V2 sobre los 32 departamentos (11.439 articulos).

Reutiliza el corpus ya scrapeado — no vuelve a tocar el scraper.

Se puntua TODO sin enmascarar: asi el A/B del pre-filtro (con vs sin) se hace
despues sobre el pkl, sin repetir GPU. Los umbrales Bajo/Medio/Alto tambien se
calibraran sobre esta distribucion nacional, que es la poblacion correcta para
fijarlos (los 4 lugares no lo son).

~32 pases sobre 11.439 articulos: unas 4 horas.

CHECKPOINTING: guarda despues de cada hipotesis y reanuda desde lo guardado.
Una version anterior guardaba solo al final y se perdio una corrida completa de
4 h al apagar el equipo. Para empezar de cero: --reiniciar

Salida: ../datos/scores/scores_v2_32deptos.pkl
"""
import argparse
import os

import numpy as np
import pandas as pd

import hipotesis_v2 as V2
from nli_core import NLIScorer

CORPUS = "../datos/corpus/df_corpus_combinado_32deptos.pkl"
SALIDA = "../datos/scores/scores_v2_32deptos.pkl"
CHECKPOINT = "../datos/scores/scores_v2_32deptos.parcial.pkl"


def _cargar_checkpoint(n_filas: int):
    """Devuelve el dict de columnas ya calculadas, o vacio si no hay o no cuadra."""
    if not os.path.exists(CHECKPOINT):
        return {}
    try:
        d = pd.read_pickle(CHECKPOINT)
    except Exception as e:
        print(f"  AVISO: checkpoint ilegible ({e}); se empieza de cero")
        return {}
    if len(d) != n_filas:
        print(f"  AVISO: el checkpoint tiene {len(d)} filas y el corpus {n_filas}; "
              f"se descarta")
        return {}
    print(f"  Checkpoint encontrado: {len(d.columns)} columnas ya calculadas")
    return {c: d[c].values for c in d.columns}


def _guardar(out: dict) -> None:
    os.makedirs(os.path.dirname(CHECKPOINT), exist_ok=True)
    pd.DataFrame(out).to_pickle(CHECKPOINT)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reiniciar", action="store_true",
                   help="ignorar el checkpoint y empezar de cero")
    args = p.parse_args()

    df = pd.read_pickle(CORPUS)
    sin_texto = df["texto"].isna() | (df["texto"].astype(str).str.strip() == "")
    df = df[~sin_texto].reset_index(drop=True)
    print(f"Corpus: {len(df)} articulos | {df['departamento'].nunique()} departamentos")

    if args.reiniciar and os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
        print("  Checkpoint eliminado por --reiniciar")

    out = _cargar_checkpoint(len(df))
    out["departamento"] = df["departamento"].astype(str).str.strip().values
    out["titulo"] = df["titulo"].values

    prem = df["texto"].fillna("").astype(str).tolist()
    scorer = NLIScorer()

    # ── 1. Sesgo por articulo (media de las 4 nulas de calibracion) ──────────
    if "sesgo" not in out:
        print("\n[1/3] Nulas de calibracion (4)...")
        nulas = []
        for i, h in enumerate(V2.NULAS_CALIBRACION, 1):
            clave = f"_nula_calib_{i}"
            if clave not in out:
                out[clave] = np.asarray(scorer.score(prem, h), dtype=float)
                _guardar(out)
            print(f"    {i}/4")
        out["sesgo"] = np.mean([out[f"_nula_calib_{i}"] for i in range(1, 5)], axis=0)
        for i in range(1, 5):
            out.pop(f"_nula_calib_{i}", None)
        _guardar(out)
    else:
        print("\n[1/3] Nulas de calibracion: ya estaban")

    # ── 2. Pre-filtro y nula reservada ──────────────────────────────────────
    print("[2/3] Pre-filtro V2 + nula reservada...")
    if "score_social_v2" not in out:
        out["score_social_v2"] = np.asarray(scorer.score(prem, V2.HIPOTESIS_SOCIAL), dtype=float)
        _guardar(out)
    if "ent_NULA_TEST" not in out:
        pr = scorer.score(prem, V2.NULA_TEST, devolver_todo=True)
        out["ent_NULA_TEST"] = np.asarray(pr["entailment"], dtype=float)
        out["neu_NULA_TEST"] = np.asarray(pr["neutral"], dtype=float)
        _guardar(out)

    # ── 3. Las 26 hipotesis ─────────────────────────────────────────────────
    print("[3/3] Las 26 hipotesis V2...")
    for i, (clave, hip) in enumerate(V2.TODAS.items(), 1):
        if f"ent_{clave}" in out:
            print(f"    {i}/26  {clave}  (ya estaba)")
            continue
        pr = scorer.score(prem, hip, devolver_todo=True)
        out[f"ent_{clave}"] = np.asarray(pr["entailment"], dtype=float)
        out[f"neu_{clave}"] = np.asarray(pr["neutral"], dtype=float)
        _guardar(out)                      # <- guarda tras CADA hipotesis
        print(f"    {i}/26  {clave}")

    d = pd.DataFrame(out)
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    d.to_pickle(SALIDA)
    if os.path.exists(CHECKPOINT):
        os.remove(CHECKPOINT)
    print(f"\nGuardado -> {SALIDA}  (shape={d.shape})")
    print(d["departamento"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
