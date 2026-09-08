"""
EXPERIMENTO 2 — eje de PREMISA + normalizacion entailment/contradiction.

Motivo: aun sin marco metalinguistico queda inflacion residual (V1 dice "si" a
los pinguinos en el 20% de los articulos). Hipotesis: viene de la premisa.
Produccion usa el cuerpo truncado a ~470 tokens y EXCLUYE el titular; XNLI se
entreno con premisas de una sola frase.

Se aprovecha el mismo forward pass para probar dos formas de leer la salida:
  raw   = P(entailment)                          <- lo que hace produccion
  norm2 = P(ent) / (P(ent) + P(con))             <- descarta la masa de neutral

La segunda es estandar en clasificacion zero-shot con NLI: cuando el modelo esta
inseguro pone masa en neutral, y esa masa contamina P(ent) de forma desigual
entre articulos. No cuesta computo adicional.

Criterio de aceptacion: una combinacion solo es mejor si sube AUC **y** baja el
control absurdo. El AUC solo llevaria a elegir V4, que afirma que hay pinguinos
en el 83% de las noticias.
"""
import os

import numpy as np
import pandas as pd

import hipotesis_base as H
import silver
from nli_core import NLIScorer, PREMISAS

CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
SALIDA = "resultados/exp2_premisa.xlsx"

HIPOTESIS = {
    "presencia_grupos_armados": {
        "V0_actual": H.TODAS["presencia_grupos_armados"],
        "V1_sin_metalenguaje": "En este territorio hay presencia de grupos armados ilegales.",
        "V2_corta": "Hay grupos armados ilegales.",
    },
    "grupos_etnicos_existentes": {
        "V0_actual": H.TODAS["grupos_etnicos_existentes"],
        "V1_sin_metalenguaje": "En este territorio hay comunidades étnicas o pueblos indígenas.",
        "V2_corta": "Hay comunidades indígenas o afrodescendientes.",
    },
}

CONTROLES = {
    "V0_formato": H.HIPOTESIS_CONTROL_ABSURDO,
    "V1_formato": "En este territorio hay presencia de pingüinos emperador.",
}


def norm2(p):
    """P(ent) / (P(ent) + P(con)) — descarta la masa de neutral."""
    e = np.asarray(p["entailment"], dtype=float)
    c = np.asarray(p["contradiction"], dtype=float)
    return e / np.clip(e + c, 1e-9, None)


def main():
    df = pd.read_pickle(CORPUS)
    print(f"Corpus: {len(df)} articulos\n")
    scorer = NLIScorer()

    premisas_construidas = {n: f(df) for n, f in PREMISAS.items()}
    for n, p in premisas_construidas.items():
        largo = int(np.mean([len(str(x)) for x in p]))
        print(f"  premisa '{n}': {largo} caracteres de media")

    etiquetas = {ind: silver.etiquetar(df, H.KEYWORDS_SILVER[ind])["label"].values
                 for ind in HIPOTESIS}

    filas = []
    for ind, variantes in HIPOTESIS.items():
        y = etiquetas[ind]
        print(f"\n{'='*88}\n{ind}   (pos={int((y==1).sum())}  neg={int((y==0).sum())})\n{'='*88}")
        print(f"{'premisa':<18}{'hipotesis':<22}{'AUC raw':>9}{'AUC n2':>9}"
              f"{'sep raw':>9}{'sep n2':>9}{'m_neg raw':>11}")
        for nom_prem, prem in premisas_construidas.items():
            for nom_hip, hip in variantes.items():
                p = scorer.score(prem, hip, devolver_todo=True)
                m_raw = silver.evaluar(p["entailment"], y)
                m_n2 = silver.evaluar(norm2(p), y)
                filas.append({
                    "indicador": ind, "premisa": nom_prem, "hipotesis": nom_hip,
                    "auc_raw": m_raw["auc"], "auc_norm2": m_n2["auc"],
                    "sep_raw": m_raw["separacion"], "sep_norm2": m_n2["separacion"],
                    "mneg_raw": m_raw["media_neg"], "mneg_norm2": m_n2["media_neg"],
                    "mpos_raw": m_raw["media_pos"], "mpos_norm2": m_n2["media_pos"],
                })
                print(f"{nom_prem:<18}{nom_hip:<22}{m_raw['auc']:>9.4f}{m_n2['auc']:>9.4f}"
                      f"{m_raw['separacion']:>+9.3f}{m_n2['separacion']:>+9.3f}"
                      f"{m_raw['media_neg']:>11.3f}")

    # ── Control absurdo por premisa y formato ────────────────────────────────
    print(f"\n{'='*88}\nCONTROL ABSURDO (pinguinos) — media / prop>0.9\n{'='*88}")
    print(f"{'premisa':<18}{'formato':<14}{'raw media':>11}{'raw p>.9':>10}"
          f"{'n2 media':>11}{'n2 p>.9':>10}")
    for nom_prem, prem in premisas_construidas.items():
        for nom_ctrl, hip in CONTROLES.items():
            p = scorer.score(prem, hip, devolver_todo=True)
            r = pd.Series(p["entailment"]); n = pd.Series(norm2(p))
            filas.append({
                "indicador": "CONTROL_ABSURDO", "premisa": nom_prem, "hipotesis": nom_ctrl,
                "auc_raw": np.nan, "auc_norm2": np.nan,
                "sep_raw": np.nan, "sep_norm2": np.nan,
                "mneg_raw": float(r.mean()), "mneg_norm2": float(n.mean()),
                "mpos_raw": np.nan, "mpos_norm2": np.nan,
            })
            print(f"{nom_prem:<18}{nom_ctrl:<14}{r.mean():>11.4f}{(r>0.9).mean():>10.4f}"
                  f"{n.mean():>11.4f}{(n>0.9).mean():>10.4f}")

    os.makedirs("resultados", exist_ok=True)
    pd.DataFrame(filas).to_excel(SALIDA, index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
