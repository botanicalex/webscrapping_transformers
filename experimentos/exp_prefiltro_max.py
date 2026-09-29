# -*- coding: utf-8 -*-
"""
Pre-filtro de relevancia social bajo MAX. Pre-registro: experimentos/PREREG_prefiltro_max.md
(congelado en 3849793, antes de calcular ninguna metrica). Todo offline sobre los pkl; la unica GPU
esta en experimentos/exp_prefiltro_gpu_lugares.py.

Pregunta: con MAX y los 26 indicadores, reintegrar el pre-filtro (score_social_v2 < 0.85 => score 0
en los 26 indicadores) ?, mejora el radar y los indicadores lo bastante para revertir el rechazo del
2026-08-31? Variable unica: mascara si/no (umbral 0.85). Decide C1-C4 (empate = NO).

Orden: sanidad (S) -> reproduccion exacta de A -> bloques B-F y decision -> sensibilidad (0.50,
0.65, 0.75; no decide) -> Excel y RESULTADOS_prefiltro_max.md.

Ejecutar desde la raiz del worktree:
  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_max.py            # todo
  PYTHONIOENCODING=utf-8 python -u experimentos/exp_prefiltro_max.py sanidad   # solo S y A

Se importan funciones de exp_5ind_max_cortes.py, exp_5ind_max_r2_metricas.py y
exp_correlacion_v2_nacional.py sin llamar a sus main(); no se escribe en ninguna carpeta de
resultados de experimentos anteriores.
"""
import os
import re
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_base as HB  # noqa: E402
import hipotesis_v2 as V2  # noqa: E402
import silver  # noqa: E402
from exp_5ind_max_cortes import clasificar, constancia, elegir_cortes  # noqa: E402
from exp_5ind_max_r2_metricas import referencia  # noqa: E402
from exp_correlacion_v2_nacional import NUNCA_ALTO, NUNCA_BAJO, _norm  # noqa: E402

# ── Rutas (desde la raiz del worktree) ──────────────────────────────────────
CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
CORPUS_L = "datos/corpus/df_corpus_5lugares.pkl"
PROCESADO_L = "resultados/tablas_lugares_max/df_procesado_5lugares.pkl"
RESUMEN_L = "resultados/tablas_lugares_max/resumen_indicadores_MAX_y_articulos_por_lugar.xlsx"
ATOMICAS_L = "datos/scores/scores_5ind_atomicas_lugares.pkl"
GPU_L = "datos/scores/scores_prefiltro_lugares.pkl"
OFICIAL = "datos/referencia/comparacion_radares_V3.xlsx"
URL_LUGARES = "experimentos/resultados/juicio_5ind/url_lugares.csv"
OLD_AB = "experimentos/resultados/exp_prefiltro_auc_indicador.xlsx"
M_R2 = "experimentos/resultados/juicio_5ind_r2/metricas_r2.xlsx"
M_HO = "experimentos/resultados/juicio_5ind_holdout/metricas_holdout.csv"
SALIDA_XLSX = "experimentos/resultados/exp_prefiltro_max.xlsx"
SALIDA_MD = "experimentos/RESULTADOS_prefiltro_max.md"

# ── Parametros fijados en el pre-registro ───────────────────────────────────
UMBRAL = 0.85
UMBRALES_SENS = [0.50, 0.65, 0.75]
N_BOOT = 2000
SEMILLA = 20260928       # bloques B, C (generador nuevo por bloque y por umbral)
SEMILLA_A = 20260831     # bloque A: la del script viejo
CORTES_VIG = (0.766, 0.9233)
CORTE = 0.766
INDS26 = list(V2.TODAS)
IND5 = H.INDICADORES_5
GA = "presencia_grupos_armados"
LUG = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]   # convencion del plan (url_lugares.csv)
HOLDOUT = ["Cauca", "Chocó", "Cundinamarca"]              # nombres del corpus nacional
MIN_POS = 20             # suficiente muestra
CAIDA_C3 = 0.04
TOL_C1 = 5e-5
SPEARMAN_MIN = 0.15


def s_corr(ent, neu, sesgo):
    return np.clip(np.clip(np.asarray(ent, dtype=float) - sesgo, 0, None)
                   * (1 - np.asarray(neu, dtype=float)), 0, 1)


def auc_fast(s, y):
    """Igual que silver.auc (rango promedio), para los remuestreos."""
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return np.nan
    r = rankdata(s)
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


# ═══════════════════════════════════════════════════════════════════════════
# Datos
# ═══════════════════════════════════════════════════════════════════════════
def cargar():
    D = SimpleNamespace()
    cn = pd.read_pickle(CORPUS_NAC).reset_index(drop=True)
    dn = pd.read_pickle(V2NAC).reset_index(drop=True)
    assert len(cn) == len(dn) == 11439
    assert (cn["titulo"].values == dn["titulo"].values).all(), "nacional desalineado (titulo)"
    assert (cn["departamento"].values == dn["departamento"].values).all(), "nacional desalineado (dep)"
    assert dn["score_social_v2"].notna().all()
    D.nac = cn[["url", "departamento", "titulo", "texto"]].copy()
    D.nac_social = dn["score_social_v2"].values.astype(float)
    D.nac_sesgo = dn["sesgo"].values.astype(float)
    D.nac_ent = {c: dn[f"ent_{c}"].values.astype(float) for c in INDS26 + ["NULA_TEST"]}
    D.nac_neu = {c: dn[f"neu_{c}"].values.astype(float) for c in INDS26 + ["NULA_TEST"]}
    D.nac_s = {c: s_corr(D.nac_ent[c], D.nac_neu[c], D.nac_sesgo) for c in INDS26 + ["NULA_TEST"]}

    cl = pd.read_pickle(CORPUS_L).reset_index(drop=True)
    proc = pd.read_pickle(PROCESADO_L).reset_index(drop=True)
    at = pd.read_pickle(ATOMICAS_L).reset_index(drop=True)
    gp = pd.read_pickle(GPU_L).reset_index(drop=True)
    for nombre, x in (("procesado", proc), ("atomicas", at), ("gpu", gp)):
        assert (x["url"].values == cl["url"].values).all(), f"{nombre} desalineado con el corpus de lugares"
    D.l = cl[["url", "departamento", "titulo"]].copy()
    D.l_social = gp["score_social_v2"].values.astype(float)
    D.l_prod = {c: proc[c].astype(float).values for c in INDS26}
    D.l_sesgo = at["sesgo"].values.astype(float)
    D.l_s5 = {i: s_corr(at[f"ent_{i}__vig"], at[f"neu_{i}__vig"], D.l_sesgo) for i in IND5}
    D.l_ent5 = {i: at[f"ent_{i}__vig"].values.astype(float) for i in IND5}
    D.l_ent_null = gp["ent_NULA_TEST"].values.astype(float)
    D.l_s_null = s_corr(D.l_ent_null, gp["neu_NULA_TEST"].values, D.l_sesgo)

    lug = pd.read_csv(URL_LUGARES)
    D.urls_lugar = {l: set(lug.loc[lug["lugar"] == l, "url"]) for l in LUG}
    ref = referencia()
    D.ref = ref
    D.juzgados = set(ref["url"])
    D.positivos = {i: set(ref.loc[ref[i] == 1, "url"]) for i in IND5}
    D.oficial = pd.read_excel(OFICIAL, engine="openpyxl")
    D.oficial.columns = [str(c).strip() for c in D.oficial.columns]
    D.oficial["_k"] = D.oficial["Departamento"].map(_norm)
    return D


# ═══════════════════════════════════════════════════════════════════════════
# Radares (nacional y lugares)
# ═══════════════════════════════════════════════════════════════════════════
def radares_nac(D, u):
    deps = D.nac["departamento"].values
    m = (D.nac_social >= u).astype(float)
    S = pd.DataFrame({c: D.nac_s[c] for c in INDS26})
    sin = S.groupby(deps).max()
    con = S.mul(m, axis=0).groupby(deps).max()
    ns = pd.Series(D.nac_s["NULA_TEST"]).groupby(deps).max()
    nc = pd.Series(D.nac_s["NULA_TEST"] * m).groupby(deps).max()
    assert sin.shape == (32, 26), sin.shape
    return sin, con, ns, nc


def radares_lug(D, u):
    labs = D.l["departamento"].values
    m = (D.l_social >= u).astype(float)
    S = pd.DataFrame({c: D.l_prod[c] for c in INDS26})
    sin = S.groupby(labs).max()
    con = S.mul(m, axis=0).groupby(labs).max()
    ns = pd.Series(D.l_s_null).groupby(labs).max()
    nc = pd.Series(D.l_s_null * m).groupby(labs).max()
    return sin, con, ns, nc


def radar_de(maxs, redondeo=False):
    return (maxs.round(4) if redondeo else maxs).mean(axis=1)


def anclas_rotas(radar, cb, ca):
    valor = {_norm(k): v for k, v in radar.items()}
    rotas = [x for x in NUNCA_ALTO if clasificar(valor[_norm(x)], cb, ca) == "Alto"]
    rotas += [x for x in NUNCA_BAJO if clasificar(valor[_norm(x)], cb, ca) == "Bajo"]
    return rotas


def dist(clases):
    vc = pd.Series(clases).value_counts()
    return {c: int(vc.get(c, 0)) for c in ("Bajo", "Medio", "Alto")}


# ═══════════════════════════════════════════════════════════════════════════
# Sanidad (S)
# ═══════════════════════════════════════════════════════════════════════════
def sanidad(D):
    filas = []

    def chk(nombre, ok, valor, esperado):
        filas.append({"chequeo": nombre, "ok": bool(ok), "valor": str(valor), "esperado": str(esperado)})
        print(f"  [{'OK' if ok else 'FALLA'}] {nombre}: {valor} (esperado {esperado})")

    # S1 nacional
    sin, con, ns, nc = radares_nac(D, UMBRAL)
    r_sin = radar_de(sin)
    cl = r_sin.map(lambda v: clasificar(v, *CORTES_VIG))
    chk("S1 clasificacion nacional sin mascara con 0.766/0.9233", dist(cl) == {"Bajo": 6, "Medio": 19, "Alto": 7},
        dist(cl), "6/19/7")
    cb, ca, _, rompe = elegir_cortes(r_sin)
    chk("S1 elegir_cortes(sin mascara) = cortes vigentes", (cb, ca) == CORTES_VIG, (cb, ca), CORTES_VIG)

    # S2 lugares (produccion) contra el encabezado del Excel del 1-sep
    sl, cl_, nsl, ncl = radares_lug(D, UMBRAL)
    rl = radar_de(sl, redondeo=True)
    x = pd.read_excel(RESUMEN_L, header=[0, 1], index_col=0)
    pat = re.compile(r"^(.*) — (Bajo|Medio|Alto) \((\d+\.\d+)\)$")
    for enc in dict.fromkeys(c[0] for c in x.columns):
        g = pat.match(enc)
        lugar, clase, rad = g.group(1), g.group(2), float(g.group(3))
        mi_rad = float(rl[lugar])
        mi_clase = clasificar(mi_rad, *CORTES_VIG)
        chk(f"S2 {lugar}: radar y clase", (f"{mi_rad:.4f}" == f"{rad:.4f}") and mi_clase == clase,
            f"{mi_rad:.4f} {mi_clase}", f"{rad:.4f} {clase}")
        if clase != "Bajo":
            v = x[(enc, "valor")].astype(float)
            dmax = float(np.abs(v.values - sl.loc[lugar, v.index].round(4).values).max())
            chk(f"S2 {lugar}: MAX de los 26 indicadores", dmax < 1e-9, f"max|dif|={dmax:.1e}", "0")
    ant_n = D.nac["departamento"].values == "Antioquia"
    chk("S2 Antioquia (2023) = Antioquia nacional (n articulos)", int(ant_n.sum()) == int(
        (D.l["departamento"] == "Antioquia (2023)").sum()), f"{int(ant_n.sum())} / "
        f"{int((D.l['departamento'] == 'Antioquia (2023)').sum())}", "iguales")
    d_ant = abs(float(radar_de(sl, True)["Antioquia (2023)"]) - float(r_sin["Antioquia"]))
    chk("S2 radar Antioquia (2023) vs Antioquia nacional", d_ant < 2e-4, f"|dif|={d_ant:.1e}", "< 2e-4")
    d_soc = float(np.abs(D.l_social[(D.l["departamento"] == "Antioquia (2023)").values][np.argsort(
        D.l["url"][(D.l["departamento"] == "Antioquia (2023)").values].values)]
        - D.nac_social[ant_n][np.argsort(D.nac["url"].values[ant_n])]).max())
    chk("S2 score_social_v2 Antioquia lugares vs nacional (por url)", d_soc < 1e-4, f"max|dif|={d_soc:.1e}", "< 1e-4")

    # S3 atomicas vs produccion (5 indicadores)
    d3 = max(float(np.abs(D.l_s5[i] - D.l_prod[i]).max()) for i in IND5)
    chk("S3 score de atomicas vs produccion en los 5 indicadores", d3 < 1e-4, f"max|dif|={d3:.1e}", "< 1e-4")

    # S4 M1-M3 sin mascara vs metricas_r2 (lugares) y metricas_holdout (holdout)
    places = armar_lugares(D)
    cells = celdas(places)
    P = puntos_C(cells, np.ones(0), None)  # sin mascara: mascara todo 1 (ver puntos_C)
    m2 = pd.read_excel(M_R2)
    m2 = m2[m2["candidata"] == "vig"].set_index("indicador")
    for i in IND5:
        cs = [c for c, (p, ii) in enumerate(cells) if ii == i and p.kind == "lugar"]
        m1n = int(sum(P[c, 0, 0] == 1.0 for c in cs))
        m2v = round(float(np.mean([P[c, 0, 2] for c in cs])), 3)
        viol = int(sum((not p.pos[ii].any() and P[c, 0, 6] >= CORTE) or (p.pos[ii].any() and P[c, 0, 6] < CORTE)
                       for c, (p, ii) in enumerate(cells) if c in cs))
        mx_ok = all(abs(round(P[c, 0, 6], 4) - m2.loc[i, f"max_{cells[c][0].name}"]) < 1e-9 for c in cs)
        ok = (m1n == int(m2.loc[i, "M1_n"])) and abs(m2v - float(m2.loc[i, "M2"])) < 1e-9 \
            and viol == int(m2.loc[i, "M3_viol"]) and mx_ok
        chk(f"S4 M1/M2/M3/MAX sin mascara, {i}", ok, f"M1_n={m1n} M2={m2v} viol={viol} max_ok={mx_ok}",
            f"M1_n={int(m2.loc[i, 'M1_n'])} M2={float(m2.loc[i, 'M2'])} viol={int(m2.loc[i, 'M3_viol'])}")
    mho = pd.read_csv(M_HO)
    mho = mho[mho["variante"] == "V01"].set_index("lugar")
    for c, (p, ii) in enumerate(cells):
        if p.kind != "holdout":
            continue
        clave = {"Chocó": "Choco"}.get(p.name, p.name)
        f = mho.loc[clave]
        ok = (p.n == int(f["n"]) and int((p.S[GA] > 0).sum()) == int(f["n_score>0"])
              and int(p.pos[GA].sum()) == int(f["npos"]) and bool(P[c, 0, 0]) == bool(f["M1"])
              and abs(round(P[c, 0, 2], 3) - float(f["M2"])) < 1e-9 and abs(round(P[c, 0, 6], 4) - float(f["max"])) < 1e-9)
        chk(f"S4 holdout {p.name}: n, n>0, npos, M1, M2, max", ok,
            f"n={p.n} n>0={int((p.S[GA] > 0).sum())} npos={int(p.pos[GA].sum())} M1={bool(P[c, 0, 0])} "
            f"M2={round(P[c, 0, 2], 3)} max={round(P[c, 0, 6], 4)}",
            f"n={int(f['n'])} n>0={int(f['n_score>0'])} npos={int(f['npos'])} M1={bool(f['M1'])} M2={f['M2']} "
            f"max={f['max']}")
    cov = float(np.nanmin(P[:, 0, 4]))
    chk("S4 cobertura sin mascara (top-k todo juzgado)", cov == 1.0, f"min={cov}", "1.0")
    return pd.DataFrame(filas)


# ═══════════════════════════════════════════════════════════════════════════
# A. AUC por articulo contra plata (calco de exp_prefiltro_auc_indicador.py)
# ═══════════════════════════════════════════════════════════════════════════
def bootstrap_delta_auc(s_sin, s_con, y, rng, n_boot=N_BOOT):
    m = ~np.isnan(y)
    s0, s1, yy = s_sin[m], s_con[m], y[m]
    n = len(yy)
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        deltas[i] = silver.auc(s1[idx], yy[idx]) - silver.auc(s0[idx], yy[idx])
    return float(deltas.mean()), (float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5)))


def etiquetas_plata(D):
    d = D.nac[["titulo", "texto"]]
    return {ind: silver.etiquetar(d, kws)["label"].values for ind, kws in HB.KEYWORDS_SILVER.items()}


def bloque_A(u, D, plata):
    rng = np.random.default_rng(SEMILLA_A)
    rel = D.nac_social >= u
    filas = []
    for ind, y in plata.items():
        ent, cor = D.nac_ent[ind], D.nac_s[ind]
        e_sin, e_con = ent, np.where(rel, ent, 0.0)
        c_sin, c_con = cor, np.where(rel, cor, 0.0)
        ret = float(rel[y == 1].mean())
        d_e, ic_e = bootstrap_delta_auc(e_sin, e_con, y, rng)
        d_c, ic_c = bootstrap_delta_auc(c_sin, c_con, y, rng)
        for esc, a0, a1, dd, ic in (("ent_crudo", e_sin, e_con, d_e, ic_e), ("score_corregido", c_sin, c_con, d_c, ic_c)):
            filas.append({"tipo": "real", "indicador": ind, "escala": esc, "auc_sin": silver.auc(a0, y),
                          "auc_con": silver.auc(a1, y), "delta": dd, "ic95_low": ic[0], "ic95_high": ic[1],
                          "retencion_positivos": ret, "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum())})
    e_n, c_n = D.nac_ent["NULA_TEST"], D.nac_s["NULA_TEST"]
    en_sin, en_con = e_n, np.where(rel, e_n, 0.0)
    cn_sin, cn_con = c_n, np.where(rel, c_n, 0.0)
    for ind, y in plata.items():
        d_e, ic_e = bootstrap_delta_auc(en_sin, en_con, y, rng)
        d_c, ic_c = bootstrap_delta_auc(cn_sin, cn_con, y, rng)
        for esc, a0, a1, dd, ic in (("ent_crudo", en_sin, en_con, d_e, ic_e), ("score_corregido", cn_sin, cn_con, d_c, ic_c)):
            filas.append({"tipo": "absurdo", "indicador": f"NULA_TEST_vs_{ind}", "escala": esc,
                          "auc_sin": silver.auc(a0, y), "auc_con": silver.auc(a1, y), "delta": dd,
                          "ic95_low": ic[0], "ic95_high": ic[1], "retencion_positivos": np.nan,
                          "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum())})
    for etq, ex, cx in (("sin_prefiltro", en_sin, cn_sin), ("con_prefiltro", en_con, cn_con)):
        filas.append({"tipo": "absurdo_escala_completa", "indicador": "NULA_TEST", "escala": etq,
                      "media_cruda": float(np.mean(ex)), "prop09_cruda": float((ex > 0.9).mean()),
                      "media_corregida": float(np.mean(cx))})
    return pd.DataFrame(filas)


def repro_A(dfA):
    old = pd.read_excel(OLD_AB)
    llaves = ["tipo", "indicador", "escala"]
    m = old.merge(dfA, on=llaves, suffixes=("_old", "_new"))
    assert len(m) == len(old) == len(dfA), (len(m), len(old), len(dfA))
    filas, ok_todo = [], True
    for col, tol in (("auc_sin", 1e-9), ("auc_con", 1e-9), ("retencion_positivos", 1e-9), ("delta", 5e-5),
                     ("ic95_low", 5e-5), ("ic95_high", 5e-5), ("media_cruda", 1e-9), ("prop09_cruda", 1e-9),
                     ("media_corregida", 1e-9), ("n_pos", 0), ("n_neg", 0)):
        a, b = m[col + "_old"].astype(float), m[col + "_new"].astype(float)
        d = (a - b).abs()[~(a.isna() & b.isna())]
        mx = float(d.max()) if len(d) else 0.0
        ok = mx <= tol
        ok_todo &= ok
        filas.append({"columna": col, "max_abs_dif": mx, "tolerancia": tol, "ok": ok})
        print(f"  [{'OK' if ok else 'FALLA'}] A {col}: max|dif| = {mx:.2e} (tol {tol:g})")
    return ok_todo, pd.DataFrame(filas)


# ═══════════════════════════════════════════════════════════════════════════
# B. AUC por articulo contra los jueces (759 juzgados en lugares o holdout)
# ═══════════════════════════════════════════════════════════════════════════
def tabla_juzgados(D):
    lug_union = set().union(*D.urls_lugar.values())
    idx_l = {u: i for i, u in enumerate(D.l["url"])}
    idx_n = {u: i for i, u in enumerate(D.nac["url"])}
    dep_n = D.nac["departamento"].values
    J = SimpleNamespace(url=[], bloque=[], social=[], s={i: [] for i in IND5}, e={i: [] for i in IND5},
                        s_null=[], e_null=[], y={i: [] for i in IND5})
    ref = D.ref.set_index("url")
    for u in D.ref["url"]:
        if u in lug_union:
            k = idx_l[u]
            J.bloque.append("lugares")
            J.social.append(D.l_social[k])
            for i in IND5:
                J.s[i].append(D.l_s5[i][k]); J.e[i].append(D.l_ent5[i][k])
            J.s_null.append(D.l_s_null[k]); J.e_null.append(D.l_ent_null[k])
        elif u in idx_n and dep_n[idx_n[u]] in HOLDOUT:
            k = idx_n[u]
            J.bloque.append("holdout")
            J.social.append(D.nac_social[k])
            for i in IND5:
                J.s[i].append(D.nac_s[i][k]); J.e[i].append(D.nac_ent[i][k])
            J.s_null.append(D.nac_s["NULA_TEST"][k]); J.e_null.append(D.nac_ent["NULA_TEST"][k])
        else:
            continue
        J.url.append(u)
        for i in IND5:
            J.y[i].append(int(ref.loc[u, i]))
    J.n = len(J.url)
    J.social = np.array(J.social)
    J.s_null, J.e_null = np.array(J.s_null), np.array(J.e_null)
    for i in IND5:
        J.s[i], J.e[i], J.y[i] = np.array(J.s[i]), np.array(J.e[i]), np.array(J.y[i])
    return J


def bloque_B(u, J):
    rng = np.random.default_rng(SEMILLA)
    m = (J.social >= u).astype(float)
    inds = [i for i in IND5 if J.y[i].sum() > 0]
    series = {}
    for i in inds:
        series[(i, "score_corregido")] = (J.s[i], J.s[i] * m, J.s_null, J.s_null * m)
        series[(i, "ent_crudo")] = (J.e[i], J.e[i] * m, J.e_null, J.e_null * m)
    boot = {k: np.empty((N_BOOT, 4)) for k in series}
    for b in range(N_BOOT):
        idx = rng.integers(0, J.n, J.n)
        for k, (rs, rc, ns, nc) in series.items():
            y = J.y[k[0]][idx]
            boot[k][b] = [auc_fast(rs[idx], y), auc_fast(rc[idx], y), auc_fast(ns[idx], y), auc_fast(nc[idx], y)]
    filas = []
    for i in IND5:
        y = J.y[i]
        npos, nneg = int(y.sum()), int(len(y) - y.sum())
        for esc in ("score_corregido", "ent_crudo"):
            f = {"indicador": i, "escala": esc, "n_juzgados": J.n, "n_pos": npos, "n_neg": nneg,
                 "suficiente_muestra": npos >= MIN_POS and nneg >= MIN_POS}
            if (i, esc) in series:
                rs, rc, ns, nc = series[(i, esc)]
                a0, a1, n0, n1 = silver.auc(rs, y), silver.auc(rc, y), silver.auc(ns, y), silver.auc(nc, y)
                assert abs(a0 - auc_fast(rs, y)) < 1e-12
                bt = boot[(i, esc)]
                dr, dn = bt[:, 1] - bt[:, 0], bt[:, 3] - bt[:, 2]
                nt = dr - dn
                ic_r, ic_n = np.nanpercentile(dr, [2.5, 97.5]), np.nanpercentile(nt, [2.5, 97.5])
                f.update({"auc_sin": a0, "auc_con": a1, "delta": a1 - a0, "delta_boot": float(np.nanmean(dr)),
                          "ic95_low": ic_r[0], "ic95_high": ic_r[1], "nula_auc_sin": n0, "nula_auc_con": n1,
                          "delta_nula": n1 - n0, "neta": (a1 - a0) - (n1 - n0), "neta_ic95_low": ic_n[0],
                          "neta_ic95_high": ic_n[1],
                          "pasa_C4": bool(f["suficiente_muestra"] and esc == "score_corregido" and ic_r[0] > 0 and ic_n[0] > 0)})
            filas.append(f)
    return pd.DataFrame(filas)


# ═══════════════════════════════════════════════════════════════════════════
# C. M1-M3 del MAX con jueces (celdas indicador x lugar y grupos armados x holdout)
# ═══════════════════════════════════════════════════════════════════════════
def armar_lugares(D):
    idx_l = {u: i for i, u in enumerate(D.l["url"])}
    places = []
    for l in LUG:
        urls = sorted(D.urls_lugar[l])
        ii = np.array([idx_l[u] for u in urls])
        places.append(SimpleNamespace(
            name=l, kind="lugar", n=len(urls), urls=np.array(urls), social=D.l_social[ii],
            S={i: D.l_s5[i][ii] for i in IND5}, Snull=D.l_s_null[ii],
            jud=np.array([u in D.juzgados for u in urls]),
            pos={i: np.array([u in D.positivos[i] for u in urls]) for i in IND5}, inds=IND5))
    for dep in HOLDOUT:
        m = np.where(D.nac["departamento"].values == dep)[0]
        urls = D.nac["url"].values[m]
        o = np.argsort(urls, kind="stable")
        m, urls = m[o], urls[o]
        places.append(SimpleNamespace(
            name=dep, kind="holdout", n=len(m), urls=urls, social=D.nac_social[m],
            S={GA: D.nac_s[GA][m]}, Snull=D.nac_s["NULA_TEST"][m],
            jud=np.array([u in D.juzgados for u in urls]),
            pos={GA: np.array([u in D.positivos[GA] for u in urls])}, inds=[GA]))
    return places


def celdas(places):
    return [(p, i) for p in places if p.kind == "lugar" for i in IND5] + \
           [(p, GA) for p in places if p.kind == "holdout"]


def metricas_celda(x, idx, pos, jud, haspos):
    """(m1_low, m1_up, m2_low, m2_up, cobertura, k, max) de una celda con la muestra idx."""
    xs = x[idx]
    k = min(10, int(np.count_nonzero(xs > 0)))
    if k == 0:
        v = 0.0 if haspos else 1.0
        return (v, v, v, v, np.nan, 0, 0.0)
    o = np.lexsort((idx, -xs))[:k]
    sel = idx[o]
    p, j = pos[sel], jud[sel]
    return (float(p[0]), float(p[0] or not j[0]), float(p.mean()), float((p | ~j).mean()),
            float(j.mean()), k, float(xs[o[0]]))


def _arrays_celda(p, i, mascara):
    m = mascara.astype(float)
    return (p.S[i], p.S[i] * m, p.Snull, p.Snull * m, p.pos[i], p.jud, bool(p.pos[i].any()))


def puntos_C(cells, _unused, mask_por_lugar):
    """Metricas puntuales por celda y condicion (0 real sin, 1 real con, 2 nula sin, 3 nula con).
    mask_por_lugar = None => sin mascara en ambas (S4)."""
    P = np.zeros((len(cells), 4, 7))
    for c, (p, i) in enumerate(cells):
        mk = np.ones(p.n, dtype=bool) if mask_por_lugar is None else mask_por_lugar[p.name]
        a, b, cn, dn, pos, jud, hp = _arrays_celda(p, i, mk)
        idx = np.arange(p.n)
        for j, arr in enumerate((a, b, cn, dn)):
            P[c, j] = metricas_celda(arr, idx, pos, jud, hp)
    return P


def bloque_C(u, places):
    cells = celdas(places)
    mask = {p.name: (p.social >= u) for p in places}
    P = puntos_C(cells, None, mask)
    X = [_arrays_celda(p, i, mask[p.name]) for p, i in cells]
    por_lugar = {p.name: [c for c, (pp, _) in enumerate(cells) if pp.name == p.name] for p in places}
    rng = np.random.default_rng(SEMILLA)
    R = np.empty((N_BOOT, len(cells), 4, 5))
    for b in range(N_BOOT):
        for p in places:
            idx = rng.integers(0, p.n, p.n)
            for c in por_lugar[p.name]:
                a, a2, cn, dn, pos, jud, hp = X[c]
                for j, arr in enumerate((a, a2, cn, dn)):
                    R[b, c, j] = metricas_celda(arr, idx, pos, jud, hp)[:5]
    # tabla por celda (puntual)
    filas = []
    for c, (p, i) in enumerate(cells):
        hp = bool(p.pos[i].any())
        f = {"indicador": i, "lugar": p.name, "tipo": p.kind, "n_articulos": p.n, "n_positivos": int(p.pos[i].sum()),
             "pasan_filtro": int(mask[p.name].sum()), "n_score_gt0_sin": int((p.S[i] > 0).sum()),
             "n_score_gt0_con": int((p.S[i] * mask[p.name] > 0).sum())}
        for tag, j in (("sin", 0), ("con", 1), ("nula_sin", 2), ("nula_con", 3)):
            m1l, m1u, m2l, m2u, cov, k, mx = P[c, j]
            f.update({f"k_{tag}": int(k), f"M1_low_{tag}": m1l, f"M1_up_{tag}": m1u, f"M2_low_{tag}": m2l,
                      f"M2_up_{tag}": m2u, f"cobertura_{tag}": cov, f"max_{tag}": mx})
        for tag, j in (("sin", 0), ("con", 1)):
            mx = P[c, j, 6]
            f[f"M3viol_{tag}"] = bool((not hp and mx >= CORTE) or (hp and mx < CORTE))
        filas.append(f)
    celdas_df = pd.DataFrame(filas)
    # unidades de decision
    unidades = {"grupos_armados (7 celdas)": [c for c, (_, i) in enumerate(cells) if i == GA],
                "todas (23 celdas)": list(range(len(cells)))}
    fu = []
    for nombre, U in unidades.items():
        for met, kl, ku in (("M1", 0, 1), ("M2", 2, 3)):
            sin, con_l, con_u = P[U, 0, kl].mean(), P[U, 1, kl].mean(), P[U, 1, ku].mean()
            n_sin, n_con = P[U, 2, kl].mean(), P[U, 3, kl].mean()
            dr = R[:, U, 1, kl].mean(axis=1) - R[:, U, 0, kl].mean(axis=1)
            dn = R[:, U, 3, kl].mean(axis=1) - R[:, U, 2, kl].mean(axis=1)
            nt = dr - dn
            ic_r, ic_n = np.percentile(dr, [2.5, 97.5]), np.percentile(nt, [2.5, 97.5])
            npos_u = len(set().union(*[set(cells[c][0].urls[cells[c][0].pos[cells[c][1]]]) for c in U]))
            elegible = npos_u >= MIN_POS
            fu.append({"unidad": nombre, "metrica": met, "n_positivos_distintos": npos_u, "elegible": elegible,
                       "sin_mascara": sin, "con_mascara_cota_inf": con_l, "con_mascara_cota_sup": con_u,
                       "delta_cota_inf": con_l - sin, "delta_cota_sup": con_u - sin,
                       "ic95_low": ic_r[0], "ic95_high": ic_r[1], "nula_sin": n_sin, "nula_con": n_con,
                       "delta_nula": n_con - n_sin, "neta": (con_l - sin) - (n_con - n_sin),
                       "neta_ic95_low": ic_n[0], "neta_ic95_high": ic_n[1],
                       "cobertura_con": float(np.nanmean(P[U, 1, 4])),
                       "pasa_C4": bool(elegible and ic_r[0] > 0 and ic_n[0] > 0)})
    unid_df = pd.DataFrame(fu)
    # M2+ y M1+ (solo celdas con >= 1 positivo) y M3, descriptivos
    conpos = [c for c, (p, i) in enumerate(cells) if p.pos[i].any()]
    lug20 = [c for c, (p, _) in enumerate(cells) if p.kind == "lugar"]
    desc = {"celdas_con_positivos": len(conpos),
            "M1plus_sin": P[conpos, 0, 0].mean(), "M1plus_con_low": P[conpos, 1, 0].mean(),
            "M2plus_sin": P[conpos, 0, 2].mean(), "M2plus_con_low": P[conpos, 1, 2].mean(),
            "M3_viol_sin_20lugares": int(celdas_df.loc[lug20, "M3viol_sin"].sum()),
            "M3_viol_con_20lugares": int(celdas_df.loc[lug20, "M3viol_con"].sum()),
            "M3_viol_sin_23": int(celdas_df["M3viol_sin"].sum()), "M3_viol_con_23": int(celdas_df["M3viol_con"].sum())}
    return celdas_df, unid_df, desc


# ═══════════════════════════════════════════════════════════════════════════
# D, E, F (radar) y decision
# ═══════════════════════════════════════════════════════════════════════════
def bloques_radar(u, D):
    R = SimpleNamespace(u=u)
    sin, con, ns, nc = radares_nac(D, u)
    r_sin, r_con = radar_de(sin), radar_de(con)
    R.max_sin, R.max_con, R.r_sin, R.r_con = sin, con, r_sin, r_con
    oficial = D.oficial
    n_art = D.nac["departamento"].value_counts()
    # E
    try:
        cb, ca, _, _ = elegir_cortes(r_con)
        R.cortes_recal = (float(cb), float(ca))
    except RuntimeError:
        R.cortes_recal = None
    cb0, ca0, _, _ = elegir_cortes(r_sin)
    R.cortes_sin = (float(cb0), float(ca0))
    c_sin = constancia(r_sin, *CORTES_VIG, oficial)
    c_con_v = constancia(r_con, *CORTES_VIG, oficial)
    R.rho_sin, R.rho_con = c_sin["rho"], c_con_v["rho"]
    filas = []
    conf = [("sin mascara", "vigentes", r_sin, CORTES_VIG), ("con mascara", "vigentes", r_con, CORTES_VIG)]
    if R.cortes_recal is not None:
        conf.append(("con mascara", "recalibrados", r_con, R.cortes_recal))
    else:
        filas.append({"radar": "con mascara", "cortes": "recalibrados", "corte_bajo_medio": np.nan,
                      "corte_medio_alto": np.nan, "nota": "sin cortes validos: ningun par evita romper anclas"})
    for radar_n, cortes_n, r, (a, b) in conf:
        c = constancia(r, a, b, oficial)
        rotas = anclas_rotas(r, a, b)
        filas.append({"radar": radar_n, "cortes": cortes_n, "corte_bajo_medio": a, "corte_medio_alto": b,
                      **{f"n_{k}": v for k, v in c["dist"].items()}, "anclas_rotas": len(rotas),
                      "anclas_rotas_lista": ", ".join(rotas), "accuracy": c["acc"], "spearman": c["rho"]})
    R.E = pd.DataFrame(filas)
    R.rho_tam = {"radar_sin": float(spearmanr(r_sin.values, n_art.reindex(r_sin.index).values).correlation),
                 "radar_con": float(spearmanr(r_con.values, n_art.reindex(r_con.index).values).correlation),
                 "nula_sin": float(spearmanr(ns.values, n_art.reindex(ns.index).values).correlation),
                 "nula_con": float(spearmanr(nc.values, n_art.reindex(nc.index).values).correlation)}
    R.anclas_con_vig = anclas_rotas(r_con, *CORTES_VIG)
    # D(b) departamentos
    gap_s, gap_c = r_sin - ns, r_con - nc
    R.gap_dep = pd.DataFrame({"radar_sin": r_sin, "null_max_sin": ns, "brecha_sin": gap_s, "radar_con": r_con,
                              "null_max_con": nc, "brecha_con": gap_c, "delta_brecha": gap_c - gap_s})
    R.gap_dep_delta = float((gap_c - gap_s).mean())
    R.gap_dep_baja = int(((gap_c - gap_s) < -TOL_C1).sum())
    # lugares (produccion)
    lsin, lcon, lns, lnc = radares_lug(D, u)
    lr_s, lr_c = radar_de(lsin, True), radar_de(lcon, True)
    R.l_sin, R.l_con, R.lr_sin, R.lr_con = lsin, lcon, lr_s, lr_c
    lg_s, lg_c = lr_s - lns, lr_c - lnc
    R.gap_lug = pd.DataFrame({"radar_sin": lr_s, "null_max_sin": lns, "brecha_sin": lg_s, "radar_con": lr_c,
                              "null_max_con": lnc, "brecha_con": lg_c, "delta_brecha": lg_c - lg_s})
    R.gap_lug_delta = float((lg_c - lg_s).mean())
    R.gap_lug_baja = int(((lg_c - lg_s) < -TOL_C1).sum())
    # D(c) escala de la nula
    m_n = (D.nac_social >= u)
    m_l = (D.l_social >= u)
    filas = []
    for ambito, ent, cor, mk, labs in (("nacional", D.nac_ent["NULA_TEST"], D.nac_s["NULA_TEST"], m_n, None),
                                       ("lugares", D.l_ent_null, D.l_s_null, m_l, D.l["departamento"].values)):
        grupos = [("total", np.ones(len(ent), bool))] + ([(g, labs == g) for g in sorted(set(labs))] if labs is not None else [])
        for g, sel in grupos:
            for cond, k in (("sin", np.ones(len(ent), bool)), ("con", mk)):
                e, c = np.where(k, ent, 0.0)[sel], np.where(k, cor, 0.0)[sel]
                filas.append({"ambito": ambito, "grupo": g, "mascara": cond, "n": int(sel.sum()),
                              "media_cruda": float(e.mean()), "prop_cruda_gt09": float((e > 0.9).mean()),
                              "media_corregida": float(c.mean()), "prop_corregida_gt09": float((c > 0.9).mean())})
    R.D_escala = pd.DataFrame(filas)
    # F
    dif = con - sin
    R.F_ind = pd.DataFrame({"media_abs_dMAX": dif.abs().mean(), "celdas_abs_dMAX_gt_0.05": (dif.abs() > 0.05).sum(),
                            "celdas_que_pasan_a_0": ((sin > 0) & (con == 0)).sum(), "MAX_medio_sin": sin.mean(),
                            "MAX_medio_con": con.mean()}).sort_values("media_abs_dMAX", ascending=False)
    R.F_ind.index.name = "indicador"
    R.pct_masc_nac = float(1 - m_n.mean())
    lab_l = D.l["departamento"].values
    R.pct_masc_lug = {g: float(1 - m_l[lab_l == g].mean()) for g in sorted(set(lab_l))}
    cls = {"sin_vig": r_sin.map(lambda v: clasificar(v, *CORTES_VIG)),
           "con_vig": r_con.map(lambda v: clasificar(v, *CORTES_VIG))}
    cls["con_recal"] = (r_con.map(lambda v: clasificar(v, *R.cortes_recal)) if R.cortes_recal else pd.Series("s/d", index=r_con.index))
    fd = pd.DataFrame({"n_articulos": n_art.reindex(r_sin.index), "radar_sin": r_sin, "radar_con": r_con,
                       "diferencia": r_con - r_sin, "clase_sin_vigentes": cls["sin_vig"],
                       "clase_con_vigentes": cls["con_vig"], "clase_con_recalibrados": cls["con_recal"]})
    fd["cambia_vig_vig"] = fd["clase_sin_vigentes"] != fd["clase_con_vigentes"]
    fd["cambia_vig_recal"] = fd["clase_sin_vigentes"] != fd["clase_con_recalibrados"]
    fd["oficial"] = [D.oficial.set_index("_k")["Clasificacion_radar_oficial_promedio"].get(_norm(k)) for k in fd.index]
    R.F_dep = fd.sort_values("radar_sin", ascending=False)
    R.n_cambian_vig = int(fd["cambia_vig_vig"].sum())
    R.n_cambian_recal = int(fd["cambia_vig_recal"].sum())
    R.n_celdas_005 = int((dif.abs() > 0.05).values.sum())
    R.n_celdas_cero = int(((sin > 0) & (con == 0)).values.sum())
    R.n_celdas_cambian = int((dif.abs() > 1e-9).values.sum())
    st = dif.stack()
    st = st[st.abs() > 0.05].sort_values()
    R.F_celdas = pd.DataFrame(
        [{"departamento": dep, "indicador": ind, "n_articulos": int(n_art[dep]), "MAX_sin": sin.loc[dep, ind],
          "MAX_con": con.loc[dep, ind], "dMAX": v} for (dep, ind), v in st.items()],
        columns=["departamento", "indicador", "n_articulos", "MAX_sin", "MAX_con", "dMAX"])
    fl = pd.DataFrame({"pct_enmascarado": pd.Series(R.pct_masc_lug), "radar_sin": lr_s, "radar_con": lr_c,
                       "diferencia": lr_c - lr_s})
    fl["clase_sin_vigentes"] = fl["radar_sin"].map(lambda v: clasificar(v, *CORTES_VIG))
    fl["clase_con_vigentes"] = fl["radar_con"].map(lambda v: clasificar(v, *CORTES_VIG))
    fl["clase_con_recalibrados"] = (fl["radar_con"].map(lambda v: clasificar(v, *R.cortes_recal)) if R.cortes_recal else "s/d")
    R.F_lug = fl
    return R


def decidir(R, A, B, Cu):
    d = {}
    d["C1_delta_brecha_dep"], d["C1_delta_brecha_lug"] = R.gap_dep_delta, R.gap_lug_delta
    d["C1_dep_baja"], d["C1_lug_baja"] = R.gap_dep_baja, R.gap_lug_baja
    c1 = R.gap_dep_delta >= -TOL_C1 and R.gap_lug_delta >= -TOL_C1
    val = R.cortes_recal is not None
    d["C2_cortes_validos"] = val
    d["C2_anclas_rotas_recal"] = (len(anclas_rotas(R.r_con, *R.cortes_recal)) if val else None)
    d["C2_rho_sin"], d["C2_rho_con"] = R.rho_sin, R.rho_con
    c2 = bool(val and d["C2_anclas_rotas_recal"] == 0 and R.rho_con >= R.rho_sin)
    ra = A[(A["tipo"] == "real") & (A["escala"] == "score_corregido")]
    caidas = [(f"A:{r.indicador}", r.auc_con - r.auc_sin) for r in ra.itertuples()]
    rb = B[(B["escala"] == "score_corregido") & B["suficiente_muestra"] & B["auc_sin"].notna()]
    caidas += [(f"B:{r.indicador}", r.auc_con - r.auc_sin) for r in rb.itertuples()]
    d["C3_caidas"] = {k: v for k, v in caidas}
    trig = any(v < -CAIDA_C3 for _, v in caidas)
    d["C3_disparada"] = trig
    c4_C = bool(Cu["pasa_C4"].any())
    c4_B = bool(rb["pasa_C4"].any()) if len(rb) else False
    d["C4_via_C"], d["C4_via_B"] = c4_C, c4_B
    d["C4_delta_spearman"] = R.rho_con - R.rho_sin
    c4_E = bool(d["C4_delta_spearman"] >= SPEARMAN_MIN)
    d["C4_via_E"] = c4_E
    c4 = c4_C or (not trig and (c4_B or c4_E))
    c3 = (not trig) or c4_C
    d.update({"C1": c1, "C2": c2, "C3": c3, "C4": bool(c4)})
    d["REINTEGRAR"] = bool(c1 and c2 and c3 and c4)
    return d


# ═══════════════════════════════════════════════════════════════════════════
# Orquestacion por umbral
# ═══════════════════════════════════════════════════════════════════════════
def correr(u, D, plata, J, places, A=None):
    R = bloques_radar(u, D)
    R.A = bloque_A(u, D, plata) if A is None else A
    R.B = bloque_B(u, J)
    R.C_celdas, R.C_unid, R.C_desc = bloque_C(u, places)
    R.dec = decidir(R, R.A, R.B, R.C_unid)
    return R




def resumen_umbral(R):
    a = R.A
    ar = a[(a["tipo"] == "real") & (a["escala"] == "score_corregido")].set_index("indicador")
    e = R.E.set_index(["radar", "cortes"])
    fila = {"umbral": R.u, "pct_enmascarado_nacional": R.pct_masc_nac,
            **{f"pct_enmasc_{k}": v for k, v in R.pct_masc_lug.items()},
            "A_dAUC_cor_grupos_etnicos": float(ar.loc["grupos_etnicos_existentes", "auc_con"] - ar.loc["grupos_etnicos_existentes", "auc_sin"]),
            "A_dAUC_cor_grupos_armados": float(ar.loc[GA, "auc_con"] - ar.loc[GA, "auc_sin"]),
            "D_dBrecha_media_dep": R.gap_dep_delta, "D_dBrecha_mediana_dep": float(R.gap_dep["delta_brecha"].median()),
            "D_dBrecha_media_lugar": R.gap_lug_delta,
            "D_deps_brecha_baja": R.gap_dep_baja, "D_lugares_brecha_baja": R.gap_lug_baja,
            "E_spearman_sin": R.rho_sin, "E_spearman_con": R.rho_con,
            "E_anclas_rotas_con_vigentes": len(R.anclas_con_vig),
            "E_cortes_recal": (f"{R.cortes_recal[0]:.4f}/{R.cortes_recal[1]:.4f}" if R.cortes_recal else "sin cortes validos"),
            "E_rho_tamano_sin": R.rho_tam["radar_sin"], "E_rho_tamano_con": R.rho_tam["radar_con"],
            "F_cambian_clase_vig": R.n_cambian_vig, "F_cambian_clase_recal": R.n_cambian_recal,
            "F_celdas_que_cambian": R.n_celdas_cambian,
            "F_celdas_dMAX_gt_005": R.n_celdas_005, "F_celdas_a_cero": R.n_celdas_cero}
    if ("con mascara", "vigentes") in e.index:
        fila["E_dist_con_vigentes"] = "/".join(str(e.loc[("con mascara", "vigentes"), f"n_{k}"]) for k in ("Bajo", "Medio", "Alto"))
    if ("con mascara", "recalibrados") in e.index:
        fila["E_dist_con_recal"] = "/".join(str(e.loc[("con mascara", "recalibrados"), f"n_{k}"]) for k in ("Bajo", "Medio", "Alto"))
    cu = R.C_unid.set_index(["unidad", "metrica"])
    for un in ("grupos_armados (7 celdas)", "todas (23 celdas)"):
        for m in ("M1", "M2"):
            r = cu.loc[(un, m)]
            fila[f"C_d{m}_{un.split(' ')[0]}"] = float(r["delta_cota_inf"])
            fila[f"C_d{m}_{un.split(' ')[0]}_ic_low"] = float(r["ic95_low"])
    for r in R.B[(R.B["escala"] == "score_corregido") & R.B["suficiente_muestra"]].itertuples():
        fila[f"B_dAUC_{r.indicador}"] = float(r.delta)
    fila.update({k: R.dec[k] for k in ("C1", "C2", "C3", "C4", "REINTEGRAR", "C3_disparada", "C4_via_B", "C4_via_C",
                                        "C4_via_E", "C4_delta_spearman")})
    return fila


def tabla_decision(R):
    d = R.dec
    cu = R.C_unid
    mejor = cu.sort_values("delta_cota_inf", ascending=False).iloc[0]
    med = float(R.gap_dep["delta_brecha"].median())
    caidas = ", ".join(f"{k.replace('A:', 'A ').replace('B:', 'B ')} {v:+.4f}" for k, v in d["C3_caidas"].items())
    filas = [
        {"criterio": "C1 control absurdo (brecha real − nula bajo MAX)", "pasa": d["C1"],
         "numero_clave": f"Δ brecha media {R.gap_dep_delta:+.4f} en los 32 departamentos (mediana {med:+.4f}; baja en "
                         f"{R.gap_dep_baja}) y {R.gap_lug_delta:+.4f} en los 4 lugares (baja en {R.gap_lug_baja})",
         "hoja": "D_brecha_dep, D_brecha_lugar"},
        {"criterio": "C2 radar nacional con cortes recalibrados", "pasa": d["C2"],
         "numero_clave": (f"cortes {R.cortes_recal[0]:.4f}/{R.cortes_recal[1]:.4f}, anclas rotas {d['C2_anclas_rotas_recal']}, "
                          f"Spearman {R.rho_sin:+.4f} sin máscara → {R.rho_con:+.4f} con máscara"
                          if R.cortes_recal else
                          f"sin cortes válidos; Spearman {R.rho_sin:+.4f} → {R.rho_con:+.4f}"),
         "hoja": "E_radar_nacional"},
        {"criterio": "C3 caída de AUC corregida > 0.04 exige mejora del bloque C", "pasa": d["C3"],
         "numero_clave": f"{'disparada' if d['C3_disparada'] else 'no disparada'}; ΔAUC corregida: {caidas}",
         "hoja": "A_auc_plata, B_auc_jueces"},
        {"criterio": "C4 mejora distinguible, neta de la nula", "pasa": d["C4"],
         "numero_clave": f"vía C (M1/M2, cota inferior): {'sí' if d['C4_via_C'] else 'no'}; vía B: "
                         f"{'sí' if d['C4_via_B'] else 'no'}; vía E (ΔSpearman {d['C4_delta_spearman']:+.3f} frente a +0.15): "
                         f"{'sí' if d['C4_via_E'] else 'no'}; el mayor cambio de C es {mejor['unidad']} {mejor['metrica']} "
                         f"{mejor['delta_cota_inf']:+.4f} [{mejor['ic95_low']:+.4f}, {mejor['ic95_high']:+.4f}]",
         "hoja": "B_auc_jueces, C_unidades, E_radar_nacional"},
        {"criterio": f"VEREDICTO (umbral {R.u})", "pasa": d["REINTEGRAR"],
         "numero_clave": "REINTEGRAR" if d["REINTEGRAR"] else "NO REINTEGRAR", "hoja": "H_decision"}]
    return pd.DataFrame(filas)


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


def sha256(ruta):
    import hashlib
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def escribir_md(R, S, sens, sens_B, sens_C, repro, hashes):
    d = R.dec
    dec = tabla_decision(R)
    fallan = [c for c in ("C1", "C2", "C3", "C4") if not d[c]]
    L = [f"# Resultados — pre-filtro de relevancia social bajo MAX (umbral {R.u})", "",
         "Generado por `experimentos/exp_prefiltro_max.py`; todas las tablas salen de "
         "`experimentos/resultados/exp_prefiltro_max.xlsx` (hoja indicada en cada sección). Pre-registro "
         "congelado antes de calcular: `experimentos/PREREG_prefiltro_max.md` (3849793). Log de consola: "
         "`experimentos/resultados/exp_prefiltro_max.log`. GPU única: "
         "`experimentos/exp_prefiltro_gpu_lugares.py` (`experimentos/resultados/exp_prefiltro_gpu_lugares.log`).", "",
         f"**Veredicto: {'REINTEGRAR' if d['REINTEGRAR'] else 'NO REINTEGRAR'}** (umbral {R.u}). "
         + (f"Fallan: {', '.join(fallan)}." if fallan else "Cumple C1–C4."), "",
         "## Criterios de decisión (hoja `H_decision`)", "",
         "| Criterio | Pasa | Número clave | Origen (hoja del Excel) |", "|---|---|---|---|"]
    for r in dec.itertuples():
        L.append(f"| {r.criterio} | {'sí' if r.pasa else 'no'} | {r.numero_clave} | `{r.hoja}` |")
    L += ["", "## Insumos y sanidad (hojas `S_sanidad`, `A_reproduccion`)", "",
          f"- Sanidad: {int(S['ok'].sum())} de {len(S)} chequeos OK (clasificación nacional 6/19/7 con 0.766/0.9233, "
          "lugares iguales al Excel del 1-sep, M1–M3 sin máscara iguales a `metricas_r2.xlsx` y `metricas_holdout.csv`).",
          "- Reproducción del A/B del 2026-08-31 (bloque A) contra `experimentos/resultados/exp_prefiltro_auc_indicador.xlsx`: "
          + ("**exacta**" if repro["ok"].all() else "**NO exacta**") + f", máxima diferencia {repro['max_abs_dif'].max():.1e} "
          "en las 11 columnas comparadas (incluido el bootstrap).",
          "- sha256 de los insumos: " + "; ".join(f"`{k}` `{v[:16]}…`" for k, v in hashes.items()) + ".", "",
          "## A. AUC por artículo contra plata, nacional (hoja `A_auc_plata`)", ""]
    L += md_tabla(R.A[R.A["tipo"].isin(["real", "absurdo"])][
        ["tipo", "indicador", "escala", "auc_sin", "auc_con", "delta", "ic95_low", "ic95_high", "retencion_positivos"]],
        ren={"auc_sin": "AUC sin", "auc_con": "AUC con", "ic95_low": "IC95 inf", "ic95_high": "IC95 sup",
             "retencion_positivos": "retención"})
    L += ["", "`delta` es la media del bootstrap (como en el script del 08-31). n de positivos/negativos de plata: "
          "871/9.935 (grupos étnicos) y 1.335/9.694 (grupos armados).", "",
          "## B. AUC por artículo contra los jueces, 759 juzgados en lugares o holdout (hoja `B_auc_jueces`)", ""]
    b = R.B[R.B["escala"] == "score_corregido"]
    L += md_tabla(b[["indicador", "n_pos", "n_neg", "suficiente_muestra", "auc_sin", "auc_con", "delta", "ic95_low",
                     "ic95_high", "delta_nula", "neta", "neta_ic95_low", "neta_ic95_high", "pasa_C4"]],
                  ren={"suficiente_muestra": "suficiente", "auc_sin": "AUC sin", "auc_con": "AUC con",
                       "ic95_low": "IC95 inf", "ic95_high": "IC95 sup", "delta_nula": "Δ nula", "neta": "Δ neta",
                       "neta_ic95_low": "neta inf", "neta_ic95_high": "neta sup", "pasa_C4": "pasa"})
    L += ["", "Score corregido (principal). La escala cruda está en la hoja. «Δ neta» = Δ del indicador − Δ de la nula, "
          "con remuestreo pareado; para contar en C4 su IC95% debe excluir cero.", "",
          "## C. M1–M3 del MAX con jueces (hojas `C_celdas`, `C_unidades`, `C_descriptivo`)", ""]
    L += md_tabla(R.C_unid[["unidad", "metrica", "elegible", "sin_mascara", "con_mascara_cota_inf", "con_mascara_cota_sup",
                            "delta_cota_inf", "ic95_low", "ic95_high", "delta_nula", "neta_ic95_low", "cobertura_con",
                            "pasa_C4"]],
                  ren={"sin_mascara": "sin", "con_mascara_cota_inf": "con (cota inf)", "con_mascara_cota_sup": "con (cota sup)",
                       "delta_cota_inf": "Δ cota inf", "ic95_low": "IC95 inf", "ic95_high": "IC95 sup", "delta_nula": "Δ nula",
                       "neta_ic95_low": "neta inf", "cobertura_con": "cobertura con", "pasa_C4": "pasa"})
    cd = R.C_desc
    L += ["", f"Descriptivo: en las {cd['celdas_con_positivos']} celdas con positivos, M1+ pasa de {cd['M1plus_sin']:.4f} a "
          f"{cd['M1plus_con_low']:.4f} y M2+ de {cd['M2plus_sin']:.4f} a {cd['M2plus_con_low']:.4f}; violaciones de M3 "
          f"(20 celdas de los lugares): {cd['M3_viol_sin_20lugares']} sin máscara, {cd['M3_viol_con_20lugares']} con máscara.", ""]
    cc = R.C_celdas
    cambia = cc[(cc["k_sin"] != cc["k_con"]) | (cc["M1_low_sin"] != cc["M1_low_con"]) | (cc["M2_low_sin"] != cc["M2_low_con"])
                | ((cc["max_sin"] - cc["max_con"]).abs() > 1e-9)]
    L += [f"Celdas donde la máscara cambia algo (k, M1, M2 o MAX): {len(cambia)} de {len(cc)}.", ""]
    L += md_tabla(cambia[["indicador", "lugar", "n_positivos", "pasan_filtro", "n_articulos", "k_sin", "k_con", "M1_low_sin",
                          "M1_low_con", "M2_low_sin", "M2_low_con", "max_sin", "max_con", "cobertura_con"]],
                  ren={"M1_low_sin": "M1 sin", "M1_low_con": "M1 con", "M2_low_sin": "M2 sin", "M2_low_con": "M2 con",
                       "max_sin": "MAX sin", "max_con": "MAX con", "pasan_filtro": "pasan filtro"})
    L += ["", "## D. Control absurdo con `NULA_TEST` y la misma máscara (hojas `D_brecha_dep`, `D_brecha_lugar`, `D_escala_nula`)", "",
          f"- Brecha = radar real − MAX de la nula corregida. Δ brecha media con máscara: {R.gap_dep_delta:+.4f} en los 32 "
          f"departamentos (mediana {float(R.gap_dep['delta_brecha'].median()):+.4f}; la brecha baja en {R.gap_dep_baja}) y "
          f"{R.gap_lug_delta:+.4f} en los 4 lugares (baja en {R.gap_lug_baja}).",
          "- Departamentos con mayor Δ brecha: " + ", ".join(
              f"{i} {v:+.4f}" for i, v in R.gap_dep["delta_brecha"].sort_values(ascending=False).head(3).items())
          + "; con menor: " + ", ".join(
              f"{i} {v:+.4f}" for i, v in R.gap_dep["delta_brecha"].sort_values().head(3).items()) + ".", ""]
    L += md_tabla(R.gap_lug.reset_index().rename(columns={"index": "lugar"}),
                  ren={"null_max_sin": "MAX nula sin", "null_max_con": "MAX nula con", "brecha_sin": "brecha sin",
                       "brecha_con": "brecha con", "delta_brecha": "Δ brecha", "radar_sin": "radar sin",
                       "radar_con": "radar con"})
    L += ["", "Escala de la nula (media y proporción > 0.9, cruda y corregida):", ""]
    L += md_tabla(R.D_escala[R.D_escala["grupo"] == "total"][["ambito", "mascara", "n", "media_cruda", "prop_cruda_gt09",
                                                             "media_corregida", "prop_corregida_gt09"]],
                  ren={"prop_cruda_gt09": "prop cruda > 0.9", "prop_corregida_gt09": "prop corregida > 0.9"})
    L += ["", "## E. Radar nacional MAX, 32 departamentos (hojas `E_radar_nacional`, `E_artefacto_tamano`)", ""]
    L += md_tabla(R.E.drop(columns=[c for c in ("anclas_rotas_lista", "nota") if c in R.E.columns]))
    L += ["", "Spearman del radar contra el número de artículos del departamento (artefacto de tamaño): "
          + ", ".join(f"{k.replace('_', ' ')} {v:+.3f}" for k, v in R.rho_tam.items()) + ".", "",
          "## F. Impacto (hojas `F_deptos`, `F_lugares`, `F_indicadores`, `F_celdas_005`)", "",
          f"- Artículos enmascarados: nacional {R.pct_masc_nac:.1%}; por lugar "
          + ", ".join(f"{k} {v:.1%}" for k, v in R.pct_masc_lug.items()) + ".",
          f"- Spearman del radar contra el oficial: {R.rho_sin:+.4f} sin máscara, {R.rho_con:+.4f} con máscara.",
          f"- Departamentos que cambian de clase: {R.n_cambian_vig} con los cortes vigentes en ambos radares; "
          f"{R.n_cambian_recal} de vigentes sin máscara a recalibrados con máscara"
          + (f" (cortes {R.cortes_recal[0]:.4f}/{R.cortes_recal[1]:.4f}): "
             + ", ".join(R.F_dep.index[R.F_dep['cambia_vig_recal']]) if R.cortes_recal else " (sin cortes válidos)") + ".",
          f"- Celdas departamento × indicador: {R.n_celdas_cambian} de 832 cambian su MAX; {R.n_celdas_005} lo hacen en "
          f"más de 0.05; {R.n_celdas_cero} pasan a 0.",
          f"- El radar baja en {int((R.F_dep['diferencia'] < -1e-9).sum())} de 32 departamentos; diferencia media "
          f"{R.F_dep['diferencia'].mean():+.4f}, mínima {R.F_dep['diferencia'].min():+.4f}.", "",
          "Los tres indicadores más afectados (media de |ΔMAX| entre departamentos):", ""]
    L += md_tabla(R.F_ind.head(3).reset_index().rename(columns={"index": "indicador"})[
        ["indicador", "media_abs_dMAX", "celdas_abs_dMAX_gt_0.05", "celdas_que_pasan_a_0"]],
        ren={"media_abs_dMAX": "media |ΔMAX|", "celdas_abs_dMAX_gt_0.05": "celdas > 0.05",
             "celdas_que_pasan_a_0": "pasan a 0"})
    L += ["", "Celdas con |ΔMAX| > 0.05:", ""]
    L += md_tabla(R.F_celdas)
    L += ["", "Radar por lugar (convención de producción):", ""]
    L += md_tabla(R.F_lug.reset_index().rename(columns={"index": "lugar"}),
                  ren={"pct_enmascarado": "% enmascarado", "radar_sin": "radar sin", "radar_con": "radar con",
                       "clase_sin_vigentes": "clase sin (vig.)", "clase_con_vigentes": "clase con (vig.)",
                       "clase_con_recalibrados": "clase con (recal.)"})
    L += ["", "## Sensibilidad a otros umbrales, descriptiva y sin efecto en la decisión (hojas `G_sensibilidad`, `G_sens_B`, `G_sens_C`)", ""]
    cols = ["umbral", "pct_enmascarado_nacional", "A_dAUC_cor_grupos_etnicos", "A_dAUC_cor_grupos_armados",
            "D_dBrecha_media_dep", "D_dBrecha_media_lugar", "E_spearman_con", "E_cortes_recal", "F_cambian_clase_recal",
            "F_celdas_dMAX_gt_005", "C1", "C2", "C3", "C4", "REINTEGRAR"]
    L += md_tabla(sens[cols], ren={"pct_enmascarado_nacional": "% enmasc. nac.", "A_dAUC_cor_grupos_etnicos": "A ΔAUC étnicos",
                                   "A_dAUC_cor_grupos_armados": "A ΔAUC armados", "D_dBrecha_media_dep": "D Δbrecha deptos",
                                   "D_dBrecha_media_lugar": "D Δbrecha lugares", "E_spearman_con": "E Spearman con",
                                   "E_cortes_recal": "E cortes recal.", "F_cambian_clase_recal": "F cambian clase (recal.)",
                                   "F_celdas_dMAX_gt_005": "F celdas > 0.05"})
    L += ["", "ΔAUC por artículo contra los jueces (score corregido) por umbral:", ""]
    sb = sens_B[(sens_B["escala"] == "score_corregido") & sens_B["auc_sin"].notna()]
    L += md_tabla(sb[["umbral", "indicador", "n_pos", "delta", "ic95_low", "ic95_high", "delta_nula", "neta_ic95_low", "pasa_C4"]],
                  ren={"ic95_low": "IC95 inf", "ic95_high": "IC95 sup", "delta_nula": "Δ nula", "neta_ic95_low": "neta inf",
                       "pasa_C4": "pasa"})
    L += ["", "Δ de M1/M2 (cota inferior) por umbral:", ""]
    L += md_tabla(sens_C[["umbral", "unidad", "metrica", "sin_mascara", "con_mascara_cota_inf", "delta_cota_inf", "ic95_low",
                          "ic95_high", "neta_ic95_low", "pasa_C4"]],
                  ren={"sin_mascara": "sin", "con_mascara_cota_inf": "con (cota inf)", "delta_cota_inf": "Δ",
                       "ic95_low": "IC95 inf", "ic95_high": "IC95 sup", "neta_ic95_low": "neta inf", "pasa_C4": "pasa"})
    with open(SALIDA_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    solo_sanidad = len(sys.argv) > 1 and sys.argv[1] == "sanidad"
    print("Cargando datos...")
    D = cargar()
    print(f"  nacional {len(D.nac)} | lugares {len(D.l)} | juzgados {len(D.juzgados)}")

    print("\n=== S. Sanidad (bloqueante) ===")
    S = sanidad(D)
    print(f"\n=== A. Reproduccion exacta del A/B del 2026-08-31 (umbral {UMBRAL}, semilla {SEMILLA_A}) ===")
    plata = etiquetas_plata(D)
    A85 = bloque_A(UMBRAL, D, plata)
    ok_repro, repro = repro_A(A85)
    if not S["ok"].all() or not ok_repro:
        os.makedirs(os.path.dirname(SALIDA_XLSX), exist_ok=True)
        with pd.ExcelWriter("experimentos/resultados/exp_prefiltro_max_PARADA.xlsx") as w:
            S.to_excel(w, sheet_name="S_sanidad", index=False)
            repro.to_excel(w, sheet_name="A_reproduccion", index=False)
        sys.exit("\nPARADA: la sanidad o la reproduccion de A no cumplen el pre-registro. "
                 "Ver experimentos/resultados/exp_prefiltro_max_PARADA.xlsx")
    print("\nSanidad y reproduccion de A: OK")
    if solo_sanidad:
        return

    J = tabla_juzgados(D)
    print(f"\nJuzgados en lugares o holdout: {J.n} | positivos: "
          + ", ".join(f"{i[:12]}={int(J.y[i].sum())}" for i in IND5))
    places = armar_lugares(D)

    print(f"\n=== Umbral principal {UMBRAL}: B-F y decision ===")
    R = correr(UMBRAL, D, plata, J, places, A=A85)   # A ya calculado y reproducido arriba
    sens_res = [R]
    for u in UMBRALES_SENS:
        print(f"  sensibilidad u={u} ...")
        sens_res.append(correr(u, D, plata, J, places))
    sens_res = sorted(sens_res, key=lambda r: r.u)
    sens = pd.DataFrame([resumen_umbral(r) for r in sens_res])
    sens_B = pd.concat([r.B.assign(umbral=r.u) for r in sens_res], ignore_index=True)
    sens_C = pd.concat([r.C_unid.assign(umbral=r.u) for r in sens_res], ignore_index=True)
    dec = tabla_decision(R)
    hashes = {"scores_prefiltro_lugares.pkl": sha256(GPU_L), "df_corpus_5lugares.pkl": sha256(CORPUS_L),
              "scores_v2_32deptos.pkl": sha256(V2NAC), "df_corpus_combinado_32deptos.pkl": sha256(CORPUS_NAC)}

    # ── Consola corta ───────────────────────────────────────────────────────
    print("\n--- A (score corregido) ---")
    a = R.A[(R.A["escala"] == "score_corregido")]
    print(a[["tipo", "indicador", "auc_sin", "auc_con", "delta", "ic95_low", "ic95_high"]].round(4).to_string(index=False))
    print("\n--- B (score corregido; nula) ---")
    b = R.B[R.B["escala"] == "score_corregido"]
    print(b[["indicador", "n_pos", "n_neg", "auc_sin", "auc_con", "delta", "ic95_low", "ic95_high", "delta_nula",
             "neta_ic95_low", "pasa_C4"]].round(4).to_string(index=False))
    print("\n--- C (unidades de decision) ---")
    print(R.C_unid[["unidad", "metrica", "elegible", "sin_mascara", "con_mascara_cota_inf", "con_mascara_cota_sup",
                    "delta_cota_inf", "ic95_low", "ic95_high", "delta_nula", "neta_ic95_low", "cobertura_con",
                    "pasa_C4"]].round(4).to_string(index=False))
    print("C descriptivo:", {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in R.C_desc.items()})
    print("\n--- E ---")
    print(R.E.round(4).to_string(index=False))
    print("Spearman(radar, n articulos):", {k: round(v, 3) for k, v in R.rho_tam.items()})
    print(f"\n--- F --- enmascarado nacional {R.pct_masc_nac:.1%}; lugares "
          + ", ".join(f"{k} {v:.1%}" for k, v in R.pct_masc_lug.items()))
    print(f"cambian de clase: {R.n_cambian_vig} (vigentes) / {R.n_cambian_recal} (recalibrados); "
          f"celdas que cambian: {R.n_celdas_cambian}; |dMAX|>0.05: {R.n_celdas_005}; a cero: {R.n_celdas_cero}")
    print(R.F_ind.head(5).round(4).to_string())
    print("\n--- Decision ---")
    print(dec[["criterio", "pasa", "numero_clave"]].to_string(index=False, max_colwidth=170))
    print("\n--- Sensibilidad ---")
    print(sens[["umbral", "pct_enmascarado_nacional", "A_dAUC_cor_grupos_etnicos", "D_dBrecha_media_dep",
                "D_dBrecha_media_lugar", "E_spearman_con", "E_cortes_recal", "F_cambian_clase_recal",
                "C1", "C2", "C3", "C4", "REINTEGRAR"]].round(4).to_string(index=False))

    # ── Excel ────────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(SALIDA_XLSX), exist_ok=True)
    with pd.ExcelWriter(SALIDA_XLSX, engine="openpyxl") as w:
        S.to_excel(w, sheet_name="S_sanidad", index=False)
        pd.DataFrame([{"archivo": k, "sha256": v} for k, v in hashes.items()]).to_excel(w, sheet_name="S_insumos", index=False)
        R.A.to_excel(w, sheet_name="A_auc_plata", index=False)
        repro.to_excel(w, sheet_name="A_reproduccion", index=False)
        R.B.to_excel(w, sheet_name="B_auc_jueces", index=False)
        R.C_celdas.to_excel(w, sheet_name="C_celdas", index=False)
        R.C_unid.to_excel(w, sheet_name="C_unidades", index=False)
        pd.DataFrame([R.C_desc]).to_excel(w, sheet_name="C_descriptivo", index=False)
        R.D_escala.to_excel(w, sheet_name="D_escala_nula", index=False)
        R.gap_dep.round(6).to_excel(w, sheet_name="D_brecha_dep")
        R.gap_lug.round(6).to_excel(w, sheet_name="D_brecha_lugar")
        R.E.to_excel(w, sheet_name="E_radar_nacional", index=False)
        pd.DataFrame([R.rho_tam]).to_excel(w, sheet_name="E_artefacto_tamano", index=False)
        R.F_dep.round(6).to_excel(w, sheet_name="F_deptos")
        R.F_lug.round(6).to_excel(w, sheet_name="F_lugares")
        R.F_ind.round(6).to_excel(w, sheet_name="F_indicadores")
        R.F_celdas.round(6).to_excel(w, sheet_name="F_celdas_005", index=False)
        sens.to_excel(w, sheet_name="G_sensibilidad", index=False)
        sens_B.to_excel(w, sheet_name="G_sens_B", index=False)
        sens_C.to_excel(w, sheet_name="G_sens_C", index=False)
        dec.to_excel(w, sheet_name="H_decision", index=False)
    escribir_md(R, S, sens, sens_B, sens_C, repro, hashes)
    print(f"\nGuardado -> {SALIDA_XLSX} y {SALIDA_MD}")


if __name__ == "__main__":
    main()
