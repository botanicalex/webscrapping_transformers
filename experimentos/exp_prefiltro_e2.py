# -*- coding: utf-8 -*-
"""
F3 de la etapa 2 del pre-filtro por indicador (experimentos/PREREG_prefiltro_indicador_e2.md): regla de inclusion (a)-(d)
de los 4 indicadores medibles, tope (§5), mecanismo combinado con cortes recalibrados y retirada (§6), impacto y
trazabilidad del MAX (§7). Todo offline (pkl y csv existentes; sin GPU; no escribe en datos/).

Mecanismo: score' = s x 1[lista del indicador en la premisa visible normalizada, recortada con la hipotesis del indicador].
V01 = sin compuerta (produccion actual); V08 = V01 x compuerta. La gemela y el absurdo total se multiplican por la MISMA
compuerta. Referencia = SI de juez-c y juez-d (etiquetas.csv).

  PYTHONIOENCODING=utf-8 python experimentos/exp_prefiltro_e2.py
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

P = C.P
DIR_J = "experimentos/resultados/juicio_prefiltro_e2"
E2_PKL = "datos/scores/scores_prefiltro_e2.pkl"
PROC_PREF = "resultados/tablas_lugares_max_prefiltro_2026-09-29/df_procesado_5lugares.pkl"
SALIDA_XLSX = "experimentos/resultados/exp_prefiltro_e2.xlsx"
SALIDA_MD = "experimentos/RESULTADOS_prefiltro_e2.md"

INDS26 = X.INDS26
LUG, HOLD = X.LUG, X.HOLDOUT
PROD = list(C.prefiltro_produccion())                       # las 2 listas de produccion (leidas de src/ sin importarlo)
NOMEDIBLES = ["reasentamiento", "danos_ambientales"]        # consolidacion.csv (F2): < 5 SI/SI
CAND = [i for i in P.TRAMO_1 if i not in NOMEDIBLES]        # a evaluar con (a)-(d)
CORTES_PROD = (0.7572, 0.9233)
CORTE, CORTE_ALT = 0.7572, 0.766
BASE_DANE, BASE_TAM = -0.0913, 0.8640
GAN_A, GAN_B, COB_MIN, TOL = 0.20, 0.10, 0.90, 5e-5
EPS = 1e-9


# ═══════════════════════════════════════════════════════════════════════════
# Datos
# ═══════════════════════════════════════════════════════════════════════════
def cargar():
    from types import SimpleNamespace as NS
    D = NS()
    tok = C.cargar_tokenizer()
    cn = pd.read_pickle(C.CORPUS_NAC).reset_index(drop=True)
    dn = pd.read_pickle(X.V2NAC).reset_index(drop=True)
    assert len(cn) == len(dn) == 11439
    assert (cn["titulo"].values == dn["titulo"].values).all() and (cn["departamento"].values == dn["departamento"].values).all()
    D.nac = cn[["url", "departamento", "titulo"]].copy()
    D.sesgo = dn["sesgo"].values.astype(float)
    D.s = {c: X.s_corr(dn[f"ent_{c}"].values, dn[f"neu_{c}"].values, D.sesgo) for c in INDS26 + ["NULA_TEST"]}
    D.n_art = D.nac["departamento"].value_counts()
    txt_n = cn["texto"].fillna("").astype(str).tolist()
    # lugares
    cl = pd.read_pickle(X.CORPUS_L).reset_index(drop=True)
    at = pd.read_pickle(X.ATOMICAS_L).reset_index(drop=True)
    pp = pd.read_pickle(PROC_PREF).reset_index(drop=True)
    pm = pd.read_pickle(X.PROCESADO_L).reset_index(drop=True)
    assert (at["url"].values == cl["url"].values).all() and (pp["url"].values == cl["url"].values).all() \
        and (pm["url"].values == cl["url"].values).all()
    D.l = cl[["url", "departamento", "titulo"]].copy()
    D.l_urls = cl["url"].values
    ses = at["sesgo"].values.astype(float)
    D.l_prod = {c: pp[c].astype(float).values for c in INDS26}     # produccion actual (2 listas ya aplicadas)
    D.l_v01 = {i: pm[i].astype(float).values for i in P.TRAMO_1}    # sin compuerta
    gl = pd.read_pickle(X.GPU_L).set_index("url").loc[cl["url"]]
    D.l_tot = X.s_corr(gl["ent_NULA_TEST"].values, gl["neu_NULA_TEST"].values, ses)
    e2 = pd.read_pickle(E2_PKL)
    assert e2["url"].is_unique
    e2 = e2.set_index("url")
    D.l_ab = {i: X.s_corr(e2.loc[cl["url"], f"ent_{i}__gemela"].values, e2.loc[cl["url"], f"neu_{i}__gemela"].values, ses)
              for i in P.TRAMO_1}
    D.h_ab = {i: X.s_corr(e2.reindex(cn["url"])[f"ent_{i}__gemela"].values, e2.reindex(cn["url"])[f"neu_{i}__gemela"].values, D.sesgo)
              for i in P.TRAMO_1}    # solo validas en el holdout (los demas departamentos no tienen gemela en el pkl)
    D.h_ab_ok = cn["url"].isin(e2.index).values  # ojo: url repetidas en el nacional se resuelven igual
    txt_l = cl["texto"].fillna("").astype(str).tolist()
    # compuertas: lista de cada indicador sobre su premisa visible con SU hipotesis
    D.rx = dict(P.LISTAS_TRAMO_1)
    D.rx.update(C.prefiltro_produccion())
    D.g_nac, D.g_l = {}, {}
    for ind in sorted(set(PROD) | set(P.TRAMO_1)):
        hip = C.V2.TODAS[ind]
        D.g_nac[ind] = np.array(C.compuerta(C.premisa_visible_prod(txt_n, tok, hip), D.rx[ind]))
        D.g_l[ind] = np.array(C.compuerta(C.premisa_visible_prod(txt_l, tok, hip), D.rx[ind]))
    lug = pd.read_csv(X.URL_LUGARES)
    D.urls_lugar = {l: set(lug.loc[lug["lugar"] == l, "url"]) for l in LUG}
    D.oficial = pd.read_excel(X.OFICIAL, engine="openpyxl")
    D.oficial.columns = [str(c).strip() for c in D.oficial.columns]
    D.oficial["_k"] = D.oficial["Departamento"].map(X._norm)
    # referencia
    et = pd.read_csv(os.path.join(DIR_J, "etiquetas.csv"))
    D.et = et.set_index(["url", "indicador"])
    D.juzg = {i: set(et.loc[et["indicador"] == i, "url"]) for i in P.TRAMO_1}
    D.pos = {i: set(et.loc[(et["indicador"] == i) & et["ref"], "url"]) for i in P.TRAMO_1}
    return D


def armar_places(D):
    idx_l = {u: i for i, u in enumerate(D.l_urls)}
    places = []
    for l in LUG:
        urls = sorted(D.urls_lugar[l])
        ii = np.array([idx_l[u] for u in urls])
        places.append(dict(name=l, kind="lugar", n=len(ii), urls=np.array(urls), titulo=D.l["titulo"].values[ii],
                           s={i: D.l_v01[i][ii] for i in P.TRAMO_1}, ab={i: D.l_ab[i][ii] for i in P.TRAMO_1},
                           tot=D.l_tot[ii], g={i: D.g_l[i][ii] for i in P.TRAMO_1},
                           jud={i: np.array([u in D.juzg[i] for u in urls]) for i in P.TRAMO_1},
                           pos={i: np.array([u in D.pos[i] for u in urls]) for i in P.TRAMO_1}))
    for dep in HOLD:
        m = np.where(D.nac["departamento"].values == dep)[0]
        urls = D.nac["url"].values[m]
        o = np.argsort(urls, kind="stable")
        m, urls = m[o], urls[o]
        assert D.h_ab_ok[m].all()
        places.append(dict(name=dep, kind="holdout", n=len(m), urls=urls, titulo=D.nac["titulo"].values[m],
                           s={i: D.s[i][m] for i in P.TRAMO_1}, ab={i: D.h_ab[i][m] for i in P.TRAMO_1},
                           tot=D.s["NULA_TEST"][m], g={i: D.g_nac[i][m] for i in P.TRAMO_1},
                           jud={i: np.array([u in D.juzg[i] for u in urls]) for i in P.TRAMO_1},
                           pos={i: np.array([u in D.pos[i] for u in urls]) for i in P.TRAMO_1}))
    return [type("Pl", (), p) for p in places]


def m_place(p, ind, con):
    x = p.s[ind] * p.g[ind] if con else p.s[ind]
    return X.metricas_celda(x, np.arange(p.n), p.pos[ind], p.jud[ind], bool(p.pos[ind].any()))


# ═══════════════════════════════════════════════════════════════════════════
# Sanidad
# ═══════════════════════════════════════════════════════════════════════════
def sanidad(D, places, base):
    filas = []

    def chk(nombre, ok, valor, esperado):
        filas.append({"chequeo": nombre, "ok": bool(ok), "valor": str(valor), "esperado": str(esperado)})
        print(f"  [{'OK' if ok else 'FALLA'}] {nombre}: {valor} (esperado {esperado})")

    chk("S1 produccion actual: cortes de elegir_cortes", base["cortes"] == CORTES_PROD, base["cortes"], CORTES_PROD)
    chk("S1 produccion actual: clases 6/19/7", base["dist"] == {"Bajo": 6, "Medio": 19, "Alto": 7}, base["dist"], "6/19/7")
    chk("S1 produccion actual: Spearman DANE", round(base["rho_dane"], 4) == BASE_DANE, round(base["rho_dane"], 4), BASE_DANE)
    chk("S1 produccion actual: Spearman con el tamano", round(base["rho_size"], 4) == BASE_TAM, round(base["rho_size"], 4), BASE_TAM)
    chk("S1 produccion actual: anclas rotas", base["anclas_rotas"] == 0, base["anclas_rotas"], 0)
    # S2 V01 de lugares: corrida de produccion 2026-09-29 = tablas_lugares_max en los 6 indicadores sin filtro
    pp = pd.read_pickle(PROC_PREF).reset_index(drop=True)
    pm0 = pd.read_pickle(X.PROCESADO_L).reset_index(drop=True)
    d = max(float(np.abs(pp[i].astype(float).values - pm0[i].astype(float).values).max()) for i in P.TRAMO_1)
    chk("S2 lugares: los 6 indicadores del tramo, produccion 2026-09-29 vs tablas_lugares_max", d < 1e-6, f"max|dif|={d:.1e}", "< 1e-6")
    # S3 produccion de lugares: columnas de las 2 listas = sin filtro x compuerta
    pm = pd.read_pickle(X.PROCESADO_L).reset_index(drop=True)
    d = max(float(np.abs(D.l_prod[i] - pm[i].astype(float).values * D.g_l[i]).max()) for i in PROD)
    chk("S3 lugares: columnas de produccion (2 listas) = sin filtro x compuerta recalculada", d < 1e-6, f"max|dif|={d:.1e}", "< 1e-6")
    # S4 top-k de V01 y V08 recalculados = pool.csv
    pool = pd.read_csv(os.path.join(DIR_J, "pool.csv"))
    malos = 0
    for ind in P.TRAMO_1:
        for p in places:
            pl = pool[(pool["indicador"] == ind) & (pool["lugar"] == p.name)]
            if pl.empty:
                continue
            nomb = set()
            for con, col in ((False, "en_topk_v01"), (True, "en_topk_v08")):
                x = p.s[ind] * p.g[ind] if con else p.s[ind]
                k = min(10, int(np.count_nonzero(x > 0)))
                o = np.lexsort((np.arange(p.n), -x))[:k]
                if set(p.urls[o]) != set(pl.loc[pl[col], "url"]):
                    malos += 1
    chk("S4 top-k de V01 y V08 (6 indicadores x 7 lugares) = pool.csv", malos == 0, f"{malos} discrepancias", 0)
    # S5 cobertura de juicio
    cov = min(float(m_place(p, i, c)[4]) for p in places for i in P.TRAMO_1 for c in (False, True) if not np.isnan(m_place(p, i, c)[4]))
    chk("S5 cobertura de juicio minima de todos los top-k", cov >= 0.999, cov, 1.0)
    # S6 gemelas completas
    ok = all(np.isfinite(p.ab[i]).all() for p in places for i in P.TRAMO_1)
    chk("S6 gemelas presentes en los 7 lugares", ok, ok, True)
    # S7 no medibles segun consolidacion
    cons = pd.read_csv(os.path.join(DIR_J, "consolidacion.csv")).set_index("indicador")
    nm = sorted(cons.index[cons["no_medible"]])
    chk("S7 no medibles de la F2 = reasentamiento y danos_ambientales", nm == sorted(NOMEDIBLES), nm, sorted(NOMEDIBLES))
    return pd.DataFrame(filas)


# ═══════════════════════════════════════════════════════════════════════════
# M1-M4 por indicador, lugar y variante
# ═══════════════════════════════════════════════════════════════════════════
def metricas_m(places):
    filas = []
    for ind in CAND:
        for p in places:
            for var, con in (("V01", False), ("V08", True)):
                x = p.s[ind] * (p.g[ind] if con else 1.0)
                m = m_place(p, ind, con)
                ga = p.g[ind] if con else 1.0
                ab, to = float((p.ab[ind] * ga).max()), float((p.tot * ga).max())
                mx = float(x.max())
                hp = bool(p.pos[ind].any())
                f = {"indicador": ind, "lugar": p.name, "tipo": p.kind, "variante": var, "n_articulos": p.n,
                     "n_positivos": int(p.pos[ind].sum()), "M1": m[0], "M1_cota_sup": m[1], "M2": m[2], "M2_cota_sup": m[3],
                     "cobertura": m[4], "k": m[5], "MAX": mx, "MAX_gemela": ab, "MAX_absurdo_total": to,
                     "prop_gt_0.7572": float((x > CORTE).mean()), "prop_gt_0.766": float((x > CORTE_ALT).mean()),
                     "razon_gemela/MAX": ab / mx if mx > 0 else np.nan, "razon_total/MAX": to / mx if mx > 0 else np.nan}
                for nm, c in (("0.7572", CORTE), ("0.766", CORTE_ALT)):
                    f[f"M3_viola_{nm}"] = bool((not hp and mx >= c) or (hp and mx < c))
                filas.append(f)
    return pd.DataFrame(filas)


# ═══════════════════════════════════════════════════════════════════════════
# Regla de inclusion (a)-(d)
# ═══════════════════════════════════════════════════════════════════════════
def inclusion(places, mm):
    lug = [p for p in places if p.kind == "lugar"]
    hol = [p for p in places if p.kind == "holdout"]
    filas, det_b, det_c = [], [], []
    for ind in CAND:
        f = {"indicador": ind}
        rec = {con: float(np.mean([m_place(p, ind, con)[2] for p in lug])) for con in (False, True)}
        f.update({"a_M2_V01": rec[False], "a_M2_V08": rec[True], "a_ganancia": rec[True] - rec[False]})
        f["a_pasa"] = bool(f["a_ganancia"] >= GAN_A - EPS)
        b_rows = []
        for p in hol:
            s0, s1 = m_place(p, ind, False), m_place(p, ind, True)
            b_rows.append({"indicador": ind, "departamento": p.name, "n_positivos": int(p.pos[ind].sum()),
                           "k_sin": int(s0[5]), "M2_sin": s0[2], "cobertura_sin": s0[4],
                           "k_con": int(s1[5]), "M2_con": s1[2], "cobertura_con": s1[4]})
        bd = pd.DataFrame(b_rows)
        det_b.append(bd)
        cv = np.r_[bd["cobertura_sin"].values, bd["cobertura_con"].values]
        cov_min = float(np.nanmin(cv)) if np.isfinite(cv).any() else 1.0   # k = 0: nada que juzgar
        f.update({"b_M2_sin": float(bd["M2_sin"].mean()), "b_M2_con": float(bd["M2_con"].mean()),
                  "b_ganancia": float(bd["M2_con"].mean() - bd["M2_sin"].mean()), "b_cobertura_min": cov_min})
        f["b_pasa"] = bool(f["b_ganancia"] >= GAN_B - EPS and cov_min >= COB_MIN - EPS)
        c_rows = []
        for p in places:
            g = p.g[ind]
            re_s, re_c = float(p.s[ind].max()), float((p.s[ind] * g).max())
            ab_s, ab_c = float(p.ab[ind].max()), float((p.ab[ind] * g).max())
            to_s, to_c = float(p.tot.max()), float((p.tot * g).max())
            c_rows.append({"indicador": ind, "lugar": p.name, "tipo": p.kind, "real_sin": re_s, "real_con": re_c,
                           "gemela_sin": ab_s, "gemela_con": ab_c, "total_sin": to_s, "total_con": to_c,
                           "brecha_gemela_sin": re_s - ab_s, "brecha_gemela_con": re_c - ab_c,
                           "brecha_total_sin": re_s - to_s, "brecha_total_con": re_c - to_c})
        cd = pd.DataFrame(c_rows)
        det_c.append(cd)
        comp = {}
        for grupo, sel in (("lugares", cd["tipo"] == "lugar"), ("holdout", cd["tipo"] == "holdout")):
            for tw in ("gemela", "total"):
                comp[f"c_dif_{tw}_{grupo}"] = float(cd.loc[sel, f"brecha_{tw}_con"].mean() - cd.loc[sel, f"brecha_{tw}_sin"].mean())
        f.update(comp)
        f["c_pasa"] = bool(all(v >= -TOL for v in comp.values()))
        sub = mm[(mm["indicador"] == ind)]
        piv = sub.pivot(index="lugar", columns="variante", values="M3_viola_0.7572")
        f["d_violaciones_V01"] = int(piv["V01"].sum())
        f["d_violaciones_V08"] = int(piv["V08"].sum())
        f["d_nuevas"] = int((piv["V08"] & ~piv["V01"]).sum())
        pv2 = sub.pivot(index="lugar", columns="variante", values="M3_viola_0.766")
        f["d_nuevas_con_0.766"] = int((pv2["V08"] & ~pv2["V01"]).sum())
        f["d_pasa"] = bool(f["d_nuevas"] == 0)
        f["entra"] = bool(f["a_pasa"] and f["b_pasa"] and f["c_pasa"] and f["d_pasa"])
        filas.append(f)
    return pd.DataFrame(filas), pd.concat(det_b, ignore_index=True), pd.concat(det_c, ignore_index=True)


def tope(inc):
    ok = inc[inc["entra"]].copy()
    ok = ok.sort_values(["b_ganancia", "a_ganancia", "indicador"], ascending=[False, False, True]).reset_index(drop=True)
    ok["orden"] = np.arange(1, len(ok) + 1)
    ok["admitida"] = ok["orden"] <= P.MAX_LISTAS_NUEVAS
    return ok[["indicador", "b_ganancia", "a_ganancia", "orden", "admitida"]]


# ═══════════════════════════════════════════════════════════════════════════
# Radar nacional (mecanismo combinado)
# ═══════════════════════════════════════════════════════════════════════════
def radar_nac(D, nuevas):
    listas = set(PROD) | set(nuevas)
    deps = D.nac["departamento"].values
    cols = {c: D.s[c] * (D.g_nac[c] if c in listas else 1.0) for c in INDS26}
    m = pd.DataFrame(cols).groupby(deps).max()
    assert m.shape == (32, 26)
    return m.mean(axis=1), m


def criterios(D, nuevas, base=None):
    r, mx = radar_nac(D, nuevas)
    try:
        cb, ca, _, _ = X.elegir_cortes(r)
        cortes = (float(cb), float(ca))
    except RuntimeError:
        cortes = None
    ofi = D.oficial.set_index("_k")["radar_oficial_promedio"]
    rho_dane = float(spearmanr(r.values, ofi.loc[[X._norm(k) for k in r.index]].values).correlation)
    rho_size = float(spearmanr(r.values, D.n_art.reindex(r.index).values).correlation)
    out = {"nuevas": "+".join(nuevas) or "(ninguna)", "n_nuevas": len(nuevas), "cortes": cortes, "radar": r, "max": mx,
           "rho_dane": rho_dane, "rho_size": rho_size}
    if cortes:
        c = X.constancia(r, *cortes, D.oficial)
        out.update({"anclas_rotas": len(X.anclas_rotas(r, *cortes)), "dist": X.dist(c["m"]["clase"])})
    else:
        out.update({"anclas_rotas": None, "dist": {}})
    if base is not None:
        out["c1_anclas"] = bool(cortes is not None and out["anclas_rotas"] == 0)
        out["c2_dane"] = bool(round(rho_dane, 4) >= BASE_DANE)
        out["c3_tam"] = bool(round(rho_size, 4) <= BASE_TAM)
        out["pasa"] = bool(out["c1_anclas"] and out["c2_dane"] and out["c3_tam"])
        out["dif_max_radar"] = float((r - base["radar"]).abs().max())
    return out


def _cz(r):
    return f"{r['cortes'][0]:.4f}/{r['cortes'][1]:.4f}" if r["cortes"] else "sin cortes validos"


def fila_cfg(r):
    return {"nuevas": r["nuevas"], "cortes": _cz(r), "anclas_rotas": r["anclas_rotas"], "rho_dane": r["rho_dane"],
            "rho_size": r["rho_size"], "clases_B/M/A": "/".join(str(r["dist"].get(k, 0)) for k in ("Bajo", "Medio", "Alto")) if r["dist"] else "",
            "c1_anclas": r["c1_anclas"], "c2_dane": r["c2_dane"], "c3_tam": r["c3_tam"], "pasa": r["pasa"], "dif_max_radar": r["dif_max_radar"]}


def cadena(D, admitidas, inc, base):
    """Retira listas nuevas de menor a mayor ganancia de M2 en el holdout (desempate: menor ganancia en lugares; luego el
    ultimo en orden alfabetico), de forma acumulativa, recalibrando cada vez."""
    g = inc.set_index("indicador")
    orden_ret = sorted(admitidas, key=lambda i: (g.loc[i, "b_ganancia"], g.loc[i, "a_ganancia"], [-ord(c) for c in i]))
    cur, pasos = list(admitidas), []
    while cur:
        r = criterios(D, cur, base)
        pasos.append(r)
        if r["pasa"]:
            return cur, pasos, orden_ret
        cur.remove(next(x for x in orden_ret if x in cur))
    return None, pasos, orden_ret


# ═══════════════════════════════════════════════════════════════════════════
# Impacto
# ═══════════════════════════════════════════════════════════════════════════
def impacto(D, nuevas, base, nombre):
    r = criterios(D, nuevas, base)
    cortes = r["cortes"]
    sin, con = base["max"], r["max"]
    dif = con - sin
    fd = pd.DataFrame({"n_articulos": D.n_art.reindex(sin.index), "radar_sin": base["radar"], "radar_con": r["radar"]})
    fd["diferencia"] = fd["radar_con"] - fd["radar_sin"]
    fd["clase_sin"] = fd["radar_sin"].map(lambda v: X.clasificar(v, *CORTES_PROD))
    fd["clase_con_cortes_prod"] = fd["radar_con"].map(lambda v: X.clasificar(v, *CORTES_PROD))
    fd["clase_con_recalibrados"] = fd["radar_con"].map(lambda v: X.clasificar(v, *cortes)) if cortes else "s/d"
    fd["cambia_recalibrados"] = fd["clase_sin"] != fd["clase_con_recalibrados"]
    fd["cambia_cortes_prod"] = fd["clase_sin"] != fd["clase_con_cortes_prod"]
    fd.insert(0, "configuracion", nombre)
    ind = pd.DataFrame({"media_abs_dMAX": dif.abs().mean(), "celdas_gt_0.05": (dif.abs() > 0.05).sum(),
                        "celdas_a_cero": ((sin > 0) & (con == 0)).sum(), "MAX_medio_sin": sin.mean(), "MAX_medio_con": con.mean()})
    ind = ind[ind["media_abs_dMAX"] > 0].sort_values("media_abs_dMAX", ascending=False)
    ind.insert(0, "configuracion", nombre)
    ind.index.name = "indicador"
    tot = {"configuracion": nombre, "cortes": _cz(r), "clases_B/M/A_recalibradas": "/".join(str(fd["clase_con_recalibrados"].eq(k).sum()) for k in ("Bajo", "Medio", "Alto")),
           "deptos_cambian_recalibrados": int(fd["cambia_recalibrados"].sum()), "deptos_cambian_cortes_prod": int(fd["cambia_cortes_prod"].sum()),
           "media_abs_dMAX_(32x26)": float(dif.abs().values.mean()), "celdas_que_cambian": int((dif.abs() > 1e-9).sum().sum()),
           "celdas_gt_0.05": int((dif.abs() > 0.05).sum().sum()), "celdas_a_cero": int(((sin > 0) & (con == 0)).sum().sum())}
    # lugares: produccion actual x compuertas de las listas nuevas
    labs = D.l["departamento"].values
    S0 = pd.DataFrame({c: D.l_prod[c] for c in INDS26})
    S1 = pd.DataFrame({c: D.l_prod[c] * (D.g_l[c] if c in nuevas else 1.0) for c in INDS26})
    l0, l1 = S0.groupby(labs).max(), S1.groupby(labs).max()
    r0, r1 = l0.round(4).mean(axis=1), l1.round(4).mean(axis=1)
    fl = pd.DataFrame({"radar_sin": r0, "radar_con": r1, "diferencia": r1 - r0})
    fl["clase_sin"] = fl["radar_sin"].map(lambda v: X.clasificar(v, *CORTES_PROD))
    fl["clase_con_cortes_prod"] = fl["radar_con"].map(lambda v: X.clasificar(v, *CORTES_PROD))
    fl["clase_con_recalibrados"] = fl["radar_con"].map(lambda v: X.clasificar(v, *cortes)) if cortes else "s/d"
    fl["indicadores_que_cambian"] = [", ".join(f"{c} {l0.loc[g, c]:.3f}->{l1.loc[g, c]:.3f}" for c in INDS26
                                               if abs(l1.loc[g, c] - l0.loc[g, c]) > 1e-9) for g in fl.index]
    fl.insert(0, "configuracion", nombre)
    dl = l1 - l0
    tot["lugares_cambian_clase"] = int((fl["clase_sin"] != fl["clase_con_recalibrados"]).sum())
    tot["lugares_MAX_que_cambian"] = int((dl.abs() > 1e-9).sum().sum())
    return fd, ind, tot, fl, r


# ═══════════════════════════════════════════════════════════════════════════
# Trazabilidad (§7)
# ═══════════════════════════════════════════════════════════════════════════
def trazabilidad(D, places):
    filas = []
    for ind in P.TRAMO_1:
        for p in places:
            for var, con in (("sin_filtro", False), ("con_filtro", True)):
                x = p.s[ind] * (p.g[ind] if con else 1.0)
                m = X.metricas_celda(x, np.arange(p.n), p.pos[ind], p.jud[ind], bool(p.pos[ind].any()))
                mx = float(x.max())
                if mx > 0:
                    j = int(np.lexsort((np.arange(p.n), -x))[0])
                    u, t = p.urls[j], p.titulo[j]
                    if (u, ind) in D.et.index:
                        e = D.et.loc[(u, ind)]
                        et = "SI" if bool(e["ref"]) else "NO"
                        ec, ed = e["etiqueta_c"], e["etiqueta_d"]
                    else:
                        et, ec, ed = "sin juzgar", "", ""
                else:
                    u, t, et, ec, ed = "", "(MAX = 0)", "n/a", "", ""
                filas.append({"indicador": ind, "medible": ind not in NOMEDIBLES, "lugar": p.name, "version": var, "MAX": mx,
                              "url": u, "titulo": t, "etiqueta_ref": et, "etiqueta_c": ec, "etiqueta_d": ed, "M1": m[0]})
    return pd.DataFrame(filas)


def resumen_traza(tr):
    f = []
    for ind in P.TRAMO_1:
        r = {"indicador": ind, "medible": ind not in NOMEDIBLES}
        for v in ("sin_filtro", "con_filtro"):
            s = tr[(tr["indicador"] == ind) & (tr["version"] == v)]
            r[f"SI_{v}"] = int((s["etiqueta_ref"] == "SI").sum())
            r[f"NO_{v}"] = int((s["etiqueta_ref"] == "NO").sum())
            r[f"MAX0_{v}"] = int((s["etiqueta_ref"] == "n/a").sum())
            r[f"M1_{v}"] = int(s["M1"].sum())
        f.append(r)
    return pd.DataFrame(f)


# ═══════════════════════════════════════════════════════════════════════════
# Salidas
# ═══════════════════════════════════════════════════════════════════════════
def _celda(v, dec=4):
    if isinstance(v, (bool, np.bool_)):
        return "sí" if v else "no"
    if v is None or (isinstance(v, (float, np.floating)) and np.isnan(v)):
        return "—"
    if isinstance(v, (float, np.floating)):
        return f"{v:.{dec}f}"
    return str(v)


def md_tabla(df, ren=None, dec=4):
    cols = list(df.columns)
    ren = ren or {}
    L = ["| " + " | ".join(ren.get(c, str(c)) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        L.append("| " + " | ".join(_celda(r[c], dec) for c in cols) + " |")
    return L


def escribir_md(ruta, R):
    V, inc = R["veredicto"], R["inc"]
    L = ["# Resultados — pre-filtro por indicador, etapa 2 (tramo 1)", "",
         "Generado por `experimentos/exp_prefiltro_e2.py`; tablas completas en `experimentos/resultados/exp_prefiltro_e2.xlsx`. "
         "Pre-registro: `experimentos/PREREG_prefiltro_indicador_e2.md`. Referencia: SÍ de `juez-c` y `juez-d` "
         "(`juicio_prefiltro_e2/etiquetas.csv`).", "",
         f"**Veredicto: {V['veredicto']}.** {V['motivo']}. Listas nuevas que cumplen (a)–(d): {', '.join(R['entran']) or 'ninguna'}; "
         f"admitidas por el tope: {', '.join(R['admitidas']) or 'ninguna'}; configuración final: "
         f"{', '.join(V['final']) or 'ninguna (producción actual, cortes 0.7572/0.9233)'}.", "",
         "## Método", "",
         "`score' = s × 1[lista ∈ premisa visible]`, V01 = sin compuerta, V08 = con ella; gemela y absurdo total con la misma compuerta. "
         "Medibles: los 4 con ≥ 5 SÍ/SÍ; `reasentamiento` y `danos_ambientales` pasan sin filtro (solo trazabilidad). "
         "Desarrollo: 4 lugares; holdout: Cauca, Chocó, Cundinamarca. M3 con corte 0.7572 (0.766 en columnas aparte).", "",
         "## Inclusión (a)–(d) (hojas `I_inclusion`, `I_holdout_b`, `I_control_c`, `M_metricas`)", ""]
    L += md_tabla(inc[["indicador", "a_M2_V01", "a_M2_V08", "a_ganancia", "a_pasa", "b_ganancia", "b_cobertura_min", "b_pasa", "c_pasa",
                       "d_nuevas", "d_pasa", "entra"]],
                  ren={"a_M2_V01": "M2 lug. V01", "a_M2_V08": "M2 lug. V08", "a_ganancia": "(a) Δ", "a_pasa": "(a)", "b_ganancia": "(b) Δ holdout",
                       "b_cobertura_min": "cobertura mín.", "b_pasa": "(b)", "c_pasa": "(c)", "d_nuevas": "M3 nuevas", "d_pasa": "(d)"})
    L += ["", "(c): diferencia de la brecha media «MAX real − MAX control» (con − sin máscara); exigido ≥ −5e-5 en las cuatro:", ""]
    L += md_tabla(inc[["indicador", "c_dif_gemela_lugares", "c_dif_total_lugares", "c_dif_gemela_holdout", "c_dif_total_holdout", "c_pasa"]],
                  ren={"c_dif_gemela_lugares": "gemela, lugares", "c_dif_total_lugares": "total, lugares", "c_dif_gemela_holdout": "gemela, holdout",
                       "c_dif_total_holdout": "total, holdout", "c_pasa": "(c)"}, dec=5)
    L += ["", "Violaciones de M3 (sin → con filtro) en los 7 lugares: " + "; ".join(
        f"{r.indicador} {r.d_violaciones_V01}→{r.d_violaciones_V08}" for r in inc.itertuples()) + ".", "",
        "## Tope (§5) y radar combinado (§6) (hojas `T_tope`, `R_base`, `R_configs`, `R_cadena`)", ""]
    L += (md_tabla(R["tope"]) if len(R["tope"]) else ["Ninguna lista cumple (a)–(d): no hay nada que topar ni combinar."])
    L += ["", f"Producción actual (base): cortes {_cz(R['base'])}, Spearman DANE {R['base']['rho_dane']:+.4f}, tamaño {R['base']['rho_size']:+.4f}, "
          f"{R['base']['anclas_rotas']} anclas rotas, clases 6/19/7. Cada lista sola y la cadena de retirada (solo la cadena decide):", ""]
    L += md_tabla(R["cfg"], ren={"rho_dane": "Spearman DANE", "rho_size": "Spearman tamaño", "c1_anclas": "0 anclas", "c2_dane": "DANE ≥ −0.0913",
                                 "c3_tam": "tamaño ≤ 0.8640", "dif_max_radar": "máx |Δ radar|"})
    L += ["", "## Impacto (hojas `F_*`)", ""]
    if len(R["imp_res"]):
        L += md_tabla(R["imp_res"]) + [""]
    L += [R["imp_texto"], "", "## Trazabilidad del MAX (§7) (hojas `Z_trazabilidad`, `Z_resumen`)", "",
          "MAX fijado por un artículo con referencia SÍ, en 7 lugares por indicador (M1 = el artículo del MAX es positivo):", ""]
    L += md_tabla(R["tr_res"], ren={"SI_sin_filtro": "SÍ sin", "SI_con_filtro": "SÍ con", "NO_sin_filtro": "NO sin", "NO_con_filtro": "NO con",
                                    "MAX0_sin_filtro": "MAX=0 sin", "MAX0_con_filtro": "MAX=0 con", "M1_sin_filtro": "M1 sin", "M1_con_filtro": "M1 con"})
    L += ["", R["tr_texto"], "", "## Salvedades y desviaciones", ""] + R["notas"]
    L += ["", "## Sanidad (hoja `S_sanidad`)", "", f"{int(R['san']['ok'].sum())} de {len(R['san'])} chequeos OK."]
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    print("Cargando datos (tokenizando; unos minutos)...")
    D = cargar()
    places = armar_places(D)
    base = criterios(D, [])
    print("\n=== S. Sanidad ===")
    san = sanidad(D, places, base)
    if not san["ok"].all():
        sys.exit("PARADA: la sanidad no cumple el pre-registro")

    mm = metricas_m(places)
    inc, det_b, det_c = inclusion(places, mm)
    entran = list(inc.loc[inc["entra"], "indicador"])
    tp = tope(inc)
    admitidas = list(tp.loc[tp["admitida"], "indicador"])
    print("\nInclusion:\n", inc.round(4).to_string(index=False))
    print("Entran:", entran, "| admitidas:", admitidas)

    # radar: cada lista sola (no decide), todas las admitidas y cadena
    solas = [criterios(D, [i], base) for i in CAND]
    pasos, final, orden_ret = [], [], []
    if admitidas:
        final_l, pasos, orden_ret = cadena(D, admitidas, inc, base)
        final = final_l or []
    if not admitidas:
        veredicto = {"veredicto": "NO ADOPTAR", "motivo": "ninguna lista nueva cumple (a)–(d) (§0 i); gana el statu quo"}
    elif not final:
        veredicto = {"veredicto": "NO ADOPTAR", "motivo": "ninguna configuración con listas nuevas cumple los tres criterios del radar (§0 ii)"}
    elif pasos[-1]["dif_max_radar"] < TOL:
        veredicto = {"veredicto": "NO ADOPTAR", "motivo": "empate con el statu quo: |Δ radar| < 5e-5 en los 32 departamentos (§0 iii)"}
    else:
        veredicto = {"veredicto": "ADOPTAR", "motivo": "cumple (a)–(d), el tope y los tres criterios del radar"}
    veredicto["final"] = final
    print("VEREDICTO:", veredicto)

    cfg_rows = [dict(paso="sola", **fila_cfg(r)) for r in solas]
    cad_rows = [dict(paso=f"cadena {k}", **fila_cfg(r)) for k, r in enumerate(pasos)]
    cfg = pd.DataFrame(cfg_rows + cad_rows)
    cfg_md = cfg[["paso", "nuevas", "cortes", "anclas_rotas", "rho_dane", "rho_size", "clases_B/M/A", "c1_anclas", "c2_dane", "c3_tam", "pasa", "dif_max_radar"]]
    r_base = pd.DataFrame([{"cortes": _cz(base), "anclas_rotas": base["anclas_rotas"], "rho_dane": base["rho_dane"], "rho_size": base["rho_size"],
                            "clases_B/M/A": "/".join(str(base["dist"].get(k, 0)) for k in ("Bajo", "Medio", "Alto"))}])

    # impacto: configuracion que entra por (a)-(d)+tope, y la final si difiere
    conj = []
    if admitidas:
        conj.append(("admitidas (tope)", admitidas))
    if final and sorted(final) != sorted(admitidas):
        conj.append(("configuracion final", final))
    imps = [impacto(D, l, base, n) for n, l in conj]
    imp_res = pd.DataFrame([x[2] for x in imps])
    if imps:
        fd, indi, tot, fl, r = imps[-1]
        top = fd.reindex(fd["diferencia"].abs().sort_values(ascending=False).index).head(4)
        imp_texto = (f"Configuración «{conj[-1][0]}» ({', '.join(conj[-1][1])}), cortes {_cz(r)}: el radar cambia en "
                     f"{int((fd['diferencia'].abs() > 1e-9).sum())} de 32 departamentos (máx. |Δ| {fd['diferencia'].abs().max():.4f}); mayores: "
                     + "; ".join(f"{i} {v:+.4f}" for i, v in top["diferencia"].items()) + ". Lugares: "
                     + "; ".join(f"{i} {a:.4f}→{b:.4f} ({c}→{d})" for i, (a, b, c, d) in
                                 fl[["radar_sin", "radar_con", "clase_sin", "clase_con_recalibrados"]].iterrows()) + ".")
    else:
        imp_texto = "Sin lista nueva admitida no se calcula impacto (radar y lugares idénticos a producción)."

    tr = trazabilidad(D, places)
    tr_res = resumen_traza(tr)
    med = tr_res[tr_res["medible"]]
    tr_texto = (f"Total 6 indicadores × 7 lugares = 42 MAX: fijados por artículo SÍ {int(tr_res['SI_sin_filtro'].sum())} sin filtro y "
                f"{int(tr_res['SI_con_filtro'].sum())} con filtro. En los 4 medibles (28): {int(med['SI_sin_filtro'].sum())} → {int(med['SI_con_filtro'].sum())}.")
    notas = [
        "- Referencia = SÍ de los dos jueces sobre el pool (top-10 de V01 ∪ V08); un artículo fuera del pool cuenta como no juzgado y como negativo en M1/M2 (cota superior en el xlsx). Cobertura de los top-k: 100 %.",
        "- (a) y (b) se recalculan con la referencia de este pool (no hay valores congelados previos para estos indicadores).",
        "- Se evalúan (a)–(d) en los 4 medibles aunque alguno falle antes; `entra` exige las cuatro. Si un top-k tiene k = 0 no entra en la cobertura mínima (nada que juzgar).",
        "- La compuerta se calcula con `premisa_visible_prod` (hipótesis de cada indicador) para las 2 listas de producción y las 6 nuevas; `PREFILTRO_OBJETO` leído de `src/` sin importarlo.",
        "- Desigualdades de §6 a 4 decimales frente a −0.0913 y 0.8640; «sin cortes válidos» cuenta como fallo del criterio 1.",
        "- M1 en la trazabilidad sigue la definición de M1: con MAX = 0 es verdadero si el lugar no tiene positivos (por eso `con filtro` puede subir M1 sin que el radar muestre un artículo).",
        "- Las configuraciones «sola» del radar son informativas: no se evaluaron con (a)–(d) como decisión y la cadena solo corre con listas admitidas.",
        "- n = 32 en el radar; con solo 3 departamentos de holdout y pocos positivos por celda, un pase de (b) es débil (PREREG §11).",
        "- Desviaciones del pre-registro: ninguna de fondo. Orden de retirada en empates: menor ganancia en lugares y luego el último alfabéticamente (lectura conservadora de «desempate como en §5»).",
    ]
    R = {"veredicto": veredicto, "inc": inc, "entran": entran, "admitidas": admitidas, "tope": tp, "base": base, "cfg": cfg_md,
         "imp_res": imp_res, "imp_texto": imp_texto, "tr_res": tr_res, "tr_texto": tr_texto, "notas": notas, "san": san}
    print(cfg_md.round(4).to_string(index=False))
    print(imp_res.to_string(index=False) if len(imp_res) else "sin impacto")
    print(imp_texto)
    print(tr_res.to_string(index=False))
    print(tr_texto)

    os.makedirs(os.path.dirname(SALIDA_XLSX), exist_ok=True)
    with pd.ExcelWriter(SALIDA_XLSX, engine="openpyxl") as w:
        san.to_excel(w, sheet_name="S_sanidad", index=False)
        mm.to_excel(w, sheet_name="M_metricas", index=False)
        inc.to_excel(w, sheet_name="I_inclusion", index=False)
        det_b.to_excel(w, sheet_name="I_holdout_b", index=False)
        det_c.to_excel(w, sheet_name="I_control_c", index=False)
        tp.to_excel(w, sheet_name="T_tope", index=False)
        r_base.to_excel(w, sheet_name="R_base", index=False)
        cfg.to_excel(w, sheet_name="R_configs", index=False)
        pd.DataFrame([{"veredicto": veredicto["veredicto"], "motivo": veredicto["motivo"], "entran": ", ".join(entran),
                       "admitidas": ", ".join(admitidas), "final": ", ".join(final),
                       "orden_retirada": ", ".join(orden_ret)}]).to_excel(w, sheet_name="V_veredicto", index=False)
        if imps:
            imp_res.to_excel(w, sheet_name="F_resumen", index=False)
            pd.concat([x[0].reset_index().rename(columns={"index": "departamento"}) for x in imps]).round(6).to_excel(w, sheet_name="F_deptos", index=False)
            pd.concat([x[1].reset_index() for x in imps]).round(6).to_excel(w, sheet_name="F_indicadores", index=False)
            pd.concat([x[3].reset_index().rename(columns={"index": "lugar"}) for x in imps]).round(6).to_excel(w, sheet_name="F_lugares", index=False)
        else:
            pd.DataFrame([{"nota": R["imp_texto"]}]).to_excel(w, sheet_name="F_resumen", index=False)
        tr.to_excel(w, sheet_name="Z_trazabilidad", index=False)
        tr_res.to_excel(w, sheet_name="Z_resumen", index=False)
    escribir_md(SALIDA_MD, R)
    print(f"\nGuardado -> {SALIDA_XLSX} y {SALIDA_MD}")


if __name__ == "__main__":
    main()
