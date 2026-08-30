"""
EXPERIMENTO 5 — pipeline completo con V2, de extremo a extremo.

Aplica la receta validada en los experimentos 1-4 a las 26 hipotesis y al
pre-filtro, y compara el radar resultante contra el baseline de produccion.

Receta:
  formato    V2 (sin marco metalinguistico)
  premisa    cuerpo del articulo (exp2: ninguna alternativa domina)
  correccion combinada = clip(P(ent) - sesgo, 0) * (1 - P(neu))
             (exp4: la mejor sobre MAX, brecha 0.5393 vs 0.0004 de produccion)

Se incluye la nula RESERVADA en todo el recorrido: es la vara de medir. El
radar de una hipotesis absurda deberia quedar MUY por debajo del real. Con
produccion quedan indistinguibles (0.9985 vs 0.9989).

El baseline V0 se lee del pkl de produccion, ya enmascarado como en produccion.
"""
import os

import numpy as np
import pandas as pd

import hipotesis_v2 as V2
import silver
import hipotesis_base as HB
from nli_core import NLIScorer

CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
BASELINE = "../datos/scores/df_procesado_baseline.pkl"
SALIDA = "resultados/exp5_pipeline_v2.xlsx"

UMBRAL_BAJO, UMBRAL_ALTO = 1 / 3, 2 / 3


def categoria(v):
    return "Bajo" if v < UMBRAL_BAJO else ("Medio" if v <= UMBRAL_ALTO else "Alto")


def main():
    df = pd.read_pickle(CORPUS)
    base = pd.read_pickle(BASELINE)
    lugares = df["departamento"].astype(str).values
    prem = df["texto"].fillna("").astype(str).tolist()
    scorer = NLIScorer()

    # 1. sesgo por articulo
    print("\n[1] Estimando sesgo por articulo (4 nulas)...")
    sesgo = np.mean([np.asarray(scorer.score(prem, h), dtype=float)
                     for h in V2.NULAS_CALIBRACION], axis=0)

    def corregir(p):
        e = np.asarray(p["entailment"], dtype=float)
        n = np.asarray(p["neutral"], dtype=float)
        return np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)

    # 2. pre-filtro V2
    print("[2] Pre-filtro V2...")
    p_soc = scorer.score(prem, V2.HIPOTESIS_SOCIAL, devolver_todo=True)
    score_social = np.asarray(p_soc["entailment"], dtype=float)
    rel = score_social >= V2.UMBRAL_SOCIAL
    print(f"    relevantes: {rel.sum()}/{len(rel)} ({rel.mean():.1%})   "
          f"[produccion V0: {(base['score_social']>=0.65).sum()}/{len(base)}]")

    # 3. las 26 + la nula reservada
    print("[3] Puntuando 26 hipotesis V2 + nula reservada...")
    scores = {}
    for i, (clave, hip) in enumerate(V2.TODAS.items(), 1):
        s = corregir(scorer.score(prem, hip, devolver_todo=True))
        s[~rel] = 0.0
        scores[clave] = s
        if i % 5 == 0 or i == 26:
            print(f"    {i}/26")
    s_nula = corregir(scorer.score(prem, V2.NULA_TEST, devolver_todo=True))
    s_nula[~rel] = 0.0

    # 4. AUC en los 2 indicadores con estandar de plata (sin enmascarar,
    #    para no confundir calidad de hipotesis con dano del pre-filtro)
    print("\n[4] AUC contra estandar de plata (V0 produccion vs V2):")
    print(f"{'indicador':<28}{'AUC V0':>9}{'AUC V2':>9}{'delta':>9}")
    filas_auc = []
    for ind in HB.KEYWORDS_SILVER:
        y = silver.etiquetar(df, HB.KEYWORDS_SILVER[ind])["label"].values
        s_v2 = corregir(scorer.score(prem, V2.TODAS[ind], devolver_todo=True))  # sin mascara
        a0 = silver.auc(base[ind].astype(float).values, y)
        a2 = silver.auc(s_v2, y)
        filas_auc.append({"indicador": ind, "auc_V0_produccion": a0, "auc_V2": a2})
        print(f"{ind:<28}{a0:>9.4f}{a2:>9.4f}{a2-a0:>+9.4f}")

    # 5. radar por lugar
    print(f"\n[5] Radar por lugar (MAX de 26 indicadores)")
    print(f"{'lugar':<22}{'V0 radar':>10}{'V0 clas':>9}{'V2 radar':>10}{'V2 clas':>9}"
          f"{'V0 nula':>9}{'V2 nula':>9}")
    inds = list(V2.TODAS)
    filas = []
    for lug in sorted(set(lugares)):
        m = lugares == lug
        r2 = float(np.mean([scores[c][m].max() for c in inds]))
        n2 = float(s_nula[m].max())
        b = base[base["departamento"].astype(str) == lug]
        r0 = float(np.mean([b[c].astype(float).max() for c in inds]))
        n0 = 0.9985  # medido en exp4 (MAX de la nula con formato produccion)
        filas.append({"lugar": lug, "radar_V0": r0, "clas_V0": categoria(r0),
                      "radar_V2": r2, "clas_V2": categoria(r2),
                      "nula_V0": n0, "nula_V2": n2,
                      "brecha_V0": r0 - n0, "brecha_V2": r2 - n2,
                      "n_articulos": int(m.sum())})
        print(f"{lug:<22}{r0:>10.4f}{categoria(r0):>9}{r2:>10.4f}{categoria(r2):>9}"
              f"{n0:>9.4f}{n2:>9.4f}")

    d = pd.DataFrame(filas)
    print(f"\n  brecha media (radar - nula):  V0 = {d.brecha_V0.mean():+.4f}   "
          f"V2 = {d.brecha_V2.mean():+.4f}")

    os.makedirs("resultados", exist_ok=True)
    with pd.ExcelWriter(SALIDA) as w:
        d.to_excel(w, sheet_name="radar_por_lugar", index=False)
        pd.DataFrame(filas_auc).to_excel(w, sheet_name="auc_plata", index=False)
        pd.DataFrame({"indicador": inds,
                      "hipotesis_V0": [HB.TODAS[c] for c in inds],
                      "hipotesis_V2": [V2.TODAS[c] for c in inds]}
                     ).to_excel(w, sheet_name="hipotesis", index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
