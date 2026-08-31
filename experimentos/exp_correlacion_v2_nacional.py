# -*- coding: utf-8 -*-
"""
La pregunta abierta más importante del proyecto (contexto/09_riesgos_y_limites.md,
contexto/07_backlog.md punto 1): con el radar V2 corregido (marco metalingüístico
arreglado, sesgo por artículo descontado, agregación P75 en vez de MAX) sobre los 32
departamentos, ¿aparece correlación con el radar oficial DANE? El V0 daba
Spearman +0.067 (cero), pero se midió sobre un radar que ya sabíamos indistinguible de
hipótesis absurdas — no probaba que un radar corregido no fuera a correlacionar.

Pregunta: Spearman(radar_V2_propio, radar_oficial_promedio) en los 32 departamentos.

Evidencia a favor de que el V2 sí lleva señal hacia el objetivo: Spearman
sustancialmente por encima de +0.067, en dirección positiva (correlación con el índice,
no anticorrelación), y que además el radar V2 pase las anclas de validez aparente
(nunca Alto: Cundinamarca/Quindío/Boyacá/San Andrés/Caldas/Risaralda; nunca Bajo:
Cauca/Nariño/Chocó/Arauca/Norte de Santander/Putumayo).

Evidencia en contra: Spearman igual de bajo o negativo, o que rompa las anclas de
validez aparente que el V0 sí pasaba — indicaría que el problema no está en los
indicadores (marco/sesgo/agregación) sino en el desajuste de constructo ya documentado
(conflicto vs vulnerabilidad estructural), y que corresponde decidir entre los tres
caminos de 09_riesgos_y_limites.md.

También corre el A/B del pre-filtro social (backlog punto 3): con y sin el umbral 0.85
de `score_social_v2`, para ver si cambia la correlación — sin volver a tocar la GPU
(regla 8), todo se reusa del pkl ya calculado.

No decide los cortes Bajo/Medio/Alto (backlog punto 2): eso es un paso aparte, posterior
a esta medición.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import hipotesis_v2 as V2

SCORES = "../datos/scores/scores_v2_32deptos.pkl"
REFERENCIA = "../datos/referencia/comparacion_radares_V3.xlsx"
SALIDA = "resultados/exp_correlacion_v2_nacional.xlsx"

UMBRAL_PREFILTRO = 0.85

NUNCA_ALTO = ["Cundinamarca", "Quindío", "Boyacá", "San Andrés y Providencia", "Caldas", "Risaralda"]
NUNCA_BAJO = ["Cauca", "Nariño", "Chocó", "Arauca", "Norte de Santander", "Putumayo"]


def _norm(s: str) -> str:
    import unicodedata
    s = str(s).strip().lower()
    if s.startswith("san andr"):
        return "san andres"
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def _terciles(serie: pd.Series) -> pd.Series:
    return pd.qcut(serie.rank(method="first"), q=3, labels=["Bajo", "Medio", "Alto"]).astype(str)


def calcular_radar_v2(d: pd.DataFrame, con_prefiltro: bool) -> pd.DataFrame:
    inds = list(V2.TODAS)
    sesgo = d["sesgo"].values
    rel = (d["score_social_v2"].values >= UMBRAL_PREFILTRO) if con_prefiltro else np.ones(len(d), dtype=bool)

    def corregido(col):
        e, n = d[f"ent_{col}"].values, d[f"neu_{col}"].values
        s = np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)
        return np.where(rel, s, 0.0)

    S = {c: corregido(c) for c in inds}
    lugares = d["departamento"].values

    filas = []
    for lug in sorted(set(lugares)):
        m = lugares == lug
        p75_por_indicador = [float(np.quantile(S[c][m], 0.75)) if m.sum() else 0.0 for c in inds]
        radar = float(np.mean(p75_por_indicador))
        filas.append({"departamento": lug, "radar_propio": radar, "n_articulos": int(m.sum())})
    return pd.DataFrame(filas)


def main():
    d = pd.read_pickle(SCORES)
    print(f"Scores: {d.shape[0]} articulos, {d['departamento'].nunique()} departamentos")

    oficial = pd.read_excel(REFERENCIA, engine="openpyxl")
    oficial.columns = [str(c).strip() for c in oficial.columns]
    oficial["_k"] = oficial["Departamento"].map(_norm)

    resultados_por_variante = {}
    hojas = {}

    for etiqueta, con_prefiltro in [("SIN_prefiltro", False), ("CON_prefiltro_0.85", True)]:
        print(f"\n{'=' * 70}\n{etiqueta}\n{'=' * 70}")
        radar = calcular_radar_v2(d, con_prefiltro)
        radar["_k"] = radar["departamento"].map(_norm)

        m = oficial.merge(radar, on="_k", how="inner")
        faltan = set(oficial["_k"]) - set(radar["_k"])
        if faltan:
            print(f"  AVISO: departamentos oficiales sin match: {faltan}")
        print(f"  n = {len(m)} departamentos cruzados")

        rho, pval = spearmanr(m["radar_propio"], m["radar_oficial_promedio"])
        print(f"  Spearman(radar_V2, radar_oficial_promedio) = {rho:+.4f}  (p={pval:.4f})")
        print(f"  Spearman V0 historico (referencia)         = +0.0670")

        m["clase_propia"] = _terciles(m["radar_propio"])
        acc = float((m["clase_propia"] == m["Clasificacion_radar_oficial_promedio"]).mean())
        print(f"  Accuracy en terciles vs oficial             = {acc * 100:.1f}%")
        print(f"  (referencia: azar 33.3%, clase mayoritaria 34.4%, radar V0 31.2%)")

        m_idx = m.set_index("Departamento")["clase_propia"]
        rotos_nunca_alto = [dep for dep in NUNCA_ALTO if dep in m_idx.index and m_idx[dep] == "Alto"]
        rotos_nunca_bajo = [dep for dep in NUNCA_BAJO if dep in m_idx.index and m_idx[dep] == "Bajo"]
        print(f"  Anclas 'nunca Alto' rotas: {rotos_nunca_alto or 'ninguna'}")
        print(f"  Anclas 'nunca Bajo' rotas: {rotos_nunca_bajo or 'ninguna'}")

        print(f"\n  {'departamento':<28}{'radar_v2':>10}{'clase_v2':>10}{'oficial':>10}{'clase_of':>10}")
        for _, row in m.sort_values("radar_propio", ascending=False).iterrows():
            print(f"  {row['Departamento']:<28}{row['radar_propio']:>10.4f}{row['clase_propia']:>10}"
                  f"{row['radar_oficial_promedio']:>10.1f}{row['Clasificacion_radar_oficial_promedio']:>10}")

        resultados_por_variante[etiqueta] = {
            "spearman": rho, "p_valor": pval, "accuracy": acc,
            "n": len(m), "anclas_alto_rotas": len(rotos_nunca_alto),
            "anclas_bajo_rotas": len(rotos_nunca_bajo),
        }
        hojas[etiqueta] = m.drop(columns=["_k"])

    print(f"\n{'=' * 70}\nRESUMEN\n{'=' * 70}")
    resumen = pd.DataFrame(resultados_por_variante).T
    print(resumen.to_string())

    import os
    os.makedirs("resultados", exist_ok=True)
    with pd.ExcelWriter(SALIDA) as w:
        resumen.to_excel(w, sheet_name="resumen")
        for etiqueta, df_h in hojas.items():
            df_h.to_excel(w, sheet_name=etiqueta[:31], index=False)
    print(f"\nGuardado -> {SALIDA}")


if __name__ == "__main__":
    main()
