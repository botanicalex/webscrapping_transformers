"""
GPU acotada de la etapa 1 del pre-filtro por indicador (experimentos/PREREG_prefiltro_indicador.md §3):
gemelas de objeto absurdo (`vig_abs`, osos polares) de `conflicto_territorial` y `desplazamiento_forzado` para los
1.117 articulos del holdout (Cauca 598, Choco 148, Cundinamarca 371). No existen en ningun pkl: el pkl nacional de
atomicas solo trae la de grupos armados.

Orden (bloqueante; si algo falla se para y NO se escribe el pkl):
  0. verificar_contra_produccion_v2 (paso 0 del skill experimento-hipotesis), max|dif| < 1e-4.
  1. Puntua `vig_abs` de grupos armados, conflicto y desplazamiento sobre los 1.117 (premisa = `texto`,
     batch_size=32, max_length=512, igual que produccion).
  2. La de grupos armados debe coincidir con datos/scores/scores_5ind_atomicas_nacional.pkl (ent y neu, por url;
     max|dif| < 1e-4): comprueba que este calculo es comparable con el nacional.

Salida (nombre nuevo; no se sobrescribe nada): datos/scores/scores_prefiltro_indicador_holdout.pkl
Columnas: url, departamento, ent_/neu_ de las tres gemelas (`<indicador>__vig_abs`), sin enmascarar.

  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_indicador_gpu.py
"""
import os
import sys
import time

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
from nli_core import NLIScorer, verificar_contra_produccion_v2  # noqa: E402

CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
ATOM_NAC = "datos/scores/scores_5ind_atomicas_nacional.pkl"
BASELINE = "datos/scores/df_procesado_baseline_v2.pkl"
SALIDA = "datos/scores/scores_prefiltro_indicador_holdout.pkl"
HOLDOUT = ["Cauca", "Chocó", "Cundinamarca"]
GA = "presencia_grupos_armados"
INDS = [GA, "conflicto_territorial", "desplazamiento_forzado"]
TOL = 1e-4


def main():
    if os.path.exists(SALIDA):
        sys.exit(f"{SALIDA} ya existe: no se sobrescribe")
    t0 = time.time()
    s = NLIScorer()
    print("\n[0] Verificacion bloqueante contra produccion V2 (presencia_grupos_armados)...")
    if not verificar_contra_produccion_v2(s, BASELINE, GA, V2.TODAS[GA], tol=TOL):
        sys.exit("DESVIACION respecto de produccion: se para, no se puntua nada")
    print(f"    ({time.time() - t0:.0f} s)")

    corpus = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    sub = corpus[corpus["departamento"].isin(HOLDOUT)].reset_index(drop=True)
    print(f"\n[1] Holdout: {len(sub)} articulos {sub['departamento'].value_counts().to_dict()}")
    assert len(sub) == 1117
    prem = sub["texto"].fillna("").astype(str).tolist()
    out = {"url": sub["url"].values, "departamento": sub["departamento"].values}
    for ind in INDS:
        hip = H.HIPOTESIS[ind]["vig_abs"]
        r = s.score(prem, hip, batch_size=32, max_length=512, devolver_todo=True)
        out[f"ent_{ind}__vig_abs"] = np.asarray(r["entailment"], dtype=float)
        out[f"neu_{ind}__vig_abs"] = np.asarray(r["neutral"], dtype=float)
        print(f"    {ind}__vig_abs listo: {hip!r} ({time.time() - t0:.0f} s)")
    res = pd.DataFrame(out)

    print("\n[2] Grupos armados vig_abs contra el pkl nacional (por url)...")
    at = pd.read_pickle(ATOM_NAC).set_index("url")
    ref = at.loc[res["url"].values]
    d_ent = float(np.abs(ref[f"ent_{GA}__vig_abs"].values - res[f"ent_{GA}__vig_abs"].values).max())
    d_neu = float(np.abs(ref[f"neu_{GA}__vig_abs"].values - res[f"neu_{GA}__vig_abs"].values).max())
    print(f"    max|dif| ent {d_ent:.2e}  neu {d_neu:.2e}  {'OK' if max(d_ent, d_neu) < TOL else 'DESVIACION'}")
    if max(d_ent, d_neu) >= TOL:
        sys.exit("la gemela de grupos armados no coincide con el nacional: se para, no se escribe el pkl")

    res.to_pickle(SALIDA)
    print(f"\nGuardado -> {SALIDA} {res.shape} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
