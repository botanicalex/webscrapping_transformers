# -*- coding: utf-8 -*-
"""
Cuanto discrimina cada indicador bajo la configuracion de produccion (V2, sesgo descontado, pre-filtro por indicador en
grupos armados y desplazamiento, MAX por departamento). Descriptivo: no decide ni toca src/; es insumo para que el usuario y
su jefe decidan que indicadores retirar. Todo offline (pkl existentes; CPU).

Criterios fijados ANTES de calcular (commit de este archivo):
- Por indicador, sobre su MAX en los 32 departamentos: media, mediana, minimo, P10, P90, amplitud P90-P10, desviacion,
  fraccion de departamentos con MAX >= 0.95; Spearman con radar_oficial_promedio (DANE) y con el nº de articulos.
- Marcas:
    PLANO          = amplitud P90-P10 < 0.05 y mediana >= 0.95 (casi el mismo valor alto en todas partes).
    SIN_SENAL_DANE = Spearman con el DANE <= 0.
    TAMANO         = Spearman con el nº de articulos >= 0.70.
- Retirada de uno en uno (radar = media de los 25 restantes): Spearman DANE, Spearman tamano y su cambio frente a la base.
- Configuraciones combinadas declaradas de antemano:
    R1 = retirar todos los PLANO (elegidos sin mirar el DANE: la unica no circular).
    R2 = retirar todos los PLANO o SIN_SENAL_DANE (INFORMATIVA: elige con el DANE y se mide contra el DANE; es circular).
  En R1 y R2: cortes recalibrados con elegir_cortes (0 anclas), clases, accuracy y los dos Spearman.
- Base (sanidad): 26 indicadores reproducen cortes 0.7572/0.9233, 6/19/7, Spearman DANE -0.0913, tamano +0.8640.
- Lugares (reporte): MAX por indicador en Antioquia (2023), Maicao, Oicata y Paraguachon (corrida de produccion 2026-09-29).
Limites: n = 32 (diferencias de Spearman < 0.15 no se distinguen del ruido); el DANE es un indice de otra cosa.

  PYTHONIOENCODING=utf-8 python experimentos/exp_indicadores_discriminacion.py
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exp_prefiltro_e2_comun as C  # noqa: E402
import exp_prefiltro_max as X  # noqa: E402

PROC_PREF = "resultados/tablas_lugares_max_prefiltro_2026-09-29/df_procesado_5lugares.pkl"
SALIDA_XLSX = "experimentos/resultados/exp_indicadores_discriminacion.xlsx"
SALIDA_MD = "experimentos/RESULTADOS_indicadores_discriminacion.md"
INDS26 = X.INDS26
PLANO_AMP, PLANO_MED, TAM_MIN = 0.05, 0.95, 0.70


def main():
    tok = C.cargar_tokenizer()
    cn = pd.read_pickle(C.CORPUS_NAC).reset_index(drop=True)
    dn = pd.read_pickle(X.V2NAC).reset_index(drop=True)
    assert len(cn) == len(dn) == 11439 and (cn["titulo"].values == dn["titulo"].values).all()
    deps = cn["departamento"].values
    sesgo = dn["sesgo"].values.astype(float)
    txt = cn["texto"].fillna("").astype(str).tolist()
    prod = C.prefiltro_produccion()
    cols = {}
    for c in INDS26:
        s = X.s_corr(dn[f"ent_{c}"].values, dn[f"neu_{c}"].values, sesgo)
        if c in prod:
            s = s * np.array(C.compuerta(C.premisa_visible_prod(txt, tok, C.V2.TODAS[c]), prod[c]))
        cols[c] = s
    M = pd.DataFrame(cols).groupby(deps).max()
    assert M.shape == (32, 26)
    n_art = pd.Series(deps).value_counts().reindex(M.index)
    of = pd.read_excel(X.OFICIAL, engine="openpyxl")
    of.columns = [str(c).strip() for c in of.columns]
    of["_k"] = of["Departamento"].map(X._norm)
    dane = of.set_index("_k")["radar_oficial_promedio"].loc[[X._norm(k) for k in M.index]].values

    def evaluar(inds, nombre):
        r = M[inds].mean(axis=1)
        out = {"config": nombre, "n_indicadores": len(inds),
               "rho_dane": float(spearmanr(r.values, dane).correlation),
               "rho_tam": float(spearmanr(r.values, n_art.values).correlation)}
        try:
            cb, ca, _, _ = X.elegir_cortes(r)
            k = X.constancia(r, cb, ca, of)
            out.update({"cortes": f"{cb:.4f}/{ca:.4f}", "anclas_rotas": len(X.anclas_rotas(r, cb, ca)),
                        "clases_B/M/A": "/".join(str(k["dist"].get(x, 0)) for x in ("Bajo", "Medio", "Alto")),
                        "accuracy": k["acc"]})
        except RuntimeError:
            out.update({"cortes": "sin cortes validos", "anclas_rotas": None, "clases_B/M/A": "", "accuracy": None})
        return out

    base = evaluar(INDS26, "base (26)")
    san = [("cortes", base["cortes"] == "0.7572/0.9233"), ("clases", base["clases_B/M/A"] == "6/19/7"),
           ("rho_dane", round(base["rho_dane"], 4) == -0.0913), ("rho_tam", round(base["rho_tam"], 4) == 0.8640),
           ("anclas", base["anclas_rotas"] == 0)]
    print("Sanidad:", san)
    assert all(ok for _, ok in san), "sanidad fallida: no se decide nada"

    filas = []
    for c in INDS26:
        v = M[c]
        p10, p90 = np.percentile(v, 10), np.percentile(v, 90)
        loo = evaluar([x for x in INDS26 if x != c], f"sin {c}")
        f = {"indicador": c, "media": v.mean(), "mediana": v.median(), "min": v.min(), "P10": p10, "P90": p90,
             "amplitud_P90_P10": p90 - p10, "desviacion": v.std(ddof=0), "frac_MAX_ge_095": float((v >= 0.95).mean()),
             "rho_dane": float(spearmanr(v.values, dane).correlation),
             "rho_tam": float(spearmanr(v.values, n_art.values).correlation),
             "sin_rho_dane": loo["rho_dane"], "delta_rho_dane": loo["rho_dane"] - base["rho_dane"],
             "sin_rho_tam": loo["rho_tam"], "delta_rho_tam": loo["rho_tam"] - base["rho_tam"]}
        f["PLANO"] = bool(f["amplitud_P90_P10"] < PLANO_AMP and f["mediana"] >= PLANO_MED)
        f["SIN_SENAL_DANE"] = bool(not (f["rho_dane"] > 0))   # NaN (constante) cuenta como sin senal
        f["TAMANO"] = bool(f["rho_tam"] >= TAM_MIN)
        filas.append(f)
    T = pd.DataFrame(filas).sort_values("amplitud_P90_P10").reset_index(drop=True)

    planos = T.loc[T["PLANO"], "indicador"].tolist()
    r2 = T.loc[T["PLANO"] | T["SIN_SENAL_DANE"], "indicador"].tolist()
    R = pd.DataFrame([base, evaluar([x for x in INDS26 if x not in planos], f"R1 sin PLANO ({len(planos)})"),
                      evaluar([x for x in INDS26 if x not in r2], f"R2 sin PLANO ni SIN_SENAL ({len(r2)}; circular)")])

    # lugares (produccion 2026-09-29)
    pp = pd.read_pickle(PROC_PREF).reset_index(drop=True)
    lug = pd.read_csv(X.URL_LUGARES)
    L = pd.DataFrame({l: pp[pp["url"].isin(set(lug.loc[lug["lugar"] == l, "url"]))][INDS26].max() for l in X.LUG})
    L.index.name = "indicador"

    os.makedirs(os.path.dirname(SALIDA_XLSX), exist_ok=True)
    with pd.ExcelWriter(SALIDA_XLSX) as w:
        T.to_excel(w, sheet_name="indicadores", index=False)
        R.to_excel(w, sheet_name="configuraciones", index=False)
        M.T.to_excel(w, sheet_name="MAX_32_departamentos")
        L.to_excel(w, sheet_name="MAX_4_lugares")
        pd.DataFrame(san, columns=["chequeo", "ok"]).to_excel(w, sheet_name="sanidad", index=False)

    def md(df, dec=3):
        d = df.copy()
        for c in d.columns:
            if d[c].dtype.kind == "f":
                d[c] = d[c].map(lambda x: "" if pd.isna(x) else f"{x:.{dec}f}")
            elif d[c].dtype == bool:
                d[c] = d[c].map(lambda x: "sí" if x else "")
        return "\n".join(["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * len(d.columns)]
                         + ["| " + " | ".join(map(str, r)) + " |" for r in d.values])

    cols_md = ["indicador", "mediana", "min", "amplitud_P90_P10", "frac_MAX_ge_095", "rho_dane", "rho_tam",
               "delta_rho_dane", "delta_rho_tam", "PLANO", "SIN_SENAL_DANE", "TAMANO"]
    with open(SALIDA_MD, "w", encoding="utf-8") as fh:
        fh.write("# Resultados — cuánto discrimina cada indicador (producción actual, 32 departamentos)\n\n")
        fh.write("Generado por `experimentos/exp_indicadores_discriminacion.py`; tablas en "
                 "`experimentos/resultados/exp_indicadores_discriminacion.xlsx`. Descriptivo: no decide nada.\n\n")
        fh.write(f"Sanidad: {sum(ok for _, ok in san)}/{len(san)} OK (base = producción).\n\n")
        fh.write("## Indicadores (ordenados de menos a más amplitud)\n\n" + md(T[cols_md]) + "\n\n")
        fh.write(f"PLANO: amplitud P90−P10 < {PLANO_AMP} y mediana ≥ {PLANO_MED}. SIN_SENAL_DANE: Spearman con el DANE ≤ 0. "
                 f"TAMANO: Spearman con el nº de artículos ≥ {TAM_MIN}. delta_*: cambio del radar al retirar solo ese.\n\n")
        fh.write("## Configuraciones\n\n" + md(R, 4) + "\n\n")
        fh.write(f"R1 retira: {', '.join(planos) or '(ninguno)'}.\n\nR2 retira: {', '.join(r2) or '(ninguno)'} "
                 "(circular: se elige con el DANE y se mide contra el DANE).\n\n")
        fh.write("## MAX en los 4 lugares (producción 2026-09-29)\n\n" + md(L.reset_index()) + "\n\n")
        fh.write("Límites: n = 32 (Spearman < 0.15 de diferencia no se distingue del ruido); el DANE mide otra cosa; "
                 "accuracy de 'siempre Bajo' = 0.344.\n")
    print(T[cols_md].to_string())
    print(R.to_string())


if __name__ == "__main__":
    main()
