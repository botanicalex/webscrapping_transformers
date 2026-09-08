# -*- coding: utf-8 -*-
"""
Re-scraping de los 4 departamentos de nombre compuesto afectados por el bug de
`GestorScraping._es_relevante` corregido en `src/scrappers.py` (ver
contexto/08_log_decisiones.md, [2026-08-30]).

El bug usaba `termino.split()[0]` como "territorio" para el filtro de relevancia,
lo que para nombres de varias palabras daba solo la primera ("la", "norte",
"valle", "san") — un no-op de facto (0 artículos descartados nunca, verificado en
el log de la prueba 3b). Ya corregido: ahora se pasa el departamento completo.

Este script usa los MISMOS términos de conflicto de producción (`cfg.TEMAS_BUSQUEDA`,
temas=None) — misma metodología que el corpus original, aislando el fix del filtro
como única variable (regla 7).

NO escribe en datos/corpus/ (junction compartida con desarrollo/): guarda en una
carpeta aparte para revisar antes de decidir cómo fusionar con el corpus nacional.
El scoring V2 de los 32 departamentos ya está corriendo sobre el corpus viejo — no
tiene sentido pisarlo a mitad de camino (regla 8, no repetir GPU); el reemplazo del
corpus y el re-scoring de estos 4 departamentos se hace como paso aparte, después.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config_pipeline as cfg  # noqa: E402
from scrappers import scrape_multiples_departamentos  # noqa: E402

DEPARTAMENTOS_AFECTADOS = [
    "La Guajira",
    "Norte de Santander",
    "San Andrés y Providencia",
    "Valle del Cauca",
]

DIR_SALIDA = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resultados", "re_scrape_bugfix_relevancia"
)


def main():
    os.makedirs(DIR_SALIDA, exist_ok=True)
    print(f"Departamentos : {DEPARTAMENTOS_AFECTADOS}")
    print(f"Periodo       : {cfg.FECHA_DESDE} -> {cfg.FECHA_HASTA}")
    print(f"Terminos      : {cfg.TEMAS_BUSQUEDA}  (produccion, sin cambios)")
    print(f"Salida        : {DIR_SALIDA}\n")

    scrape_multiples_departamentos(
        departamentos=DEPARTAMENTOS_AFECTADOS,
        fecha_desde=cfg.FECHA_DESDE,
        fecha_hasta=cfg.FECHA_HASTA,
        min_menciones=None,  # automatico por departamento, igual que correr_grupo.py
        directorio_salida=DIR_SALIDA,
        temas=None,  # cfg.TEMAS_BUSQUEDA, igual que produccion
    )

    print("\nComparacion rapida contra el corpus viejo:")
    import pandas as pd
    import unicodedata

    viejo = pd.read_pickle(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos", "corpus",
                     "df_corpus_combinado_32deptos.pkl")
    )
    for dep in DEPARTAMENTOS_AFECTADOS:
        n_viejo = int((viejo["departamento"].astype(str).str.strip() == dep).sum())
        norm = unicodedata.normalize("NFD", dep.lower()).encode("ascii", "ignore").decode()
        archivo_nuevo = os.path.join(DIR_SALIDA, f"df_corpus_{norm.replace(' ', '_')}.pkl")
        n_nuevo = len(pd.read_pickle(archivo_nuevo)) if os.path.exists(archivo_nuevo) else 0
        print(f"  {dep:<28}: viejo={n_viejo:>5}  nuevo={n_nuevo:>5}")


if __name__ == "__main__":
    main()
