# -*- coding: utf-8 -*-
"""
F3 del tramo 2 de la etapa 2 del pre-filtro (experimentos/PREREG_prefiltro_indicador_e2_t2.md §4 -> PREREG_prefiltro_indicador_e2.md
§3-§6 tal cual): analisis final de UNA lista, zonas_proteccion_alimentaria (unica sobreviviente del cribado). Regla de inclusion
(a)-(d), mecanismo combinado (§6), impacto y trazabilidad (§7). Todo offline (pkl y csv existentes; sin GPU).

Reutiliza por import, sin modificarlos, exp_prefiltro_e2.py (metricas_m, inclusion, tope, criterios, cadena, impacto: se les
inyecta la lista de indicadores a evaluar) y exp_prefiltro_e2_t2.py (cargar ampliado con gemelas/compuertas de las 11).
Referencia = SI de juez-e Y juez-f (etiquetas.csv de juicio_prefiltro_e2_t2).

  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_e2_t2_analisis.py
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exp_prefiltro_e2 as E  # noqa: E402
import exp_prefiltro_e2_t2 as T2  # noqa: E402

C, X, P = E.C, E.X, E.P
IND = "zonas_proteccion_alimentaria"
DIR_J = "experimentos/resultados/juicio_prefiltro_e2_t2"
SALIDA_XLSX = "experimentos/resultados/exp_prefiltro_e2_t2_analisis.xlsx"
SALIDA_MD = "experimentos/RESULTADOS_prefiltro_e2_t2_analisis.md"
C_ESPERADA = {"c_dif_gemela_lugares": 0.1993, "c_dif_total_lugares": 0.0507, "c_dif_gemela_holdout": 0.0609, "c_dif_total_holdout": 0.1298}

E.CAND = [IND]   # inclusion() y metricas_m() leen este global


def cargar_t2():
    D = E.cargar()
    D = T2.ampliar(D)
    et = pd.read_csv(os.path.join(DIR_J, "etiquetas.csv"))
    D.et2 = et.set_index(["url", "indicador"])
    D.juzg2 = set(et.loc[et["indicador"] == IND, "url"])
    D.pos2 = set(et.loc[(et["indicador"] == IND) & et["ref"], "url"])
    return D


def armar_places_t2(D):
    """Igual que E.armar_places (orden por url, desempate de M1-M4) con los datos de zonas y las etiquetas del tramo 2."""
    idx_l = {u: i for i, u in enumerate(D.l_urls)}
    out = []

    def uno(name, kind, urls, s, ab, tot, g, titulo):
        return type("Pl", (), dict(name=name, kind=kind, n=len(urls), urls=urls, titulo=titulo, s={IND: s}, ab={IND: ab}, tot=tot,
                                   g={IND: g}, jud={IND: np.array([u in D.juzg2 for u in urls])},
                                   pos={IND: np.array([u in D.pos2 for u in urls])}))

    for l in E.LUG:
        urls = sorted(D.urls_lugar[l])
        ii = np.array([idx_l[u] for u in urls])
        out.append(uno(l, "lugar", np.array(urls), D.l_prod[IND][ii], D.t2_ab_l[IND][ii], D.l_tot[ii], D.g_l[IND][ii], D.l["titulo"].values[ii]))
    for dep in E.HOLD:
        m = np.where(D.nac["departamento"].values == dep)[0]
        urls = D.nac["url"].values[m]
        o = np.argsort(urls, kind="stable")
        m, urls = m[o], urls[o]
        assert D.t2_h_ok[m].all()
        out.append(uno(dep, "holdout", urls, D.s[IND][m], D.t2_ab_h[IND][m], D.s["NULA_TEST"][m], D.g_nac[IND][m], D.nac["titulo"].values[m]))
    return out


def sanidad(D, places, base, inc):
    filas = []

    def chk(nombre, ok, valor, esperado):
        filas.append({"chequeo": nombre, "ok": bool(ok), "valor": str(valor), "esperado": str(esperado)})
        print(f"  [{'OK' if ok else 'FALLA'}] {nombre}: {valor} (esperado {esperado})")

    chk("S1 sin lista nueva: cortes", base["cortes"] == E.CORTES_PROD, base["cortes"], E.CORTES_PROD)
    chk("S1 clases 6/19/7", base["dist"] == {"Bajo": 6, "Medio": 19, "Alto": 7}, base["dist"], "6/19/7")
    chk("S1 Spearman DANE", round(base["rho_dane"], 4) == E.BASE_DANE, round(base["rho_dane"], 4), E.BASE_DANE)
    chk("S1 Spearman tamano", round(base["rho_size"], 4) == E.BASE_TAM, round(base["rho_size"], 4), E.BASE_TAM)
    chk("S1 anclas rotas", base["anclas_rotas"] == 0, base["anclas_rotas"], 0)
    pool = pd.read_csv(os.path.join(DIR_J, "pool.csv"))
    pool = pool[pool["indicador"] == IND]
    malos, det = 0, []
    for p in places:
        pl = pool[pool["lugar"] == p.name]
        for con, col in ((False, "en_topk_v01"), (True, "en_topk_v08")):
            x = p.s[IND] * p.g[IND] if con else p.s[IND]
            k = min(10, int(np.count_nonzero(x > 0)))
            o = np.lexsort((np.arange(p.n), -x))[:k]
            if set(p.urls[o]) != set(pl.loc[pl[col], "url"]):
                malos += 1
                det.append((p.name, col))
    chk("S2 top-k de V01 y V08 (7 lugares) recalculados = pool.csv", malos == 0, f"{malos} discrepancias {det}", 0)
    lugares_pool = set(pool["lugar"])
    chk("S2 lugares del pool = los 7", lugares_pool == {p.name for p in places}, sorted(lugares_pool), "7 lugares")
    cov = min(float(E.m_place(p, IND, c)[4]) for p in places for c in (False, True) if not np.isnan(E.m_place(p, IND, c)[4]))
    chk("S3 cobertura de juicio minima de los 14 top-k", cov >= 0.999, cov, 1.0)
    fila = inc.set_index("indicador").loc[IND]
    got = {c: round(float(fila[c]), 4) for c in C_ESPERADA}
    chk("S4 condicion C reproduce la del cribado (4 comparaciones)", got == C_ESPERADA, got, C_ESPERADA)
    ok = all(np.isfinite(p.ab[IND]).all() for p in places)
    chk("S5 gemelas presentes en los 7 lugares", ok, ok, True)
    cons = pd.read_csv(os.path.join(DIR_J, "consolidacion.csv")).iloc[0]
    chk("S6 consolidacion: medible y kappa >= 0.4", (not cons["no_medible"]) and (not cons["kappa_baja"]),
        f"kappa {cons['kappa_pool']}, SI/SI {int(cons['si_si_pool'])}", "kappa >= 0.4 y SI/SI >= 5")
    return pd.DataFrame(filas)


def trazabilidad(D, places):
    filas = []
    for p in places:
        for var, con in (("sin_filtro", False), ("con_filtro", True)):
            x = p.s[IND] * (p.g[IND] if con else 1.0)
            m = X.metricas_celda(x, np.arange(p.n), p.pos[IND], p.jud[IND], bool(p.pos[IND].any()))
            mx = float(x.max())
            if mx > 0:
                j = int(np.lexsort((np.arange(p.n), -x))[0])
                u, t = p.urls[j], p.titulo[j]
                if (u, IND) in D.et2.index:
                    e = D.et2.loc[(u, IND)]
                    et, ee, ef = ("SI" if bool(e["ref"]) else "NO"), e["etiqueta_e"], e["etiqueta_f"]
                else:
                    et, ee, ef = "sin juzgar", "", ""
            else:
                u, t, et, ee, ef = "", "(MAX = 0)", "n/a", "", ""
            filas.append({"indicador": IND, "lugar": p.name, "version": var, "MAX": mx, "url": u, "titulo": t,
                          "etiqueta_ref": et, "etiqueta_e": ee, "etiqueta_f": ef, "M1": m[0]})
    return pd.DataFrame(filas)


def main():
    print("Cargando datos (tokenizando; unos minutos)...")
    D = cargar_t2()
    places = armar_places_t2(D)
    base = E.criterios(D, [])
    mm = E.metricas_m(places)
    inc, det_b, det_c = E.inclusion(places, mm)
    print("\n=== S. Sanidad ===")
    san = sanidad(D, places, base, inc)
    if not san["ok"].all():
        with pd.ExcelWriter(SALIDA_XLSX.replace(".xlsx", "_FALLA_SANIDAD.xlsx"), engine="openpyxl") as w:
            san.to_excel(w, sheet_name="S_sanidad", index=False)
        sys.exit("PARADA: la sanidad no cumple el pre-registro; no se decide nada")

    print("\nInclusion:\n", inc.round(5).T.to_string())
    entra = bool(inc.loc[0, "entra"])
    tp = E.tope(inc)
    admitidas = list(tp.loc[tp["admitida"], "indicador"])
    sola = E.criterios(D, [IND], base)
    final, pasos, orden_ret = [], [], []
    if admitidas:
        f_, pasos, orden_ret = E.cadena(D, admitidas, inc, base)
        final = f_ or []
    if not entra:
        cfalla = [k for k, c in (("(a)", "a_pasa"), ("(b)", "b_pasa"), ("(c)", "c_pasa"), ("(d)", "d_pasa")) if not bool(inc.loc[0, c])]
        ver = {"veredicto": "NO ADOPTAR", "motivo": f"no cumple la regla de inclusión: falla {', '.join(cfalla)}; gana el statu quo (PREREG e2 §0)"}
    elif not final:
        ver = {"veredicto": "NO ADOPTAR", "motivo": "el mecanismo combinado no cumple los tres criterios del radar (§6)"}
    elif pasos[-1]["dif_max_radar"] < E.TOL:
        ver = {"veredicto": "NO ADOPTAR", "motivo": "empate con el statu quo: |Δ radar| < 5e-5 en los 32 departamentos"}
    else:
        ver = {"veredicto": "ADOPTAR", "motivo": "cumple (a)-(d) y los tres criterios del radar combinado"}
    print("VEREDICTO:", ver)

    tr = trazabilidad(D, places)
    ntr = {v: int((tr[tr["version"] == v]["etiqueta_ref"] == "SI").sum()) for v in ("sin_filtro", "con_filtro")}
    m1 = {v: int(tr[tr["version"] == v]["M1"].sum()) for v in ("sin_filtro", "con_filtro")}
    print("trazabilidad SI:", ntr, "M1:", m1)

    fila_cfg = E.fila_cfg(sola)
    imp = None
    if entra:
        imp = E.impacto(D, [IND], base, "zonas_proteccion_alimentaria (+2 de produccion)")
    r_base = pd.DataFrame([{"cortes": E._cz(base), "anclas_rotas": base["anclas_rotas"], "rho_dane": base["rho_dane"], "rho_size": base["rho_size"],
                            "clases_B/M/A": "6/19/7"}])
    os.makedirs(os.path.dirname(SALIDA_XLSX), exist_ok=True)
    with pd.ExcelWriter(SALIDA_XLSX, engine="openpyxl") as w:
        san.to_excel(w, sheet_name="S_sanidad", index=False)
        mm.to_excel(w, sheet_name="M_metricas", index=False)
        inc.to_excel(w, sheet_name="I_inclusion", index=False)
        det_b.to_excel(w, sheet_name="I_holdout_b", index=False)
        det_c.to_excel(w, sheet_name="I_control_c", index=False)
        r_base.to_excel(w, sheet_name="R_base", index=False)
        pd.DataFrame([fila_cfg]).to_excel(w, sheet_name="R_combinado", index=False)
        pd.DataFrame([{"veredicto": ver["veredicto"], "motivo": ver["motivo"], "entra": entra}]).to_excel(w, sheet_name="V_veredicto", index=False)
        if imp:
            fd, indi, tot, fl, r = imp
            pd.DataFrame([tot]).to_excel(w, sheet_name="F_resumen", index=False)
            fd.reset_index().rename(columns={"index": "departamento"}).round(6).to_excel(w, sheet_name="F_deptos", index=False)
            indi.reset_index().round(6).to_excel(w, sheet_name="F_indicadores", index=False)
            fl.reset_index().rename(columns={"index": "lugar"}).round(6).to_excel(w, sheet_name="F_lugares", index=False)
        else:
            pd.DataFrame([{"nota": "no entra por (a)-(d): sin mecanismo combinado ni impacto"}]).to_excel(w, sheet_name="F_resumen", index=False)
        tr.to_excel(w, sheet_name="Z_trazabilidad", index=False)

    escribir_md(ver, inc, det_b, mm, sola, imp, tr, ntr, m1, san, entra, pasos)
    print(f"\nGuardado -> {SALIDA_XLSX} y {SALIDA_MD}")


def escribir_md(ver, inc, det_b, mm, sola, imp, tr, ntr, m1, san, entra, pasos):
    i = inc.iloc[0]
    cons = pd.read_csv(os.path.join(DIR_J, "consolidacion.csv")).iloc[0]
    pf = lambda b: "pasa" if b else "falla"  # noqa: E731
    L = ["# Resultados — pre-filtro por indicador, etapa 2 (tramo 2): análisis final de `zonas_proteccion_alimentaria`", "",
         f"**Veredicto: {ver['veredicto']}.** {ver['motivo']}.", "",
         "Generado por `experimentos/exp_prefiltro_e2_t2_analisis.py`; tablas en `experimentos/resultados/exp_prefiltro_e2_t2_analisis.xlsx`. "
         "Pre-registro: `PREREG_prefiltro_indicador_e2_t2.md` §4 → `PREREG_prefiltro_indicador_e2.md` §3–§6 tal cual. Referencia: SÍ de `juez-e` "
         "y de `juez-f` (`juicio_prefiltro_e2_t2/etiquetas.csv`); kappa (pool) "
         f"{cons['kappa_pool']:.2f}, SÍ/SÍ {int(cons['si_si_pool'])} (SÍ juez-e {int(cons['si_e_pool'])}, juez-f {int(cons['si_f_pool'])}), "
         f"{int(cons['n_pool'])} url, cobertura mínima de los top-k {cons['cobertura_min']:.2f}.", "",
         "## Regla de inclusión (a)–(d)", "",
         f"- (a) M2 medio de los 4 lugares: V01 {i['a_M2_V01']:.4f} → V08 {i['a_M2_V08']:.4f}, Δ {i['a_ganancia']:+.4f} (exigido ≥ +0.20): **{pf(i['a_pasa'])}**.",
         f"- (b) M2 medio del holdout: {i['b_M2_sin']:.4f} → {i['b_M2_con']:.4f}, Δ {i['b_ganancia']:+.4f} (exigido ≥ +0.10) y cobertura mínima {i['b_cobertura_min']:.3f} (≥ 0.90): **{pf(i['b_pasa'])}**.",
         f"- (c) control absurdo (con − sin máscara de la brecha, tol 5e-5): gemela lugares {i['c_dif_gemela_lugares']:+.5f}, total lugares {i['c_dif_total_lugares']:+.5f}, "
         f"gemela holdout {i['c_dif_gemela_holdout']:+.5f}, total holdout {i['c_dif_total_holdout']:+.5f}: **{pf(i['c_pasa'])}**.",
         f"- (d) M3 (corte 0.7572), violaciones en los 7 lugares: {int(i['d_violaciones_V01'])} → {int(i['d_violaciones_V08'])}, nuevas {int(i['d_nuevas'])} "
         f"(con corte 0.766: {int(i['d_nuevas_con_0.766'])} nuevas): **{pf(i['d_pasa'])}**.",
         f"- Entra por (a)–(d): **{'sí' if entra else 'no'}**.", "",
         "### M1–M4 por lugar y variante (V01 sin compuerta, V08 con compuerta)", ""]
    mt = mm[["lugar", "tipo", "variante", "n_positivos", "M1", "M2", "cobertura", "k", "MAX", "M3_viola_0.7572", "M3_viola_0.766", "MAX_gemela", "MAX_absurdo_total"]]
    L += E.md_tabla(mt, ren={"M3_viola_0.7572": "M3 viola 0.7572", "M3_viola_0.766": "M3 viola 0.766", "MAX_absurdo_total": "MAX absurdo"})
    L += ["", "M4 = `MAX_gemela` y `MAX_absurdo_total` (razones a MAX en la hoja `M_metricas`). Holdout, detalle de (b):", ""]
    L += E.md_tabla(det_b)
    L += ["", "## Mecanismo combinado (§6) y radar nacional", ""]
    if entra:
        p = pasos[-1]
        L += [f"2 listas de producción + `{IND}`: cortes {E._cz(p)}, anclas rotas {p['anclas_rotas']}, Spearman DANE {p['rho_dane']:+.4f} (≥ −0.0913: {'sí' if p['c2_dane'] else 'no'}), "
              f"tamaño {p['rho_size']:+.4f} (≤ +0.8640: {'sí' if p['c3_tam'] else 'no'}), clases {'/'.join(str(p['dist'].get(k, 0)) for k in ('Bajo', 'Medio', 'Alto'))}, "
              f"máx |Δ radar| {p['dif_max_radar']:.4f} (empate si < 5e-5). Pasa: {'sí' if p['pasa'] else 'no'}.", ""]
    else:
        L += [f"No entra por (a)–(d): el mecanismo combinado no se evalúa como decisión. Informativo (cribado, lista sola): cortes {E._cz(sola)}, anclas {sola['anclas_rotas']}, "
              f"Spearman DANE {sola['rho_dane']:+.4f}, tamaño {sola['rho_size']:+.4f}, máx |Δ radar| {sola['dif_max_radar']:.4f}.", ""]
    L += ["## Impacto", ""]
    if imp:
        fd, indi, tot, fl, r = imp
        L += E.md_tabla(pd.DataFrame([tot])) + ["", "Departamentos (radar sin → con; clase con cortes recalibrados):", ""]
        L += E.md_tabla(fd.reset_index().rename(columns={"index": "departamento"})[["departamento", "radar_sin", "radar_con", "diferencia", "clase_sin", "clase_con_recalibrados", "cambia_recalibrados"]])
        L += ["", "Lugares (producción × compuerta de zonas):", ""]
        L += E.md_tabla(fl.reset_index().rename(columns={"index": "lugar"})[["lugar", "radar_sin", "radar_con", "diferencia", "clase_sin", "clase_con_recalibrados", "indicadores_que_cambian"]])
        L += ["", "Indicadores con celdas MAX cambiadas:", ""] + E.md_tabla(indi.reset_index())
    else:
        L += ["No entra: sin impacto (radar y lugares idénticos a producción)."]
    L += ["", "## Trazabilidad del MAX (§7, reporte)", "",
          f"Artículo que fija el MAX de `{IND}` en los 7 lugares: referencia SÍ {ntr['sin_filtro']} de 7 sin filtro y {ntr['con_filtro']} de 7 con filtro (M1: {m1['sin_filtro']} → {m1['con_filtro']}).", ""]
    L += E.md_tabla(tr[["lugar", "version", "MAX", "etiqueta_ref", "etiqueta_e", "etiqueta_f", "M1", "titulo"]])
    L += ["", "## Salvedades y desviaciones", "",
          f"- n pequeño: {int(cons['si_si_pool'])} SÍ/SÍ en 105 url; el M2 de cada lugar descansa en pocos positivos y el holdout son solo 3 departamentos (PREREG e2 §11).",
          "- La condición R del cribado pasó por igualdad de Spearman DANE: −0.0913 a 4 decimales, igual al de producción (criterio de no empeorar, mejora nula; n = 32).",
          "- Un pase sería marginal: una lista sobreviviente entre once evaluadas en el cribado (multiplicidad, PREREG t2 §9).",
          "- Referencia = SÍ de ambos jueces sobre el pool (top-10 de V01 ∪ V08); lo no juzgado cuenta como negativo en M1/M2 (cotas superiores en el xlsx).",
          "- Se reutilizan `metricas_m`, `inclusion`, `tope`, `criterios`, `cadena` e `impacto` de `exp_prefiltro_e2.py` inyectando el indicador (sin modificar ese archivo); la trazabilidad se reescribe para las etiquetas de juez-e/juez-f.",
          "- Desviaciones del pre-registro: ninguna.", "",
          "## Sanidad", ""] + E.md_tabla(san[["chequeo", "ok", "valor", "esperado"]]) + ["", f"{int(san['ok'].sum())} de {len(san)} chequeos OK."]
    with open(SALIDA_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
