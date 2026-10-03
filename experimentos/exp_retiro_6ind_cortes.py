"""
Retiro de 6 indicadores (decision de la reunion con el jefe, 2026-10-03): recalibrar
CORTE_BAJO_MEDIO_RADAR / CORTE_MEDIO_ALTO_RADAR con los 20 restantes (regla 2: cambia lo medido).

Mismo flujo que exp_prefiltro_indicador_equivalencia.py: corpus nacional + datos/scores/scores_v2_32deptos.pkl
(sin GPU), score corregido con el sesgo y las compuertas PREFILTRO_OBJETO de src/, MAX por departamento.
  - Sanidad: con los 26 indicadores, elegir_cortes debe devolver 0.7572/0.9233 (produccion actual).
  - Con los 20: elegir_cortes (huecos naturales > 0.008, 12 anclas, el DANE no se mira para elegir).
  - Constancia: distribucion de clases, Spearman contra el DANE y contra el numero de articulos,
    departamentos que cambian de clase.

  python experimentos/exp_retiro_6ind_cortes.py
Salida: experimentos/resultados/exp_retiro_6ind_cortes.csv
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "src"))
import hipotesis_v2 as V2  # noqa: E402
import Transformer_optimo as T  # noqa: E402
from exp_5ind_max_cortes import elegir_cortes  # noqa: E402
from exp_correlacion_v2_nacional import _norm  # noqa: E402

CORPUS = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
OFICIAL = "datos/referencia/comparacion_radares_V3.xlsx"
SALIDA = "experimentos/resultados/exp_retiro_6ind_cortes.csv"
MODELO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
CORTES_26 = (0.7572, 0.9233)
RETIRADOS = ["rechazo_proyecto", "exclusion_beneficios_economicos", "incentivos_economicos_inequitativos",
             "conflicto_activo", "derechos_vulnerados", "exclusion_comunidades"]


def clase(v, cb, ca):
    return "Bajo" if v < cb else ("Medio" if v < ca else "Alto")


def main():
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(d) == len(corpus) == 11439
    assert (corpus["titulo"].values == d["titulo"].values).all()
    deps = corpus["departamento"].values
    textos = corpus["texto"].fillna("").astype(str).tolist()
    todas = list(V2.TODAS)
    assert len(todas) == 26 and set(RETIRADOS) <= set(todas)
    quedan = [c for c in todas if c not in RETIRADOS]
    assert len(quedan) == 20

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local(MODELO))
    sesgo = d["sesgo"].values
    art = pd.DataFrame({c: np.clip(np.clip(d[f"ent_{c}"].values - sesgo, 0, None) * (1 - d[f"neu_{c}"].values), 0, 1)
                        for c in todas})
    for ind in T.PREFILTRO_OBJETO:
        art[ind] = art[ind] * T.compuerta_objeto(T.premisa_visible(textos, tok, V2.TODAS[ind]), ind)
    mx = art.assign(departamento=deps).groupby("departamento")[todas].max()
    assert mx.shape == (32, 26)
    r26, r20 = mx[todas].mean(axis=1), mx[quedan].mean(axis=1)

    cb26, ca26, _, rompe26 = elegir_cortes(r26)
    print(f"Sanidad 26 indicadores: elegir_cortes {cb26}/{ca26} (esperado {CORTES_26[0]}/{CORTES_26[1]}); "
          f"anclas rotas {rompe26(cb26, ca26) or 'ninguna'}")
    sanidad = (cb26, ca26) == CORTES_26

    cb, ca, cand, rompe = elegir_cortes(r20)
    rotas = rompe(cb, ca)
    print(f"20 indicadores: elegir_cortes {cb}/{ca}; anclas rotas {rotas or 'ninguna'}; huecos candidatos {len(cand)}")

    of = pd.read_excel(OFICIAL, engine="openpyxl")
    of.columns = [str(c).strip() for c in of.columns]
    ofi = of.set_index(of["Departamento"].map(_norm))
    n_art = pd.Series(deps).value_counts()
    for nombre, r in (("26", r26), ("20", r20)):
        dane = ofi.loc[[_norm(k) for k in r.index], "radar_oficial_promedio"].values
        print(f"  Spearman {nombre}: DANE {spearmanr(r.values, dane).correlation:+.4f}; "
              f"numero de articulos {spearmanr(r.values, n_art.reindex(r.index).values).correlation:+.4f}")

    cl26 = r26.map(lambda v: clase(v, *CORTES_26))
    cl20 = r20.map(lambda v: clase(v, cb, ca))
    oficial = ofi.loc[[_norm(k) for k in r20.index], "Clasificacion_radar_oficial_promedio"].values
    print(f"Clases 26: {cl26.value_counts().to_dict()}; clases 20: {cl20.value_counts().to_dict()}")
    print(f"Accuracy contra el DANE (constancia): 26 {float((cl26.values == oficial).mean()):.3f}; "
          f"20 {float((cl20.values == oficial).mean()):.3f}")
    cambian = cl26[cl26 != cl20]
    print(f"Departamentos que cambian de clase: {len(cambian)}")
    for dep in cambian.index:
        print(f"  {dep}: {cl26[dep]} ({r26[dep]:.4f}) -> {cl20[dep]} ({r20[dep]:.4f})")

    out = pd.DataFrame({"radar_26": r26, "clase_26": cl26, "radar_20": r20, "clase_20": cl20,
                        "n_articulos": n_art.reindex(r20.index)})
    out.sort_values("radar_20", ascending=False).round(6).to_csv(SALIDA)
    print(f"-> {SALIDA}")
    print(f"RESULTADO: sanidad {'OK' if sanidad else 'FALLA'}; cortes 20 = {cb}/{ca}; anclas {'OK' if not rotas else 'ROTAS'}")
    if not sanidad or rotas:
        sys.exit(1)


if __name__ == "__main__":
    main()
