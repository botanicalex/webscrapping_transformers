"""
F8 del plan 5ind MAX: equivalencia offline entre la compuerta promovida a src/ y la de F7.

Aplica las funciones de src/Transformer_optimo.py (premisa_visible + compuerta_grupos_armados)
al corpus nacional y a datos/scores/scores_v2_32deptos.pkl (union por posicion, sin GPU), y
compara con exp_5ind_max_cortes.py (truncacion de produccion):
  - compuerta articulo a articulo (debe ser identica);
  - MAX de los 26 indicadores por departamento y radar (max|dif| debe ser 0);
  - CalculadorRadar de src/ con los cortes de config_pipeline: 6 Bajo / 19 Medio / 7 Alto,
    y el procedimiento de b060b3b sobre ese radar debe devolver los mismos cortes.

  python experimentos/exp_5ind_max_f8_equivalencia.py
Salida: experimentos/resultados/juicio_5ind_holdout/f8_equivalencia.csv
"""
import inspect
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "src"))
import config_pipeline as cfg  # noqa: E402
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import Transformer_optimo as T  # noqa: E402
from exp_5ind_max_cortes import CORPUS, DIR, GA, V2NAC, elegir_cortes, radar_max  # noqa: E402


def main():
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(d) == len(corpus)
    deps = corpus["departamento"].values
    textos = corpus["texto"].fillna("").astype(str).tolist()

    vig = H.HIPOTESIS[GA]["vig"]
    assert f'"{GA}": "{vig}"' in inspect.getsource(T.PipelineTransformers.__init__), "hipotesis de src distinta"
    assert T.REGEX_COMPUERTA_GRUPOS_ARMADOS == H.REGEX_F5[GA], "regex de src distinta de la del experimento"

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local("MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"))
    g_src = T.compuerta_grupos_armados(T.premisa_visible(textos, tok, vig))
    g_f7 = np.asarray(H.compuerta(H.premisa_visible(textos, tok, [vig]), GA))
    prem_exp = pd.read_pickle(os.path.join(DIR, "premisas_visibles_nacional.pkl")).loc[corpus["url"]]
    g_exp = np.asarray(H.compuerta(prem_exp.values, GA))
    print(f"Compuerta src abre en {g_src.mean():.1%}; distinta de F7-produccion en {int((g_src != g_f7).sum())} "
          f"articulos; distinta de F7-experimento en {int((g_src != g_exp).sum())} (F7 midio 16)")

    # MAX por departamento: src (26 corregidos, grupos x compuerta) vs exp_5ind_max_cortes.
    sesgo = d["sesgo"].values
    art = pd.DataFrame({c: np.clip(np.clip(d[f"ent_{c}"].values - sesgo, 0, None) * (1 - d[f"neu_{c}"].values), 0, 1)
                        for c in V2.TODAS})
    art[GA] = art[GA] * g_src
    art["departamento"] = deps
    art["compuerta_grupos_armados"] = g_src
    max_src = art.groupby("departamento")[list(V2.TODAS)].max()
    r_f7, ga_f7 = radar_max(d, deps, g_f7)
    print(f"max|dif| MAX grupos src vs F7: {np.abs(max_src[GA] - ga_f7).max():.1e}; "
          f"radar (media 26) src vs F7: {np.abs(max_src.mean(axis=1) - r_f7).max():.1e}")

    # Radar de produccion (src/radar.py) con los cortes de config_pipeline.
    rad = T.CalculadorRadar().calcular(art).set_index("departamento")
    assert len(rad) == 32
    dif_r = np.abs(rad["radar_propio"] - r_f7.round(4).reindex(rad.index)).max()
    dist = rad["categoria_riesgo"].value_counts().to_dict()
    # El procedimiento de cortes va sobre el radar SIN redondear, como en F7: sobre
    # radar_propio (round 4) el punto medio del hueco alto cae en 0.92335 -> 0.9234.
    cb, ca, _, rompe = elegir_cortes(max_src.mean(axis=1))
    print(f"CalculadorRadar src: cortes cfg {cfg.CORTE_BAJO_MEDIO_RADAR}/{cfg.CORTE_MEDIO_ALTO_RADAR}; "
          f"dist {dist}; max|dif| radar_propio vs F7 {dif_r:.1e}")
    print(f"Procedimiento b060b3b sobre el radar src: {cb}/{ca}; anclas rotas {rompe(cb, ca) or 'ninguna'}")

    ok = (int((g_src != g_f7).sum()) == 0 and np.abs(max_src[GA] - ga_f7).max() == 0 and dif_r == 0
          and (cb, ca) == (cfg.CORTE_BAJO_MEDIO_RADAR, cfg.CORTE_MEDIO_ALTO_RADAR)
          and dist == {"Medio": 19, "Alto": 7, "Bajo": 6} and not rompe(cb, ca))
    print(f"EQUIVALENCIA F8: {'OK' if ok else 'FALLA'}")

    out = pd.DataFrame({"ga_max_src": max_src[GA], "ga_max_f7": ga_f7, "radar_src": rad["radar_propio"],
                        "radar_f7": r_f7.round(4), "clase_src": rad["categoria_riesgo"],
                        "n_articulos": rad["n_articulos"]}).sort_values("radar_src", ascending=False)
    out.to_csv(os.path.join(DIR, "f8_equivalencia.csv"))
    print(f"-> {DIR}/f8_equivalencia.csv")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
