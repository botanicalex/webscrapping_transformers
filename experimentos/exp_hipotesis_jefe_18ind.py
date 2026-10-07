"""
Hipótesis nuevas del jefe (2026-10-06) para 3 indicadores del radar de 18 indicadores.

PREGUNTA. ¿Las 3 frases pedidas por el jefe (conflicto_territorial, zonas_proteccion_alimentaria,
resistencia_territorial) superan el control absurdo (osos polares, en el mismo formato de cada
frase) al menos tan bien como las 3 actuales de src/Transformer_optimo.py?

PAR MÍNIMO. Por indicador: la frase actual de V2 contra la frase nueva del jefe. Difieren en la
redacción completa (no es un par de una sola palabra: es un pedido de negocio, no un experimento
de aislamiento). La nula de cada frase nueva conserva su formato y cambia el contenido por
"colonias de osos polares" (contenido de V2.NULA_TEST, el mismo de la medición actual).

LO QUE NO SE PUEDE MEDIR. Ninguno de los 3 indicadores tiene estándar de plata
(hipotesis_base.KEYWORDS_SILVER solo cubre grupos_etnicos y grupos_armados): el AUC es
"no medible". Según el skill experimento-hipotesis, sin AUC la variante no se adopta por
mérito propio; aquí el cambio lo ordena el jefe, así que el control se REPORTA y no decide.

CRITERIOS (fijados antes de correr; skill, pasos 6-7). Por indicador y por corpus nacional
(32 deptos, 11.439 arts):
  P1  prop(ent nula cruda > 0.9) <= 5 %  y  media(nula corregida) <= 0.10.
  P2  el control absurdo no empeora respecto de la actual: prop(nula cruda > 0.9) y
      media(nula corregida) de la nueva <= los de la actual (NULA_TEST).
  P3  brecha por lugar = MAX(real corregido) - MAX(nula corregida) por departamento (la
      agregación de esta rama es MAX): la brecha media de la nueva no baja respecto de la actual.
  Falla una puerta = se marca FALLA. La implementación sigue (decisión del jefe); el informe lo dice.
Los 5 lugares (df_corpus_5lugares.pkl) se reportan como constancia, sin puertas.

SESGO. Nacional: columna `sesgo` ya guardada en datos/scores/scores_v2_32deptos.pkl (la que
usará producción). Lugares: media de V2.NULAS_CALIBRACION calculada aquí (como producción).
NULA_TEST jamás entra al sesgo. Se guardan ent/neu SIN enmascarar (regla 8) en
datos/scores/scores_hipotesis_jefe_18ind.pkl (no sobrescribe: aborta si existe).

  python experimentos/exp_hipotesis_jefe_18ind.py            # puntúa (GPU, ~1 h) y analiza
  python experimentos/exp_hipotesis_jefe_18ind.py --analizar # solo analiza el pkl
Salida: datos/scores/scores_hipotesis_jefe_18ind.pkl, experimentos/resultados/exp_hipotesis_jefe_18ind.csv
"""
import os
import sys

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipotesis_v2 as V2  # noqa: E402

CORPUS_NAC = "datos/corpus/df_corpus_combinado_32deptos.pkl"
CORPUS_LUG = "datos/corpus/df_corpus_5lugares.pkl"
SCORES_NAC = "datos/scores/scores_v2_32deptos.pkl"
BASE_LUG = "datos/scores/df_procesado_baseline_v2.pkl"
SALIDA_PKL = "datos/scores/scores_hipotesis_jefe_18ind.pkl"
SALIDA_CSV = "experimentos/resultados/exp_hipotesis_jefe_18ind.csv"

NUEVAS = {
    "conflicto_territorial": "Dos o más actores disputan el control, uso o propiedad de un territorio.",
    "zonas_proteccion_alimentaria": "El territorio tiene una figura de protección especial para la producción de alimentos.",
    "resistencia_territorial": "Una comunidad realiza acciones para defender su territorio frente a proyectos, intervenciones o decisiones externas.",
}
NULAS_NUEVAS = {
    "conflicto_territorial": "Dos o más actores disputan el control de colonias de osos polares en un territorio.",
    "zonas_proteccion_alimentaria": "El territorio tiene una figura de protección especial para colonias de osos polares.",
    "resistencia_territorial": "Una comunidad realiza acciones para defender colonias de osos polares frente a proyectos externos.",
}
INDS = list(NUEVAS)


def corregido(ent, neu, sesgo):
    return np.clip(np.clip(ent - sesgo, 0, None) * (1 - neu), 0, 1)


def puntuar():
    if os.path.exists(SALIDA_PKL):
        sys.exit(f"{SALIDA_PKL} ya existe: no se sobrescribe (regla 8, no repetir GPU). Usa --analizar.")
    from nli_core import NLIScorer, verificar_contra_produccion_v2
    s = NLIScorer()
    # Paso 0 del skill: bloqueante.
    ok = verificar_contra_produccion_v2(s, BASE_LUG, "presencia_grupos_armados",
                                        V2.TODAS["presencia_grupos_armados"])
    if not ok:
        sys.exit("Paso 0 FALLA: nli_core se desvió de producción. Se detiene.")

    partes = []
    for nombre, ruta_c in (("nacional", CORPUS_NAC), ("lugares", CORPUS_LUG)):
        df = pd.read_pickle(ruta_c).reset_index(drop=True)
        prem = df["texto"].fillna("").astype(str).tolist()
        out = {"corpus": nombre, "titulo": df["titulo"].values,
               "departamento": df["departamento"].astype(str).str.strip().values}
        if nombre == "nacional":
            d = pd.read_pickle(SCORES_NAC).reset_index(drop=True)
            assert len(d) == len(df) == 11439
            assert (d["titulo"].values == df["titulo"].values).all()
            out["sesgo"] = d["sesgo"].values.astype(float)
            for c in INDS:
                out[f"ent_actual_{c}"] = d[f"ent_{c}"].values.astype(float)
                out[f"neu_actual_{c}"] = d[f"neu_{c}"].values.astype(float)
        else:
            out["sesgo"] = np.mean([np.asarray(s.score(prem, h), dtype=float)
                                    for h in V2.NULAS_CALIBRACION], axis=0)
            for c in INDS:
                p = s.score(prem, V2.TODAS[c], devolver_todo=True)
                out[f"ent_actual_{c}"] = np.asarray(p["entailment"], dtype=float)
                out[f"neu_actual_{c}"] = np.asarray(p["neutral"], dtype=float)
        p = s.score(prem, V2.NULA_TEST, devolver_todo=True)
        out["ent_nula_actual"] = np.asarray(p["entailment"], dtype=float)
        out["neu_nula_actual"] = np.asarray(p["neutral"], dtype=float)
        for c in INDS:
            p = s.score(prem, NUEVAS[c], devolver_todo=True)
            out[f"ent_nueva_{c}"] = np.asarray(p["entailment"], dtype=float)
            out[f"neu_nueva_{c}"] = np.asarray(p["neutral"], dtype=float)
            p = s.score(prem, NULAS_NUEVAS[c], devolver_todo=True)
            out[f"ent_nula_nueva_{c}"] = np.asarray(p["entailment"], dtype=float)
            out[f"neu_nula_nueva_{c}"] = np.asarray(p["neutral"], dtype=float)
            print(f"[{nombre}] {c} listo", flush=True)
        partes.append(pd.DataFrame(out))
    pd.concat(partes, ignore_index=True).to_pickle(SALIDA_PKL)
    print(f"-> {SALIDA_PKL}")


def analizar():
    P = pd.read_pickle(SALIDA_PKL)
    filas = []
    for corpus in ("nacional", "lugares"):
        g = P[P["corpus"] == corpus]
        sesgo = g["sesgo"].values
        dep = g["departamento"].values
        nula_a_cruda = g["ent_nula_actual"].values
        nula_a_corr = corregido(nula_a_cruda, g["neu_nula_actual"].values, sesgo)
        for c in INDS:
            res = {}
            for v in ("actual", "nueva"):
                real = corregido(g[f"ent_{v}_{c}"].values, g[f"neu_{v}_{c}"].values, sesgo)
                if v == "actual":
                    nc, ncorr = nula_a_cruda, nula_a_corr
                else:
                    nc = g[f"ent_nula_nueva_{c}"].values
                    ncorr = corregido(nc, g[f"neu_nula_nueva_{c}"].values, sesgo)
                mr = pd.Series(real).groupby(dep).max()
                mn = pd.Series(ncorr).groupby(dep).max()
                brecha = mr - mn
                res[v] = dict(
                    real_ent_media=g[f"ent_{v}_{c}"].mean(), real_corr_media=real.mean(),
                    real_corr_p_gt_05=(real > 0.5).mean(),
                    nula_cruda_media=nc.mean(), nula_cruda_prop_gt_09=(nc > 0.9).mean(),
                    nula_corr_media=ncorr.mean(),
                    radar_real_media=mr.mean(), radar_nula_media=mn.mean(),
                    brecha_media=brecha.mean(), brecha_min=brecha.min(),
                )
            filas.append({"corpus": corpus, "indicador": c, **{f"{v}_{k}": x for v, r in res.items() for k, x in r.items()}})
    R = pd.DataFrame(filas)
    # Puertas (solo nacional)
    pu = []
    for _, r in R[R["corpus"] == "nacional"].iterrows():
        p1 = r["nueva_nula_cruda_prop_gt_09"] <= 0.05 and r["nueva_nula_corr_media"] <= 0.10
        p2 = (r["nueva_nula_cruda_prop_gt_09"] <= r["actual_nula_cruda_prop_gt_09"]
              and r["nueva_nula_corr_media"] <= r["actual_nula_corr_media"])
        p3 = r["nueva_brecha_media"] >= r["actual_brecha_media"]
        pu.append({"indicador": r["indicador"], "P1": p1, "P2": p2, "P3": p3})
    PU = pd.DataFrame(pu)
    R.to_csv(SALIDA_CSV, index=False)
    pd.set_option("display.width", 250, "display.max_columns", 50)
    for corpus in ("nacional", "lugares"):
        print(f"\n=== {corpus} ===")
        print(R[R["corpus"] == corpus].set_index("indicador").drop(columns="corpus").T.round(4).to_string())
    print("\n=== PUERTAS (nacional; AUC: no medible, sin estándar de plata) ===")
    print(PU.to_string(index=False))
    print(f"-> {SALIDA_CSV}")


if __name__ == "__main__":
    if "--analizar" not in sys.argv:
        puntuar()
    analizar()
