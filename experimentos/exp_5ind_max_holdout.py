"""
F7 del plan 5ind MAX (experimentos/PREREG_5ind_MAX.md §4, criterio 6), paso 2: holdout
Cauca, Choco, Cundinamarca sobre el corpus nacional. Todo offline (sin GPU).

  python experimentos/exp_5ind_max_holdout.py pool        # pool TREC + lotes ciegos
  python experimentos/exp_5ind_max_holdout.py m4          # control absurdo a escala nacional (reporte)
  python experimentos/exp_5ind_max_holdout.py consolidar  # etiquetas_a + etiquetas_b -> referencia, kappa
  python experimentos/exp_5ind_max_holdout.py metricas    # M1-M4 de V01/V08 grupos, criterio 6, exclusion

Scores: vigente, sesgo y absurdo total (= NULA_TEST) de datos/scores/scores_v2_32deptos.pkl
(union por posicion con el corpus combinado); gemela de objeto absurdo de grupos armados de
datos/scores/scores_5ind_atomicas_nacional.pkl; compuerta F5 sobre la premisa visible
nacional. Pool: por departamento, top-15 (score > 0, desempate por URL) de V01 y V08 de
grupos armados y de V01 de exclusion (esta ultima solo para buscar positivos).
Lotes: semilla 20260922, ids opacos "h0000" (distintos de los "a0000" del corpus de lugares).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
import exp_5ind_max_juicio as J  # noqa: E402

CORPUS = "datos/corpus/df_corpus_combinado_32deptos.pkl"
V2NAC = "datos/scores/scores_v2_32deptos.pkl"
ABSNAC = "datos/scores/scores_5ind_atomicas_nacional.pkl"
DIR = "experimentos/resultados/juicio_5ind_holdout"
HOLDOUT = ["Cauca", "Choco", "Cundinamarca"]
GA, EX = "presencia_grupos_armados", "exclusion_beneficios_economicos"
POOL = [(GA, "V01"), (GA, "V08"), (EX, "V01")]
TOP_POOL = 15
CORTE = 0.766


def s(d: pd.DataFrame, col: str, sesgo) -> np.ndarray:
    ent, neu = d[f"ent_{col}"].values.astype(float), d[f"neu_{col}"].values.astype(float)
    return np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)


def scores_nacionales() -> pd.DataFrame:
    """url, departamento (normalizado) y las columnas de variante/controles, 11.439 filas."""
    corpus = pd.read_pickle(CORPUS).reset_index(drop=True)
    v2 = pd.read_pickle(V2NAC).reset_index(drop=True)
    ab = pd.read_pickle(ABSNAC)
    assert len(v2) == len(corpus) == len(ab) and (ab["url"].values == corpus["url"].values).all()
    prem = pd.read_pickle(os.path.join(DIR, "premisas_visibles_nacional.pkl")).loc[corpus["url"]]
    g = np.asarray(H.compuerta(prem.values, GA))
    sesgo = v2["sesgo"].values
    vig, tot = s(v2, GA, sesgo), s(v2, "NULA_TEST", sesgo)
    vig_abs = s(ab, f"{GA}__vig_abs", sesgo)
    return pd.DataFrame({
        "url": corpus["url"].values,
        "departamento": corpus["departamento"].map(lambda x: H.normalizar(x).title()).values,
        f"{GA}__V01": vig, f"{GA}__V01__abs": vig_abs, f"{GA}__V01__tot": tot,
        f"{GA}__V08": vig * g, f"{GA}__V08__abs": vig_abs * g, f"{GA}__V08__tot": tot * g,
        f"{EX}__V01": s(v2, EX, sesgo),
        "g_grupos": g,
    })


def orden(sub: pd.DataFrame, c: str) -> pd.DataFrame:
    return sub.sort_values([c, "url"], ascending=[False, True])


def pool():
    var = scores_nacionales()
    var.to_pickle(os.path.join(DIR, "variantes_nacional.pkl"))
    filas = []
    for dep in HOLDOUT:
        sub = var[var["departamento"] == dep]
        assert len(sub), dep
        for ind, v in POOL:
            c = f"{ind}__{v}"
            top = orden(sub[sub[c] > 0], c).head(TOP_POOL)
            filas += [{"url": u, "indicador": ind, "lugar": dep, "variante": v, "rango": r}
                      for r, u in enumerate(top["url"], 1)]
    p = pd.DataFrame(filas)
    p.to_csv(os.path.join(DIR, "pool.csv"), index=False)
    print("Articulos por departamento (n) y entradas del pool por variante:")
    print(p.pivot_table(index="lugar", columns=["indicador", "variante"], values="url", aggfunc="count")
          .rename(columns=lambda x: x[:8]).to_string())
    print(f"n corpus: {var['departamento'].value_counts().reindex(HOLDOUT).to_dict()}")
    print(f"Pool: {p['url'].nunique()} articulos unicos")

    # Lotes ciegos: mismo procedimiento que F4, ids opacos con prefijo propio.
    prem = pd.read_pickle(os.path.join(DIR, "premisas_visibles_nacional.pkl"))
    urls = np.array(sorted(p["url"].unique()))
    urls = urls[np.random.default_rng(J.SEMILLA).permutation(len(urls))]
    mapa = pd.DataFrame({"id": [f"h{i:04d}" for i in range(len(urls))], "url": urls})
    mapa.to_csv(os.path.join(DIR, "mapa_ids.csv"), index=False)
    d = os.path.join(DIR, "lotes")
    os.makedirs(d, exist_ok=True)
    n = 0
    for n, ini in enumerate(range(0, len(mapa), J.TAM_LOTE), 1):
        with open(os.path.join(d, f"lote_{n:02d}.jsonl"), "w", encoding="utf-8") as f:
            for _, r in mapa.iloc[ini: ini + J.TAM_LOTE].iterrows():
                f.write(json.dumps({"id": r["id"], "premisa": prem[r["url"]]}, ensure_ascii=False) + "\n")
    print(f"{len(mapa)} articulos -> {n} lotes de <= {J.TAM_LOTE} en {d}")


def m4():
    """M4 a escala nacional (32 departamentos): MAX de la variante, de su gemela de objeto
    absurdo y del absurdo total, para V01 y V08 de grupos armados. Solo reporte."""
    var = scores_nacionales()
    c = f"{GA}__"
    t = var.groupby("departamento")[[c + v + x for v in ("V01", "V08") for x in ("", "__abs", "__tot")]].max()
    t.columns = [x.replace(c, "") for x in t.columns]
    t.to_csv(os.path.join(DIR, "m4_nacional.csv"))
    art = {v: {x: float((var[c + v + x] > CORTE).mean()) for x in ("", "__abs", "__tot")} for v in ("V01", "V08")}
    for v in ("V01", "V08"):
        print(f"{v}: deptos con MAX > {CORTE}: variante {int((t[v] > CORTE).sum())}/32, "
              f"objeto absurdo {int((t[v + '__abs'] > CORTE).sum())}/32, absurdo total "
              f"{int((t[v + '__tot'] > CORTE).sum())}/32 | MAX abs mediana {t[v + '__abs'].median():.3f} "
              f"max {t[v + '__abs'].max():.3f} | articulos > {CORTE}: var {art[v]['']:.2%}, "
              f"abs {art[v]['__abs']:.2%}, tot {art[v]['__tot']:.2%}")
    d = t["V08__abs"] - t["V01__abs"]
    print(f"V08 - V01 en el MAX de objeto absurdo por depto: max {d.max():+.4f} (nunca sube si <= 0)")
    print("Deptos con objeto absurdo > corte (V01 -> V08):")
    print(t.loc[(t["V01__abs"] > CORTE) | (t["V08__abs"] > CORTE), ["V01", "V01__abs", "V08", "V08__abs"]]
          .round(3).to_string())


def consolidar():
    J.DIR = DIR  # misma consolidacion y kappa que F4, sobre la carpeta del holdout
    J.consolidar()


def metricas():
    var = pd.read_pickle(os.path.join(DIR, "variantes_nacional.pkl"))
    ref = pd.read_csv(os.path.join(DIR, "referencia.csv"))
    pool_ = pd.read_csv(os.path.join(DIR, "pool.csv"))
    titulo = pd.read_pickle(CORPUS).set_index("url")["titulo"]
    filas = []
    for dep in HOLDOUT:
        sub = var[var["departamento"] == dep]
        pos = set(ref.loc[ref["url"].isin(pool_.loc[pool_["lugar"] == dep, "url"]) & (ref[GA] == 1), "url"])
        for v in ("V01", "V08"):
            c = f"{GA}__{v}"
            o = orden(sub[sub[c] > 0], c)
            k = min(10, len(o))
            if k == 0:
                m2, m1, u_max, mx = (1.0 if not pos else 0.0), not pos, "", 0.0
            else:
                m2 = float(np.mean([u in pos for u in o["url"].head(k)]))
                u_max, mx = o["url"].iloc[0], float(o[c].iloc[0])
                m1 = u_max in pos
            filas.append({"lugar": dep, "variante": v, "n": len(sub), "n_score>0": len(o), "npos": len(pos),
                          "M1": m1, "M2": round(m2, 3), "max": round(mx, 4),
                          "M3viol": (not pos and mx >= CORTE) or (bool(pos) and mx < CORTE),
                          "max_abs": round(sub[c + "__abs"].max(), 4), "max_tot": round(sub[c + "__tot"].max(), 4),
                          "top1": str(titulo.get(u_max, ""))[:70]})
    M = pd.DataFrame(filas)
    M.to_csv(os.path.join(DIR, "metricas_holdout.csv"), index=False)
    print(M.drop(columns="top1").to_string(index=False))
    for _, r in M.iterrows():
        print(f"  top1 {r.lugar} {r.variante}: {r.top1}")
    m2 = M.groupby("variante")["M2"].mean()
    c6 = bool(m2["V08"] >= 0.50 and m2["V08"] >= m2["V01"])
    print(f"M2 medio holdout: V01 {m2['V01']:.3f}  V08 {m2['V08']:.3f}  -> criterio 6 "
          f"{'CUMPLE' if c6 else 'NO CUMPLE'} (V08 >= 0.50 y >= V01)")

    # Clausula de exclusion y positivos de los otros indicadores (insumo de la 2a ronda).
    ref = ref.merge(pool_.drop_duplicates("url")[["url", "lugar"]], on="url")
    print("SI/SI por indicador y departamento del holdout:")
    print(ref.groupby("lugar")[H.INDICADORES_5].sum().rename(columns=lambda x: x[:14]).to_string())
    ex = ref[ref[EX] == 1]
    print(f"Exclusion: {len(ex)} SI/SI en el holdout"
          + ("".join(f"\n  {r.lugar}: {str(titulo.get(r.url, ''))[:80]}" for r in ex.itertuples())))


if __name__ == "__main__":
    {"pool": pool, "m4": m4, "consolidar": consolidar, "metricas": metricas}[sys.argv[1]]()
