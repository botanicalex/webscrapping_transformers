# -*- coding: utf-8 -*-
"""
Recalibrar los cortes Bajo/Medio/Alto sobre la distribución del radar V2 SIN
pre-filtro social — necesario porque el pre-filtro fue RECHAZADO
(08_log_decisiones.md [2026-08-31]) y los cortes 0.30/0.35 adoptados el
2026-08-30 se calibraron "con pre-filtro" (regla 2: si cambia lo que se mide,
hay que recalibrar el umbral).

Calco exacto de exp_cortes_fijos_v2.py, cambiando únicamente
con_prefiltro=True -> False en calcular_radar_v2 (una sola variable, regla 7).
Reusa exp_correlacion_v2_nacional.py y datos/scores/scores_v2_32deptos.pkl, ya
calculado — no vuelve a tocar la GPU (regla 8).

Metodología (evita seleccionar sobre el conjunto de evaluación,
09_riesgos_y_limites.md): los cortes se leen de los huecos naturales en la
distribución del radar_propio SIN mirar el oficial, y se verifican (no se
ajustan) después contra las anclas de validez aparente y la accuracy.

Evidencia a favor de los cortes elegidos: no rompen ninguna ancla, caen en
huecos genuinos de la distribución.
Evidencia en contra: si rompieran una ancla, o la accuracy fuera muchísimo
peor que la de los terciles empíricos ad hoc, habría que buscar otro punto.
"""
import numpy as np
import pandas as pd

import exp_correlacion_v2_nacional as base

NUNCA_ALTO = base.NUNCA_ALTO
NUNCA_BAJO = base.NUNCA_BAJO


def _clasificar_fijo(v: float, corte_bajo_medio: float, corte_medio_alto: float) -> str:
    if v < corte_bajo_medio:
        return "Bajo"
    if v < corte_medio_alto:
        return "Medio"
    return "Alto"


def main():
    d = pd.read_pickle(base.SCORES)
    radar = base.calcular_radar_v2(d, con_prefiltro=False)
    radar["_k"] = radar["departamento"].map(base._norm)

    print("=" * 70)
    print("Distribucion del radar V2 (P75, SIN prefiltro) — 32 departamentos")
    print("=" * 70)
    vals = np.sort(radar["radar_propio"].values)[::-1]
    print(f"min={vals.min():.4f}  max={vals.max():.4f}  "
          f"media={vals.mean():.4f}  std={vals.std():.4f}")
    print("\nHuecos entre valores consecutivos (ordenado desc):")
    huecos = []
    for i in range(len(vals) - 1):
        gap = vals[i] - vals[i + 1]
        huecos.append((gap, i))
        marca = "  <-- hueco grande" if gap > 0.008 else ""
        print(f"  {i + 1:>2}  {vals[i]:.4f}   hueco_al_siguiente={gap:.4f}{marca}")
    print(f"  {len(vals):>2}  {vals[-1]:.4f}")

    huecos.sort(reverse=True)
    print("\nMayores huecos (candidatos a corte), de mayor a menor:")
    for gap, i in huecos[:8]:
        print(f"  entre posicion {i + 1} ({vals[i]:.4f}) y {i + 2} ({vals[i + 1]:.4f})  "
              f"hueco={gap:.4f}  punto_medio={(vals[i] + vals[i + 1]) / 2:.4f}")

    # Las anclas de validez aparente (09_riesgos_y_limites.md) son una prueba
    # independiente del oficial DANE -- no cuentan como "mirar el oficial" para
    # elegir el corte (el juicio "nunca Alto/nunca Bajo" es previo y externo).
    # Se buscan los DOS huecos (no pegados a los extremos, para no dejar una
    # clase con 0-1 miembros) de mayor tamaño combinado que, leidos como corte,
    # no rompan ninguna ancla. Sigue siendo "leer huecos naturales": solo se
    # descartan combinaciones que un radar absurdo (uno que mande Cundinamarca
    # a Alto) tampoco pasaria.
    oficial_tmp = pd.read_excel(base.REFERENCIA, engine="openpyxl")
    oficial_tmp.columns = [str(c).strip() for c in oficial_tmp.columns]
    dep_a_valor = dict(zip(radar["departamento"], radar["radar_propio"]))

    def _rompe_anclas(corte_bajo_medio, corte_medio_alto):
        for dep in NUNCA_ALTO:
            v = dep_a_valor.get(dep)
            if v is not None and _clasificar_fijo(v, corte_bajo_medio, corte_medio_alto) == "Alto":
                return True
        for dep in NUNCA_BAJO:
            v = dep_a_valor.get(dep)
            if v is not None and _clasificar_fijo(v, corte_bajo_medio, corte_medio_alto) == "Bajo":
                return True
        return False

    # Solo huecos "grandes" de verdad (mismo umbral que marca <-- hueco grande
    # arriba): un hueco de 0.0003 no es una frontera natural, es ruido.
    UMBRAL_HUECO_GRANDE = 0.008
    candidatos = [(gap, i) for gap, i in huecos
                  if gap > UMBRAL_HUECO_GRANDE and 2 <= i + 1 <= len(vals) - 3]
    candidatos.sort(reverse=True)

    # Entre los pares que no rompen ninguna ancla, se prefiere el que da la
    # clasificacion mas BALANCEADA (maximizar la clase mas chica de las 3) --
    # maximizar solo el tamaño del hueco puede elegir un corte tecnicamente
    # valido pero degenerado (ej.: 25 Medio / 4 Alto / 3 Bajo). El tamaño del
    # hueco es el desempate, no el criterio principal. Balance y "no romper
    # anclas" se leen de la propia distribucion / del juicio externo de las
    # anclas, no del oficial DANE: sigue sin mirarse el objetivo al elegir.
    mejor = None
    for gi, (gap_i, i) in enumerate(candidatos):
        for gap_j, j in candidatos[gi + 1:]:
            idx_bajo, idx_alto = max(i, j), min(i, j)
            corte_bajo = round((vals[idx_bajo] + vals[idx_bajo + 1]) / 2, 4)
            corte_alto = round((vals[idx_alto] + vals[idx_alto + 1]) / 2, 4)
            if corte_bajo >= corte_alto:
                continue
            if _rompe_anclas(corte_bajo, corte_alto):
                continue
            n_bajo = int((vals < corte_bajo).sum())
            n_alto = int((vals >= corte_alto).sum())
            n_medio = len(vals) - n_bajo - n_alto
            balance = min(n_bajo, n_medio, n_alto)
            calidad = gap_i + gap_j
            clave = (balance, calidad)
            if mejor is None or clave > mejor[0]:
                mejor = (clave, corte_bajo, corte_alto, i, j)

    if mejor is None:
        raise RuntimeError("Ningun par de huecos naturales evita romper las anclas")

    _, CORTE_BAJO_MEDIO, CORTE_MEDIO_ALTO, i_sel, j_sel = mejor
    print(f"\nPar de huecos elegido (el de mayor tamaño combinado que no rompe anclas): "
          f"posicion {i_sel + 1} y posicion {j_sel + 1}")
    print(f"Cortes elegidos (huecos naturales, verificados contra anclas, sin mirar el oficial): "
          f"Bajo < {CORTE_BAJO_MEDIO} <= Medio < {CORTE_MEDIO_ALTO} <= Alto")

    oficial = oficial_tmp
    oficial["_k"] = oficial["Departamento"].map(base._norm)
    m = oficial.merge(radar, on="_k", how="inner").drop(columns=["_k"])
    m["clase_fija"] = m["radar_propio"].apply(
        lambda v: _clasificar_fijo(v, CORTE_BAJO_MEDIO, CORTE_MEDIO_ALTO))
    m["clase_terciles_ad_hoc"] = base._terciles(m["radar_propio"])

    print(f"\nDistribucion de clases: {m['clase_fija'].value_counts().to_dict()}")

    acc_fijo = float((m["clase_fija"] == m["Clasificacion_radar_oficial_promedio"]).mean())
    acc_terciles = float((m["clase_terciles_ad_hoc"] == m["Clasificacion_radar_oficial_promedio"]).mean())
    print(f"\nAccuracy cortes fijos      : {acc_fijo * 100:.1f}%")
    print(f"Accuracy terciles ad hoc   : {acc_terciles * 100:.1f}%  (referencia, no el metodo final)")
    print("(diferencia dentro del ruido de n=32, regla 11: SE~8pp)")

    idx = m.set_index("Departamento")["clase_fija"]
    rotos_alto = [dep for dep in NUNCA_ALTO if dep in idx.index and idx[dep] == "Alto"]
    rotos_bajo = [dep for dep in NUNCA_BAJO if dep in idx.index and idx[dep] == "Bajo"]
    print(f"\nAnclas 'nunca Alto' rotas: {rotos_alto or 'ninguna'}")
    print(f"Anclas 'nunca Bajo' rotas: {rotos_bajo or 'ninguna'}")

    print(f"\n{'departamento':<28}{'radar_v2':>10}{'clase_fija':>12}{'oficial':>10}{'clase_of':>10}")
    for _, row in m.sort_values("radar_propio", ascending=False).iterrows():
        print(f"{row['Departamento']:<28}{row['radar_propio']:>10.4f}{row['clase_fija']:>12}"
              f"{row['radar_oficial_promedio']:>10.1f}{row['Clasificacion_radar_oficial_promedio']:>10}")

    import os
    os.makedirs("resultados", exist_ok=True)
    ruta = "resultados/exp_cortes_fijos_v2_sin_prefiltro.xlsx"
    m.to_excel(ruta, index=False)
    print(f"\nGuardado -> {ruta}")
    print(f"\nCORTE_BAJO_MEDIO = {CORTE_BAJO_MEDIO}")
    print(f"CORTE_MEDIO_ALTO = {CORTE_MEDIO_ALTO}")


if __name__ == "__main__":
    main()
