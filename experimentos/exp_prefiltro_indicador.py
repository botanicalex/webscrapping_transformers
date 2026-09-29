# -*- coding: utf-8 -*-
"""
Fase 3 del pre-filtro por indicador (experimentos/PREREG_prefiltro_indicador.md, commit 12c494c): consolidacion
del juicio del holdout, regla de inclusion (a)-(d) por indicador, criterios del radar nacional MAX con cortes
recalibrados, retirada de listas en el orden declarado, veredicto e impacto. Todo offline; la unica GPU esta en
exp_prefiltro_indicador_gpu.py.

Mecanismo: score' = s x 1[REGEX_F5[indicador] en la premisa visible normalizada] (V08 = vigente x compuerta;
V01 = vigente sin compuerta). Las 5 listas son las congeladas de hipotesis_5ind_max.py; nada se retoca.

Modos (desde la raiz del worktree, PYTHONIOENCODING=utf-8):
  python experimentos/exp_prefiltro_indicador.py consolidar  # etiquetas_a + etiquetas_b -> referencia.csv (tras el juicio)
  python experimentos/exp_prefiltro_indicador.py            # analisis completo (requiere referencia.csv)
  python experimentos/exp_prefiltro_indicador.py radar      # solo lo que no usa juicio (sanidad del radar y del control)
  python experimentos/exp_prefiltro_indicador.py prueba     # etiquetas SINTETICAS; salidas en un directorio temporal

Reutiliza (sin llamar a sus main()) funciones de exp_prefiltro_max.py, exp_5ind_max_cortes.py,
exp_5ind_max_r2_metricas.py y exp_5ind_max_juicio.py. No escribe en carpetas de experimentos anteriores.
"""
import json
import os
import sys
import tempfile
from itertools import combinations
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import exp_prefiltro_max as X  # noqa: E402
from exp_5ind_max_juicio import kappa  # noqa: E402
from exp_5ind_max_r2_metricas import referencia  # noqa: E402

# ── Rutas (desde la raiz del worktree) ──────────────────────────────────────
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
PREM_NAC = "experimentos/resultados/juicio_5ind_holdout/premisas_visibles_nacional.pkl"
PREM_L = "experimentos/resultados/juicio_5ind/premisas_visibles.pkl"
CORPUS_L = "datos/corpus/df_corpus_5lugares.pkl"
ATOMICAS_L = "datos/scores/scores_5ind_atomicas_lugares.pkl"
ATOM_NAC = "datos/scores/scores_5ind_atomicas_nacional.pkl"
GPU_HOLD = "datos/scores/scores_prefiltro_indicador_holdout.pkl"
PROCESADO_L = "resultados/tablas_lugares_max/df_procesado_5lugares.pkl"
URL_LUGARES = "experimentos/resultados/juicio_5ind/url_lugares.csv"
OFICIAL = "datos/referencia/comparacion_radares_V3.xlsx"
M_R1 = "experimentos/resultados/juicio_5ind/metricas_5ind.xlsx"
M_HO = "experimentos/resultados/juicio_5ind_holdout/metricas_holdout.csv"
CORTES_F7 = "experimentos/resultados/juicio_5ind_holdout/cortes_radar.xlsx"
DIR_J = "experimentos/resultados/juicio_prefiltro_indicador"
SALIDA_XLSX = "experimentos/resultados/exp_prefiltro_indicador.xlsx"
SALIDA_MD = "experimentos/RESULTADOS_prefiltro_indicador.md"

# ── Parametros fijados en el pre-registro ───────────────────────────────────
GA, CONF, DESP = "presencia_grupos_armados", "conflicto_territorial", "desplazamiento_forzado"
IND5 = H.INDICADORES_5
INDS26 = X.INDS26
CANDIDATAS = [GA, CONF, DESP]
ORDEN_RETIRADA = [DESP, CONF, GA]
LUG = X.LUG
HOLDOUT = X.HOLDOUT
CORTES_VIG = X.CORTES_VIG
CORTE = X.CORTE
GANANCIA_A, GANANCIA_B, COBERTURA_MIN, TOL = 0.20, 0.10, 0.90, 5e-5
VALORES = {"SI", "NO", "DUDOSO"}


# ═══════════════════════════════════════════════════════════════════════════
# Juicio: consolidacion (como la ronda 2) y referencia total
# ═══════════════════════════════════════════════════════════════════════════
def leer_etiquetas(carpeta):
    filas = []
    for fn in sorted(os.listdir(carpeta)):
        if not fn.endswith(".jsonl"):
            continue
        with open(os.path.join(carpeta, fn), encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    o = json.loads(linea)
                    fila = {"id": o["id"]}
                    for ind in IND5:
                        v = o[ind][0].strip().upper().replace("SÍ", "SI")
                        assert v in VALORES, (fn, o["id"], ind, v)
                        fila[ind] = v
                    filas.append(fila)
    return pd.DataFrame(filas).drop_duplicates("id").set_index("id")


def consolidar(dir_j=DIR_J, dir_etiquetas=None, escribir=True):
    """etiquetas_a + etiquetas_b -> referencia.csv (id, url, origen, indicador, indicador__a, indicador__b)."""
    de = dir_etiquetas or dir_j
    mapa = pd.read_csv(os.path.join(dir_j, "mapa_ids.csv")).set_index("id")
    A, B = leer_etiquetas(os.path.join(de, "etiquetas_a")), leer_etiquetas(os.path.join(de, "etiquetas_b"))
    faltan = (set(mapa.index) - set(A.index)) | (set(mapa.index) - set(B.index))
    assert not faltan, f"faltan {len(faltan)} ids: {sorted(faltan)[:5]}"
    ref = pd.DataFrame({"url": mapa["url"], "origen": mapa["origen"]})
    filas = []
    for ind in IND5:
        sa, sb = A.loc[mapa.index, ind] == "SI", B.loc[mapa.index, ind] == "SI"
        ref[ind] = (sa & sb).astype(int).values
        ref[ind + "__a"] = A.loc[mapa.index, ind].values
        ref[ind + "__b"] = B.loc[mapa.index, ind].values
        k = kappa(sa, sb)
        filas.append({"indicador": ind, "SI_a": int(sa.sum()), "SI_b": int(sb.sum()), "SI_SI": int(ref[ind].sum()),
                      "kappa": k, "referencia_debil": bool(k < 0.4) if not np.isnan(k) else None})
    kap = pd.DataFrame(filas)
    # Control entre rondas: los 10 ya juzgados conservan su etiqueta previa; aqui solo se mide el acuerdo.
    old = referencia().set_index("url")
    ctl = ref[ref["origen"] == "control"]
    ctrl = pd.DataFrame([{"indicador": ind, "n_control": len(ctl),
                          "acuerdo_SI_SI": float((ctl[ind].values == old.loc[ctl["url"], ind].values).mean()),
                          "SI_SI_previo": int(old.loc[ctl["url"], ind].sum()), "SI_SI_nuevo": int(ctl[ind].sum())}
                         for ind in IND5])
    if escribir:
        ref.reset_index().to_csv(os.path.join(dir_j, "referencia.csv"), index=False)
        kap.to_csv(os.path.join(dir_j, "kappa.csv"), index=False)
        ctrl.to_csv(os.path.join(dir_j, "control_entre_rondas.csv"), index=False)
    return ref.reset_index(), kap, ctrl


def referencia_total(nueva):
    """940 previos + los nuevos del pool (los 10 de control conservan su etiqueta previa)."""
    old = referencia()
    nuevo = nueva[nueva["origen"] == "pool"]
    total = pd.concat([old[["url"] + IND5], nuevo[["url"] + IND5]], ignore_index=True)
    assert total["url"].is_unique, "url juzgada dos veces"
    return total


# ═══════════════════════════════════════════════════════════════════════════
# Datos
# ═══════════════════════════════════════════════════════════════════════════
def cargar():
    D = SimpleNamespace()
    cn = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    dn = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(cn) == len(dn) == 11439
    assert (cn["titulo"].values == dn["titulo"].values).all() and (cn["departamento"].values == dn["departamento"].values).all()
    D.nac = cn[["url", "departamento", "titulo", "texto"]].copy()
    D.sesgo = dn["sesgo"].values.astype(float)
    D.s = {c: X.s_corr(dn[f"ent_{c}"].values, dn[f"neu_{c}"].values, D.sesgo) for c in INDS26 + ["NULA_TEST"]}
    prem = pd.read_pickle(PREM_NAC)
    assert prem.index.is_unique and set(cn["url"]) <= set(prem.index)
    D.prem_nac = prem.loc[cn["url"]].values
    D.g_nac = {i: np.asarray(H.compuerta(D.prem_nac, i), dtype=float) for i in IND5}
    # gemelas de objeto absurdo en el nacional: grupos armados completa; conflicto y desplazamiento solo holdout (GPU)
    an = pd.read_pickle(ATOM_NAC).reset_index(drop=True)
    assert (an["url"].values == cn["url"].values).all()
    D.abs_nac = {GA: X.s_corr(an[f"ent_{GA}__vig_abs"].values, an[f"neu_{GA}__vig_abs"].values, D.sesgo)}
    if os.path.exists(GPU_HOLD):
        gh = pd.read_pickle(GPU_HOLD).set_index("url")
        m = cn["url"].isin(gh.index).values
        for i in (CONF, DESP):
            arr = np.full(len(cn), np.nan)
            u = cn["url"].values[m]
            arr[m] = X.s_corr(gh.loc[u, f"ent_{i}__vig_abs"].values, gh.loc[u, f"neu_{i}__vig_abs"].values, D.sesgo[m])
            D.abs_nac[i] = arr
    # lugares (convencion del plan) y produccion
    cl = pd.read_pickle(CORPUS_L).reset_index(drop=True)
    at = pd.read_pickle(ATOMICAS_L).reset_index(drop=True)
    proc = pd.read_pickle(PROCESADO_L).reset_index(drop=True)
    assert (at["url"].values == cl["url"].values).all() and (proc["url"].values == cl["url"].values).all()
    D.l = cl[["url", "departamento", "titulo"]].copy()
    D.l_urls = cl["url"].values
    ses = at["sesgo"].values.astype(float)
    D.l_s = {i: X.s_corr(at[f"ent_{i}__vig"].values, at[f"neu_{i}__vig"].values, ses) for i in IND5}
    D.l_abs = {i: X.s_corr(at[f"ent_{i}__vig_abs"].values, at[f"neu_{i}__vig_abs"].values, ses) for i in IND5}
    D.l_tot = X.s_corr(at["ent_ABSURDO_TOTAL"].values, at["neu_ABSURDO_TOTAL"].values, ses)
    prem_l = pd.read_pickle(PREM_L)
    assert set(cl["url"]) <= set(prem_l.index)
    D.prem_l = prem_l.loc[cl["url"]].values
    D.g_l = {i: np.asarray(H.compuerta(D.prem_l, i), dtype=float) for i in IND5}
    D.l_prod = {c: proc[c].astype(float).values for c in INDS26}
    lug = pd.read_csv(URL_LUGARES)
    D.urls_lugar = {l: set(lug.loc[lug["lugar"] == l, "url"]) for l in LUG}
    D.oficial = pd.read_excel(OFICIAL, engine="openpyxl")
    D.oficial.columns = [str(c).strip() for c in D.oficial.columns]
    D.oficial["_k"] = D.oficial["Departamento"].map(X._norm)
    D.n_art = D.nac["departamento"].value_counts()
    return D


def armar_places(D, ref):
    """4 lugares (convencion del plan) y 3 departamentos del holdout, con puntajes, gemelas, compuertas y referencia."""
    positivos = {i: set(ref.loc[ref[i] == 1, "url"]) for i in IND5}
    juzgados = set(ref["url"])
    idx_l = {u: i for i, u in enumerate(D.l_urls)}
    places = []
    for l in LUG:
        urls = sorted(D.urls_lugar[l])
        ii = np.array([idx_l[u] for u in urls])
        places.append(SimpleNamespace(
            name=l, kind="lugar", n=len(ii), urls=np.array(urls),
            s={i: D.l_s[i][ii] for i in IND5}, ab={i: D.l_abs[i][ii] for i in IND5}, tot=D.l_tot[ii],
            g={i: D.g_l[i][ii] for i in IND5}, jud=np.array([u in juzgados for u in urls]),
            pos={i: np.array([u in positivos[i] for u in urls]) for i in IND5}))
    for dep in HOLDOUT:
        m = np.where(D.nac["departamento"].values == dep)[0]
        urls = D.nac["url"].values[m]
        o = np.argsort(urls, kind="stable")
        m, urls = m[o], urls[o]
        places.append(SimpleNamespace(
            name=dep, kind="holdout", n=len(m), urls=urls,
            s={i: D.s[i][m] for i in IND5}, ab={i: D.abs_nac[i][m] for i in D.abs_nac}, tot=D.s["NULA_TEST"][m],
            g={i: D.g_nac[i][m] for i in IND5}, jud=np.array([u in juzgados for u in urls]),
            pos={i: np.array([u in positivos[i] for u in urls]) for i in IND5}))
    return places


def m_place(p, ind, con):
    x = p.s[ind] * p.g[ind] if con else p.s[ind]
    return X.metricas_celda(x, np.arange(p.n), p.pos[ind], p.jud, bool(p.pos[ind].any()))


# ═══════════════════════════════════════════════════════════════════════════
# Sanidad sin juicio (solo puntajes): radar F8 y MAX de la ronda 1 / F7
# ═══════════════════════════════════════════════════════════════════════════
def radar_nac(D, listas):
    deps = D.nac["departamento"].values
    cols = {c: D.s[c] * (D.g_nac[c] if c in listas else 1.0) for c in INDS26}
    m = pd.DataFrame(cols).groupby(deps).max()
    assert m.shape == (32, 26), m.shape
    return m.mean(axis=1), m


def criterios(D, listas, base=None):
    r, mx = radar_nac(D, listas)
    try:
        cb, ca, _, _ = X.elegir_cortes(r)
        cortes = (float(cb), float(ca))
    except RuntimeError:
        cortes = None
    rho_dane = float(spearmanr(r.values, D.oficial.set_index("_k").loc[[X._norm(k) for k in r.index],
                                                                    "radar_oficial_promedio"].values).correlation)
    rho_size = float(spearmanr(r.values, D.n_art.reindex(r.index).values).correlation)
    out = {"listas": "+".join(l.split("_")[0] for l in listas) or "(ninguna)", "n_listas": len(listas),
           "cortes": cortes, "radar": r, "max": mx, "rho_dane": rho_dane, "rho_size": rho_size}
    if cortes:
        c = X.constancia(r, *cortes, D.oficial)
        out.update({"anclas_rotas": len(X.anclas_rotas(r, *cortes)), "acc": c["acc"], "dist": c["dist"]})
    else:
        out.update({"anclas_rotas": None, "acc": np.nan, "dist": {}})
    if base is not None:
        out["c1_anclas"] = bool(cortes is not None and out["anclas_rotas"] == 0)
        out["c2_spearman_dane"] = bool(round(rho_dane, 4) >= round(base["rho_dane"], 4))
        out["c3_tamano_no_sube"] = bool(round(rho_size, 4) <= round(base["rho_size"], 4))
        out["pasa"] = bool(out["c1_anclas"] and out["c2_spearman_dane"] and out["c3_tamano_no_sube"])
        out["dif_max_radar"] = float((r - base["radar"]).abs().max())
    return out


def sanidad_sin_juicio(D, base):
    filas = []

    def chk(nombre, ok, valor, esperado):
        filas.append({"chequeo": nombre, "ok": bool(ok), "valor": str(valor), "esperado": str(esperado)})
        print(f"  [{'OK' if ok else 'FALLA'}] {nombre}: {valor} (esperado {esperado})")

    # S1 sin mecanismo
    cl = base["radar"].map(lambda v: X.clasificar(v, *CORTES_VIG))
    chk("S1 sin mecanismo: clasificacion con 0.766/0.9233", X.dist(cl) == {"Bajo": 6, "Medio": 19, "Alto": 7}, X.dist(cl), "6/19/7")
    chk("S1 sin mecanismo: elegir_cortes", base["cortes"] == CORTES_VIG, base["cortes"], CORTES_VIG)
    chk("S1 sin mecanismo: Spearman DANE", round(base["rho_dane"], 4) == -0.1653, round(base["rho_dane"], 4), -0.1653)
    chk("S1 sin mecanismo: Spearman con el tamano", round(base["rho_size"], 3) == 0.884, round(base["rho_size"], 3), 0.884)
    # S2 solo grupos armados = F8
    f8 = criterios(D, [GA], base)
    chk("S2 solo grupos armados: cortes de la F8", f8["cortes"] == (0.7574, 0.9233), f8["cortes"], (0.7574, 0.9233))
    chk("S2 solo grupos armados: Spearman DANE", round(f8["rho_dane"], 4) == -0.1173, round(f8["rho_dane"], 4), -0.1173)
    chk("S2 solo grupos armados: 6/19/7 y 0 anclas rotas", f8["dist"] == {"Bajo": 6, "Medio": 19, "Alto": 7} and f8["anclas_rotas"] == 0,
        (f8["dist"], f8["anclas_rotas"]), "6/19/7, 0")
    # El log de la F7 cita 3 decimales redondeados desde los 4 del archivo (Caldas 0.7245 -> «0.725»; exacto 0.724465):
    # se compara contra el archivo original de la F7, a 4 decimales, en los 32 departamentos (Quindio, Caldas,
    # San Andres y Guainia son los que cambian).
    f7 = pd.read_excel(CORTES_F7, sheet_name="radar_32", index_col=0)
    mxs, mxc = base["max"][GA].round(4), f8["max"][GA].round(4)
    d_ga = max(float((mxs - f7.loc[mxs.index, "ga_V01"]).abs().max()), float((mxc - f7.loc[mxc.index, "ga_V08"]).abs().max()))
    d_rad = max(float((base["radar"].round(4) - f7.loc[base["radar"].index, "radar_V01"]).abs().max()),
                float((f8["radar"].round(4) - f7.loc[f8["radar"].index, "radar_V08"]).abs().max()))
    chk("S2 MAX de grupos armados (32 deptos) y radar (32) de V01 y V08 vs F7, a 4 decimales", d_ga < 1e-9 and d_rad < 1e-9,
        f"max|dif| MAX={d_ga:.1e}, radar={d_rad:.1e}", "0")
    # (El log de la F7 solo cita los cuatro cambios mayores; el resto de departamentos cambia menos y tambien
    # coincide con el archivo original, que es lo que comprueba el chequeo anterior.)
    mayores = sorted(((mxs - mxc).sort_values(ascending=False).head(4)).index)
    chk("S2 los cuatro mayores cambios de MAX de grupos armados son Quindío, Caldas, San Andrés y Guainía",
        mayores == sorted(["Quindío", "Caldas", "San Andrés y Providencia", "Guainía"]), mayores, "esos cuatro")
    # S3 MAX por lugar (ronda 1) de V01/V08 de los 5 indicadores, solo puntajes
    m1 = pd.read_excel(M_R1)
    dif = 0.0
    for ind in IND5:
        for v, con in (("V01", False), ("V08", True)):
            r = m1[(m1["indicador"] == ind) & (m1["variante"] == v)].iloc[0]
            for l in LUG:
                x = D.l_s[ind] * (D.g_l[ind] if con else 1.0)
                m = np.array([u in D.urls_lugar[l] for u in D.l_urls])
                dif = max(dif, abs(round(float(x[m].max()), 4) - float(r[f"max_{l}"])))
                xa = D.l_abs[ind] * (D.g_l[ind] if con else 1.0)
                dif = max(dif, abs(round(float(xa[m].max()), 4) - float(r[f"abs_{l}"])))
                xt = D.l_tot * (D.g_l[ind] if con else 1.0)
                dif = max(dif, abs(round(float(xt[m].max()), 4) - float(r[f"tot_{l}"])))
    chk("S3 lugares: MAX real/gemela/absurdo total de V01 y V08 (5 indicadores) vs ronda 1", dif < 1e-9, f"max|dif|={dif:.1e}", "0")
    # S4 holdout de grupos armados: MAX real/gemela/total de V01 y V08 vs F7
    ho = pd.read_csv(M_HO)
    dif = 0.0
    for dep in HOLDOUT:
        m = D.nac["departamento"].values == dep
        for v, con in (("V01", False), ("V08", True)):
            f = ho[(ho["lugar"] == {"Chocó": "Choco"}.get(dep, dep)) & (ho["variante"] == v)].iloc[0]
            g = D.g_nac[GA][m] if con else 1.0
            for val, col in ((D.s[GA][m] * g, "max"), (D.abs_nac[GA][m] * g, "max_abs"), (D.s["NULA_TEST"][m] * g, "max_tot")):
                dif = max(dif, abs(round(float(val.max()), 4) - float(f[col])))
    chk("S4 holdout de grupos armados: MAX real/gemela/total de V01 y V08 vs F7", dif < 1e-9, f"max|dif|={dif:.1e}", "0")
    # S5 gemelas del holdout completas
    for i in (CONF, DESP):
        ok = i in D.abs_nac and int(np.isfinite(D.abs_nac[i]).sum()) == 1117
        chk(f"S5 gemela de {i} en los 1.117 del holdout", ok, int(np.isfinite(D.abs_nac.get(i, np.array([]))).sum()), 1117)
    return pd.DataFrame(filas), f8


# ═══════════════════════════════════════════════════════════════════════════
# Regla de inclusion (a)-(d)
# ═══════════════════════════════════════════════════════════════════════════
def inclusion(D, places):
    m1 = pd.read_excel(M_R1)
    lug = [p for p in places if p.kind == "lugar"]
    hol = [p for p in places if p.kind == "holdout"]
    filas, det_b, det_c, det_d = [], [], [], []
    for ind in IND5:
        fr = {v: float(m1[(m1["indicador"] == ind) & (m1["variante"] == v)]["M2"].iloc[0]) for v in ("V01", "V08")}
        a_cong = fr["V08"] - fr["V01"]
        rec = {con: float(np.mean([m_place(p, ind, con)[2] for p in lug])) for con in (False, True)}
        a_rec = rec[True] - rec[False]
        f = {"indicador": ind, "a_M2_V01_congelado": fr["V01"], "a_M2_V08_congelado": fr["V08"], "a_ganancia": a_cong,
             "a_ganancia_recalculada": a_rec, "a_coincide": bool(abs(round(rec[False], 3) - fr["V01"]) < 1e-9 and abs(round(rec[True], 3) - fr["V08"]) < 1e-9),
             "a_pasa": bool(a_cong >= GANANCIA_A - 1e-9)}
        if ind not in CANDIDATAS or not f["a_pasa"]:
            f.update({"b_pasa": None, "c_pasa": None, "d_pasa": None, "entra": False,
                      "nota": "no pasa (a): pasa sin filtro" if not f["a_pasa"] else ""})
            filas.append(f)
            continue
        # (b) holdout
        b_rows = []
        for p in hol:
            s0, s1 = m_place(p, ind, False), m_place(p, ind, True)
            b_rows.append({"indicador": ind, "departamento": p.name, "n_positivos": int(p.pos[ind].sum()),
                           "k_sin": int(s0[5]), "M2_sin": s0[2], "M2_sin_cota_sup": s0[3], "cobertura_sin": s0[4],
                           "k_con": int(s1[5]), "M2_con": s1[2], "M2_con_cota_sup": s1[3], "cobertura_con": s1[4]})
        bd = pd.DataFrame(b_rows)
        det_b.append(bd)
        b_gan = float(bd["M2_con"].mean() - bd["M2_sin"].mean())
        cov_min = float(np.nanmin(np.r_[bd["cobertura_sin"].values, bd["cobertura_con"].values]))
        f.update({"b_M2_sin_media": float(bd["M2_sin"].mean()), "b_M2_con_media": float(bd["M2_con"].mean()), "b_ganancia": b_gan,
                  "b_cobertura_min": cov_min, "b_pasa": bool(b_gan >= GANANCIA_B - 1e-9 and cov_min >= COBERTURA_MIN - 1e-9)})
        # (c) control absurdo con la misma mascara
        c_rows = []
        for p in places:
            g = p.g[ind]
            assert ind in p.ab and not np.isnan(p.ab[ind]).any(), (ind, p.name)
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
        for grupo, sel in (("lugares", cd["tipo"] == "lugar"), ("holdout", cd["tipo"] == "holdout"), ("los_7", cd["tipo"].notna())):
            for tw in ("gemela", "total"):
                comp[f"c_dif_brecha_{tw}_{grupo}"] = float(cd.loc[sel, f"brecha_{tw}_con"].mean() - cd.loc[sel, f"brecha_{tw}_sin"].mean())
        f.update(comp)
        f["c_pasa"] = bool(all(comp[f"c_dif_brecha_{tw}_{g}"] >= -TOL for tw in ("gemela", "total") for g in ("lugares", "holdout")))
        # (d) M3: sin violaciones nuevas en los 7 lugares
        d_rows = []
        for p in places:
            hp = bool(p.pos[ind].any())
            mx0, mx1 = float(p.s[ind].max()), float((p.s[ind] * p.g[ind]).max())
            v0 = (not hp and mx0 >= CORTE) or (hp and mx0 < CORTE)
            v1 = (not hp and mx1 >= CORTE) or (hp and mx1 < CORTE)
            d_rows.append({"indicador": ind, "lugar": p.name, "tipo": p.kind, "con_positivos": hp, "n_positivos": int(p.pos[ind].sum()),
                           "MAX_V01": mx0, "MAX_V08": mx1, "viola_V01": v0, "viola_V08": v1, "nueva": bool(v1 and not v0)})
        dd = pd.DataFrame(d_rows)
        det_d.append(dd)
        f["d_violaciones_nuevas"] = int(dd["nueva"].sum())
        f["d_pasa"] = bool(f["d_violaciones_nuevas"] == 0)
        f["entra"] = bool(f["a_pasa"] and f["b_pasa"] and f["c_pasa"] and f["d_pasa"])
        f["nota"] = ""
        filas.append(f)
    cat = lambda L: pd.concat(L, ignore_index=True) if L else pd.DataFrame()  # noqa: E731
    return pd.DataFrame(filas), cat(det_b), cat(det_c), cat(det_d)


# ═══════════════════════════════════════════════════════════════════════════
# Mecanismo combinado: criterios del radar, cadena de retirada y veredicto
# ═══════════════════════════════════════════════════════════════════════════
def cadena(D, entran, base):
    pasos, cur = [], list(entran)
    while cur:
        r = criterios(D, cur, base)
        pasos.append(r)
        if r["pasa"]:
            return cur, pasos
        for x in ORDEN_RETIRADA:
            if x in cur:
                cur.remove(x)
                break
    return None, pasos


def veredicto(D, entran, base):
    final, pasos = cadena(D, entran, base)
    if not entran:
        return {"veredicto": "NO ADOPTAR", "motivo": "ninguna lista cumple (a)-(d)", "final": [], "pasos": pasos}
    if final is None:
        return {"veredicto": "NO ADOPTAR", "motivo": "ninguna configuracion cumple los tres criterios del radar", "final": [], "pasos": pasos}
    r = pasos[-1]
    if r["dif_max_radar"] < TOL:
        return {"veredicto": "NO ADOPTAR", "motivo": "empate: el radar es identico al de sin mecanismo", "final": final, "pasos": pasos}
    return {"veredicto": "ADOPTAR", "motivo": "cumple los tres criterios del radar", "final": final, "pasos": pasos}


def tabla_configs(D, base):
    """Cada lista sola (5) y todas las combinaciones de las candidatas (7), con los tres criterios."""
    confs = [[i] for i in IND5] + [list(c) for n in (2, 3) for c in combinations(CANDIDATAS, n)]
    filas = []
    for c in confs:
        r = criterios(D, c, base)
        filas.append({"listas": " + ".join(c), "cortes": (f"{r['cortes'][0]:.4f}/{r['cortes'][1]:.4f}" if r["cortes"] else "sin cortes validos"),
                      "anclas_rotas": r["anclas_rotas"], "rho_dane": r["rho_dane"], "rho_size": r["rho_size"],
                      "clases_B/M/A": "/".join(str(r["dist"].get(k, 0)) for k in ("Bajo", "Medio", "Alto")) if r["dist"] else "",
                      "c1_anclas": r["c1_anclas"], "c2_spearman_dane": r["c2_spearman_dane"], "c3_tamano_no_sube": r["c3_tamano_no_sube"],
                      "pasa": r["pasa"], "dif_max_radar": r["dif_max_radar"]})
    return pd.DataFrame(filas)


# ═══════════════════════════════════════════════════════════════════════════
# Impacto (Fase 4): 32 departamentos y 4 lugares
# ═══════════════════════════════════════════════════════════════════════════
def impacto(D, listas, base, nombre):
    r = criterios(D, listas, base)
    cortes = r["cortes"]
    sin, con = base["max"], r["max"]
    dif = con - sin
    fd = pd.DataFrame({"n_articulos": D.n_art.reindex(sin.index), "radar_sin": base["radar"], "radar_con": r["radar"]})
    fd["diferencia"] = fd["radar_con"] - fd["radar_sin"]
    fd["clase_sin_vigentes"] = fd["radar_sin"].map(lambda v: X.clasificar(v, *CORTES_VIG))
    fd["clase_con_vigentes"] = fd["radar_con"].map(lambda v: X.clasificar(v, *CORTES_VIG))
    fd["clase_con_recalibrados"] = fd["radar_con"].map(lambda v: X.clasificar(v, *cortes)) if cortes else "s/d"
    fd["cambia_vigentes"] = fd["clase_sin_vigentes"] != fd["clase_con_vigentes"]
    fd["cambia_recalibrados"] = fd["clase_sin_vigentes"] != fd["clase_con_recalibrados"]
    fd["oficial"] = [D.oficial.set_index("_k")["Clasificacion_radar_oficial_promedio"].get(X._norm(k)) for k in fd.index]
    fd.insert(0, "configuracion", nombre)
    ind = pd.DataFrame({"media_abs_dMAX": dif.abs().mean(), "celdas_gt_0.05": (dif.abs() > 0.05).sum(),
                        "celdas_a_cero": ((sin > 0) & (con == 0)).sum(), "MAX_medio_sin": sin.mean(), "MAX_medio_con": con.mean()})
    ind = ind[ind["media_abs_dMAX"] > 0].sort_values("media_abs_dMAX", ascending=False)
    ind.insert(0, "configuracion", nombre)
    ind.index.name = "indicador"
    st = dif.stack()
    st = st[st.abs() > 1e-9].sort_values()
    celdas = pd.DataFrame([{"configuracion": nombre, "departamento": d, "indicador": i, "n_articulos": int(D.n_art[d]),
                            "MAX_sin": sin.loc[d, i], "MAX_con": con.loc[d, i], "dMAX": v} for (d, i), v in st.items()],
                          columns=["configuracion", "departamento", "indicador", "n_articulos", "MAX_sin", "MAX_con", "dMAX"])
    # lugares (produccion): 26 puntajes de produccion x compuertas de la configuracion
    labs = D.l["departamento"].values
    S0 = pd.DataFrame({c: D.l_prod[c] for c in INDS26})
    S1 = pd.DataFrame({c: D.l_prod[c] * (D.g_l[c] if c in listas else 1.0) for c in INDS26})
    l0, l1 = S0.groupby(labs).max(), S1.groupby(labs).max()
    r0, r1 = l0.round(4).mean(axis=1), l1.round(4).mean(axis=1)
    fl = pd.DataFrame({"radar_sin": r0, "radar_con": r1, "diferencia": r1 - r0})
    fl["clase_sin_vigentes"] = fl["radar_sin"].map(lambda v: X.clasificar(v, *CORTES_VIG))
    fl["clase_con_vigentes"] = fl["radar_con"].map(lambda v: X.clasificar(v, *CORTES_VIG))
    fl["clase_con_recalibrados"] = fl["radar_con"].map(lambda v: X.clasificar(v, *cortes)) if cortes else "s/d"
    fl["indicadores_que_cambian"] = [", ".join(f"{c} {l0.loc[g, c]:.3f}->{l1.loc[g, c]:.3f}" for c in INDS26
                                               if abs(l1.loc[g, c] - l0.loc[g, c]) > 1e-9) for g in fl.index]
    fl.insert(0, "configuracion", nombre)
    return fd, ind, celdas, fl, r


# ═══════════════════════════════════════════════════════════════════════════
# Robustez: compuerta con la truncacion de produccion de cada indicador
# ═══════════════════════════════════════════════════════════════════════════
def robustez_truncacion(D, base, listas):
    from transformers import AutoTokenizer
    from nli_core import MODELO_NLI, _ruta_modelo_local
    tok = AutoTokenizer.from_pretrained(_ruta_modelo_local(MODELO_NLI))
    textos = D.nac["texto"].fillna("").astype(str).tolist()
    filas, g_prod = [], {}
    for ind in listas:
        pv = H.premisa_visible(textos, tok, [H.HIPOTESIS[ind]["vig"]])
        g_prod[ind] = np.asarray(H.compuerta(pv, ind), dtype=float)
        filas.append({"indicador": ind, "articulos_distintos": int((g_prod[ind] != D.g_nac[ind]).sum())})
    deps = D.nac["departamento"].values
    cols = {c: D.s[c] * (g_prod[c] if c in listas else 1.0) for c in INDS26}
    r_prod = pd.DataFrame(cols).groupby(deps).max().mean(axis=1)
    r_exp, _ = radar_nac(D, listas)
    tabla = pd.DataFrame(filas)
    tabla["listas"] = " + ".join(listas)
    tabla["max_dif_radar"] = float((r_prod - r_exp).abs().max())
    return tabla


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
    V = R["veredicto"]
    inc = R["inclusion"]
    L = ["# Resultados — pre-filtro por indicador (listas de objeto) bajo MAX, etapa 1", "",
         "Generado por `experimentos/exp_prefiltro_indicador.py`; todas las tablas salen de "
         "`experimentos/resultados/exp_prefiltro_indicador.xlsx` (hoja indicada). Pre-registro congelado antes de calcular: "
         "`experimentos/PREREG_prefiltro_indicador.md` (12c494c). Juicio: `experimentos/resultados/juicio_prefiltro_indicador/`.", "",
         f"**Veredicto: {V['veredicto']}.** {V['motivo'].capitalize()}. Listas que entran por (a)–(d): "
         f"{', '.join(R['entran']) or 'ninguna'}. Configuración final: {', '.join(V['final']) or 'ninguna'}.", "",
         "## Inclusión por indicador (hoja `I_inclusion`)", ""]
    cols = ["indicador", "a_ganancia", "a_pasa", "b_ganancia", "b_cobertura_min", "b_pasa", "c_pasa", "d_violaciones_nuevas", "d_pasa", "entra"]
    L += md_tabla(inc[[c for c in cols if c in inc.columns]],
                  ren={"a_ganancia": "(a) ΔM2 lugares", "a_pasa": "(a)", "b_ganancia": "(b) ΔM2 holdout", "b_cobertura_min": "cobertura mín.",
                       "b_pasa": "(b)", "c_pasa": "(c)", "d_violaciones_nuevas": "M3 nuevas", "d_pasa": "(d)", "entra": "entra"})
    L += ["", "(a) usa los valores congelados de la ronda 1 (`juicio_5ind/metricas_5ind.xlsx`); recalculados con la referencia actual coinciden "
          "en los 5 indicadores (columna `a_coincide`).", "", "### (b) Holdout por departamento (hoja `I_holdout_b`)", ""]
    L += md_tabla(R["det_b"][["indicador", "departamento", "n_positivos", "k_sin", "M2_sin", "cobertura_sin", "k_con", "M2_con", "cobertura_con"]],
                  ren={"k_sin": "k sin filtro", "M2_sin": "M2 sin", "cobertura_sin": "cobertura sin", "k_con": "k con filtro",
                       "M2_con": "M2 con", "cobertura_con": "cobertura con"})
    L += ["", "### (c) Control absurdo con la misma máscara (hoja `I_control_c`)", "",
          "Diferencia de la brecha media «MAX real − MAX de la gemela» (con máscara − sin máscara); debe ser ≥ −5e-5 en las cuatro primeras columnas.", ""]
    ccols = ["indicador", "c_dif_brecha_gemela_lugares", "c_dif_brecha_total_lugares", "c_dif_brecha_gemela_holdout",
             "c_dif_brecha_total_holdout", "c_dif_brecha_gemela_los_7", "c_dif_brecha_total_los_7", "c_pasa"]
    L += md_tabla(inc[inc["c_pasa"].notna()][ccols],
                  ren={"c_dif_brecha_gemela_lugares": "gemela, lugares", "c_dif_brecha_total_lugares": "total, lugares",
                       "c_dif_brecha_gemela_holdout": "gemela, holdout", "c_dif_brecha_total_holdout": "total, holdout",
                       "c_dif_brecha_gemela_los_7": "gemela, los 7", "c_dif_brecha_total_los_7": "total, los 7", "c_pasa": "(c)"})
    dc = R["det_c"]
    dc = dc[dc["indicador"].isin(R["entran"])]
    L += ["", "MAX de la hipótesis real, de su gemela de objeto absurdo y del absurdo total, sin → con máscara, en las listas que entran:", ""]
    L += md_tabla(dc[["indicador", "lugar", "real_sin", "real_con", "gemela_sin", "gemela_con", "total_sin", "total_con"]],
                  ren={"real_sin": "real sin", "real_con": "real con", "gemela_sin": "gemela sin", "gemela_con": "gemela con",
                       "total_sin": "total sin", "total_con": "total con"}, dec=3)
    L += ["", "### (d) M3 (hoja `I_m3_d`)", "",
          "Lugares donde V01 o V08 violan M3 (el MAX contradice la existencia de casos confirmados); «nueva» = solo V08 la viola:", ""]
    dd = R["det_d"]
    dd = dd[dd["viola_V01"] | dd["viola_V08"]]
    L += md_tabla(dd[["indicador", "lugar", "n_positivos", "MAX_V01", "MAX_V08", "viola_V01", "viola_V08", "nueva"]], dec=3)
    L += ["", "## Juicio (hojas `J_kappa`, `J_control`)", ""]
    L += md_tabla(R["kappa"]) + [""] + md_tabla(R["control"]) + ["",
         "Los 10 de control conservan su etiqueta previa en la referencia; aquí solo se mide el acuerdo.", "",
         "## Radar nacional: cada lista y cada combinación (hoja `R_configs`)", ""]
    L += md_tabla(R["configs"][["listas", "cortes", "anclas_rotas", "rho_dane", "rho_size", "clases_B/M/A", "c1_anclas",
                                "c2_spearman_dane", "c3_tamano_no_sube", "pasa"]],
                  ren={"rho_dane": "Spearman DANE", "rho_size": "Spearman tamaño", "c1_anclas": "0 anclas", "c2_spearman_dane": "DANE ≥ base",
                       "c3_tamano_no_sube": "tamaño no sube"})
    L += ["", f"Sin mecanismo: Spearman DANE {R['base']['rho_dane']:+.4f}; Spearman con el tamaño {R['base']['rho_size']:+.4f}; cortes 0.766/0.9233.", "",
          "## Cadena de retirada (hoja `R_cadena`)", ""]
    L += md_tabla(R["cadena"]) if len(R["cadena"]) else ["(no hubo configuración que evaluar)"]
    L += ["", "## Impacto (hojas `F_*`)", ""]
    L += md_tabla(R["impacto_resumen"])
    nom = "incluidas por (a)-(d)" if "incluidas por (a)-(d)" in R["imp"] else next(iter(R["imp"]))
    fd, indi, celdas, fl, r = R["imp"][nom]
    cz = f"{r['cortes'][0]:.4f}/{r['cortes'][1]:.4f}" if r["cortes"] else "sin cortes válidos"
    L += ["", f"Configuración «{nom}» (cortes recalibrados {cz}):", "",
          f"- El radar baja en {int((fd['diferencia'] < -1e-9).sum())} de 32 departamentos; diferencia media {fd['diferencia'].mean():+.4f}, "
          f"mínima {fd['diferencia'].min():+.4f}. Cambian de clase: {int(fd['cambia_vigentes'].sum())} con los cortes vigentes y "
          f"{int(fd['cambia_recalibrados'].sum())} con los recalibrados.", "",
          "Mayores caídas del radar:", ""]
    L += md_tabla(fd.sort_values("diferencia").head(6).reset_index().rename(columns={"index": "departamento"})[
        ["departamento", "n_articulos", "radar_sin", "radar_con", "diferencia", "clase_sin_vigentes", "clase_con_recalibrados"]])
    L += ["", "MAX que se mueven, por indicador:", ""]
    L += md_tabla(indi.reset_index()[["indicador", "media_abs_dMAX", "celdas_gt_0.05", "celdas_a_cero", "MAX_medio_sin", "MAX_medio_con"]])
    L += ["", "Celdas departamento × indicador con |ΔMAX| > 0.05:", ""]
    L += md_tabla(celdas[celdas["dMAX"].abs() > 0.05][["departamento", "indicador", "n_articulos", "MAX_sin", "MAX_con", "dMAX"]], dec=3)
    L += ["", "Los 4 lugares (convención de producción):", ""]
    L += md_tabla(fl.reset_index().rename(columns={"index": "lugar"})[
        ["lugar", "radar_sin", "radar_con", "diferencia", "clase_sin_vigentes", "clase_con_recalibrados", "indicadores_que_cambian"]])
    L += ["", "## Robustez: compuerta con la truncación de producción de cada indicador (hoja `Z_robustez`)", ""]
    L += md_tabla(R["rob"], dec=6)
    L += ["", "## Sanidad (hoja `S_sanidad`)", "", f"{int(R['sanidad']['ok'].sum())} de {len(R['sanidad'])} chequeos OK."]
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


# ═══════════════════════════════════════════════════════════════════════════
def ref_sintetica(nueva_urls, seed=1):
    """SOLO para el modo prueba: etiquetas al azar (no representan a ningun juez)."""
    rng = np.random.default_rng(seed)
    urls = list(referencia()["url"]) + list(nueva_urls)
    df = pd.DataFrame({"url": urls})
    for i in IND5:
        df[i] = (rng.random(len(df)) < 0.15).astype(int)
    return df


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "completo"
    if modo == "consolidar":
        ref, kap, ctrl = consolidar()
        print(kap.round(3).to_string(index=False))
        print(ctrl.round(3).to_string(index=False))
        print(f"-> {DIR_J}/referencia.csv, kappa.csv, control_entre_rondas.csv")
        return
    salida_xlsx, salida_md = SALIDA_XLSX, SALIDA_MD
    if modo == "prueba":
        tmp = tempfile.mkdtemp(prefix="prefiltro_prueba_")
        salida_xlsx, salida_md = os.path.join(tmp, "prueba.xlsx"), os.path.join(tmp, "prueba.md")
        print(f"MODO PRUEBA (etiquetas sinteticas; nada de esto es un resultado). Salidas en {tmp}")

    print("Cargando datos...")
    D = cargar()
    base = criterios(D, [])
    print("\n=== S. Sanidad sin juicio (puntajes y radar) ===")
    S, f8 = sanidad_sin_juicio(D, base)
    if not S["ok"].all():
        sys.exit("PARADA: la sanidad no cumple el pre-registro")
    if modo == "radar":
        print("\nModo radar: sanidad OK; se omiten los bloques con juicio.")
        cfg = tabla_configs(D, base)
        print(cfg[["listas", "cortes", "anclas_rotas", "pasa"]].to_string(index=False))
        return

    print("\n=== Referencia ===")
    mapa = pd.read_csv(os.path.join(DIR_J, "mapa_ids.csv"))
    if modo == "prueba":
        nueva_urls = mapa.loc[mapa["origen"] == "pool", "url"]
        ref = ref_sintetica(nueva_urls)
        kap = pd.DataFrame({"nota": ["prueba: sin kappa"]})
        ctrl = pd.DataFrame({"nota": ["prueba: sin control"]})
    else:
        nueva = pd.read_csv(os.path.join(DIR_J, "referencia.csv"))
        ref = referencia_total(nueva)
        kap = pd.read_csv(os.path.join(DIR_J, "kappa.csv"))
        ctrl = pd.read_csv(os.path.join(DIR_J, "control_entre_rondas.csv"))
    print(f"  referencia total: {len(ref)} juzgados")
    places = armar_places(D, ref)

    print("\n=== I. Inclusion (a)-(d) ===")
    inc, det_b, det_c, det_d = inclusion(D, places)
    entran = [i for i in CANDIDATAS if bool(inc.loc[inc["indicador"] == i, "entra"].iloc[0])]

    print("\n=== R. Radar nacional: configuraciones, cadena y veredicto ===")
    cfg = tabla_configs(D, base)
    V = veredicto(D, entran, base)
    cad = pd.DataFrame([{"paso": k, "listas": r["listas"], "cortes": (f"{r['cortes'][0]:.4f}/{r['cortes'][1]:.4f}" if r["cortes"] else "sin cortes validos"),
                         "anclas_rotas": r["anclas_rotas"], "rho_dane": r["rho_dane"], "rho_size": r["rho_size"], "pasa": r["pasa"]}
                        for k, r in enumerate(V["pasos"])])

    print("\n=== F. Impacto ===")
    conjuntos = [("F8: solo grupos armados", [GA])]
    if entran and sorted(entran) != [GA]:
        conjuntos.append(("incluidas por (a)-(d)", entran))
    if V["final"] and sorted(V["final"]) != sorted(entran):
        conjuntos.append(("configuracion final", V["final"]))
    imp = [impacto(D, l, base, n) for n, l in conjuntos]
    imp_res = pd.DataFrame([{"configuracion": n, "cortes": (f"{r['cortes'][0]:.4f}/{r['cortes'][1]:.4f}" if r["cortes"] else "sin cortes validos"),
                             "deptos_cambian_vigentes": int(fd["cambia_vigentes"].sum()), "deptos_cambian_recalibrados": int(fd["cambia_recalibrados"].sum()),
                             "celdas_que_cambian": int(len(celdas)), "celdas_gt_0.05": int((celdas["dMAX"].abs() > 0.05).sum()),
                             "celdas_a_cero": int(((celdas["MAX_sin"] > 0) & (celdas["MAX_con"] == 0)).sum()),
                             "lugares_cambian_clase": int((fl["clase_sin_vigentes"] != fl["clase_con_recalibrados"]).sum())}
                            for (n, _), (fd, ind, celdas, fl, r) in zip(conjuntos, imp)])
    lista_rob = V["final"] or entran or [GA]
    rob = robustez_truncacion(D, base, lista_rob)

    R = {"veredicto": V, "inclusion": inc, "entran": entran, "kappa": kap, "control": ctrl, "configs": cfg, "cadena": cad,
         "base": base, "impacto_resumen": imp_res, "sanidad": S, "det_b": det_b, "det_c": det_c, "det_d": det_d,
         "imp": {n: x for (n, _), x in zip(conjuntos, imp)}, "rob": rob}
    print(f"\nEntran: {entran or 'ninguna'} | Final: {V['final'] or 'ninguna'} | VEREDICTO: {V['veredicto']} ({V['motivo']})")
    print(inc[["indicador", "a_ganancia", "a_pasa", "b_ganancia", "b_cobertura_min", "b_pasa", "c_pasa", "d_violaciones_nuevas", "d_pasa", "entra"]]
          .round(3).to_string(index=False))
    print(cfg[["listas", "cortes", "anclas_rotas", "rho_dane", "rho_size", "pasa"]].round(4).to_string(index=False))
    print(imp_res.to_string(index=False))

    os.makedirs(os.path.dirname(salida_xlsx), exist_ok=True)
    with pd.ExcelWriter(salida_xlsx, engine="openpyxl") as w:
        S.to_excel(w, sheet_name="S_sanidad", index=False)
        kap.to_excel(w, sheet_name="J_kappa", index=False)
        ctrl.to_excel(w, sheet_name="J_control", index=False)
        inc.to_excel(w, sheet_name="I_inclusion", index=False)
        det_b.to_excel(w, sheet_name="I_holdout_b", index=False)
        det_c.to_excel(w, sheet_name="I_control_c", index=False)
        det_d.to_excel(w, sheet_name="I_m3_d", index=False)
        cfg.to_excel(w, sheet_name="R_configs", index=False)
        cad.to_excel(w, sheet_name="R_cadena", index=False)
        pd.DataFrame([{"veredicto": V["veredicto"], "motivo": V["motivo"], "entran": ", ".join(entran), "final": ", ".join(V["final"])}]).to_excel(
            w, sheet_name="V_veredicto", index=False)
        imp_res.to_excel(w, sheet_name="F_resumen", index=False)
        pd.concat([x[0].reset_index().rename(columns={"index": "departamento"}) for x in imp]).round(6).to_excel(w, sheet_name="F_deptos", index=False)
        pd.concat([x[1].reset_index() for x in imp]).round(6).to_excel(w, sheet_name="F_indicadores", index=False)
        pd.concat([x[2] for x in imp]).round(6).to_excel(w, sheet_name="F_celdas_MAX", index=False)
        pd.concat([x[3].reset_index().rename(columns={"index": "lugar"}) for x in imp]).round(6).to_excel(w, sheet_name="F_lugares", index=False)
        rob.to_excel(w, sheet_name="Z_robustez", index=False)
    escribir_md(salida_md, R)
    print(f"\nGuardado -> {salida_xlsx} y {salida_md}")


if __name__ == "__main__":
    main()
