"""
EXPERIMENTO 4 — efecto de las correcciones sobre el MAX (la agregacion real).

Por que hace falta: el exp3 mide AUC y separacion, que describen el grueso de la
distribucion. Pero produccion agrega con MAX, y el MAX depende UNICAMENTE de la
cola. Una correccion puede mejorar el grueso y no arreglar nada del MAX.

Prueba decisiva: calcular el MAX por lugar de una hipotesis NULA reservada
(osos polares). Con el metodo actual el MAX de cualquier hipotesis da ~0.999 por
construccion, y por eso los 32 departamentos salieron "Alto". Una correccion
sirve si, y solo si, el MAX de la nula se desploma mientras el MAX de un
indicador real se mantiene alto donde el fenomeno existe.

Metrica de merito: brecha = MAX(indicador real) - MAX(nula), por lugar.
"""
import os

import numpy as np
import pandas as pd

import hipotesis_base as H
import silver
from nli_core import NLIScorer

CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
SALIDA = "resultados/exp4_agregacion.xlsx"

HIPOTESIS_V1 = {
    "presencia_grupos_armados": "En este territorio hay presencia de grupos armados ilegales.",
    "grupos_etnicos_existentes": "En este territorio hay comunidades étnicas o pueblos indígenas.",
}
NULAS_CALIBRACION = [
    "En este territorio hay presencia de pingüinos emperador.",
    "En este territorio hay yacimientos de helio-3 lunar.",
    "En este territorio se practica la caligrafía medieval japonesa.",
    "En este territorio hay glaciares de metano líquido.",
]
NULA_TEST = "En este territorio hay colonias de osos polares."


def correcciones(ent, neu, sesgo):
    """Todas devuelven un score comparable; se recortan a [0,1] para el MAX."""
    return {
        "V0_produccion": None,  # se rellena aparte (hipotesis distinta)
        "raw_V1": np.clip(ent, 0, 1),
        "resta_sesgo": np.clip(ent - sesgo, 0, 1),
        "ent_menos_neu": np.clip(ent - neu, 0, 1),
        "combinada": np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1),
    }


def main():
    df = pd.read_pickle(CORPUS)
    lugares = df["departamento"].astype(str).values
    scorer = NLIScorer()
    prem = df["texto"].fillna("").astype(str).tolist()

    print("Estimando sesgo por articulo (4 nulas)...")
    sesgo = np.mean([np.asarray(scorer.score(prem, h), dtype=float)
                     for h in NULAS_CALIBRACION], axis=0)

    print("Puntuando nula reservada (osos polares)...")
    pn = scorer.score(prem, NULA_TEST, devolver_todo=True)
    ent_n = np.asarray(pn["entailment"], dtype=float)
    neu_n = np.asarray(pn["neutral"], dtype=float)
    corr_nula = correcciones(ent_n, neu_n, sesgo)

    filas = []
    for ind, hip in HIPOTESIS_V1.items():
        p = scorer.score(prem, hip, devolver_todo=True)
        ent = np.asarray(p["entailment"], dtype=float)
        neu = np.asarray(p["neutral"], dtype=float)
        corr_ind = correcciones(ent, neu, sesgo)

        # V0 produccion: hipotesis original, sin correccion
        v0 = np.asarray(scorer.score(prem, H.TODAS[ind]), dtype=float)
        v0_nula = np.asarray(scorer.score(prem, H.HIPOTESIS_CONTROL_ABSURDO), dtype=float)
        corr_ind["V0_produccion"] = v0
        corr_nula_local = dict(corr_nula)
        corr_nula_local["V0_produccion"] = v0_nula

        print(f"\n{'='*86}\n{ind}\n{'='*86}")
        print(f"{'correccion':<16}{'lugar':<22}{'MAX ind':>9}{'MAX nula':>10}{'brecha':>9}")
        for nombre in ["V0_produccion", "raw_V1", "resta_sesgo", "ent_menos_neu", "combinada"]:
            s_ind, s_nul = corr_ind[nombre], corr_nula_local[nombre]
            for lug in sorted(set(lugares)):
                m = lugares == lug
                mi, mn = float(np.max(s_ind[m])), float(np.max(s_nul[m]))
                filas.append({"indicador": ind, "correccion": nombre, "lugar": lug,
                              "max_indicador": mi, "max_nula": mn, "brecha": mi - mn})
                print(f"{nombre:<16}{lug:<22}{mi:>9.4f}{mn:>10.4f}{mi-mn:>+9.4f}")
            print()

    os.makedirs("resultados", exist_ok=True)
    d = pd.DataFrame(filas)
    d.to_excel(SALIDA, index=False)

    print(f"\n{'='*86}\nRESUMEN — brecha media entre indicador real y nula\n{'='*86}")
    print(d.groupby("correccion")[["max_indicador", "max_nula", "brecha"]]
          .mean().round(4).sort_values("brecha", ascending=False).to_string())
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
