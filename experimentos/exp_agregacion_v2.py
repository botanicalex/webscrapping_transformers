"""
EXPERIMENTO 6 — recalibracion del pre-filtro y eleccion de la agregacion.

Todo se calcula sobre resultados/scores_v2.pkl: sin GPU.

Cuando se comparo TOP3 contra MAX hace semanas dieron practicamente lo mismo
(0.9988 vs 0.9991) porque bajo V0 todo estaba saturado. Con la escala V2
corregida (negativos cerca de 0) las agregaciones deberian separarse.

PARTE A — umbral del pre-filtro
  El 0.65 estaba calibrado para la hipotesis vieja. Criterio para el nuevo:
  conservar >=95% de los positivos de plata excluyendo lo mas posible.

PARTE B — agregacion
  Merito = brecha entre el radar real y el radar de la nula reservada.

PARTE C — estabilidad frente al tamano del corpus
  El defecto estructural del MAX: mas articulos -> mas probable un extremo
  espurio. Se submuestrea Maicao (1101 art.) a distintos n y se mide como
  cambia el radar de la NULA. Una buena agregacion lo mantiene bajo y plano.
"""
import numpy as np
import pandas as pd

import hipotesis_base as HB
import hipotesis_v2 as V2
import silver

SCORES = "../datos/scores/scores_v2.pkl"
CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
SALIDA = "resultados/exp6_agregacion_v2.xlsx"

RNG = np.random.default_rng(20260826)
UMBRAL_BAJO, UMBRAL_ALTO = 1 / 3, 2 / 3


def categoria(v):
    return "Bajo" if v < UMBRAL_BAJO else ("Medio" if v <= UMBRAL_ALTO else "Alto")


AGREGACIONES = {
    "MAX": lambda x: np.max(x) if len(x) else 0.0,
    "TOP3": lambda x: np.mean(np.sort(x)[-3:]) if len(x) else 0.0,
    "TOP5": lambda x: np.mean(np.sort(x)[-5:]) if len(x) else 0.0,
    "P90": lambda x: float(np.quantile(x, 0.90)) if len(x) else 0.0,
    "P75": lambda x: float(np.quantile(x, 0.75)) if len(x) else 0.0,
    "MEDIA": lambda x: float(np.mean(x)) if len(x) else 0.0,
    "PROP>0.5": lambda x: float((x > 0.5).mean()) if len(x) else 0.0,
}


def main():
    d = pd.read_pickle(SCORES)
    df = pd.read_pickle(CORPUS)
    inds = list(V2.TODAS)
    sesgo = d["sesgo"].values

    def corregir(col):
        e, n = d[f"ent_{col}"].values, d[f"neu_{col}"].values
        return np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)

    S = {c: corregir(c) for c in inds}
    S_nula = corregir("NULA_TEST")
    soc = d["score_social_v2"].values
    lugares = d["departamento"].values

    # ── PARTE A ──────────────────────────────────────────────────────────────
    print("=" * 78)
    print("A. UMBRAL DEL PRE-FILTRO  (score_social_v2)")
    print("=" * 78)
    plata = {i: silver.etiquetar(df, HB.KEYWORDS_SILVER[i])["label"].values
             for i in HB.KEYWORDS_SILVER}
    print(f"{'umbral':>8}{'% pasa':>9}{'% pos etnicos':>15}{'% pos armados':>15}")
    filas_a = []
    for u in [0.0, 0.30, 0.50, 0.65, 0.75, 0.85, 0.90, 0.95]:
        rel = soc >= u
        ret = {}
        for ind, y in plata.items():
            pos = y == 1
            ret[ind] = float(rel[pos].mean())
        filas_a.append({"umbral": u, "pct_pasa": float(rel.mean()),
                        **{f"ret_{k}": v for k, v in ret.items()}})
        print(f"{u:>8.2f}{rel.mean():>9.1%}"
              f"{ret['grupos_etnicos_existentes']:>15.1%}{ret['presencia_grupos_armados']:>15.1%}")
    print("\n  produccion V0 (referencia): pasa 65.5% | retiene 66.4% etnicos, 82.3% armados")

    UMBRAL = 0.85
    rel = soc >= UMBRAL
    print(f"\n  -> se adopta umbral {UMBRAL}: pasa {rel.mean():.1%}, "
          f"retiene {rel[plata['grupos_etnicos_existentes']==1].mean():.1%} / "
          f"{rel[plata['presencia_grupos_armados']==1].mean():.1%} de los positivos")

    for c in inds:
        S[c] = np.where(rel, S[c], 0.0)
    S_nula_m = np.where(rel, S_nula, 0.0)

    # ── PARTE B ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("B. AGREGACION  (radar real vs radar de la nula reservada)")
    print("=" * 78)
    filas_b = []
    for nom, fn in AGREGACIONES.items():
        print(f"\n  {nom}")
        print(f"    {'lugar':<22}{'radar':>9}{'clase':>8}{'nula':>9}{'brecha':>9}")
        brechas = []
        for lug in sorted(set(lugares)):
            m = lugares == lug
            r = float(np.mean([fn(S[c][m]) for c in inds]))
            n = float(fn(S_nula_m[m]))
            brechas.append(r - n)
            filas_b.append({"agregacion": nom, "lugar": lug, "radar": r,
                            "clase": categoria(r), "nula": n, "brecha": r - n})
            print(f"    {lug:<22}{r:>9.4f}{categoria(r):>8}{n:>9.4f}{r-n:>+9.4f}")
        print(f"    {'brecha media':<22}{np.mean(brechas):>+9.4f}")

    # ── PARTE C ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    print("C. ESTABILIDAD FRENTE AL TAMANO DEL CORPUS  (radar de la NULA en Maicao)")
    print("=" * 78)
    idx = np.where(lugares == "Municipio Maicao")[0]
    tamanos = [20, 50, 100, 200, 500, 1000]
    print(f"    {'agregacion':<12}" + "".join(f"{f'n={t}':>10}" for t in tamanos) + f"{'rango':>10}")
    filas_c = []
    for nom, fn in AGREGACIONES.items():
        vals = []
        for t in tamanos:
            reps = [fn(S_nula_m[RNG.choice(idx, size=t, replace=False)]) for _ in range(50)]
            vals.append(float(np.mean(reps)))
        filas_c.append({"agregacion": nom, **{f"n_{t}": v for t, v in zip(tamanos, vals)},
                        "rango": max(vals) - min(vals)})
        print(f"    {nom:<12}" + "".join(f"{v:>10.4f}" for v in vals)
              + f"{max(vals)-min(vals):>10.4f}")

    with pd.ExcelWriter(SALIDA) as w:
        pd.DataFrame(filas_a).to_excel(w, sheet_name="A_prefiltro", index=False)
        pd.DataFrame(filas_b).to_excel(w, sheet_name="B_agregacion", index=False)
        pd.DataFrame(filas_c).to_excel(w, sheet_name="C_estabilidad", index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
