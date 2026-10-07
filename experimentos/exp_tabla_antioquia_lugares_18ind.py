"""
Tabla comparativa radar 20 indicadores (version anterior) vs 18 (nueva) para Antioquia y los lugares
(Paraguachon, Maicao, Guintiva, Oicata). Sin GPU.

  20 ind = los 18 de CalculadorRadar.COLUMNAS_BINARIAS + movimientos_sociales + exclusion_servicios_derechos,
           todos con frases V2 originales, cortes 0.7138/0.905.
  18 ind = los 18, con conflicto_territorial, zonas_proteccion_alimentaria y resistencia_territorial tomados de
           datos/scores/scores_hipotesis_jefe_18ind.pkl (frase nueva); cortes = los de config_pipeline AL CORRER.
Score por articulo: clip(clip(ent - sesgo, 0) * (1 - neu), 0, 1) x compuerta PREFILTRO_OBJETO (src/).
  - Antioquia: corpus nacional + scores_v2_32deptos.pkl (ent/neu V2 originales, recalculados aqui).
  - Lugares: score por articulo de resultados/tablas_lugares_max_prefiltro_2026-09-29/df_procesado_5lugares.pkl
    (produccion V2 original, ya con sesgo y compuertas; no hay ent/neu V2 de los lugares en datos/scores/) y,
    para las 3 frases nuevas, ent/neu del pkl del jefe (filas 'lugares', mismo orden que el corpus de 5 lugares).
Por lugar: MAX por indicador; radar = media simple de los MAX (redondeados a 4 decimales, como paso5_resumen).

  python experimentos/exp_tabla_antioquia_lugares_18ind.py
Salida: experimentos/resultados/tabla_antioquia_lugares_18ind.{xlsx,md}
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
os.chdir(RAIZ)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "src"))
import config_pipeline as cfg  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import radar as R  # noqa: E402
import Transformer_optimo as T  # noqa: E402

MODELO = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
CORPUS_LUG = "datos/corpus/df_corpus_5lugares.pkl"
PROC_LUG = "resultados/tablas_lugares_max_prefiltro_2026-09-29/df_procesado_5lugares.pkl"
JEFE = "datos/scores/scores_hipotesis_jefe_18ind.pkl"
VALID = "experimentos/resultados/exp_retiro_6ind_cortes.csv"
SAL = "experimentos/resultados/tabla_antioquia_lugares_18ind"
CORTES_20 = (0.7138, 0.905)
CAMBIAN = ["conflicto_territorial", "zonas_proteccion_alimentaria", "resistencia_territorial"]
RETIRADOS2 = ["movimientos_sociales", "exclusion_servicios_derechos"]
I18 = list(R.CalculadorRadar.COLUMNAS_BINARIAS)
I20 = I18 + RETIRADOS2
assert len(I18) == 18 and len(set(I20)) == 20 and set(CAMBIAN) <= set(I18)
# prefijos ASCII de la etiqueta del corpus (la tilde viene mal codificada en los pkl)
LUGARES = {"Antioquia": None, "Paraguachón": "Vereda Paraguach", "Maicao": "Municipio Maicao",
           "Güintiva": "Vereda G", "Oicatá": "Municipio Oicat"}


def corte_a_clase(v, cb, ca):
    return "Bajo" if v < cb else ("Medio" if v < ca else "Alto")


def score(ent, neu, sesgo):
    return np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)


def main():
    cb18, ca18 = cfg.CORTE_BAJO_MEDIO_RADAR, cfg.CORTE_MEDIO_ALTO_RADAR
    prov = (cb18, ca18) == CORTES_20
    print(f"Cortes config: {cb18}/{ca18}" + ("  -> PROVISIONALES (iguales a los de 20)" if prov else ""))

    # ---- Antioquia (nacional)
    corpus = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    d = pd.read_pickle(V2NAC).reset_index(drop=True)
    j = pd.read_pickle(JEFE).reset_index(drop=True)
    assert len(corpus) == len(d) == 11439
    assert (corpus["titulo"].values == d["titulo"].values).all()
    jn = j[j["corpus"] == "nacional"].reset_index(drop=True)
    jl = j[j["corpus"] == "lugares"].reset_index(drop=True)
    assert len(jn) == 11439 and len(jl) == 1647
    assert (jn["titulo"].values == corpus["titulo"].values).all() and (jn["departamento"].values == corpus["departamento"].values).all()
    assert np.allclose(jn["sesgo"].values, d["sesgo"].values, atol=1e-6)
    textos = corpus["texto"].fillna("").astype(str).tolist()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(T._ruta_modelo_local(MODELO))
    sesgo = d["sesgo"].values
    art20 = pd.DataFrame({c: score(d[f"ent_{c}"].values, d[f"neu_{c}"].values, sesgo) for c in I20})
    for ind in T.PREFILTRO_OBJETO:
        if ind in art20:
            art20[ind] = art20[ind] * T.compuerta_objeto(T.premisa_visible(textos, tok, V2.TODAS[ind]), ind)
    for c in CAMBIAN:  # 'actual' del pkl del jefe debe reproducir la frase original
        a = score(jn[f"ent_actual_{c}"].values, jn[f"neu_actual_{c}"].values, sesgo)
        assert np.abs(a - art20[c].values).max() < 1e-4, f"actual != V2 original en {c}"
    art18 = art20[I18].copy()
    for c in CAMBIAN:
        art18[c] = score(jn[f"ent_nueva_{c}"].values, jn[f"neu_nueva_{c}"].values, sesgo)
    ant = (corpus["departamento"] == "Antioquia").values
    assert ant.sum() == 494

    # ---- Lugares
    cl = pd.read_pickle(CORPUS_LUG).reset_index(drop=True)
    pr = pd.read_pickle(PROC_LUG).reset_index(drop=True)
    assert len(cl) == len(pr) == len(jl) == 1647
    assert (cl["url"].values == pr["url"].values).all()
    assert (jl["titulo"].values == cl["titulo"].values).all() and (jl["departamento"].values == cl["departamento"].values).all()
    assert np.allclose(jl["sesgo"].values, pr["sesgo"].values, atol=1e-6)
    l20 = pr[I20].astype(float).copy()
    for c in CAMBIAN:
        a = score(jl[f"ent_actual_{c}"].values, jl[f"neu_actual_{c}"].values, pr["sesgo"].values)
        print(f"  lugares: max|actual(jefe) - produccion| en {c}: {np.abs(a - l20[c].values).max():.2e}")
        assert np.abs(a - l20[c].values).max() < 1e-4, f"lugares: actual != produccion en {c}"
    l18 = l20[I18].copy()
    for c in CAMBIAN:
        l18[c] = score(jl[f"ent_nueva_{c}"].values, jl[f"neu_nueva_{c}"].values, pr["sesgo"].values)
    # validacion cruzada: Antioquia (2023) de lugares == Antioquia nacional (mismos articulos)
    m = (cl["departamento"] == "Antioquia (2023)").values
    tn = pd.Series(np.arange(len(corpus))[ant], index=corpus.loc[ant, "url"].values)
    idx = tn.reindex(cl.loc[m, "url"].values)
    if idx.notna().all():
        dif = np.abs(l20[m].values - art20.iloc[idx.astype(int).values][I20].values).max()
        print(f"Cruce Antioquia(2023) lugares vs nacional (mismos urls): max|dif| {dif:.2e}")
        assert dif < 1e-4
    else:
        print("Cruce Antioquia(2023): urls no coinciden con el nacional (se omite)")

    # ---- agregacion
    def agg(titulos, art, mask):
        g = art[mask].reset_index(drop=True)
        tt = titulos[mask].reset_index(drop=True)
        mx = g.max().round(4) if len(g) else pd.Series(dtype=float)
        ti = {c: (tt[g[c].idxmax()] if g[c].max() > 0 else "—") for c in g.columns} if len(g) else {}
        return mx, ti, int(mask.sum())

    res = {}
    for lug, pref in LUGARES.items():
        if lug == "Antioquia":
            res[lug] = (agg(corpus["titulo"], art20, ant), agg(corpus["titulo"], art18, ant))
        else:
            mk = cl["departamento"].astype(str).str.startswith(pref).values
            res[lug] = (agg(cl["titulo"], l20, mk), agg(cl["titulo"], l18, mk))
    print({k: v[0][2] for k, v in res.items()})

    # ---- validacion contra produccion anterior
    v = pd.read_csv(VALID, index_col=0)["radar_20"]["Antioquia"]
    r20_ant_sin_red = float(art20[ant].max().mean())
    print(f"Validacion Antioquia 20 ind: mio {r20_ant_sin_red:.6f} vs produccion {v:.6f}")
    if abs(r20_ant_sin_red - v) > 2e-6:
        sys.exit("NO COINCIDE con exp_retiro_6ind_cortes.csv: PARA")

    filas = []
    for lug, ((m20, t20, n), (m18, t18, _)) in res.items():
        if n == 0:
            filas.append({"lugar": lug, "n_articulos": 0, "radar_20": np.nan, "clase_20": "sin datos", "radar_18": np.nan,
                          "clase_18": "sin datos", "dif": np.nan})
            continue
        r20, r18 = round(float(m20.mean()), 4), round(float(m18.mean()), 4)
        filas.append({"lugar": lug, "n_articulos": n, "radar_20": r20, "clase_20": corte_a_clase(r20, *CORTES_20),
                      "radar_18": r18, "clase_18": corte_a_clase(r18, cb18, ca18), "dif": round(r18 - r20, 4)})
    resumen = pd.DataFrame(filas)

    ind_filas = {}
    for lug, ((m20, t20, n), (m18, t18, _)) in res.items():
        if n == 0:
            continue
        rows = []
        for c in I20:
            nuevo, ret = c in CAMBIAN, c in RETIRADOS2
            v18 = m18.get(c, np.nan)
            rows.append({"indicador": c, "tipo": "frase nueva" if nuevo else ("retirado" if ret else "igual"),
                         "MAX_20": m20[c], "MAX_18": v18, "dif": np.nan if ret else v18 - m20[c],
                         "articulo_MAX_20": t20[c], "articulo_MAX_18": t18.get(c, "(retirado)")})
        ind_filas[lug] = pd.DataFrame(rows)

    nota = (f"Cortes 20 ind: {CORTES_20[0]}/{CORTES_20[1]}. Cortes 18 ind: {cb18}/{ca18}"
            + (" (PROVISIONALES: iguales a los de 20; otro agente los recalibra, re-correr)" if prov else "") + ".")
    with pd.ExcelWriter(SAL + ".xlsx") as xw:
        resumen.to_excel(xw, sheet_name="resumen", index=False)
        pd.DataFrame({"nota": [nota, "Paraguachon: 20 articulos del corpus combinado (definicion de pipeline_lugares.py), no los 77 del pkl individual.",
                               "Guintiva: 0 articulos en el corpus (sin cobertura de prensa).",
                               "Radar = media simple de los MAX redondeados a 4 decimales."]}).to_excel(xw, sheet_name="notas", index=False)
        for lug, df in ind_filas.items():
            df.to_excel(xw, sheet_name=lug[:30], index=False)

    # ---- markdown
    def f(x):
        return "—" if pd.isna(x) else f"{x:.4f}"

    L = ["# Radar 20 vs 18 indicadores: Antioquia y lugares", "", nota, "",
         "Paraguachón: 20 artículos (corpus combinado). Güintiva: 0 artículos, sin radar. Oicatá y Paraguachón son bases pequeñas (frágiles).", "",
         "| Lugar | n art. | Radar 20 | Clase 20 | Radar 18 | Clase 18 | Dif |", "|---|---:|---:|:--:|---:|:--:|---:|"]
    for r in resumen.itertuples():
        L.append(f"| {r.lugar} | {r.n_articulos} | {f(r.radar_20)} | {r.clase_20} | {f(r.radar_18)} | {r.clase_18} | {f(r.dif)} |")
    for lug, df in ind_filas.items():
        r = resumen[resumen.lugar == lug].iloc[0]
        L += ["", f"## {lug} (n={r.n_articulos}): 20 ind {f(r.radar_20)} {r.clase_20} → 18 ind {f(r.radar_18)} {r.clase_18}", "",
              "| Indicador | Tipo | MAX 20 | MAX 18 | Artículo MAX 20 | Artículo MAX 18 |", "|---|---|---:|---:|---|---|"]
        for x in df.itertuples():
            a20 = str(x.articulo_MAX_20).replace("|", "/")[:90]
            a18 = str(x.articulo_MAX_18).replace("|", "/")[:90]
            nom = f"**{x.indicador}**" if x.tipo == "frase nueva" else (f"~~{x.indicador}~~" if x.tipo == "retirado" else x.indicador)
            L.append(f"| {nom} | {x.tipo} | {f(x.MAX_20)} | {f(x.MAX_18)} | {a20} | {a18} |")
        nu = df[df.tipo == "frase nueva"]
        ret = df[df.tipo == "retirado"]
        s_nuevas = ", ".join(f"{x.indicador} {x.MAX_20:.4f}→{x.MAX_18:.4f}" for x in nu.itertuples())
        s_ret = ", ".join(f"{x.indicador} {x.MAX_20:.4f}" for x in ret.itertuples())
        base = df[df.tipo != "retirado"]["MAX_20"].round(4).mean()  # 18 con frases originales
        L += ["", f"Efecto de quitar los 2 retirados (frases originales): radar {r.radar_20:.4f} → {base:.4f} ({base - r.radar_20:+.4f}); {s_ret}.",
              f"Efecto de las 3 frases nuevas (sobre los 18): radar {base:.4f} → {r.radar_18:.4f} ({r.radar_18 - base:+.4f}); {s_nuevas}."]
    open(SAL + ".md", "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(resumen.to_string(index=False))
    print("->", SAL + ".xlsx", SAL + ".md")


if __name__ == "__main__":
    main()
