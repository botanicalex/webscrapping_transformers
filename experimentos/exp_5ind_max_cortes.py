"""
F7 del plan 5ind MAX, paso 3: recalibrar CORTE_BAJO_MEDIO_RADAR / CORTE_MEDIO_ALTO_RADAR
con los 26 indicadores y V08 en `presencia_grupos_armados` (regla 2: cambia lo medido).

Procedimiento del commit b060b3b (calco de exp_cortes_fijos_v2_sin_prefiltro.py con MAX en
vez de P75): radar = media de los 26 MAX por departamento; huecos naturales > 0.008 en la
distribucion nacional, sin pegarse a los extremos; entre los pares que no rompen ninguna de
las 12 anclas (09_riesgos_y_limites.md) se elige el mas balanceado (max de la clase mas
chica), desempate por tamano combinado de hueco. El oficial DANE NO se mira para elegir;
accuracy y Spearman solo como constancia.

Sanidad previa: con V01 (produccion actual) el procedimiento debe devolver 0.766 / 0.9233.

  python experimentos/exp_5ind_max_cortes.py
Salida: experimentos/resultados/juicio_5ind_holdout/cortes_radar.xlsx
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
from exp_correlacion_v2_nacional import NUNCA_ALTO, NUNCA_BAJO, _norm  # noqa: E402

CORPUS = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
REFERENCIA = "datos/referencia/comparacion_radares_V3.xlsx"
DIR = "experimentos/resultados/juicio_5ind_holdout"
GA = "presencia_grupos_armados"
UMBRAL_HUECO_GRANDE = 0.008
CORTES_B060 = (0.766, 0.9233)


def clasificar(v, cb, ca):
    return "Bajo" if v < cb else ("Medio" if v < ca else "Alto")


def radar_max(d: pd.DataFrame, deps: np.ndarray, g_grupos=None):
    """Media de los 26 MAX por departamento; si g_grupos, grupos armados = V08 (s(vig)*g)."""
    sesgo = d["sesgo"].values
    cols = {}
    for c in V2.TODAS:
        e, n = d[f"ent_{c}"].values, d[f"neu_{c}"].values
        x = np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)
        cols[c] = x * g_grupos if (c == GA and g_grupos is not None) else x
    m = pd.DataFrame(cols).groupby(deps).max()
    assert m.shape == (32, 26), m.shape
    return m.mean(axis=1), m[GA]


def elegir_cortes(radar: pd.Series):
    vals = np.sort(radar.values)[::-1]
    valor = {_norm(k): v for k, v in radar.items()}
    anclas = [(_norm(x), "Alto") for x in NUNCA_ALTO] + [(_norm(x), "Bajo") for x in NUNCA_BAJO]
    assert all(k in valor for k, _ in anclas), [k for k, _ in anclas if k not in valor]

    def rompe(cb, ca):
        return [k for k, prohibida in anclas if clasificar(valor[k], cb, ca) == prohibida]

    huecos = sorted(((vals[i] - vals[i + 1], i) for i in range(len(vals) - 1)), reverse=True)
    cand = [(g, i) for g, i in huecos if g > UMBRAL_HUECO_GRANDE and 2 <= i + 1 <= len(vals) - 3]
    mejor = None
    for gi, (g_i, i) in enumerate(cand):
        for g_j, j in cand[gi + 1:]:
            ib, ia = max(i, j), min(i, j)
            cb = round((vals[ib] + vals[ib + 1]) / 2, 4)
            ca = round((vals[ia] + vals[ia + 1]) / 2, 4)
            if cb >= ca or rompe(cb, ca):
                continue
            nb, na = int((vals < cb).sum()), int((vals >= ca).sum())
            clave = (min(nb, len(vals) - nb - na, na), g_i + g_j)
            if mejor is None or clave > mejor[0]:
                mejor = (clave, cb, ca)
    if mejor is None:
        raise RuntimeError("Ningun par de huecos naturales evita romper las anclas")
    return mejor[1], mejor[2], cand, rompe


def constancia(radar: pd.Series, cb, ca, oficial: pd.DataFrame) -> dict:
    r = pd.DataFrame({"_k": [_norm(k) for k in radar.index], "radar_propio": radar.values,
                      "departamento": radar.index})
    m = oficial.merge(r, on="_k", how="inner")
    assert len(m) == 32, len(m)
    m["clase"] = m["radar_propio"].map(lambda v: clasificar(v, cb, ca))
    acc = float((m["clase"] == m["Clasificacion_radar_oficial_promedio"]).mean())
    rho = float(spearmanr(m["radar_propio"], m["radar_oficial_promedio"]).correlation)
    return {"m": m, "acc": acc, "rho": rho, "dist": m["clase"].value_counts().to_dict()}


def main():
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(d) == len(corpus)
    deps = corpus["departamento"].values
    prem = pd.read_pickle(os.path.join(DIR, "premisas_visibles_nacional.pkl")).loc[corpus["url"]]
    g = np.asarray(H.compuerta(prem.values, GA))

    # Compuerta con la truncacion de produccion (premisa que ve el NLI con la vigente de
    # grupos, no con la hipotesis mas larga del experimento): se mide si cambia algo.
    from transformers import AutoTokenizer
    from nli_core import MODELO_NLI, _ruta_modelo_local
    tok = AutoTokenizer.from_pretrained(_ruta_modelo_local(MODELO_NLI))
    prem_prod = H.premisa_visible(corpus["texto"].fillna("").astype(str).tolist(), tok,
                                  [H.HIPOTESIS[GA]["vig"]])
    g_prod = np.asarray(H.compuerta(prem_prod, GA))

    oficial = pd.read_excel(REFERENCIA, engine="openpyxl")
    oficial.columns = [str(c).strip() for c in oficial.columns]
    oficial["_k"] = oficial["Departamento"].map(_norm)

    r01, ga01 = radar_max(d, deps)
    r08, ga08 = radar_max(d, deps, g)
    r08p, ga08p = radar_max(d, deps, g_prod)
    print(f"Compuerta grupos: abre en {g.mean():.1%} (experimento) / {g_prod.mean():.1%} (truncacion prod); "
          f"articulos distintos {int((g != g_prod).sum())}; max|dif| radar {np.abs(r08 - r08p).max():.1e}")

    res = {}
    for nombre, r in (("V01", r01), ("V08", r08)):
        cb, ca, cand, rompe = elegir_cortes(r)
        c = constancia(r, cb, ca, oficial)
        res[nombre] = (cb, ca, c, rompe)
        print(f"{nombre}: huecos>0.008 {len(cand)}; cortes Bajo < {cb} <= Medio < {ca} <= Alto; "
              f"dist {c['dist']}; anclas rotas {rompe(cb, ca) or 'ninguna'}; "
              f"acc {c['acc']:.3f}; Spearman {c['rho']:+.4f}")
    ok = res["V01"][:2] == CORTES_B060
    print(f"Sanidad V01 = b060b3b {CORTES_B060}: {'OK' if ok else 'DIFIERE'}")
    cb, ca, c08, rompe = res["V08"]
    c_viejos = constancia(r08, *CORTES_B060, oficial)
    print(f"V08 con los cortes viejos {CORTES_B060}: dist {c_viejos['dist']}, anclas rotas "
          f"{rompe(*CORTES_B060) or 'ninguna'}, acc {c_viejos['acc']:.3f}")

    # Departamentos que cambian: MAX de grupos, radar y clase (V01 cortes b060 -> V08 cortes nuevos).
    t = pd.DataFrame({"ga_V01": ga01, "ga_V08": ga08, "radar_V01": r01, "radar_V08": r08})
    t["clase_V01"] = t["radar_V01"].map(lambda v: clasificar(v, *CORTES_B060))
    t["clase_V08"] = t["radar_V08"].map(lambda v: clasificar(v, cb, ca))
    t["clase_V08_cortes_viejos"] = t["radar_V08"].map(lambda v: clasificar(v, *CORTES_B060))
    of = oficial.set_index("_k")["Clasificacion_radar_oficial_promedio"]
    t["oficial"] = [of.get(_norm(k)) for k in t.index]
    t = t.sort_values("radar_V08", ascending=False).round(4)
    cambia = t[(t.ga_V01 != t.ga_V08) | (t.clase_V01 != t.clase_V08)]
    print(f"Departamentos con MAX de grupos o clase distinta ({len(cambia)}):")
    print(cambia.rename(columns=lambda x: x.replace("clase_", "c_")).to_string())
    with pd.ExcelWriter(os.path.join(DIR, "cortes_radar.xlsx")) as w:
        t.to_excel(w, sheet_name="radar_32")
        pd.DataFrame([{"variante": k, "corte_bajo_medio": v[0], "corte_medio_alto": v[1], "acc": v[2]["acc"],
                       "spearman": v[2]["rho"], **{f"n_{c}": v[2]["dist"].get(c, 0) for c in ("Bajo", "Medio", "Alto")}}
                      for k, v in res.items()]).to_excel(w, sheet_name="cortes", index=False)
    print(f"-> {DIR}/cortes_radar.xlsx")


if __name__ == "__main__":
    main()
