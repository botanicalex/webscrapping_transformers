# -*- coding: utf-8 -*-
"""
Prueba barata del backlog 3b (contexto/07_backlog.md): ¿la prensa regional cubre el
déficit estructural (acueducto, salud, educación, vías...) si se busca con esos
términos en vez de los de conflicto (`cfg.TEMAS_BUSQUEDA`)?

Departamento de prueba: La Guajira. El oficial la clasifica Alto
(radar_oficial_promedio 41.8, la 3a más alta de los 32) y hoy solo tiene 11 artículos
en el corpus de producción, buscados con los términos de conflicto pese al respaldo
automático en El Tiempo / Las2Orillas. Es además el caso que motiva 3c: `desnutricion`
es uno de los indicadores candidatos y La Guajira es donde más pertinente sería.

Pregunta: buscando "{La Guajira} {término}" en vez de "{La Guajira} conflicto" (etc.),
¿aparecen más artículos, y hablan de otra cosa?

Evidencia a favor: el corpus crece sensiblemente (no ±2-3 artículos, que es ruido de
scraping con n tan chico) Y los títulos hablan de acueducto/salud/educación/vías, no
de lo mismo que ya traían los términos de conflicto.

Evidencia en contra: el corpus no crece, o crece pero repite el mismo tipo de
contenido — indicaría que el departamento simplemente tiene poca cobertura de
prensa en general (la hipótesis alternativa que ya señala 09_riesgos_y_limites.md,
Spearman(n_articulos, radar_oficial) = -0.26), y no que el término de búsqueda sea
la palanca.

No escribe en datos/corpus/ (junction compartida con desarrollo/): guarda el
resultado aparte, en resultados/.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config_pipeline as cfg  # noqa: E402
from scrappers import scrape_departamento  # noqa: E402

DEPARTAMENTO = "La Guajira"
N_ARTICULOS_BASELINE_CONFLICTO = 11  # ver contexto/01_objetivo_y_radar.md

TERMINOS_DEFICIT = [
    "acueducto", "agua potable", "energía", "alcantarillado", "gas", "salud",
    "hospital", "escuela", "educación", "docentes", "vías", "carretera",
    "desnutrición", "vivienda", "servicios públicos", "conectividad",
]


def main():
    print(f"Departamento : {DEPARTAMENTO}")
    print(f"Periodo      : {cfg.FECHA_DESDE} -> {cfg.FECHA_HASTA}")
    print(f"Terminos ({len(TERMINOS_DEFICIT)}): {TERMINOS_DEFICIT}")
    print(f"Baseline con terminos de conflicto: {N_ARTICULOS_BASELINE_CONFLICTO} articulos\n")

    df = scrape_departamento(
        departamento=DEPARTAMENTO,
        fecha_desde=cfg.FECHA_DESDE,
        fecha_hasta=cfg.FECHA_HASTA,
        temas=TERMINOS_DEFICIT,
    )

    print(f"\n{'=' * 60}")
    print(f"RESULTADO: {len(df)} articulos "
          f"(vs {N_ARTICULOS_BASELINE_CONFLICTO} con terminos de conflicto)")
    print(f"{'=' * 60}")
    if not df.empty:
        print(df["terminos_encontrado"].value_counts().to_string())
        print()
        print(df[["periodico", "titulo", "terminos_encontrado"]].to_string(index=False))

    os.makedirs("resultados", exist_ok=True)
    ruta = os.path.join("resultados", "exp_terminos_deficit_la_guajira.pkl")
    df.to_pickle(ruta)
    print(f"\nGuardado -> {ruta}")


if __name__ == "__main__":
    main()
