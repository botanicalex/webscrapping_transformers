# -*- coding: utf-8 -*-
"""
F1 del tramo 2 de la etapa 2 del pre-filtro (experimentos/PREREG_prefiltro_indicador_e2_t2.md): cribado SIN jueces de las 11 listas
restantes. Sanidad S1-S5 (bloqueante), condicion C (control absurdo), condicion R (radar nacional con la lista sola) y veredicto.
Reutiliza por import cargar(), radar/criterios() y las utilidades de exp_prefiltro_e2.py (tramo 1, sin modificarlo); la formula
de C es la de inclusion() parte (c), generalizada a cualquier indicador. La sanidad S3 aplica C y R a las 4 medibles del tramo 1 y
compara con RESULTADOS_prefiltro_e2.md.

  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_e2_t2.py
"""
import os
import re
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exp_prefiltro_e2 as E  # noqa: E402
import hipotesis_prefiltro_e2_t2 as T  # noqa: E402

C, X = E.C, E.X
T2_PKL = "datos/scores/scores_prefiltro_e2_t2.pkl"
LOG_GPU = "experimentos/resultados/exp_prefiltro_e2_t2_gpu.log"
APERTURAS = "experimentos/resultados/juicio_prefiltro_e2/aperturas.csv"
SALIDA_XLSX = "experimentos/resultados/exp_prefiltro_e2_t2.xlsx"
SALIDA_MD = "experimentos/RESULTADOS_prefiltro_e2_t2.md"
CRIB = T.CRIBADO
MEDIBLES_T1 = E.CAND
COLS_C = ["c_dif_gemela_lugares", "c_dif_total_lugares", "c_dif_gemela_holdout", "c_dif_total_holdout"]

# Valores del tramo 1 (RESULTADOS_prefiltro_e2.md) para la sanidad S3.
S3_C = {  # gemela lug, total lug, gemela hold, total hold  (5 decimales)
    "amenaza_lideres": (-0.03515, 0.08585, 0.18113, 0.09288),
    "amenaza_intimidacion": (-0.11386, 0.01020, 0.06461, 0.16896),
    "protesta_social": (0.00000, 0.15250, 0.06937, 0.28841),
    "violacion_derechos_humanos": (0.15500, -0.03488, 0.02038, 0.32134),
}
S3_R = {  # cortes, DANE, tamano (4 decimales)
    "amenaza_lideres": ("0.7450/0.9233", -0.1085, 0.8702),
    "amenaza_intimidacion": ("0.7572/0.9230", -0.1015, 0.8666),
    "protesta_social": ("0.7559/0.9093", -0.0960, 0.8666),
    "violacion_derechos_humanos": ("0.7541/0.9233", -0.0872, 0.8658),
}


def ampliar(D):
    """Agrega a D los datos de las 11: gemelas (lugares y holdout), compuertas (hipotesis de cada indicador) y puntajes reales."""
    for i in CRIB:
        assert C.V2.TODAS[i] == T.HIPOTESIS[i], f"hipotesis de {i} difiere de V2"
    tok = C.cargar_tokenizer()
    cn = pd.read_pickle(C.CORPUS_NAC).reset_index(drop=True)
    cl = pd.read_pickle(X.CORPUS_L).reset_index(drop=True)
    assert (cn["url"].values == D.nac["url"].values).all() and (cl["url"].values == D.l_urls).all()
    txt_n = cn["texto"].fillna("").astype(str).tolist()
    txt_l = cl["texto"].fillna("").astype(str).tolist()
    for i in CRIB:
        hip = C.V2.TODAS[i]
        D.rx[i] = T.LISTAS[i]
        D.g_nac[i] = np.array(C.compuerta(C.premisa_visible_prod(txt_n, tok, hip), D.rx[i]))
        D.g_l[i] = np.array(C.compuerta(C.premisa_visible_prod(txt_l, tok, hip), D.rx[i]))
    t2 = pd.read_pickle(T2_PKL)
    assert t2["url"].is_unique
    t2 = t2.set_index("url")
    ses_l = pd.read_pickle(X.ATOMICAS_L).reset_index(drop=True)["sesgo"].values.astype(float)
    ab_l = t2.loc[cl["url"]]
    ab_h = t2.reindex(cn["url"])
    D.t2_ab_l = {i: X.s_corr(ab_l[f"ent_{i}__gemela"].values, ab_l[f"neu_{i}__gemela"].values, ses_l) for i in CRIB}
    D.t2_ab_h = {i: X.s_corr(ab_h[f"ent_{i}__gemela"].values, ab_h[f"neu_{i}__gemela"].values, D.sesgo) for i in CRIB}
    D.t2_h_ok = cn["url"].isin(t2.index).values
    D.txt_n = txt_n
    return D


def places_t2(D):
    """Lugares (reales = corrida de produccion 2026-09-29; 2 listas de produccion ya aplicadas, las 11 no estan entre ellas)."""
    idx_l = {u: i for i, u in enumerate(D.l_urls)}
    out = []
    for l in E.LUG:
        ii = np.array([idx_l[u] for u in sorted(D.urls_lugar[l])])
        out.append(dict(name=l, kind="lugar", s={i: D.l_prod[i][ii] for i in CRIB}, ab={i: D.t2_ab_l[i][ii] for i in CRIB},
                        tot=D.l_tot[ii], g={i: D.g_l[i][ii] for i in CRIB}))
    for dep in E.HOLD:
        m = np.where(D.nac["departamento"].values == dep)[0]
        assert D.t2_h_ok[m].all()
        out.append(dict(name=dep, kind="holdout", s={i: D.s[i][m] for i in CRIB}, ab={i: D.t2_ab_h[i][m] for i in CRIB},
                        tot=D.s["NULA_TEST"][m], g={i: D.g_nac[i][m] for i in CRIB}))
    return [type("Pl", (), p) for p in out]


def control_c(places, inds):
    """Condicion C: misma formula que inclusion() parte (c) de exp_prefiltro_e2.py, sin/con mascara, por lugar."""
    filas, det = [], []
    for ind in inds:
        rows = []
        for p in places:
            g = p.g[ind]
            re_s, re_c = float(p.s[ind].max()), float((p.s[ind] * g).max())
            ab_s, ab_c = float(p.ab[ind].max()), float((p.ab[ind] * g).max())
            to_s, to_c = float(p.tot.max()), float((p.tot * g).max())
            rows.append({"indicador": ind, "lugar": p.name, "tipo": p.kind, "real_sin": re_s, "real_con": re_c,
                         "gemela_sin": ab_s, "gemela_con": ab_c, "total_sin": to_s, "total_con": to_c,
                         "brecha_gemela_sin": re_s - ab_s, "brecha_gemela_con": re_c - ab_c,
                         "brecha_total_sin": re_s - to_s, "brecha_total_con": re_c - to_c})
        cd = pd.DataFrame(rows)
        det.append(cd)
        f = {"indicador": ind}
        for grupo, sel in (("lugares", cd["tipo"] == "lugar"), ("holdout", cd["tipo"] == "holdout")):
            for tw in ("gemela", "total"):
                f[f"c_dif_{tw}_{grupo}"] = float(cd.loc[sel, f"brecha_{tw}_con"].mean() - cd.loc[sel, f"brecha_{tw}_sin"].mean())
        f["c_pasa"] = bool(all(f[c] >= -T.TOL_C for c in COLS_C))
        filas.append(f)
    return pd.DataFrame(filas), pd.concat(det, ignore_index=True)


def radar_r(D, inds, base):
    """Condicion R con la lista sola (+ las 2 de produccion, dentro de E.criterios)."""
    filas, rs = [], {}
    for ind in inds:
        r = E.criterios(D, [ind], base)
        rs[ind] = r
        filas.append({"indicador": ind, "cortes": E._cz(r), "anclas_rotas": r["anclas_rotas"], "rho_dane": r["rho_dane"],
                      "rho_size": r["rho_size"], "clases_B/M/A": "/".join(str(r["dist"].get(k, 0)) for k in ("Bajo", "Medio", "Alto")) if r["dist"] else "",
                      "r1_anclas": r["c1_anclas"], "r2_dane": r["c2_dane"], "r3_tam": r["c3_tam"], "r_pasa": r["pasa"],
                      "dif_max_radar": r["dif_max_radar"]})
    return pd.DataFrame(filas), rs


def sanidad(D, base, c_t1, r_t1, apert):
    filas = []

    def chk(nombre, ok, valor, esperado):
        filas.append({"chequeo": nombre, "ok": bool(ok), "valor": str(valor), "esperado": str(esperado)})
        print(f"  [{'OK' if ok else 'FALLA'}] {nombre}: {valor} (esperado {esperado})")

    chk("S1 sin listas nuevas: cortes", base["cortes"] == E.CORTES_PROD, base["cortes"], E.CORTES_PROD)
    chk("S1 clases 6/19/7", base["dist"] == {"Bajo": 6, "Medio": 19, "Alto": 7}, base["dist"], "6/19/7")
    chk("S1 Spearman DANE", round(base["rho_dane"], 4) == T.BASE_DANE, round(base["rho_dane"], 4), T.BASE_DANE)
    chk("S1 Spearman tamano", round(base["rho_size"], 4) == T.BASE_TAM, round(base["rho_size"], 4), T.BASE_TAM)
    chk("S1 anclas rotas", base["anclas_rotas"] == 0, base["anclas_rotas"], 0)
    # S2: verificacion de produccion del NLI en el log de la GPU
    log = open(LOG_GPU, encoding="utf-8").read()
    mm = re.search(r"max\|dif\| = ([0-9.eE+-]+) -> (OK|FALLA\w*)", log)
    chk("S2 verificacion de produccion del NLI (log GPU)", bool(mm) and mm.group(2) == "OK" and float(mm.group(1)) < 1e-4,
        f"max|dif|={mm.group(1) if mm else 'n/d'}", "< 1e-4")
    # S3
    for ind in MEDIBLES_T1:
        fila = c_t1.set_index("indicador").loc[ind]
        got = tuple(round(float(fila[c]), 5) for c in COLS_C)
        chk(f"S3 C tramo 1 {ind}", all(abs(a - b) < 1.5e-5 for a, b in zip(got, S3_C[ind])), got, S3_C[ind])
        rr = r_t1.set_index("indicador").loc[ind]
        got = (rr["cortes"], round(float(rr["rho_dane"]), 4), round(float(rr["rho_size"]), 4))
        chk(f"S3 R tramo 1 {ind}", got == S3_R[ind], got, S3_R[ind])
    surv = [i for i in MEDIBLES_T1 if bool(c_t1.set_index("indicador").loc[i, "c_pasa"]) and bool(r_t1.set_index("indicador").loc[i, "r_pasa"])]
    chk("S3 ninguna de las 4 del tramo 1 sobrevive", not surv, surv or "ninguna", "ninguna")
    # S4
    ap = pd.read_csv(APERTURAS).set_index("indicador")
    dif = {i: (int(D.g_nac[i].sum()), int(ap.loc[i, "n_abre"])) for i in CRIB}
    malos = {i: v for i, v in dif.items() if v[0] != v[1]}
    chk("S4 aperturas nacionales de los 11 = aperturas.csv (n_abre)", not malos, malos or "11/11 iguales", "iguales")
    # S5
    pm = pd.read_pickle(X.PROCESADO_L).reset_index(drop=True)
    d = max(float(np.abs(D.l_prod[i] - pm[i].astype(float).values).max()) for i in CRIB)
    chk("S5 puntajes reales lugares (produccion 2026-09-29) = tablas_lugares_max, 11 indicadores", d < 1e-4, f"max|dif|={d:.1e}", "< 1e-4")
    return pd.DataFrame(filas)


def md_lineas(df, ren=None, dec=4):
    return E.md_tabla(df, ren, dec)


def main():
    print("Cargando datos (tokenizando; unos minutos)...")
    D = E.cargar()
    places_t1 = E.armar_places(D)
    D = ampliar(D)
    pl = places_t2(D)
    base = E.criterios(D, [])
    print("\n=== Condicion C y R de las 4 medibles del tramo 1 (S3) ===")
    c_t1, cd_t1 = control_c(places_t1, MEDIBLES_T1)
    r_t1, _ = radar_r(D, MEDIBLES_T1, base)
    print("\n=== S. Sanidad ===")
    san = sanidad(D, base, c_t1, r_t1, None)
    if not san["ok"].all():
        with pd.ExcelWriter(SALIDA_XLSX.replace(".xlsx", "_FALLA_SANIDAD.xlsx"), engine="openpyxl") as w:
            san.to_excel(w, "S_sanidad", index=False)
        sys.exit("PARADA: la sanidad no cumple el pre-registro; no se decide nada")

    c_res, c_det = control_c(pl, CRIB)
    r_res, rs = radar_r(D, CRIB, base)
    k = c_res.merge(r_res[["indicador", "cortes", "anclas_rotas", "rho_dane", "rho_size", "r_pasa"]], on="indicador")
    k["sobrevive"] = k["c_pasa"] & k["r_pasa"]
    k = k.set_index("indicador").loc[CRIB].reset_index()
    print("\n", k.round(5).to_string(index=False))
    surv = list(k.loc[k["sobrevive"], "indicador"])
    veredicto = ("CIERRE DE LA ETAPA 2: ninguna lista sobrevive (C y R a la vez); los 11 pasan sin filtro, no se lanza ningun juez."
                 if not surv else f"PARADA: {len(surv)} sobreviviente(s): {', '.join(surv)}. Se reporta al usuario antes de cualquier juez.")
    print("\nVEREDICTO:", veredicto)

    c_t1.insert(0, "grupo", "S3_tramo1")
    c_res.insert(0, "grupo", "cribado")
    cd_t1.insert(0, "grupo", "S3_tramo1")
    c_det.insert(0, "grupo", "cribado")
    r_t1.insert(0, "grupo", "S3_tramo1")
    r_res.insert(0, "grupo", "cribado")
    base_fila = pd.DataFrame([{"grupo": "base", "indicador": "(produccion, sin listas nuevas)", "cortes": E._cz(base),
                               "anclas_rotas": base["anclas_rotas"], "rho_dane": base["rho_dane"], "rho_size": base["rho_size"],
                               "clases_B/M/A": "/".join(str(base["dist"].get(x, 0)) for x in ("Bajo", "Medio", "Alto"))}])
    os.makedirs(os.path.dirname(SALIDA_XLSX), exist_ok=True)
    with pd.ExcelWriter(SALIDA_XLSX, engine="openpyxl") as w:
        san.to_excel(w, sheet_name="S_sanidad", index=False)
        pd.concat([c_res, c_t1], ignore_index=True).to_excel(w, sheet_name="C_control", index=False)
        pd.concat([c_det, cd_t1], ignore_index=True).to_excel(w, sheet_name="C_detalle", index=False)
        pd.concat([base_fila, r_res, r_t1], ignore_index=True).to_excel(w, sheet_name="R_radar", index=False)
        k.to_excel(w, sheet_name="K_cribado", index=False)
    print("xlsx ->", SALIDA_XLSX)

    # Markdown
    L = ["# Resultados — pre-filtro por indicador, etapa 2 (tramo 2): cribado sin jueces de los 11", "",
         "Generado por `experimentos/exp_prefiltro_e2_t2.py`; tablas completas en `experimentos/resultados/exp_prefiltro_e2_t2.xlsx` "
         "(hojas `S_sanidad`, `C_control`, `C_detalle`, `R_radar`, `K_cribado`). Pre-registro: `experimentos/PREREG_prefiltro_indicador_e2_t2.md`. "
         "GPU: `experimentos/resultados/exp_prefiltro_e2_t2_gpu.log`.", "",
         f"**Veredicto: {veredicto}**", "",
         f"Sobrevivientes (C y R): {', '.join(surv) if surv else 'ninguna'} (hoja `K_cribado`).", "",
         "## Resumen del cribado (hoja `K_cribado`)", ""]
    kk = k[["indicador", "c_pasa", "cortes", "anclas_rotas", "rho_dane", "rho_size", "r_pasa", "sobrevive"]]
    L += md_lineas(kk, {"c_pasa": "pasa C", "cortes": "cortes (lista sola)", "anclas_rotas": "anclas", "rho_dane": "Spearman DANE",
                        "rho_size": "Spearman tamaño", "r_pasa": "pasa R"})
    L += ["", "## Condición C: control absurdo (hojas `C_control`, `C_detalle`)", "",
          "Diferencia de la brecha media «MAX real − MAX control» (con − sin máscara); exigido ≥ −5e-5 en las cuatro:", ""]
    cc = c_res[["indicador"] + COLS_C + ["c_pasa"]]
    L += md_lineas(cc, {"c_dif_gemela_lugares": "gemela, lugares", "c_dif_total_lugares": "total, lugares",
                        "c_dif_gemela_holdout": "gemela, holdout", "c_dif_total_holdout": "total, holdout", "c_pasa": "pasa C"}, dec=5)
    L += ["", "## Condición R: radar nacional con la lista sola (hoja `R_radar`)", "",
          f"Producción (base): cortes {E._cz(base)}, Spearman DANE {base['rho_dane']:.4f}, tamaño {base['rho_size']:.4f}, "
          f"{base['anclas_rotas']} anclas, clases 6/19/7. Criterios: 0 anclas, DANE ≥ {T.BASE_DANE}, tamaño ≤ {T.BASE_TAM} (4 decimales).", ""]
    rr = r_res[["indicador", "cortes", "anclas_rotas", "rho_dane", "rho_size", "clases_B/M/A", "r1_anclas", "r2_dane", "r3_tam", "r_pasa", "dif_max_radar"]]
    L += md_lineas(rr, {"anclas_rotas": "anclas", "rho_dane": "Spearman DANE", "rho_size": "Spearman tamaño", "r1_anclas": "0 anclas",
                        "r2_dane": "DANE ok", "r3_tam": "tamaño ok", "r_pasa": "pasa R", "dif_max_radar": "máx |Δ radar|"})
    L += ["", "## Sanidad (hoja `S_sanidad`)", ""]
    L += md_lineas(san[["chequeo", "ok", "valor", "esperado"]])
    L += ["", f"{int(san['ok'].sum())} de {len(san)} chequeos OK.", "",
          "## Desviaciones y notas", "",
          "- Ninguna desviación del pre-registro.",
          "- Puntajes reales de lugares = columnas de la corrida de producción 2026-09-29 (`df_procesado_5lugares.pkl` de "
          "`tablas_lugares_max_prefiltro_2026-09-29/`); las 11 no están entre las 2 listas de producción, así que equivalen a las tablas sin filtro (S5).",
          "- Máscaras nacionales con `premisa_visible_prod` y la hipótesis V2 de cada indicador (verificada igual a `hipotesis_prefiltro_e2_t2.HIPOTESIS`), sobre `df_corpus_combinado_32deptos.pkl`.",
          "- Once pruebas: el cribado reduce multiplicidad, no la elimina (PREREG §9)."]
    open(SALIDA_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("md ->", SALIDA_MD)


if __name__ == "__main__":
    main()
