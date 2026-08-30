"""
EXPERIMENTO 1 — eje de FORMATO DE HIPOTESIS.

Premisa fija (cuerpo del articulo, como produccion) para aislar el efecto del
formato. Todos los articulos se puntuan SIN enmascarar por el pre-filtro social:
el enmascarado es una decision de produccion y destruiria el ranking.

Cada variante difiere de V0 en UNA sola cosa:
  V1 quita el marco metalinguistico  ("Este articulo reporta que X" -> "X")
  V2 corta y simple                  (lo mas cercano a XNLI)
  V3 quita "explicitamente"          (calificador de evidencialidad)
  V4 quita la disyuncion multiple    (un solo verbo en vez de cuatro)
  V5 nombra entidades concretas      (en vez de la categoria abstracta)

Metrica: AUC contra el estandar de plata. Libre de umbral.
"""
import os

import pandas as pd

import hipotesis_base as H
import silver
from nli_core import NLIScorer

CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
SALIDA = "resultados/exp1_formato.xlsx"

VARIANTES = {
    "presencia_grupos_armados": {
        "V0_actual": H.TODAS["presencia_grupos_armados"],
        "V1_sin_metalenguaje": "En este territorio hay presencia de grupos armados ilegales.",
        "V2_corta": "Hay grupos armados ilegales.",
        "V3_sin_explicitamente": "Este artículo menciona la presencia, acción, control o intervención de grupos armados ilegales en un territorio.",
        "V4_sin_disyuncion": "Este artículo menciona explícitamente la presencia de grupos armados ilegales en un territorio.",
        "V5_entidades": "Hay guerrilla, paramilitares o bandas criminales.",
    },
    "grupos_etnicos_existentes": {
        "V0_actual": H.TODAS["grupos_etnicos_existentes"],
        "V1_sin_metalenguaje": "En este territorio hay comunidades étnicas o pueblos indígenas.",
        "V2_corta": "Hay comunidades indígenas o afrodescendientes.",
        "V3_sin_explicitamente": "Este artículo menciona comunidades étnicas, pueblos indígenas, comunidades afrodescendientes, raizales, palenqueras o grupos étnicos que tienen presencia o participación relevante en el territorio.",
        "V4_sin_disyuncion": "Este artículo menciona explícitamente comunidades étnicas en el territorio.",
        "V5_entidades": "Hay indígenas, afrodescendientes o resguardos.",
    },
}


def main():
    df = pd.read_pickle(CORPUS)
    print(f"Corpus: {len(df)} articulos (sin enmascarar)\n")

    scorer = NLIScorer()
    premisas = df["texto"].fillna("").astype(str).tolist()

    filas = []
    for indicador, variantes in VARIANTES.items():
        etq = silver.etiquetar(df, H.KEYWORDS_SILVER[indicador])
        labels = etq["label"].values
        print(f"\n{'='*72}\n{indicador}  "
              f"(pos={int((etq.label==1).sum())}  neg={int((etq.label==0).sum())})\n{'='*72}")
        print(f"{'variante':<24} {'AUC':>7} {'m_pos':>7} {'m_neg':>7} {'separac':>8}")

        for nombre, hip in variantes.items():
            sc = scorer.score(premisas, hip)
            m = silver.evaluar(sc, labels)
            filas.append({"indicador": indicador, "variante": nombre,
                          "hipotesis": hip, **m})
            print(f"{nombre:<24} {m['auc']:>7.4f} {m['media_pos']:>7.3f} "
                  f"{m['media_neg']:>7.3f} {m['separacion']:>+8.3f}")

    # Control negativo: formato real, contenido imposible
    print(f"\n{'='*72}\nCONTROL ABSURDO (formato real, contenido imposible)\n{'='*72}")
    sc = scorer.score(premisas, H.HIPOTESIS_CONTROL_ABSURDO)
    s = pd.Series(sc)
    print(f"  hipotesis: {H.HIPOTESIS_CONTROL_ABSURDO}")
    print(f"  media={s.mean():.4f}  mediana={s.median():.4f}  max={s.max():.4f}")
    print(f"  prop>0.9 = {(s>0.9).mean():.4f}   prop>0.5 = {(s>0.5).mean():.4f}")
    filas.append({"indicador": "CONTROL_ABSURDO", "variante": "pinguinos",
                  "hipotesis": H.HIPOTESIS_CONTROL_ABSURDO,
                  "auc": float("nan"), "media_pos": float("nan"),
                  "media_neg": float(s.mean()), "separacion": float("nan"),
                  "n_pos": 0, "n_neg": len(s)})

    os.makedirs("resultados", exist_ok=True)
    pd.DataFrame(filas).to_excel(SALIDA, index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
