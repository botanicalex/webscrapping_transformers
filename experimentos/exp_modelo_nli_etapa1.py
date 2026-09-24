"""
Prueba del modelo NLI alternativo (SOLO PRUEBAS), etapa 1: experimentos/PREREG_modelo_nli.md
§1, §2, §4 y §7.3. Una sola variable, el modelo: premisa = solo `texto`, truncation=True,
max_length=512; hipotesis, formula, sesgo y MAX de produccion.

  python experimentos/exp_modelo_nli_etapa1.py etiquetas   # modelo nuevo: (2,1,0), pares, especiales
  python experimentos/exp_modelo_nli_etapa1.py lote        # modelo nuevo, lote 16 vs 8, 50 art.
  python experimentos/exp_modelo_nli_etapa1.py sanidad     # modelo de produccion, 300 art., lote elegido
  python experimentos/exp_modelo_nli_etapa1.py cobertura   # CPU: premisa del juez vs lo que ve el nuevo
  python experimentos/exp_modelo_nli_etapa1.py gpu         # 15 hipotesis x 1.647, con checkpoint
  python experimentos/exp_modelo_nli_etapa1.py filtro      # offline: filtro (a)/(b) y reportes

Regla 8: se guardan ent_, neu_, con_ SIN enmascarar; todo lo demas se calcula offline.
Salidas en experimentos/resultados/modelo_nli/ (los pkl no se versionan).
"""
import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # §1: modelo y tokenizador sin red

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_5ind_max as H  # noqa: E402
from nli_core import NLIScorer  # noqa: E402

MODELO_NUEVO = os.path.join(
    os.path.expanduser("~"), ".cache", "huggingface", "hub",
    "models--vicgalle--xlm-roberta-large-xnli-anli", "snapshots",
    "85981da85b85045fecd6e81e501767de7da370eb")
CORPUS = "datos/corpus/df_corpus_5lugares.pkl"
R1_SCORES = "datos/scores/scores_5ind_atomicas_lugares.pkl"
DIR = "experimentos/resultados/modelo_nli"
SALIDA = os.path.join(DIR, "scores_xlmr_lugares.pkl")
CHECKPOINT = os.path.join(DIR, "scores_xlmr_lugares.parcial.pkl")
DIR_R1 = "experimentos/resultados/juicio_5ind"
DIR_HO = "experimentos/resultados/juicio_5ind_holdout"
DIR_R2 = "experimentos/resultados/juicio_5ind_r2"
LUGARES = ["Antioquia", "Maicao", "Oicata", "Paraguachon"]
GA = "presencia_grupos_armados"
CORTE = 0.766
TOL = 1e-4
N_SANIDAD = 300
N_LOTE = 50
MAX_LENGTH = 512
ESPECIALES_XLMR = 4  # <s> A </s></s> B </s>
MAX_COBERTURA = 0.05   # §2: proporcion maxima de articulos que pierden mas de PERDIDA_TOL tokens
PERDIDA_TOL = 10
LOTE_ELEGIDO = os.path.join(DIR, "lote.txt")
DECISIVOS = ["rechazo_proyecto", "desplazamiento_forzado", "conflicto_territorial"]  # §4
EXCL = "exclusion_beneficios_economicos"
PAR_IGUAL = ("El alcalde inauguró un hospital nuevo en el municipio.",
             "El alcalde inauguró un hospital nuevo en el municipio.")
PAR_CONTRARIO = ("El alcalde inauguró un hospital nuevo en el municipio.",
                 "En el municipio no se inauguró ningún hospital.")


def hipotesis_etapa1() -> dict:
    """§4: 5 vigentes, 5 gemelas vig_abs, 4 NULAS_CALIBRACION y ABSURDO_TOTAL (15)."""
    out = {}
    for ind in H.INDICADORES_5:
        out[f"{ind}__vig"] = H.HIPOTESIS[ind]["vig"]
    for ind in H.INDICADORES_5:
        out[f"{ind}__vig_abs"] = H.HIPOTESIS[ind]["vig_abs"]
    out["ABSURDO_TOTAL"] = H.ABSURDO_TOTAL
    for i, h in enumerate(H.NULAS_CALIBRACION):
        out[f"NULA_CAL_{i}"] = h
    assert len(out) == 15 and len(set(out.values())) == 15
    return out


def textos_corpus():
    df = pd.read_pickle(CORPUS).reset_index(drop=True)
    return df, df["texto"].fillna("").astype(str).tolist()


def puntuar(scorer, textos, hip, bs):
    p = scorer.score(textos, hip, batch_size=bs, max_length=MAX_LENGTH, devolver_todo=True)
    return {k: np.asarray(p[v], dtype=np.float32)
            for k, v in (("ent", "entailment"), ("neu", "neutral"), ("con", "contradiction"))}


def s(ent, neu, sesgo):
    """Formula de produccion: clip(clip(ent - sesgo, 0) * (1 - neu), 0, 1)."""
    return np.clip(np.clip(ent.astype(float) - sesgo, 0, None) * (1 - neu.astype(float)), 0, 1)


# ── §1 sanidad del codigo y tamano de lote ───────────────────────────────────

def lote_elegido() -> int:
    with open(LOTE_ELEGIDO) as f:
        return int(f.read().strip())


def sanidad():
    """Modelo de produccion, los 300 articulos de `texto` mas largo (desempate por URL), vigente
    de grupos armados, mismo lote que la etapa 1: reproduce la ronda 1 con max|dif| < 1e-4."""
    df, textos = textos_corpus()
    r1 = pd.read_pickle(R1_SCORES)
    assert (r1["url"].values == df["url"].values).all()
    bs = lote_elegido()
    idx = (pd.DataFrame({"n": [len(t) for t in textos], "url": df["url"].values})
           .sort_values(["n", "url"], ascending=[False, True]).index[:N_SANIDAD].to_numpy())
    scorer = NLIScorer(verbose=True)
    t0 = time.time()
    p = puntuar(scorer, [textos[i] for i in idx], H.HIPOTESIS[GA]["vig"], bs)
    col = H.columna(GA, "vig")
    dif = max(float(np.abs(p[k] - r1[f"{k}_{col}"].values[idx]).max()) for k in p)
    n_trunc = sum(len(scorer.tokenizer(textos[i])["input_ids"]) > MAX_LENGTH for i in idx)
    print(f"SANIDAD modelo de produccion ({N_SANIDAD} art. mas largos, {n_trunc} truncados, {col}, "
          f"lote {bs}, {time.time()-t0:.0f} s): max|dif| = {dif:.1e} {'OK' if dif < TOL else 'FALLA'}")
    if dif >= TOL:
        sys.exit("PARADA: el script no aisla el modelo (pre-registro §1)")


def cargar_nuevo(verbose=True):
    assert os.path.isdir(MODELO_NUEVO), f"falta el modelo en {MODELO_NUEVO}"
    sc = NLIScorer(modelo=MODELO_NUEVO, verbose=verbose)
    assert (sc.label_ent, sc.label_neu, sc.label_con) == (2, 1, 0), sc.modelo.config.id2label
    return sc


def etiquetas():
    """§1: orden (2,1,0) resuelto por nombre, pares de control y 4 tokens especiales."""
    sc = cargar_nuevo()
    id2 = {int(k): str(v).lower() for k, v in sc.modelo.config.id2label.items()}
    assert "contrad" in id2[0] and "neutral" in id2[1] and "entail" in id2[2], id2
    pi = sc.score([PAR_IGUAL[0]], PAR_IGUAL[1], devolver_todo=True)
    pc = sc.score([PAR_CONTRARIO[0]], PAR_CONTRARIO[1], devolver_todo=True)
    tok = sc.tokenizer
    par = tok("a", "b")["input_ids"]
    n_esp = len(par) - len(tok("a", add_special_tokens=False)["input_ids"]) \
        - len(tok("b", add_special_tokens=False)["input_ids"])
    print(f"id2label {id2}; (ent, neu, con) = ({sc.label_ent}, {sc.label_neu}, {sc.label_con})")
    print(f"par identico:  ent {pi['entailment'][0]:.3f} neu {pi['neutral'][0]:.3f} con {pi['contradiction'][0]:.3f}")
    print(f"par contrario: ent {pc['entailment'][0]:.3f} neu {pc['neutral'][0]:.3f} con {pc['contradiction'][0]:.3f}")
    print(f"tokens especiales en un par: {n_esp} ({tok.convert_ids_to_tokens(par)})")
    ok = pi["entailment"][0] > 0.9 and pc["contradiction"][0] > 0.9 and n_esp == ESPECIALES_XLMR
    print("ETIQUETAS OK" if ok else "ETIQUETAS FALLA")
    if not ok:
        sys.exit("PARADA: etiquetas o tokens especiales del modelo nuevo no son los esperados (§1)")


def lote():
    """Modelo nuevo: lote 16 frente a 8 en 50 articulos (vigente de grupos armados). Guarda el
    lote elegido en lote.txt: 16, u 8 si no cabe o si difiere > 1e-4 (§1)."""
    _, textos = textos_corpus()
    scorer = cargar_nuevo()
    hip = H.HIPOTESIS[GA]["vig"]
    os.makedirs(DIR, exist_ok=True)
    try:
        a = puntuar(scorer, textos[:N_LOTE], hip, 16)
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        bs = 8
        print("Lote 16 no cabe en la GPU: se usa 8 (§1); no hay comparacion 16 vs 8")
    else:
        b = puntuar(scorer, textos[:N_LOTE], hip, 8)
        dif = max(float(np.abs(a[k] - b[k]).max()) for k in a)
        bs = 16 if dif < TOL else 8
        print(f"LOTE 16 vs 8 ({N_LOTE} art.): max|dif| = {dif:.1e}; memoria GPU pico "
              f"{torch.cuda.max_memory_allocated()/2**30:.2f} GiB -> lote {bs}")
    with open(LOTE_ELEGIDO, "w") as f:
        f.write(str(bs))


# ── §2 cobertura de la premisa del juez ──────────────────────────────────────

def cobertura():
    """Proporcion de articulos cuya premisa de juez (rondas 1-2) no cabe completa en lo que ve
    el modelo nuevo: 512 - 4 - n_hip tokens de su tokenizador, n_hip = su hipotesis mas larga."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODELO_NUEVO)
    n_tok = lambda t: len(tok(str(t), add_special_tokens=False)["input_ids"])  # noqa: E731
    hips = hipotesis_etapa1()
    n_hip = max(n_tok(h) for h in hips.values())
    k = MAX_LENGTH - ESPECIALES_XLMR - n_hip
    # Comprobacion empirica de los tokens especiales con un par real.
    par = tok("a", "b", truncation=True, max_length=MAX_LENGTH)["input_ids"]
    assert len(par) - n_tok("a") - n_tok("b") == ESPECIALES_XLMR, par
    filas = []
    for nombre, ruta in (("lugares", os.path.join(DIR_R1, "premisas_visibles.pkl")),
                         ("nacional", os.path.join(DIR_HO, "premisas_visibles_nacional.pkl"))):
        perd = (pd.read_pickle(ruta).map(n_tok) - k).clip(lower=0)
        filas.append({"premisas": nombre, "n": len(perd), "con_perdida": int((perd > 0).sum()),
                      "prop_con_perdida": round(float((perd > 0).mean()), 4),
                      f"prop_pierde_mas_de_{PERDIDA_TOL}": round(float((perd > PERDIDA_TOL).mean()), 4),
                      "perdida_P50_si_pierde": float(perd[perd > 0].median()) if (perd > 0).any() else 0.0,
                      "perdida_P95": float(perd.quantile(.95)), "perdida_max": int(perd.max())})
    r = pd.DataFrame(filas)
    print(f"Hipotesis mas larga (etapa 1): {n_hip} tokens XLM-R; el modelo ve {k} tokens de premisa")
    print(r.to_string(index=False))
    os.makedirs(DIR, exist_ok=True)
    r.to_csv(os.path.join(DIR, "cobertura.csv"), index=False)
    p = float(r.loc[r.premisas == "lugares", f"prop_pierde_mas_de_{PERDIDA_TOL}"].iloc[0])
    if p > MAX_COBERTURA:
        print(f"AVISO (§2): {p:.1%} > 5 % de los articulos pierde > {PERDIDA_TOL} tokens. La etapa 1 "
              "se corre igual; PARADA antes de juzgar, decide el usuario")
    else:
        print(f"Cobertura OK en los 4 lugares ({p:.1%} pierde > {PERDIDA_TOL} tokens; tope 5 %)")


# ── §4 GPU de la etapa 1 ─────────────────────────────────────────────────────

def gpu():
    df, textos = textos_corpus()
    hips = hipotesis_etapa1()
    os.makedirs(DIR, exist_ok=True)
    out = {"url": df["url"].values}
    if os.path.exists(CHECKPOINT):
        cp = pd.read_pickle(CHECKPOINT)
        if len(cp) == len(df) and (cp["url"].values == df["url"].values).all():
            out = {c: cp[c].values for c in cp.columns}
            print(f"checkpoint: {sum(c.startswith('ent_') for c in out)} hipotesis ya hechas")
    scorer = cargar_nuevo(verbose=True)
    bs = lote_elegido()
    pend = [k for k in hips if f"ent_{k}" not in out]
    print(f"{len(textos)} articulos x {len(pend)} hipotesis pendientes (de {len(hips)})", flush=True)
    t0 = time.time()
    for i, k in enumerate(pend, 1):
        try:
            p = puntuar(scorer, textos, hips[k], bs)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            bs = 8
            print("lote 16 no cabe: se sigue con 8 (§1)", flush=True)
            p = puntuar(scorer, textos, hips[k], bs)
        for c, v in p.items():
            out[f"{c}_{k}"] = v
        pd.DataFrame(out).to_pickle(CHECKPOINT)
        dt = time.time() - t0
        print(f"[{i}/{len(pend)}] {k}  {dt/60:.1f} min (lote {bs}), faltan ~{dt/i*(len(pend)-i)/60:.0f} min",
              flush=True)
    res = pd.DataFrame(out)
    assert all(f"{c}_{k}" in res for k in hips for c in ("ent", "neu", "con"))
    res.to_pickle(SALIDA)
    os.remove(CHECKPOINT)
    print(f"OK -> {SALIDA} {res.shape}")


# ── §4 filtro (offline) ──────────────────────────────────────────────────────

def referencia() -> pd.DataFrame:
    """Las 940 etiquetas: ronda 1 (lugares + holdout) y ronda 2 sin los 40 de control."""
    a = pd.read_csv(os.path.join(DIR_R1, "referencia.csv"))
    b = pd.read_csv(os.path.join(DIR_HO, "referencia.csv"))
    c = pd.read_csv(os.path.join(DIR_R2, "referencia.csv"))
    c = c[c["origen"] != "control"]
    ref = pd.concat([a, b, c], ignore_index=True)
    assert ref["url"].is_unique and len(ref) == 940, len(ref)
    return ref


def tabla_scores(x: pd.DataFrame, r1: pd.DataFrame) -> pd.DataFrame:
    """s(h) de vigentes, gemelas y absurdo total con el modelo nuevo (sesgo del nuevo) y con el
    actual (sesgo de la ronda 1)."""
    sesgo_n = np.mean([x[f"ent_NULA_CAL_{i}"].values.astype(float) for i in range(4)], axis=0)
    out = {"url": x["url"].values, "sesgo_nuevo": sesgo_n, "sesgo_actual": r1["sesgo"].values}
    for ind in H.INDICADORES_5:
        for k in ("vig", "vig_abs"):
            out[f"nuevo__{ind}__{k}"] = s(x[f"ent_{ind}__{k}"].values, x[f"neu_{ind}__{k}"].values, sesgo_n)
            c = H.columna(ind, k)
            out[f"actual__{ind}__{k}"] = s(r1[f"ent_{c}"].values, r1[f"neu_{c}"].values, r1["sesgo"].values)
    out["nuevo__ABSURDO_TOTAL"] = s(x["ent_ABSURDO_TOTAL"].values, x["neu_ABSURDO_TOTAL"].values, sesgo_n)
    out["actual__ABSURDO_TOTAL"] = s(r1["ent_ABSURDO_TOTAL"].values, r1["neu_ABSURDO_TOTAL"].values,
                                     r1["sesgo"].values)
    return pd.DataFrame(out)


def filtro():
    x = pd.read_pickle(SALIDA)
    r1 = pd.read_pickle(R1_SCORES)
    assert (x["url"].values == r1["url"].values).all()
    t = tabla_scores(x, r1)
    lug = pd.read_csv(os.path.join(DIR_R1, "url_lugares.csv"))
    ul = {l: set(lug.loc[lug["lugar"] == l, "url"]) for l in LUGARES}
    ref = referencia()
    juzg = set(ref["url"])
    pos = {ind: set(ref.loc[ref[ind] == 1, "url"]) for ind in H.INDICADORES_5}

    sn = t["sesgo_nuevo"]
    print(f"Sesgo del modelo nuevo: media {sn.mean():.3f}, P95 {sn.quantile(.95):.3f}, "
          f"% > 0.5 {100*(sn > .5).mean():.1f} (actual: media {t['sesgo_actual'].mean():.3f}, "
          f"P95 {t['sesgo_actual'].quantile(.95):.3f}, % > 0.5 {100*(t['sesgo_actual'] > .5).mean():.1f})")
    tot = {m: [float(t.loc[t.url.isin(ul[l]), f"{m}__ABSURDO_TOTAL"].max()) for l in LUGARES]
           for m in ("nuevo", "actual")}
    print("Absurdo total, MAX A/M/O/P: nuevo " + "/".join(f"{v:.2f}" for v in tot["nuevo"])
          + " | actual " + "/".join(f"{v:.2f}" for v in tot["actual"]))

    filas = []
    for ind in H.INDICADORES_5:
        f = {"indicador": ind}
        for m in ("nuevo", "actual"):
            for k in ("vig", "vig_abs"):
                c = f"{m}__{ind}__{k}"
                f[f"{m}_{k}_max"] = [round(float(t.loc[t.url.isin(ul[l]), c].max()), 4) for l in LUGARES]
                f[f"{m}_{k}_prop"] = round(float((t[c] > CORTE).mean()), 4)
            # M2 provisional: precision@10 media en los 4 lugares con las etiquetas existentes.
            c = f"{m}__{ind}__vig"
            p10, sinj = [], 0
            for l in LUGARES:
                sub = t[t.url.isin(ul[l]) & (t[c] > 0)].sort_values([c, "url"], ascending=[False, True])
                top = list(sub["url"].head(10))
                sinj += sum(u not in juzg for u in top)
                pl = pos[ind] & ul[l]
                p10.append((1.0 if not pl else 0.0) if not top else float(np.mean([u in pl for u in top])))
            f[f"{m}_M2prov"] = round(float(np.mean(p10)), 3)
            f[f"{m}_top10_sin_juzgar"] = sinj
        f["npos"] = [len(pos[ind] & ul[l]) for l in LUGARES]
        for m in ("nuevo", "actual"):
            f[f"{m}_razon_abs"] = [round(g / v, 3) if v > 0 else np.nan
                                   for g, v in zip(f[f"{m}_vig_abs_max"], f[f"{m}_vig_max"])]
        f["a_gemela"] = sum(v < CORTE for v in f["nuevo_vig_abs_max"]) >= 3
        f["b_vigente"] = all(v >= CORTE for v, n in zip(f["nuevo_vig_max"], f["npos"]) if n > 0)
        f["decisivo"] = ind in DECISIVOS
        f["pasa"] = bool(f["a_gemela"] and f["b_vigente"]) and ind in DECISIVOS
        filas.append(f)
    F = pd.DataFrame(filas)
    # §4: grupos armados entra si pasa alguno de los tres decisivos; exclusion nunca entra.
    alguno = bool(F.loc[F.decisivo, "pasa"].any())
    F["etapa2"] = F["pasa"] | ((F.indicador == GA) & alguno)
    fmt = lambda v: "/".join(f"{a:.2f}" for a in v)  # noqa: E731
    print(f"\n{'indicador':32s} {'pos A/M/O/P':>11s} | {'vig nuevo':>19s} {'gem nuevo':>19s} | "
          f"{'vig actual':>19s} {'gem actual':>19s} | a b pasa")
    for r in F.itertuples():
        print(f"{r.indicador[:32]:32s} {'/'.join(map(str, r.npos)):>11s} | {fmt(r.nuevo_vig_max):>19s} "
              f"{fmt(r.nuevo_vig_abs_max):>19s} | {fmt(r.actual_vig_max):>19s} {fmt(r.actual_vig_abs_max):>19s} | "
              f"{'s' if r.a_gemela else 'n'} {'s' if r.b_vigente else 'n'} "
              f"{('SI' if r.pasa else 'no') if r.decisivo else '(no decide)'}")
    print("\nRazon MAX(gemela)/MAX(vigente) A/M/O/P, nuevo | actual:")
    for r in F.itertuples():
        print(f"  {r.indicador[:32]:32s} {fmt(r.nuevo_razon_abs)} | {fmt(r.actual_razon_abs)}")
    print(f"\n{'indicador':32s} {'% s>0.766 vig n/a':>18s} {'% gem n/a':>14s} {'M2prov n/a':>11s} {'top10 sin juzgar n/a':>21s}")
    for r in F.itertuples():
        print(f"{r.indicador[:32]:32s} {100*r.nuevo_vig_prop:7.1f}/{100*r.actual_vig_prop:<7.1f}   "
              f"{100*r.nuevo_vig_abs_prop:5.1f}/{100*r.actual_vig_abs_prop:<5.1f}  "
              f"{r.nuevo_M2prov:.2f}/{r.actual_M2prov:.2f}   {r.nuevo_top10_sin_juzgar:3d}/{r.actual_top10_sin_juzgar}")
    excl = int(sum(len(pos['exclusion_beneficios_economicos'] & ul[l]) for l in LUGARES))
    print(f"\nExclusion: solo reporte (no medible salvo >= 5 SI/SI en total; hoy "
          f"{len(pos['exclusion_beneficios_economicos'])} en total, {excl} en los 4 lugares)")
    pasan = F.loc[F.pasa, "indicador"].tolist()
    print(f"Pasan el filtro (rechazo, desplazamiento, conflicto): {pasan or 'NINGUNO'}; "
          f"entran a la etapa 2: {F.loc[F.etapa2, 'indicador'].tolist() or 'ninguno'}")
    t.to_pickle(os.path.join(DIR, "etapa1_scores.pkl"))
    with pd.ExcelWriter(os.path.join(DIR, "etapa1_filtro.xlsx")) as w:
        F.astype({c: str for c in F.columns if F[c].map(lambda v: isinstance(v, list)).any()}) \
            .to_excel(w, sheet_name="filtro", index=False)
        pd.DataFrame({"lugar": LUGARES, "absurdo_nuevo": tot["nuevo"], "absurdo_actual": tot["actual"]}) \
            .to_excel(w, sheet_name="absurdo_total", index=False)
    if not pasan:
        print("PARADA (§4): ningun indicador pasa el filtro; se rechaza el modelo")


if __name__ == "__main__":
    {"etiquetas": etiquetas, "sanidad": sanidad, "lote": lote, "cobertura": cobertura, "gpu": gpu, "filtro": filtro}[sys.argv[1]]()
