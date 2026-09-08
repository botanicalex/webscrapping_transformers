# -*- coding: utf-8 -*-
"""
Repetición de exp_terminos_deficit.py (backlog 3b) en Chocó en vez de La Guajira,
para separar dos preguntas que la primera corrida mezcló:

  (a) ¿la prensa regional cubre más déficit que conflicto si se buscan esos
      términos? — la pregunta real de 3b.
  (b) ¿funciona el filtro de relevancia? — resultó ser NO para La Guajira
      (nombre compuesto, bug confirmado en contexto/08_log_decisiones.md
      [2026-08-30]: el filtro nunca descartó un solo artículo).

Chocó es de una sola palabra: el filtro de relevancia (`territorio = "chocó"`)
funciona igual que siempre funcionó, sin el bug. Además tiene scraper local
(choco7dias) y el oficial lo clasifica Alto (41.6, 4º más alto de los 32), y ya
tiene un corpus de tamaño razonable (148 artículos con términos de conflicto,
nada que ver con los 11 de La Guajira) — así que el contraste no está contaminado
por ruido de n pequeño.

Pregunta: con el filtro de relevancia funcionando de verdad, ¿los términos de
déficit siguen trayendo más cobertura que los de conflicto, y de contenido
genuinamente distinto (acueducto, salud, vías, no política/sucesos genéricos)?

Evidencia a favor: crecimiento sustancial Y, al inspeccionar muestras por
término, mayoría de títulos genuinamente sobre el tema buscado (como pasó con
`desnutrición` en La Guajira).

Evidencia en contra: sin crecimiento, o con el mismo patrón de ruido que ya se
vio en La Guajira término por término — indicaría que el problema no era (solo)
el filtro roto, sino algo más en cómo cada periódico resuelve la búsqueda.

No escribe en datos/corpus/: guarda aparte en resultados/.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config_pipeline as cfg  # noqa: E402
from scrappers import scrape_departamento  # noqa: E402

DEPARTAMENTO = "Chocó"
N_ARTICULOS_BASELINE_CONFLICTO = 148  # datos/corpus/df_corpus_combinado_32deptos.pkl

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
    ruta = os.path.join("resultados", "exp_terminos_deficit_choco.pkl")
    df.to_pickle(ruta)
    print(f"\nGuardado -> {ruta}")


if __name__ == "__main__":
    main()
