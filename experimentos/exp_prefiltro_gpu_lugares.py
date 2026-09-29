"""
GPU unica del experimento del pre-filtro social bajo MAX (experimentos/PREREG_prefiltro_max.md §3).

Puntua los 1.647 articulos de datos/corpus/df_corpus_5lugares.pkl con dos hipotesis que los pkl de
los lugares no tienen: HIPOTESIS_SOCIAL (score_social_v2 = P(entailment) crudo) y NULA_TEST
(ent, neu). Premisa = `texto`, batch_size=32, max_length=512, igual que produccion.

Orden (bloqueante, si algo falla se para y NO se escribe el pkl):
  0. verificar_contra_produccion_v2 (paso 0 del skill experimento-hipotesis), max|dif| < 1e-4.
  1. Puntuacion de las dos hipotesis.
  2. Antioquia (494, vienen del corpus nacional): score_social_v2 y NULA_TEST coinciden con los
     de datos/scores/scores_v2_32deptos.pkl, unidos por url (max|dif| < 1e-4).
  3. NULA_TEST coincide con ent_/neu_ABSURDO_TOTAL del pkl de atomicas (mismo texto).

Salida (nombre nuevo; no se sobrescribe nada): datos/scores/scores_prefiltro_lugares.pkl
Columnas: url, score_social_v2, ent_NULA_TEST, neu_NULA_TEST (mismo orden que el corpus).

Ejecutar desde la raiz del worktree:  python experimentos/exp_prefiltro_gpu_lugares.py
"""
import os
import sys
import time

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_v2 as V2  # noqa: E402
from nli_core import NLIScorer, verificar_contra_produccion_v2  # noqa: E402

CORPUS = "datos/corpus/df_corpus_5lugares.pkl"
BASELINE = "datos/scores/df_procesado_baseline_v2.pkl"
NACIONAL = "datos/scores/scores_v2_32deptos.pkl"
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
ATOMICAS = "datos/scores/scores_5ind_atomicas_lugares.pkl"
SALIDA = "datos/scores/scores_prefiltro_lugares.pkl"
TOL = 1e-4


def main():
    if os.path.exists(SALIDA):
        sys.exit(f"{SALIDA} ya existe: no se sobrescribe")
    t0 = time.time()
    s = NLIScorer()

    print("\n[0] Verificacion bloqueante contra produccion V2 (presencia_grupos_armados)...")
    ok = verificar_contra_produccion_v2(s, BASELINE, "presencia_grupos_armados",
                                        V2.TODAS["presencia_grupos_armados"], tol=TOL)
    if not ok:
        sys.exit("DESVIACION respecto de produccion: se para, no se puntua nada")
    print(f"    ({time.time() - t0:.0f} s)")

    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    prem = corpus["texto"].fillna("").astype(str).tolist()
    print(f"\n[1] Puntuando {len(prem)} articulos: HIPOTESIS_SOCIAL y NULA_TEST")
    print(f"    social: {V2.HIPOTESIS_SOCIAL!r}\n    nula  : {V2.NULA_TEST!r}")
    social = np.asarray(s.score(prem, V2.HIPOTESIS_SOCIAL, batch_size=32, max_length=512), dtype=float)
    print(f"    social listo ({time.time() - t0:.0f} s)")
    nula = s.score(prem, V2.NULA_TEST, batch_size=32, max_length=512, devolver_todo=True)
    ent_n = np.asarray(nula["entailment"], dtype=float)
    neu_n = np.asarray(nula["neutral"], dtype=float)
    print(f"    nula lista ({time.time() - t0:.0f} s)")
    out = pd.DataFrame({"url": corpus["url"].values, "score_social_v2": social,
                        "ent_NULA_TEST": ent_n, "neu_NULA_TEST": neu_n})

    print("\n[2] Antioquia (2023) contra el pkl nacional, unido por url...")
    nac = pd.read_pickle(NACIONAL).reset_index(drop=True)
    cnac = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    assert len(nac) == len(cnac) and (nac["titulo"].values == cnac["titulo"].values).all()
    nac = nac.assign(url=cnac["url"].values).set_index("url")
    ant = corpus["departamento"].astype(str).str.startswith("Antioquia").values
    sub = out[ant].set_index("url")
    comun = sub.index.intersection(nac.index)
    print(f"    Antioquia en lugares: {int(ant.sum())} | presentes en el nacional: {len(comun)}")
    assert len(comun) == int(ant.sum()), "hay articulos de Antioquia que no estan en el nacional"
    difs = {"score_social_v2": np.abs(sub.loc[comun, "score_social_v2"].values - nac.loc[comun, "score_social_v2"].values).max(),
            "ent_NULA_TEST": np.abs(sub.loc[comun, "ent_NULA_TEST"].values - nac.loc[comun, "ent_NULA_TEST"].values).max(),
            "neu_NULA_TEST": np.abs(sub.loc[comun, "neu_NULA_TEST"].values - nac.loc[comun, "neu_NULA_TEST"].values).max()}
    for k, v in difs.items():
        print(f"    max|dif| {k:16s}: {v:.2e}  {'OK' if v < TOL else 'DESVIACION'}")
    if max(difs.values()) >= TOL:
        sys.exit("Antioquia no coincide con el nacional: se para, no se escribe el pkl")

    print("\n[3] NULA_TEST contra ABSURDO_TOTAL del pkl de atomicas (mismo texto)...")
    at = pd.read_pickle(ATOMICAS)
    assert (at["url"].values == out["url"].values).all()
    d_ent = float(np.abs(at["ent_ABSURDO_TOTAL"].values - ent_n).max())
    d_neu = float(np.abs(at["neu_ABSURDO_TOTAL"].values - neu_n).max())
    print(f"    max|dif| ent: {d_ent:.2e}  neu: {d_neu:.2e}  {'OK' if max(d_ent, d_neu) < TOL else 'DESVIACION'}")
    if max(d_ent, d_neu) >= TOL:
        sys.exit("NULA_TEST no coincide con ABSURDO_TOTAL: se para, no se escribe el pkl")

    pct = {u: float((social >= u).mean()) for u in (0.50, 0.65, 0.75, 0.85)}
    print("\nProporcion que pasa el filtro por umbral (descriptivo): "
          + ", ".join(f"{u:.2f}: {p:.1%}" for u, p in pct.items()))
    out.to_pickle(SALIDA)
    print(f"\nGuardado -> {SALIDA} {out.shape} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
