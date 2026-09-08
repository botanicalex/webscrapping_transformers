# -*- coding: utf-8 -*-
"""
Backlog punto 2 (contexto/07_backlog.md): recalibrar los cortes Bajo/Medio/Alto sobre
la distribución nacional del radar V2 (P75), y congelarlos. Con P75 los valores caen
entre 0.22 y 0.41 — los cortes viejos (1/3, 2/3 de la escala [0,1]) mandan casi todo a
"Bajo"/"Medio" y ya no significan nada (contexto/08_log_decisiones.md
[2026-06] "Umbrales fijos, no terciles, para el radar propio").

Restricción externa (pedido del jefe del usuario, no negociable): cortes FIJOS sobre el
valor de `radar_propio`, no terciles empíricos recalculados por lote. La razón práctica:
el radar debe poder clasificar una vereda sola, sin otros 31 lugares con qué hacer
terciles.

Pregunta: ¿qué dos valores fijos de corte son defendibles?

Metodología (para no caer en el riesgo ya señalado en 09_riesgos_y_limites.md de
"seleccionar sobre el conjunto de evaluación"): los cortes se leen de la FORMA de la
distribución del radar_propio en sí — huecos naturales entre valores consecutivos —
SIN mirar la clasificación oficial. Solo después de fijarlos se verifican (no se
ajustan) contra dos criterios independientes: las anclas de validez aparente y la
accuracy resultante, reportada tal como salga.

Evidencia a favor de los cortes elegidos: no rompen ninguna ancla de validez aparente,
y caen en huecos genuinos de la distribución (no cortan un grupo de valores casi
iguales por la mitad).

Evidencia en contra: si la accuracy resultante fuera muchísimo peor que la de los
terciles empíricos ad hoc (contexto/08_log_decisiones.md [2026-08-30]), o si rompieran
alguna ancla, habría que buscar otro punto en la distribución.

Reusa exp_correlacion_v2_nacional.py para el cálculo del radar V2 (mismo score
corregido, misma agregación P75, con pre-filtro 0.85 — la configuración que coincide
con el pipeline de producción actual). No vuelve a tocar la GPU (regla 8).
"""
import numpy as np
import pandas as pd

import exp_correlacion_v2_nacional as base

CORTE_BAJO_MEDIO = 0.30
CORTE_MEDIO_ALTO = 0.35

NUNCA_ALTO = base.NUNCA_ALTO
NUNCA_BAJO = base.NUNCA_BAJO


def _clasificar_fijo(v: float) -> str:
    if v < CORTE_BAJO_MEDIO:
        return "Bajo"
    if v < CORTE_MEDIO_ALTO:
        return "Medio"
    return "Alto"


def main():
    d = pd.read_pickle(base.SCORES)
    radar = base.calcular_radar_v2(d, con_prefiltro=True)
    radar["_k"] = radar["departamento"].map(base._norm)

    print("=" * 70)
    print("Distribucion del radar V2 (P75, con prefiltro) — 32 departamentos")
    print("=" * 70)
    vals = np.sort(radar["radar_propio"].values)[::-1]
    print(f"min={vals.min():.4f}  max={vals.max():.4f}  "
          f"media={vals.mean():.4f}  std={vals.std():.4f}")
    print("\nHuecos entre valores consecutivos (ordenado desc):")
    for i in range(len(vals) - 1):
        gap = vals[i] - vals[i + 1]
        marca = "  <-- hueco grande" if gap > 0.008 else ""
        print(f"  {i + 1:>2}  {vals[i]:.4f}   hueco_al_siguiente={gap:.4f}{marca}")
    print(f"  {len(vals):>2}  {vals[-1]:.4f}")

    print(f"\nCortes elegidos (huecos naturales, sin mirar el oficial): "
          f"Bajo < {CORTE_BAJO_MEDIO} <= Medio < {CORTE_MEDIO_ALTO} <= Alto")

    oficial = pd.read_excel(base.REFERENCIA, engine="openpyxl")
    oficial.columns = [str(c).strip() for c in oficial.columns]
    oficial["_k"] = oficial["Departamento"].map(base._norm)
    m = oficial.merge(radar, on="_k", how="inner").drop(columns=["_k"])
    m["clase_fija"] = m["radar_propio"].apply(_clasificar_fijo)
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
    ruta = "resultados/exp_cortes_fijos_v2.xlsx"
    m.to_excel(ruta, index=False)
    print(f"\nGuardado -> {ruta}")


if __name__ == "__main__":
    main()
