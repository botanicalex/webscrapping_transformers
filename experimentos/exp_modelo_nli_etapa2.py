"""
Prueba del modelo NLI alternativo (SOLO PRUEBAS), etapa 2: experimentos/PREREG_modelo_nli.md §5
y §7.4. Todo offline, sobre experimentos/resultados/modelo_nli/scores_xlmr_lugares.pkl (modelo
nuevo) y datos/scores/scores_5ind_atomicas_lugares.pkl (modelo actual).

  python experimentos/exp_modelo_nli_etapa2.py lotes       # pool TREC + control -> lotes ciegos
  python experimentos/exp_modelo_nli_etapa2.py consolidar  # etiquetas_a + etiquetas_b -> referencia
  python experimentos/exp_modelo_nli_etapa2.py metricas    # M1-M4, M6, M2+, kappa, criterios 1-5

Candidata = la vigente con el modelo nuevo; base = la vigente con el modelo actual, las dos con
la formula de produccion s(h) = clip(clip(ent - sesgo, 0)*(1 - neu), 0, 1) y el sesgo de su
propio modelo. Referencia = SI/SI de juez-a y juez-b: las 940 de las rondas 1-2 mas las nuevas.
Salidas en experimentos/resultados/juicio_modelo_nli/ y experimentos/RESULTADOS_modelo_nli.md.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import exp_modelo_nli_etapa1 as E  # noqa: E402
import hipotesis_5ind_max as H  # noqa: E402
import hipotesis_base as HB  # noqa: E402
import silver  # noqa: E402
from exp_5ind_max_juicio import VALORES, kappa  # noqa: E402

DIR = "experimentos/resultados/juicio_modelo_nli"
CANDIDATAS_R2 = os.path.join(E.DIR_R2, "candidatas_r2.pkl")
FILTRO = os.path.join(E.DIR, "etapa1_filtro.xlsx")
LUGARES, GA, CORTE = E.LUGARES, E.GA, E.CORTE
SEMILLA = 20260924
TAM_LOTE = 40
TOP_POOL = 15
N_CONTROL = 40
MODELOS = ("nuevo", "actual")


def etapa2() -> list:
    """Indicadores que entran a la etapa 2 segun el filtro de la etapa 1 (§4)."""
    F = pd.read_excel(FILTRO, sheet_name="filtro")
    return F.loc[F["etapa2"].astype(bool), "indicador"].tolist()


def scores() -> pd.DataFrame:
    """s(h) de vigente, gemela y absurdo total con los dos modelos. La base se comprueba contra
    las columnas `vig` de candidatas_r2.pkl (§3)."""
    x, r1 = pd.read_pickle(E.SALIDA), pd.read_pickle(E.R1_SCORES)
    assert (x["url"].values == r1["url"].values).all()
    t = E.tabla_scores(x, r1)
    c2 = pd.read_pickle(CANDIDATAS_R2)
    assert (c2["url"].values == t["url"].values).all()
    for ind in H.INDICADORES_5:
        assert np.allclose(c2[f"{ind}__vig"], t[f"actual__{ind}__vig"])
        assert np.allclose(c2[f"{ind}__vig__abs"], t[f"actual__{ind}__vig_abs"])
    assert np.allclose(c2["ABSURDO_TOTAL"], t["actual__ABSURDO_TOTAL"])
    return t


def urls_lugar() -> dict:
    lug = pd.read_csv(os.path.join(E.DIR_R1, "url_lugares.csv"))
    return {l: set(lug.loc[lug["lugar"] == l, "url"]) for l in LUGARES}


def orden(sub: pd.DataFrame, c: str) -> pd.DataFrame:
    return sub[sub[c] > 0].sort_values([c, "url"], ascending=[False, True])


# ── lotes ────────────────────────────────────────────────────────────────────

def lotes():
    os.makedirs(os.path.join(DIR, "lotes"), exist_ok=True)
    inds = etapa2()
    t, ul = scores(), urls_lugar()
    juzg = set(E.referencia()["url"])
    pool = []
    for l in LUGARES:
        sub = t[t["url"].isin(ul[l])]
        for ind in inds:
            for r, u in enumerate(orden(sub, f"nuevo__{ind}__vig")["url"].head(TOP_POOL), 1):
                pool.append({"url": u, "indicador": ind, "lugar": l, "rango": r})
    pool = pd.DataFrame(pool)
    pool.to_csv(os.path.join(DIR, "pool.csv"), index=False)
    u_pool = set(pool["url"])
    nuevos = u_pool - juzg
    print(f"Indicadores de la etapa 2: {inds}")
    print(f"Pool: {len(u_pool)} URL unicas ({len(pool)} entradas); ya juzgadas {len(u_pool & juzg)}; "
          f"nuevas {len(nuevos)}")
    print(pool.assign(nueva=~pool["url"].isin(juzg)).groupby(["indicador", "lugar"])["nueva"]
          .agg(["size", "sum"]).rename(columns={"size": "top", "sum": "nuevas"}).to_string())

    rng = np.random.default_rng(SEMILLA)
    base = np.array(sorted(juzg))
    control = set(base[rng.permutation(len(base))[:N_CONTROL]])
    urls = np.array(sorted(nuevos | control))
    urls = urls[rng.permutation(len(urls))]
    mapa = pd.DataFrame({"id": [f"c{i:04d}" for i in range(len(urls))], "url": urls,
                         "origen": ["control" if u in control else "pool" for u in urls]})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)
    prem_l = pd.read_pickle(os.path.join(E.DIR_R1, "premisas_visibles.pkl"))
    prem_n = pd.read_pickle(os.path.join(E.DIR_HO, "premisas_visibles_nacional.pkl"))
    n = 0
    for n, ini in enumerate(range(0, len(mapa), TAM_LOTE), 1):
        with open(os.path.join(DIR, "lotes", f"lote_{n:02d}.jsonl"), "w", encoding="utf-8") as f:
            for u, i in zip(mapa["url"].iloc[ini: ini + TAM_LOTE], mapa["id"].iloc[ini: ini + TAM_LOTE]):
                p = prem_l[u] if u in prem_l.index else prem_n[u]
                f.write(json.dumps({"id": i, "premisa": p}, ensure_ascii=False) + "\n")
    print(f"{len(mapa)} articulos ({len(nuevos)} nuevos + {len(control)} control) -> {n} lotes de "
          f"<= {TAM_LOTE} en {DIR}/lotes")


# ── consolidar ───────────────────────────────────────────────────────────────

def _leer(carpeta: str) -> pd.DataFrame:
    filas = []
    d = os.path.join(DIR, carpeta)
    for fn in sorted(os.listdir(d)):
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    o = json.loads(linea)
                    fila = {"id": o["id"]}
                    for ind in H.INDICADORES_5:
                        v = o[ind][0].strip().upper().replace("SÍ", "SI")
                        assert v in VALORES, (fn, o["id"], ind, v)
                        fila[ind] = v
                    filas.append(fila)
    return pd.DataFrame(filas).drop_duplicates("id").set_index("id")


def consolidar():
    mapa = pd.read_csv(os.path.join(DIR, "mapa_ids.csv")).set_index("id")
    A, B = _leer("etiquetas_a"), _leer("etiquetas_b")
    faltan = (set(mapa.index) - set(A.index)) | (set(mapa.index) - set(B.index))
    assert not faltan, f"faltan {len(faltan)} ids: {sorted(faltan)[:5]}"
    ref = pd.DataFrame({"url": mapa["url"], "origen": mapa["origen"]})
    for ind in H.INDICADORES_5:
        sa, sb = A.loc[mapa.index, ind] == "SI", B.loc[mapa.index, ind] == "SI"
        ref[ind] = (sa & sb).astype(int).values
        ref[ind + "__a"] = A.loc[mapa.index, ind].values
        ref[ind + "__b"] = B.loc[mapa.index, ind].values
    ref.reset_index().to_csv(os.path.join(DIR, "referencia.csv"), index=False)
    nuevos, ctl = ref[ref["origen"] != "control"], ref[ref["origen"] == "control"]
    antes = E.referencia().set_index("url").loc[ctl["url"]]
    print(f"{len(nuevos)} nuevos + {len(ctl)} control -> {DIR}/referencia.csv")
    print(f"{'indicador':34s} {'SI_a':>5s} {'SI_b':>5s} {'SI/SI':>6s} {'kappa':>6s} | control: "
          f"{'acuerdo':>7s} {'SI/SI antes':>11s} {'SI/SI ahora':>11s}")
    for ind in H.INDICADORES_5:
        sa, sb = nuevos[ind + "__a"] == "SI", nuevos[ind + "__b"] == "SI"
        acu = float((ctl[ind].values == antes[ind].values).mean())
        print(f"{ind:34s} {sa.sum():5d} {sb.sum():5d} {nuevos[ind].sum():6d} {kappa(sa, sb):6.2f} | "
              f"{acu:7.2f} {int(antes[ind].sum()):11d} {int(ctl[ind].sum()):11d}")


# ── metricas ─────────────────────────────────────────────────────────────────

def referencia_ampliada() -> pd.DataFrame:
    r = pd.read_csv(os.path.join(DIR, "referencia.csv"))
    r = r[r["origen"] != "control"].assign(ronda="modelo_nli")
    ref = pd.concat([E.referencia().assign(ronda="rondas_1_2"), r], ignore_index=True)
    assert ref["url"].is_unique
    return ref


def por_modelo(t, ref, ul, ind, m, plata) -> dict:
    """M1-M4, M6 y M2+ de la vigente de `ind` con el modelo `m`."""
    c, cg, ct = f"{m}__{ind}__vig", f"{m}__{ind}__vig_abs", f"{m}__ABSURDO_TOTAL"
    pos = set(ref.loc[ref[ind] == 1, "url"])
    f, m1, m2, m2p, m3 = {}, [], [], [], []
    for l in LUGARES:
        sub = t[t["url"].isin(ul[l])]
        pl = pos & ul[l]
        o = orden(sub, c)
        mx = float(sub[c].max())
        am = sub.sort_values([c, "url"], ascending=[False, True])["url"].iloc[0]
        k = min(10, len(o))
        if k == 0:
            p, ok1 = (1.0 if not pl else 0.0), not pl
        else:
            assert o["url"].head(k).isin(ref["url"]).all(), ("top-10 sin juzgar", c, l)
            p, ok1 = float(np.mean([u in pl for u in o["url"].head(k)])), am in pl
        viol = (not pl and mx >= CORTE) or (bool(pl) and mx < CORTE)
        gm, tot = float(sub[cg].max()), float(sub[ct].max())
        m1.append(ok1); m2.append(p); m3.append(viol)
        if pl:
            m2p.append(p)
        f.update({f"M1_{l}": ok1, f"M2_{l}": round(p, 3), f"M3viol_{l}": viol, f"npos_{l}": len(pl),
                  f"max_{l}": round(mx, 4), f"abs_{l}": round(gm, 4), f"tot_{l}": round(tot, 4),
                  f"prop_abs_{l}": round(float((sub[cg] > CORTE).mean()), 4),
                  f"razon_abs_{l}": round(gm / mx, 3) if mx > 0 else np.nan, f"top1_{l}": am})
    f.update({"M1_n": int(sum(m1)), "M2": round(float(np.mean(m2)), 3),
              "M2mas": round(float(np.mean(m2p)), 3) if m2p else np.nan, "M3_viol": int(sum(m3)),
              "M6_auc": round(silver.auc(t[c].values, plata), 4) if ind == GA else np.nan})
    return f


def metricas():
    inds = etapa2()
    t, ul, ref = scores(), urls_lugar(), referencia_ampliada()
    corpus = pd.read_pickle(E.CORPUS).reset_index(drop=True)
    assert (corpus["url"].values == t["url"].values).all()
    plata = silver.etiquetar(corpus, HB.KEYWORDS_SILVER[GA])["label"].values
    en_lug = set().union(*ul.values())
    ref_l = ref[ref["url"].isin(en_lug)]
    filas = []
    for ind in inds:
        kap = kappa(ref_l[ind + "__a"] == "SI", ref_l[ind + "__b"] == "SI")
        for m in MODELOS:
            filas.append({"indicador": ind, "modelo": m, "kappa": round(kap, 3),
                          **por_modelo(t, ref, ul, ind, m, plata)})
    M = pd.DataFrame(filas)
    # §3: la base (modelo actual) reproduce la ronda 2.
    b_ga = M[(M.indicador == GA) & (M.modelo == "actual")]
    if len(b_ga):
        assert abs(b_ga["M6_auc"].iloc[0] - 0.788) < 5e-4, b_ga["M6_auc"].iloc[0]

    for ind in inds:
        b = M[(M.indicador == ind) & (M.modelo == "actual")].iloc[0]
        i = M.index[(M.indicador == ind) & (M.modelo == "nuevo")][0]
        r = M.loc[i]
        con_pos = [l for l in LUGARES if r[f"npos_{l}"] > 0]
        c1 = r["M2"] >= max(0.60, b["M2"] + 0.20)
        c2 = r["M1_n"] >= 3 or (len(con_pos) > 0 and all(r[f"M1_{l}"] for l in con_pos))
        c3 = all(not r[f"M3viol_{l}"] or b[f"M3viol_{l}"] for l in LUGARES)
        c4 = all(r[f"abs_{l}"] < CORTE and r[f"abs_{l}"] <= b[f"abs_{l}"] + 0.05
                 and r[f"tot_{l}"] <= b[f"tot_{l}"] + 0.05 for l in LUGARES)
        c5 = (r["M6_auc"] >= b["M6_auc"] - 0.02) if ind == GA else True
        ck = bool(r["kappa"] >= 0.4)
        M.loc[i, ["c1", "c2", "c3", "c4", "c5", "c_kappa"]] = [c1, c2, c3, c4, c5, ck]
        M.loc[i, "pasa_1a5"] = bool(c1 and c2 and c3 and c4 and c5 and ck)
    os.makedirs(DIR, exist_ok=True)
    M.to_excel(os.path.join(DIR, "metricas_modelo_nli.xlsx"), index=False)

    ex = ref[ref["exclusion_beneficios_economicos"] == 1]
    for ind in inds:
        s = M[M.indicador == ind]
        n, a = s[s.modelo == "nuevo"].iloc[0], s[s.modelo == "actual"].iloc[0]
        print(f"{ind[:26]:26s} kappa={n.kappa:.2f} M2 nuevo {n.M2:.2f} / actual {a.M2:.2f}; "
              f"M1 {n.M1_n}/{a.M1_n}; M3 {n.M3_viol}/{a.M3_viol}; c1-5 "
              + "".join("s" if n[c] else "n" for c in ("c1", "c2", "c3", "c4", "c5", "c_kappa"))
              + f" -> {'PASA 1-5' if n.pasa_1a5 else 'no pasa'}")
    print(f"Exclusion SI/SI en total: {len(ex)} (por ronda {ex['ronda'].value_counts().to_dict()})")
    A = absurdo_total(t, ul, corpus)
    print("Criterio 4, absurdo total por lugar (tope = actual + 0.05):")
    print(A.to_string(index=False))
    escribir_md(M, inds, ref, ex, corpus, A)


def absurdo_total(t, ul, corpus) -> pd.DataFrame:
    """Parte del criterio 4 comun a todos los indicadores: MAX del absurdo total por lugar con los
    dos modelos, articulos del modelo nuevo por encima del tope y el que fija su MAX."""
    tit = corpus.set_index("url")["titulo"]
    filas = []
    for l in LUGARES:
        sub = t[t["url"].isin(ul[l])]
        n, a = sub["nuevo__ABSURDO_TOTAL"], sub["actual__ABSURDO_TOTAL"]
        tope = float(a.max()) + 0.05
        am = sub.sort_values(["nuevo__ABSURDO_TOTAL", "url"], ascending=[False, True])["url"].iloc[0]
        filas.append({"lugar": l, "max_actual": round(float(a.max()), 4), "tope": round(tope, 4),
                      "max_nuevo": round(float(n.max()), 4), "n_sobre_tope": int((n > tope).sum()),
                      "n_articulos": len(sub), "top1_nuevo": tit.get(am, "")})
    return pd.DataFrame(filas)


def escribir_md(M, inds, ref, ex, corpus, A):
    ok = lambda x: "sí" if x else "no"  # noqa: E731
    tit = corpus.set_index("url")["titulo"]
    r = pd.read_csv(os.path.join(DIR, "referencia.csv"))
    n_r = r["origen"].value_counts().to_dict()
    L = ["# Resultados — prueba del modelo NLI alternativo, etapa 2 (4 lugares, SOLO PRUEBAS)", "",
         "Generado por `experimentos/exp_modelo_nli_etapa2.py metricas`; detalle en "
         "`experimentos/resultados/juicio_modelo_nli/metricas_modelo_nli.xlsx`. Pre-registro "
         "`experimentos/PREREG_modelo_nli.md` (congelado). Etapa 1: "
         "`experimentos/resultados/modelo_nli/etapa1_filtro.log`.", "",
         "Una sola variable: el modelo. **Nuevo** = `vicgalle/xlm-roberta-large-xnli-anli` (85981da); "
         "**actual** = `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (producción). "
         "Misma frase vigente, misma fórmula, sesgo de cada modelo, MAX por lugar.", "",
         f"Referencia: {len(ref)} artículos juzgados (940 de las rondas 1–2 + "
         f"{n_r.get('pool', 0)} nuevos del pool de esta etapa). Los {n_r.get('control', 0)} de control "
         "conservan su etiqueta anterior.", "",
         "M2 = precisión@10 media en los 4 lugares (A/M/O/P = Antioquia/Maicao/Oicatá/Paraguachón); "
         "M2+ = solo lugares con positivos; M3 = violaciones de coherencia del MAX; gemela = frase con "
         "«osos polares»; absurdo total = «colonias de osos polares».", ""]
    for ind in inds:
        s = M[M.indicador == ind]
        n = s[s.modelo == "nuevo"].iloc[0]
        npos = "/".join(str(n[f"npos_{l}"]) for l in LUGARES)
        L += [f"## `{ind}` — kappa {n.kappa:.2f} — positivos {npos} — "
              f"{'CUMPLE los criterios 1–5' if n.pasa_1a5 else 'no cumple los criterios 1–5'}", "",
              "| modelo | M2 | M2+ | M1 (de 4) | M3 viol | máx (A/M/O/P) | máx gemela (A/M/O/P) | "
              "absurdo total (A/M/O/P) | M6 |", "|---|---|---|---|---|---|---|---|---|"]
        for _, x in s.iterrows():
            f3 = lambda p: "/".join(f"{x[f'{p}_{l}']:.2f}" for l in LUGARES)  # noqa: E731
            m2p = "—" if pd.isna(x.M2mas) else f"{x.M2mas:.2f}"
            m6 = "—" if pd.isna(x.M6_auc) else f"{x.M6_auc:.3f}"
            L.append(f"| {x.modelo} | {x.M2:.2f} | {m2p} | {x.M1_n} | {x.M3_viol} | {f3('max')} | "
                     f"{f3('abs')} | {f3('tot')} | {m6} |")
        a = s[s.modelo == "actual"].iloc[0]
        f4 = lambda x: "/".join(f"{x[f'prop_abs_{l}']:.3f}" for l in LUGARES)  # noqa: E731
        L += ["", f"M4 (proporción de artículos con gemela > {CORTE}, A/M/O/P): nuevo {f4(n)}; "
              f"actual {f4(a)} (solo reporte).", "",
              "Criterios (modelo nuevo frente al actual): " + ", ".join(
            f"{c} {ok(n[c])}" for c in ("c1", "c2", "c3", "c4", "c5")) + f", kappa ≥ 0.4 {ok(n.c_kappa)}.", "",
            "Artículo que fija el MAX, actual → nuevo:"]
        for l in LUGARES:
            ua, un = a[f"top1_{l}"], n[f"top1_{l}"]
            pa, pn = ("positivo" if ref.set_index("url").loc[u, ind] == 1 else "negativo"
                      if u in set(ref["url"]) else "sin juzgar" for u in (ua, un))
            L.append(f"- {l}: «{tit.get(ua, '')}» ({a[f'max_{l}']:.2f}, {pa}) → «{tit.get(un, '')}» "
                     f"({n[f'max_{l}']:.2f}, {pn})")
        L.append("")
    L += ["## Criterio 4: absurdo total por lugar (común a los dos indicadores)", "",
          "| lugar | máx actual | tope (actual + 0.05) | máx nuevo | artículos nuevos > tope | "
          "artículo que fija el máx nuevo |", "|---|---|---|---|---|---|"]
    for _, x in A.iterrows():
        L.append(f"| {x.lugar} | {x.max_actual:.4f} | {x.tope:.4f} | {x.max_nuevo:.4f} | "
                 f"{x.n_sobre_tope} de {x.n_articulos} | «{x.top1_nuevo}» |")
    L += ["", "## Exclusión de beneficios económicos (solo reporte, §4)", "",
          f"SÍ/SÍ en total: **{len(ex)}** ({'≥ 5: decide el usuario' if len(ex) >= 5 else 'sigue no medible'}).", ""]
    ctl = r[r["origen"] == "control"]
    antes = E.referencia().set_index("url").loc[ctl["url"]]
    L += ["## Control entre rondas (40 artículos ya juzgados, solo reporte)", "",
          "| indicador | acuerdo SI/SI | SI/SI antes | SI/SI ahora |", "|---|---|---|---|"]
    for ind in H.INDICADORES_5:
        L.append(f"| `{ind}` | {float((ctl[ind].values == antes[ind].values).mean()):.2f} | "
                 f"{int(antes[ind].sum())} | {int(ctl[ind].sum())} |")
    with open("experimentos/RESULTADOS_modelo_nli.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    {"lotes": lotes, "consolidar": consolidar, "metricas": metricas}[sys.argv[1]]()
