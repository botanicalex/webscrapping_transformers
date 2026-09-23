"""
Reversion de la F8 del plan 5ind MAX (2026-09-23): comprobacion offline, sin GPU.

Regla del usuario: de cada indicador solo se cambia la hipotesis; ni compuertas ni columnas
nuevas. src/ vuelve al estado de base-26ind-f7 (= radar-max_Septiembre). Aqui se comprueba, con
el corpus nacional y datos/scores/scores_v2_32deptos.pkl (union por posicion), que:
  - src/ ya no tiene compuerta (ni funcion ni columna auxiliar);
  - el radar de CalculadorRadar (26 indicadores V2, MAX) coincide con el V01 de F7 (max|dif| 0);
  - cortes de config_pipeline = 0.766 / 0.9233 y clasificacion 6 Bajo / 19 Medio / 7 Alto;
  - el procedimiento de b060b3b sobre ese radar devuelve esos mismos cortes sin romper anclas.

  python experimentos/exp_5ind_max_f8_reversion.py
Salida: experimentos/resultados/juicio_5ind_holdout/f8_reversion.csv
(exp_5ind_max_f8_equivalencia.py queda como registro historico: depende de la compuerta de src/.)
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "src"))
import config_pipeline as cfg  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import Transformer_optimo as T  # noqa: E402
from exp_5ind_max_cortes import CORPUS, DIR, V2NAC, elegir_cortes, radar_max  # noqa: E402


def main():
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(d) == len(corpus)
    deps = corpus["departamento"].values

    sin_compuerta = not any("compuerta" in n.lower() for n in dir(T))
    print(f"src/ sin compuerta: {sin_compuerta}")

    sesgo = d["sesgo"].values
    art = pd.DataFrame({c: np.clip(np.clip(d[f"ent_{c}"].values - sesgo, 0, None) * (1 - d[f"neu_{c}"].values), 0, 1)
                        for c in V2.TODAS})
    art["departamento"] = deps
    r_v01, _ = radar_max(d, deps)  # F7, V01 en los 26
    rad = T.CalculadorRadar().calcular(art).set_index("departamento")
    assert len(rad) == 32
    dif_r = np.abs(rad["radar_propio"] - r_v01.round(4).reindex(rad.index)).max()
    dist = rad["categoria_riesgo"].value_counts().to_dict()
    cb, ca, _, rompe = elegir_cortes(art.groupby("departamento")[list(V2.TODAS)].max().mean(axis=1))
    print(f"CalculadorRadar src: cortes cfg {cfg.CORTE_BAJO_MEDIO_RADAR}/{cfg.CORTE_MEDIO_ALTO_RADAR}; "
          f"dist {dist}; max|dif| radar_propio vs V01 de F7 {dif_r:.1e}")
    print(f"Procedimiento b060b3b sobre el radar src: {cb}/{ca}; anclas rotas {rompe(cb, ca) or 'ninguna'}")

    ok = (sin_compuerta and dif_r == 0 and (cb, ca) == (0.766, 0.9233)
          and (cfg.CORTE_BAJO_MEDIO_RADAR, cfg.CORTE_MEDIO_ALTO_RADAR) == (0.766, 0.9233)
          and dist == {"Medio": 19, "Alto": 7, "Bajo": 6} and not rompe(cb, ca))
    print(f"REVERSION F8: {'OK' if ok else 'FALLA'}")

    rad[["radar_propio", "categoria_riesgo", "n_articulos"]].sort_values("radar_propio", ascending=False) \
        .to_csv(os.path.join(DIR, "f8_reversion.csv"))
    print(f"-> {DIR}/f8_reversion.csv")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
