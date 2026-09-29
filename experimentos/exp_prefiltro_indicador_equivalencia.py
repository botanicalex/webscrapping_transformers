"""
Promocion del pre-filtro por indicador a src/ (log [2026-09-29]): equivalencia offline entre lo que ahora hace
src/Transformer_optimo.py y lo que midio el experimento (experimentos/exp_prefiltro_indicador.py, etapa 1).

Aplica las funciones de src/ (premisa_visible + compuerta_objeto, con la hipotesis de CADA indicador) al corpus
nacional y a datos/scores/scores_v2_32deptos.pkl (union por posicion, sin GPU) y compara con el experimento:
  - las hipotesis y las listas de src coinciden con las del experimento (V2 y REGEX_F5 congelada);
  - compuerta articulo a articulo: src frente a la del experimento con la truncacion de produccion (debe ser
    identica) y frente a la del experimento con su premisa recortada con la hipotesis mas larga (se reporta);
  - MAX de los 26 indicadores por departamento y radar (max|dif| debe ser 0);
  - CalculadorRadar de src/ con los cortes de config_pipeline: 6 Bajo / 19 Medio / 7 Alto;
  - el procedimiento de cortes (elegir_cortes) sobre el radar sin redondear devuelve 0.7572/0.9233 sin
    romper las 12 anclas; Spearman contra el DANE y contra el numero de articulos.

  python experimentos/exp_prefiltro_indicador_equivalencia.py
Salida: experimentos/resultados/exp_prefiltro_indicador_equivalencia.csv
"""
import inspect
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "src"))
import config_pipeline as cfg  # noqa: E402
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import Transformer_optimo as T  # noqa: E402
from exp_5ind_max_cortes import elegir_cortes  # noqa: E402
from exp_correlacion_v2_nacional import NUNCA_ALTO, NUNCA_BAJO, _norm  # noqa: E402

CORPUS = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
PREM_NAC = "experimentos/resultados/juicio_5ind_holdout/premisas_visibles_nacional.pkl"
OFICIAL = "datos/referencia/comparacion_radares_V3.xlsx"
SALIDA = "experimentos/resultados/exp_prefiltro_indicador_equivalencia.csv"
MODELO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"


def clase(v, cb, ca):
    return "Bajo" if v < cb else ("Medio" if v < ca else "Alto")


def main():
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(d) == len(corpus) == 11439
    assert (corpus["titulo"].values == d["titulo"].values).all()
    deps = corpus["departamento"].values
    textos = corpus["texto"].fillna("").astype(str).tolist()
    inds = list(T.PREFILTRO_OBJETO)

    # 1. Hipotesis y listas de src frente al experimento
    fuente = inspect.getsource(T.PipelineTransformers.__init__)
    for ind in inds:
        hip = V2.TODAS[ind]
        assert f'"{ind}": "{hip}"' in fuente, f"hipotesis de {ind} en src distinta de V2"
        assert T.PREFILTRO_OBJETO[ind] == H.REGEX_F5[ind], f"lista de {ind} en src distinta de REGEX_F5"
    print(f"Hipotesis y listas de src iguales a las del experimento en {inds}")

    # 2. Compuertas: src (truncacion de produccion, hipotesis de cada indicador) vs experimento
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local(MODELO))
    prem_exp = pd.read_pickle(PREM_NAC).loc[corpus["url"]].values
    g_src, g_prod, g_exp = {}, {}, {}
    for ind in inds:
        hip = V2.TODAS[ind]
        g_src[ind] = T.compuerta_objeto(T.premisa_visible(textos, tok, hip), ind)
        g_prod[ind] = np.asarray(H.compuerta(H.premisa_visible(textos, tok, [hip]), ind))
        g_exp[ind] = np.asarray(H.compuerta(prem_exp, ind))
        print(f"  {ind}: la compuerta abre en {g_src[ind].mean():.1%}; distinta del experimento con truncacion de produccion en "
              f"{int((g_src[ind] != g_prod[ind]).sum())} articulos; distinta de la del experimento (premisa mas larga) en "
              f"{int((g_src[ind] != g_exp[ind]).sum())}")

    # 3. MAX por departamento: 26 corregidos con las compuertas de src / del experimento (produccion) / (experimento)
    sesgo = d["sesgo"].values
    base = pd.DataFrame({c: np.clip(np.clip(d[f"ent_{c}"].values - sesgo, 0, None) * (1 - d[f"neu_{c}"].values), 0, 1)
                         for c in V2.TODAS})

    def con(gates):
        a = base.copy()
        for ind in inds:
            a[ind] = a[ind] * gates[ind]
        return a

    art_src = con(g_src)
    art_src["departamento"] = deps
    max_src = art_src.groupby("departamento")[list(V2.TODAS)].max()
    max_prod = con(g_prod).assign(departamento=deps).groupby("departamento")[list(V2.TODAS)].max()
    max_exp = con(g_exp).assign(departamento=deps).groupby("departamento")[list(V2.TODAS)].max()
    max_sin = base.assign(departamento=deps).groupby("departamento")[list(V2.TODAS)].max()
    r_src, r_prod, r_exp, r_sin = (m.mean(axis=1) for m in (max_src, max_prod, max_exp, max_sin))
    dif_max_prod = float(np.abs(max_src - max_prod).values.max())
    dif_max_exp = float(np.abs(max_src - max_exp).values.max())
    print(f"max|dif| MAX (26 x 32) src vs experimento-produccion: {dif_max_prod:.1e}; vs experimento-premisa larga: {dif_max_exp:.1e}; "
          f"radar src vs experimento-produccion: {np.abs(r_src - r_prod).max():.1e}, vs premisa larga: {np.abs(r_src - r_exp).max():.1e}")

    # 4. Radar de produccion (src/radar.py) con los cortes de config_pipeline
    rad = T.CalculadorRadar().calcular(art_src).set_index("departamento")
    assert len(rad) == 32
    dif_r = float(np.abs(rad["radar_propio"] - r_prod.round(4).reindex(rad.index)).max())
    dist = rad["categoria_riesgo"].value_counts().to_dict()
    print(f"CalculadorRadar src: cortes cfg {cfg.CORTE_BAJO_MEDIO_RADAR}/{cfg.CORTE_MEDIO_ALTO_RADAR}; dist {dist}; "
          f"max|dif| radar_propio vs experimento {dif_r:.1e}")

    # 5. Procedimiento de cortes (sin redondear, como en el experimento) y anclas
    cb, ca, _, rompe = elegir_cortes(r_src)
    rotas = rompe(cb, ca)
    print(f"elegir_cortes sobre el radar src: {cb}/{ca}; anclas rotas {rotas or 'ninguna'}")
    of = pd.read_excel(OFICIAL, engine="openpyxl")
    of.columns = [str(c).strip() for c in of.columns]
    ofi = of.set_index(of["Departamento"].map(_norm))
    rho_dane = float(spearmanr(r_src.values, ofi.loc[[_norm(k) for k in r_src.index], "radar_oficial_promedio"].values).correlation)
    rho_sin = float(spearmanr(r_sin.values, ofi.loc[[_norm(k) for k in r_sin.index], "radar_oficial_promedio"].values).correlation)
    n_art = pd.Series(deps).value_counts().reindex(r_src.index)
    rho_tam = float(spearmanr(r_src.values, n_art.values).correlation)
    print(f"Spearman contra el DANE: sin mecanismo {rho_sin:+.4f} -> src {rho_dane:+.4f}; con el numero de articulos {rho_tam:+.4f}")
    cl_nueva = rad["categoria_riesgo"]
    cl_vieja = r_sin.reindex(rad.index).map(lambda v: clase(v, 0.766, 0.9233))
    print(f"Departamentos que cambian de clase (0.766/0.9233 sin mecanismo -> 0.7572/0.9233 con src): "
          f"{int((cl_nueva != cl_vieja).sum())}")

    ok = (all(int((g_src[i] != g_prod[i]).sum()) == 0 for i in inds) and dif_max_prod == 0 and dif_r == 0
          and (cb, ca) == (cfg.CORTE_BAJO_MEDIO_RADAR, cfg.CORTE_MEDIO_ALTO_RADAR)
          and dist == {"Medio": 19, "Alto": 7, "Bajo": 6} and not rotas)
    print(f"EQUIVALENCIA pre-filtro por indicador: {'OK' if ok else 'FALLA'}")

    out = pd.DataFrame({"radar_sin_mecanismo": r_sin, "radar_src": r_src, "radar_experimento": r_prod,
                        "radar_propio_src": rad["radar_propio"], "clase_src": rad["categoria_riesgo"],
                        "n_articulos": rad["n_articulos"]})
    for ind in inds:
        out[f"MAX_{ind}_sin"] = max_sin[ind]
        out[f"MAX_{ind}_src"] = max_src[ind]
        out[f"MAX_{ind}_experimento"] = max_prod[ind]
    out.sort_values("radar_src", ascending=False).round(6).to_csv(SALIDA)
    print(f"-> {SALIDA}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
