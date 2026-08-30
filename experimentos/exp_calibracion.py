"""
EXPERIMENTO 3 — calibracion por articulo.

Hallazgo que motiva esto: incluso con la mejor configuracion (premisa=cuerpo,
hipotesis V1 sin metalenguaje) el control absurdo sigue en media 0.466 y dice
"si" a los pinguinos en el 20% de los articulos. Hay articulos "si-decidores"
que puntuan alto contra cualquier hipotesis.

Idea: estimar ese sesgo POR ARTICULO con un conjunto de hipotesis nulas
(contenido imposible en dominios variados) y descontarlo. Es la misma logica de
la "contextual calibration" del prompting: medir la respuesta del modelo ante
entradas sin informacion y usarla como linea base.

DISENO CRITICO: se calibra con 4 nulas y se evalua el control con una QUINTA
nula RESERVADA. Si se evaluara con las mismas nulas de calibracion el control
daria 0 por construccion y no probaria nada.

Tambien se prueba el aprovechamiento de P(neutral): el exp2 mostro que la masa
de neutral es la que carga la senal de "este texto no habla de eso" (por eso
normalizar ent/(ent+con) empeoro tanto el control absurdo).
"""
import os

import numpy as np
import pandas as pd

import hipotesis_base as H
import silver
from nli_core import NLIScorer

CORPUS = "../datos/corpus/df_corpus_5lugares.pkl"
SALIDA = "resultados/exp3_calibracion.xlsx"

# Mejor configuracion del exp1+exp2
HIPOTESIS_V1 = {
    "presencia_grupos_armados": "En este territorio hay presencia de grupos armados ilegales.",
    "grupos_etnicos_existentes": "En este territorio hay comunidades étnicas o pueblos indígenas.",
}

# Nulas de calibracion: formato V1, dominios variados, todas imposibles
NULAS_CALIBRACION = [
    "En este territorio hay presencia de pingüinos emperador.",
    "En este territorio hay yacimientos de helio-3 lunar.",
    "En este territorio se practica la caligrafía medieval japonesa.",
    "En este territorio hay glaciares de metano líquido.",
]
# Reservada — NO entra en la calibracion, sirve para evaluar honestamente
NULA_TEST = "En este territorio hay colonias de osos polares."


def main():
    df = pd.read_pickle(CORPUS)
    print(f"Corpus: {len(df)} articulos")
    scorer = NLIScorer()
    prem = df["texto"].fillna("").astype(str).tolist()

    print("\nEstimando sesgo por articulo con 4 hipotesis nulas...")
    nulas = []
    for h in NULAS_CALIBRACION:
        nulas.append(np.asarray(scorer.score(prem, h), dtype=float))
    sesgo = np.mean(nulas, axis=0)
    s_ser = pd.Series(sesgo)
    print(f"  sesgo por articulo: media={s_ser.mean():.4f}  mediana={s_ser.median():.4f}  "
          f"p90={s_ser.quantile(.9):.4f}  max={s_ser.max():.4f}")
    print(f"  articulos con sesgo>0.9 ('si-decidores'): {(s_ser>0.9).mean():.1%}")

    print("\nPuntuando la nula RESERVADA (control honesto)...")
    p_test = scorer.score(prem, NULA_TEST, devolver_todo=True)
    ctrl_raw = np.asarray(p_test["entailment"], dtype=float)
    ctrl_neu = np.asarray(p_test["neutral"], dtype=float)

    filas = []

    def registrar(nombre, ind, sc, y, ctrl):
        m = silver.evaluar(sc, y)
        c = pd.Series(ctrl)
        filas.append({"indicador": ind, "correccion": nombre,
                      "auc": m["auc"], "separacion": m["separacion"],
                      "media_pos": m["media_pos"], "media_neg": m["media_neg"],
                      "ctrl_media": float(c.mean()), "ctrl_prop09": float((c > 0.9).mean())})
        print(f"{nombre:<22}{m['auc']:>8.4f}{m['separacion']:>+10.3f}"
              f"{m['media_neg']:>10.3f}{c.mean():>11.4f}{(c>0.9).mean():>10.4f}")

    for ind, hip in HIPOTESIS_V1.items():
        y = silver.etiquetar(df, H.KEYWORDS_SILVER[ind])["label"].values
        p = scorer.score(prem, hip, devolver_todo=True)
        ent = np.asarray(p["entailment"], dtype=float)
        neu = np.asarray(p["neutral"], dtype=float)

        print(f"\n{'='*74}\n{ind}  (pos={int((y==1).sum())} neg={int((y==0).sum())})\n{'='*74}")
        print(f"{'correccion':<22}{'AUC':>8}{'separac':>10}{'m_neg':>10}"
              f"{'ctrl med':>11}{'ctrl>.9':>10}")

        registrar("raw (V1)", ind, ent, y, ctrl_raw)
        registrar("resta_sesgo", ind, ent - sesgo, y, ctrl_raw - sesgo)
        registrar("resta_sesgo_clip0", ind, np.clip(ent - sesgo, 0, None), y,
                  np.clip(ctrl_raw - sesgo, 0, None))
        registrar("por_1_menos_neu", ind, ent * (1 - neu), y, ctrl_raw * (1 - ctrl_neu))
        registrar("ent_menos_neu", ind, ent - neu, y, ctrl_raw - ctrl_neu)
        registrar("combinada", ind, np.clip(ent - sesgo, 0, None) * (1 - neu), y,
                  np.clip(ctrl_raw - sesgo, 0, None) * (1 - ctrl_neu))

    os.makedirs("resultados", exist_ok=True)
    pd.DataFrame(filas).to_excel(SALIDA, index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
