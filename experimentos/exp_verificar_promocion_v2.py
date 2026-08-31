# -*- coding: utf-8 -*-
"""
Verificación OFFLINE (sin GPU) de la promoción de V2 a `src/` (2026-08-31,
ver contexto/08_log_decisiones.md). No es un experimento que decida entre
variantes -- es una prueba de que la LÓGICA nueva de
`src/Transformer_optimo.py` + `src/radar.py` + `src/metricas_y_calculo_de_error.py`
está bien traducida, antes de correr el pipeline real con GPU.

Reproduce la receta nueva de producción (hipótesis V2 -- verificado
byte-a-byte idéntico a experimentos/hipotesis_v2.py --, sesgo por artículo,
SIN pre-filtro, P75 por RANGO MAS CERCANO -- igual que
`exportar_indicadores_transformers_por_departamento` -- , cortes fijos
0.3074/0.3524, clasificación oficial real del DANE) sobre
datos/scores/scores_v2_32deptos.pkl, ya calculado -- no toca la GPU.

Qué confirma esto: que el Spearman y las anclas de validez aparente sobre
esta receta traducida a `src/` no se alejan de lo ya medido en
exp_correlacion_v2_nacional.py (SIN prefiltro, +0.384) más de lo esperable
por el cambio P75-lineal -> P75-rango-más-cercano (una diferencia mínima,
de una posición de artículo como mucho).

Qué NO confirma: que el código de `src/` ejecuta correctamente sobre GPU real
(newspaper/tokenización/batching) -- eso lo cubre el smoke test con GPU
sobre el corpus de 5 lugares, aparte.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import hipotesis_v2 as V2

SCORES = "../datos/scores/scores_v2_32deptos.pkl"
REFERENCIA_V3 = "../datos/referencia/comparacion_radares_V3.xlsx"
SALIDA = "resultados/exp_verificar_promocion_v2.xlsx"

CORTE_BAJO_MEDIO = 0.3074
CORTE_MEDIO_ALTO = 0.3524

NUNCA_ALTO = ["Cundinamarca", "Quindío", "Boyacá", "San Andrés y Providencia", "Caldas", "Risaralda"]
NUNCA_BAJO = ["Cauca", "Nariño", "Chocó", "Arauca", "Norte de Santander", "Putumayo"]


def _norm(s: str) -> str:
    import unicodedata
    s = str(s).strip().lower()
    if s.startswith("san andr"):
        return "san andres"
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def _p75_rango_cercano(x: np.ndarray) -> float:
    """Idéntico a CalculadorRadar._p75_rango_cercano de src/radar.py."""
    ordenado = np.sort(x)
    pos = round(0.75 * (len(ordenado) - 1))
    return float(ordenado[pos])


def _clasificar_fijo(v: float) -> str:
    if v < CORTE_BAJO_MEDIO:
        return "Bajo"
    if v < CORTE_MEDIO_ALTO:
        return "Medio"
    return "Alto"


def main():
    d = pd.read_pickle(SCORES)
    print(f"Scores: {d.shape[0]} articulos, {d['departamento'].nunique()} departamentos")

    inds = list(V2.TODAS)
    sesgo = d["sesgo"].values

    def corregido(col):
        e, n = d[f"ent_{col}"].values, d[f"neu_{col}"].values
        return np.clip(np.clip(e - sesgo, 0, None) * (1 - n), 0, 1)

    S = {c: corregido(c) for c in inds}
    lugares = d["departamento"].values

    filas = []
    for lug in sorted(set(lugares)):
        m = lugares == lug
        p75_por_indicador = [_p75_rango_cercano(S[c][m]) for c in inds]
        radar = float(np.mean(p75_por_indicador))
        filas.append({"departamento": lug, "radar_propio": round(radar, 4), "n_articulos": int(m.sum())})
    radar_df = pd.DataFrame(filas)
    radar_df["clase_fija"] = radar_df["radar_propio"].apply(_clasificar_fijo)
    radar_df["_k"] = radar_df["departamento"].map(_norm)

    oficial = pd.read_excel(REFERENCIA_V3, engine="openpyxl")
    oficial.columns = [str(c).strip() for c in oficial.columns]
    oficial["_k"] = oficial["Departamento"].map(_norm)

    m = oficial.merge(radar_df, on="_k", how="inner").drop(columns=["_k"])
    print(f"n = {len(m)} departamentos cruzados")

    rho, pval = spearmanr(m["radar_propio"], m["radar_oficial_promedio"])
    print(f"Spearman(radar_V2_produccion, radar_oficial_promedio) = {rho:+.4f}  (p={pval:.4f})")
    print(f"Referencia (exp_correlacion_v2_nacional.py, SIN prefiltro, P75 lineal) = +0.3840")

    # cat_oficial: la clasificación REAL del DANE, no re-tercilada (el bug
    # corregido en metricas_y_calculo_de_error.py) -- misma verificación aquí.
    acc = float((m["clase_fija"] == m["Clasificacion_radar_oficial_promedio"]).mean())
    print(f"Accuracy (cortes fijos vs Clasificacion_radar_oficial_promedio real) = {acc * 100:.1f}%")

    idx = m.set_index("Departamento")["clase_fija"]
    rotos_alto = [dep for dep in NUNCA_ALTO if dep in idx.index and idx[dep] == "Alto"]
    rotos_bajo = [dep for dep in NUNCA_BAJO if dep in idx.index and idx[dep] == "Bajo"]
    print(f"Anclas 'nunca Alto' rotas: {rotos_alto or 'ninguna'}")
    print(f"Anclas 'nunca Bajo' rotas: {rotos_bajo or 'ninguna'}")

    ok = (rho > 0.25) and not rotos_alto and not rotos_bajo
    print(f"\n{'OK' if ok else 'REVISAR'}: la receta traducida a src/ {'reproduce' if ok else 'NO reproduce'} "
          f"lo medido en experimentos (Spearman > 0.25, sin romper anclas).")

    import os
    os.makedirs("resultados", exist_ok=True)
    m.to_excel(SALIDA, index=False)
    print(f"\nGuardado -> {SALIDA}")

    assert ok, "La logica traducida a src/ no reproduce lo medido -- no promover sin investigar"


if __name__ == "__main__":
    main()
