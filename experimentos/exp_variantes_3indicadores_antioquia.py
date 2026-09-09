"""
Prueba las 3 hipotesis nuevas (rechazo_proyecto, exclusion_beneficios_economicos,
derechos_vulnerados) contra las vigentes en produccion, sobre los 102 articulos de
Antioquia anotados a mano en resultados/muestra_manual_antioquia_3indicadores.xlsx.

Pregunta: la reescritura reduce los falsos positivos observados en produccion sin
perder los positivos reales, y sobrevive el control absurdo?

Evidencia a favor: separacion positivo/negativo igual o mejor que la vieja, y
el control absurdo (NULA_TEST en el formato de cada variante) no empeora.
Evidencia en contra: el AUC/separacion empeora, o el control absurdo sube.

Nota metodologica (regla 11 del proyecto, aplicada aqui de forma mas estricta):
- derechos_vulnerados tiene 12 positivos de 102 -> AUC calculable, con cautela.
- rechazo_proyecto tiene 2 positivos de 102 -> AUC no es confiable (n insuficiente).
  Se reporta en su lugar el score de los 2 positivos conocidos y la media de los
  100 negativos, vieja vs nueva.
- exclusion_beneficios_economicos tiene 0 positivos -> no hay AUC posible. Se
  reporta solo la media de los 102 (todos negativos) y el control absurdo.
"""
import json
import numpy as np
import pandas as pd

import nli_core as nc
from silver import auc, evaluar

RUTA_MUESTRA = "_muestra_anotacion_antioquia.jsonl"
RUTA_LABELS = "../resultados/muestra_manual_antioquia_3indicadores.xlsx"
RUTA_SCORES_OUT = "../datos/scores/scores_variantes_3indicadores_antioquia.pkl"  # ent_/neu_ sin enmascarar (regla 8)

HIPOTESIS = {
    "rechazo_proyecto_vieja": "Hay oposición de comunidades o autoridades a un proyecto.",
    "rechazo_proyecto_nueva": "Una comunidad o autoridad se opuso a la ejecución de un proyecto específico.",
    "exclusion_beneficios_economicos_vieja": "Una comunidad quedó excluida de los beneficios económicos de un proyecto.",
    "exclusion_beneficios_economicos_nueva": "Una comunidad no recibió compensaciones o beneficios económicos de un proyecto.",
    "derechos_vulnerados_vieja": "Se vulneraron los derechos de una comunidad.",
    "derechos_vulnerados_nueva": "Una comunidad denunció la vulneración de sus derechos.",
}

NULAS_CALIBRACION = [
    "En este territorio hay presencia de pingüinos emperador.",
    "En este territorio hay yacimientos de helio-3 lunar.",
    "En este territorio se practica la caligrafía medieval japonesa.",
    "En este territorio hay glaciares de metano líquido.",
]

# Control absurdo: NULA_TEST reservada, reescrita en el formato de cada variante
# (regla 3). Las viejas comparten el formato declarativo generico de V2; solo
# derechos_vulnerados_nueva cambia de formato (denuncia), asi que ahi si hace
# falta una version distinta. Para rechazo/exclusion nuevas, tambien se
# construye una version igual de especifica por prudencia.
NULA_TEST = {
    "generica": "En este territorio hay colonias de osos polares.",
    "rechazo_nueva": "Una comunidad o autoridad se opuso a la llegada de pingüinos emperador a su territorio.",
    "exclusion_nueva": "Una comunidad no recibió compensaciones ni beneficios económicos por la presencia de pingüinos emperador en su territorio.",
    "derechos_nueva": "Una comunidad denunció la presencia de pingüinos emperador en su territorio.",
}


def cargar_muestra():
    rows = []
    with open(RUTA_MUESTRA, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    return df


def main():
    df = cargar_muestra()
    labels = pd.read_excel(RUTA_LABELS)
    df = df.merge(
        labels[[
            "idx_original",
            "rechazo_proyecto_LLM",
            "exclusion_beneficios_economicos_LLM",
            "derechos_vulnerados_LLM",
        ]],
        on="idx_original", how="left",
    )

    textos = df["texto"].fillna("").astype(str).tolist()
    scorer = nc.NLIScorer(verbose=True)

    resultados = {}
    todas_hipotesis = dict(HIPOTESIS)
    for k, v in NULA_TEST.items():
        todas_hipotesis[f"nula_test_{k}"] = v
    for i, texto_nula in enumerate(NULAS_CALIBRACION):
        todas_hipotesis[f"nula_calibracion_{i}"] = texto_nula

    for nombre, hipotesis in todas_hipotesis.items():
        print(f"Puntuando: {nombre} -> {hipotesis!r}")
        p = scorer.score(textos, hipotesis, devolver_todo=True)
        resultados[f"ent_{nombre}"] = p["entailment"]
        resultados[f"neu_{nombre}"] = p["neutral"]

    out = df.copy()
    for k, v in resultados.items():
        out[k] = v

    # sesgo por articulo (regla 4: NULA_TEST no entra aqui)
    sesgo = np.mean([
        np.asarray(resultados[f"ent_nula_calibracion_{i}"]) for i in range(len(NULAS_CALIBRACION))
    ], axis=0)
    out["sesgo"] = sesgo

    def corregido(ent_col, neu_col):
        ent = np.asarray(out[ent_col], dtype=float)
        neu = np.asarray(out[neu_col], dtype=float)
        return np.clip(np.clip(ent - out["sesgo"].values, 0, None) * (1 - neu), 0, 1)

    for base in ["rechazo_proyecto_vieja", "rechazo_proyecto_nueva",
                 "exclusion_beneficios_economicos_vieja", "exclusion_beneficios_economicos_nueva",
                 "derechos_vulnerados_vieja", "derechos_vulnerados_nueva"]:
        out[f"score_{base}"] = corregido(f"ent_{base}", f"neu_{base}")

    for base in ["nula_test_generica", "nula_test_rechazo_nueva",
                 "nula_test_exclusion_nueva", "nula_test_derechos_nueva"]:
        out[f"score_{base}"] = corregido(f"ent_{base}", f"neu_{base}")

    out.to_pickle(RUTA_SCORES_OUT)
    print(f"\nGuardado {RUTA_SCORES_OUT} con ent_/neu_ sin enmascarar (regla 8).")

    print("\n" + "=" * 70)
    print("RESULTADOS")
    print("=" * 70)

    # --- derechos_vulnerados: AUC calculable (12 positivos) ---
    print("\n--- derechos_vulnerados (12 positivos / 102) ---")
    y = out["derechos_vulnerados_LLM"].values
    for variante in ["vieja", "nueva"]:
        s = out[f"score_derechos_vulnerados_{variante}"].values
        ev = evaluar(s, y)
        print(f"  {variante:6s} AUC={ev['auc']:.4f}  media_pos={ev['media_pos']:.4f}  "
              f"media_neg={ev['media_neg']:.4f}  separacion={ev['separacion']:.4f}  "
              f"n_pos={ev['n_pos']} n_neg={ev['n_neg']}")
    control_vieja = out["score_nula_test_generica"].mean()
    control_nueva = out["score_nula_test_derechos_nueva"].mean()
    print(f"  Control absurdo (media sobre 102): vieja(generica)={control_vieja:.4f}  "
          f"nueva(formato denuncia)={control_nueva:.4f}")

    # --- rechazo_proyecto: solo 2 positivos, AUC no confiable ---
    print("\n--- rechazo_proyecto (2 positivos / 102 -- AUC NO confiable, se reporta directo) ---")
    idx_pos = out.index[out["rechazo_proyecto_LLM"] == 1]
    idx_neg = out.index[out["rechazo_proyecto_LLM"] == 0]
    for variante in ["vieja", "nueva"]:
        s = out[f"score_rechazo_proyecto_{variante}"]
        print(f"  {variante:6s} score en los 2 positivos conocidos: "
              f"{s.loc[idx_pos].round(4).tolist()}  |  media de los {len(idx_neg)} negativos: {s.loc[idx_neg].mean():.4f}")
    control_vieja = out["score_nula_test_generica"].mean()
    control_nueva = out["score_nula_test_rechazo_nueva"].mean()
    print(f"  Control absurdo (media sobre 102): vieja(generica)={control_vieja:.4f}  "
          f"nueva(formato especifico)={control_nueva:.4f}")

    # --- exclusion_beneficios_economicos: 0 positivos, ni AUC ni sensibilidad ---
    print("\n--- exclusion_beneficios_economicos (0 positivos / 102 -- sin AUC posible) ---")
    for variante in ["vieja", "nueva"]:
        s = out[f"score_exclusion_beneficios_economicos_{variante}"]
        print(f"  {variante:6s} media sobre los 102 (todos negativos): {s.mean():.4f}  "
              f"| p95: {s.quantile(0.95):.4f} | max: {s.max():.4f}")
    control_vieja = out["score_nula_test_generica"].mean()
    control_nueva = out["score_nula_test_exclusion_nueva"].mean()
    print(f"  Control absurdo (media sobre 102): vieja(generica)={control_vieja:.4f}  "
          f"nueva(formato especifico)={control_nueva:.4f}")


if __name__ == "__main__":
    main()
