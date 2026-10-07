"""
Version de 18 indicadores (decision del jefe, 2026-10-06): retiro de movimientos_sociales y
exclusion_servicios_derechos y 3 hipotesis nuevas (conflicto_territorial, zonas_proteccion_alimentaria,
resistencia_territorial). Recalibrar CORTE_BAJO_MEDIO_RADAR / CORTE_MEDIO_ALTO_RADAR (regla 2).

Mismo flujo que exp_retiro_6ind_cortes.py: corpus nacional + datos/scores/scores_v2_32deptos.pkl
(sin GPU) y, para las 3 hipotesis nuevas, ent/neu de datos/scores/scores_hipotesis_jefe_18ind.pkl
(filas corpus == nacional, mismo orden); score corregido con el sesgo y las compuertas
PREFILTRO_OBJETO de src/, MAX por departamento.
  - Sanidad: con la config de 20 (hipotesis actuales), elegir_cortes debe devolver 0.7138/0.905.
  - Con la config de 18: elegir_cortes (huecos naturales > 0.008, 12 anclas, el DANE no se mira).
  - Constancia: clases, Spearman contra el DANE y contra el numero de articulos, deptos que cambian.

  python experimentos/exp_retiro_2ind_cortes.py
Salida: experimentos/resultados/exp_retiro_2ind_cortes.csv
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
SALIDA = "experimentos/resultados/exp_retiro_2ind_cortes.csv"
NUEVAS = "datos/scores/scores_hipotesis_jefe_18ind.pkl"
MODELO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
CORTES_20 = (0.7138, 0.905)
RETIRADOS_6 = ["rechazo_proyecto", "exclusion_beneficios_economicos", "incentivos_economicos_inequitativos",
               "conflicto_activo", "derechos_vulnerados", "exclusion_comunidades"]
RETIRADOS_2 = ["movimientos_sociales", "exclusion_servicios_derechos"]
CAMBIADAS = ["conflicto_territorial", "zonas_proteccion_alimentaria", "resistencia_territorial"]


def clase(v, cb, ca):
    return "Bajo" if v < cb else ("Medio" if v < ca else "Alto")


def main():
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(d) == len(corpus) == 11439
    assert (corpus["titulo"].values == d["titulo"].values).all()
    nu = pd.read_pickle(NUEVAS)
    nu = nu[nu["corpus"] == "nacional"].reset_index(drop=True)
    assert len(nu) == 11439 and (nu["titulo"].values == corpus["titulo"].values).all()
    assert np.allclose(nu["sesgo"].values, d["sesgo"].values)
    deps = corpus["departamento"].values
    textos = corpus["texto"].fillna("").astype(str).tolist()
    todas = list(V2.TODAS)
    assert len(todas) == 26 and set(RETIRADOS_6) <= set(todas)
    q20 = [c for c in todas if c not in RETIRADOS_6]
    q18 = [c for c in q20 if c not in RETIRADOS_2]
    assert len(q20) == 20 and len(q18) == 18 and set(CAMBIADAS) <= set(q18)

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local(MODELO))
    sesgo = d["sesgo"].values

    def corr(ent, neu):
        return np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)

    art = pd.DataFrame({c: corr(d[f"ent_{c}"].values, d[f"neu_{c}"].values) for c in todas})
    art_n = art.copy()
    for c in CAMBIADAS:
        art_n[c] = corr(nu[f"ent_nueva_{c}"].values, nu[f"neu_nueva_{c}"].values)
    for ind in T.PREFILTRO_OBJETO:   # grupos armados y desplazamiento: hipotesis sin cambio
        comp = T.compuerta_objeto(T.premisa_visible(textos, tok, V2.TODAS[ind]), ind)
        art[ind] = art[ind] * comp
        art_n[ind] = art_n[ind] * comp
    mx = art.assign(departamento=deps).groupby("departamento")[todas].max()
    mx_n = art_n.assign(departamento=deps).groupby("departamento")[todas].max()
    assert mx.shape == (32, 26)
    r20, r18 = mx[q20].mean(axis=1), mx_n[q18].mean(axis=1)

    cb20, ca20, _, rompe20 = elegir_cortes(r20)
    print(f"Sanidad 20 indicadores: elegir_cortes {cb20}/{ca20} (esperado {CORTES_20[0]}/{CORTES_20[1]}); "
          f"anclas rotas {rompe20(cb20, ca20) or 'ninguna'}")
    sanidad = (cb20, ca20) == CORTES_20

    cb, ca, cand, rompe = elegir_cortes(r18)
    rotas = rompe(cb, ca)
    print(f"18 indicadores: elegir_cortes {cb}/{ca}; anclas rotas {rotas or 'ninguna'}; huecos candidatos {len(cand)}")

    of = pd.read_excel(OFICIAL, engine="openpyxl")
    of.columns = [str(c).strip() for c in of.columns]
    ofi = of.set_index(of["Departamento"].map(_norm))
    n_art = pd.Series(deps).value_counts()
    for nombre, r in (("20", r20), ("18", r18)):
        dane = ofi.loc[[_norm(k) for k in r.index], "radar_oficial_promedio"].values
        print(f"  Spearman {nombre}: DANE {spearmanr(r.values, dane).correlation:+.4f}; "
              f"numero de articulos {spearmanr(r.values, n_art.reindex(r.index).values).correlation:+.4f}")

    cl20 = r20.map(lambda v: clase(v, *CORTES_20))
    cl18 = r18.map(lambda v: clase(v, cb, ca))
    oficial = ofi.loc[[_norm(k) for k in r18.index], "Clasificacion_radar_oficial_promedio"].values
    print(f"Clases 20: {cl20.value_counts().to_dict()}; clases 18: {cl18.value_counts().to_dict()}")
    print(f"Accuracy contra el DANE (constancia): 20 {float((cl20.values == oficial).mean()):.3f}; "
          f"18 {float((cl18.values == oficial).mean()):.3f}")
    cambian = cl20[cl20 != cl18]
    print(f"Departamentos que cambian de clase: {len(cambian)}")
    for dep in cambian.index:
        print(f"  {dep}: {cl20[dep]} ({r20[dep]:.4f}) -> {cl18[dep]} ({r18[dep]:.4f})")

    out = pd.DataFrame({"radar_20": r20, "clase_20": cl20, "radar_18": r18, "clase_18": cl18,
                        "n_articulos": n_art.reindex(r18.index)})
    out.sort_values("radar_18", ascending=False).round(6).to_csv(SALIDA)
    print(f"-> {SALIDA}")
    print(f"RESULTADO: sanidad {'OK' if sanidad else 'FALLA'}; cortes 18 = {cb}/{ca}; anclas {'OK' if not rotas else 'ROTAS'}")
    if not sanidad or rotas:
        sys.exit(1)


if __name__ == "__main__":
    main()
