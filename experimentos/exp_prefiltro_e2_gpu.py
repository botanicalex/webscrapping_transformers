"""
F1-T2 (PREREG_prefiltro_indicador_e2.md §8): GPU de las 6 gemelas absurdas del tramo 1, calcado de
exp_prefiltro_indicador_gpu.py. Orden (bloqueante; si algo falla se para y NO se escribe el pkl):
  0. verificar_contra_produccion_v2 (grupos armados, baseline V2), max|dif| < 1e-4.
  1. Puntua las 6 gemelas (premisa = `texto`, batch_size=32, max_length=512, como produccion) sobre los 1.647
     articulos de los lugares (corpus de 5 lugares; membresia = url_lugares.csv) y los 1.117 del holdout
     (Cauca, Choco, Cundinamarca del nacional).
Salida (pkl nuevo; no se sobrescribe nada): datos/scores/scores_prefiltro_e2.pkl
Columnas: url, origen ('lugares'|'holdout'), departamento, ent_/neu_ `<indicador>__gemela` sin enmascarar.
El log completo va a experimentos/resultados/exp_prefiltro_e2_gpu.log.

  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_e2_gpu.py
"""
import os
import sys
import time

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_prefiltro_e2 as P  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
from nli_core import NLIScorer, verificar_contra_produccion_v2  # noqa: E402

CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
CORPUS_L = "datos/corpus/df_corpus_5lugares.pkl"
URL_LUGARES = "experimentos/resultados/juicio_5ind/url_lugares.csv"
BASELINE = "datos/scores/df_procesado_baseline_v2.pkl"
SALIDA = "datos/scores/scores_prefiltro_e2.pkl"
LOG = "experimentos/resultados/exp_prefiltro_e2_gpu.log"
HOLDOUT = ["Cauca", "Chocó", "Cundinamarca"]
GA = "presencia_grupos_armados"
TOL = 1e-4


class Tee:
    def __init__(self, *fs):
        self.fs = fs

    def write(self, s):
        for f in self.fs:
            f.write(s)
            f.flush()

    def flush(self):
        for f in self.fs:
            f.flush()


def main():
    if os.path.exists(SALIDA):
        sys.exit(f"{SALIDA} ya existe: no se sobrescribe")
    if os.path.exists(LOG):
        sys.exit(f"{LOG} ya existe: no se sobrescribe")
    logf = open(LOG, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, logf)
    t0 = time.time()
    print(f"Inicio {time.strftime('%Y-%m-%d %H:%M:%S')}")
    s = NLIScorer()
    print("\n[0] Verificacion bloqueante contra produccion V2 (presencia_grupos_armados)...")
    if not verificar_contra_produccion_v2(s, BASELINE, GA, V2.TODAS[GA], tol=TOL):
        sys.exit("DESVIACION respecto de produccion: se para, no se puntua nada")
    print(f"    ({time.time() - t0:.0f} s)")

    cl = pd.read_pickle(CORPUS_L).reset_index(drop=True)
    lug = pd.read_csv(URL_LUGARES)
    assert len(cl) == 1647 and cl["url"].is_unique and set(lug["url"]) == set(cl["url"]), "lugares no cuadra con url_lugares.csv"
    cn = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    ho = cn[cn["departamento"].isin(HOLDOUT)].reset_index(drop=True)
    assert len(ho) == 1117, len(ho)
    print(f"\n[1] Lugares {len(cl)} + holdout {len(ho)} {ho['departamento'].value_counts().to_dict()}")
    base = pd.concat([cl[["url", "departamento", "texto"]].assign(origen="lugares"),
                      ho[["url", "departamento", "texto"]].assign(origen="holdout")], ignore_index=True)
    prem = base["texto"].fillna("").astype(str).tolist()
    out = {"url": base["url"].values, "origen": base["origen"].values, "departamento": base["departamento"].values}
    for ind in P.TRAMO_1:
        hip = P.GEMELAS[ind]
        t1 = time.time()
        r = s.score(prem, hip, batch_size=32, max_length=512, devolver_todo=True)
        out[f"ent_{ind}__gemela"] = np.asarray(r["entailment"], dtype=float)
        out[f"neu_{ind}__gemela"] = np.asarray(r["neutral"], dtype=float)
        print(f"    {ind}__gemela listo: {hip!r} ({(time.time() - t1) / 60:.1f} min; acumulado {(time.time() - t0) / 60:.1f} min)")
    res = pd.DataFrame(out)
    assert not res.filter(regex="^(ent|neu)_").isna().any().any()
    res.to_pickle(SALIDA)
    print(f"\nGuardado -> {SALIDA} {res.shape}")
    print(f"TOTAL {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
