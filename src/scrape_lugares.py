"""
Scraping de lugares sub-departamentales (veredas / municipios) para el
calculo de indicadores.

IMPORTANTE — el filtro de relevancia de scrappers.py (_es_relevante) usa
SOLO LA PRIMERA PALABRA del termino de busqueda:

    territorio = self.termino.split()[0].lower()

Por eso 'nombre' NUNCA debe llevar el prefijo 'Vereda' o 'Municipio':
si se pasa "Vereda Paraguachon", el filtro contaria menciones de la palabra
"vereda" y devolveria basura. Se pasa solo "Paraguachon".

La etiqueta descriptiva va en 'etiqueta', que se escribe en la columna
'departamento' (nombre que espera el pipeline aguas abajo para agrupar).

Salida: un pkl por lugar en corpus_lugares/
"""
import os
import time
import unicodedata

import pandas as pd

import scrappers as sc

# Rango: agosto 2025 -> fecha actual
FECHA_DESDE = "2025-08-01"
FECHA_HASTA = "2026-08-17"

DIR_SALIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos", "corpus")

# nombre     -> termino real de busqueda (SIN 'Vereda'/'Municipio')
# etiqueta   -> nombre completo, va a la columna 'departamento'
# periodicos -> segun DEPARTAMENTO_PERIODICOS del depto que lo contiene
#               La Guajira -> elpilon | Boyaca -> eltiempo
# min_menciones=1 -> son lugares pequenos, rara vez repetidos en el texto
LUGARES = [
    {"nombre": "Paraguachón", "etiqueta": "Vereda Paraguachón",  "periodicos": ["diariodelnorte", "laguajirahoy", "elpilon", "eltiempo"], "min_menciones": 1},
    {"nombre": "Maicao",      "etiqueta": "Municipio Maicao",    "periodicos": ["diariodelnorte", "laguajirahoy", "elpilon", "eltiempo"], "min_menciones": 1},
    {"nombre": "Güintiva",    "etiqueta": "Vereda Güintiva",     "periodicos": ["boyaca7dias", "eltiempo"],                               "min_menciones": 1},
    {"nombre": "Oicatá",      "etiqueta": "Municipio Oicatá",    "periodicos": ["boyaca7dias", "eltiempo"],                               "min_menciones": 1},
]


def slug(txt: str) -> str:
    t = unicodedata.normalize("NFD", str(txt).lower()).encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() else "_" for c in t).strip("_")


def main():
    os.makedirs(DIR_SALIDA, exist_ok=True)
    print(f"Periodo: {FECHA_DESDE} -> {FECHA_HASTA}")
    print(f"Temas ({len(sc.TEMAS_BUSQUEDA)}): {sc.TEMAS_BUSQUEDA}")
    print(f"Salida: {DIR_SALIDA}\n")

    resumen = []
    for lugar in LUGARES:
        nombre, etiqueta = lugar["nombre"], lugar["etiqueta"]
        print(f"\n{'='*70}\n>> {etiqueta}  (termino de busqueda: '{nombre}')\n{'='*70}")
        t0 = time.time()
        try:
            df = sc.scrape_municipio(
                municipio=nombre,
                fecha_desde=FECHA_DESDE,
                fecha_hasta=FECHA_HASTA,
                periodicos=lugar["periodicos"],
                min_menciones=lugar["min_menciones"],
            )
        except Exception as e:
            print(f"  ERROR en {etiqueta}: {e}")
            resumen.append((etiqueta, -1, None))
            continue

        mins = (time.time() - t0) / 60
        if df is None or df.empty:
            print(f"  {etiqueta}: 0 articulos ({mins:.1f} min)")
            resumen.append((etiqueta, 0, None))
            continue

        # El pipeline aguas abajo agrupa por 'departamento'
        df["departamento"] = etiqueta
        ruta = os.path.join(DIR_SALIDA, f"df_corpus_{slug(etiqueta)}.pkl")
        df.to_pickle(ruta)
        print(f"  {etiqueta}: {len(df)} articulos ({mins:.1f} min) -> {ruta}")
        resumen.append((etiqueta, len(df), ruta))

    print(f"\n{'='*70}\nRESUMEN\n{'='*70}")
    for etiqueta, n, ruta in resumen:
        estado = "ERROR" if n < 0 else (f"{n} articulos" if n else "SIN RESULTADOS")
        print(f"  {etiqueta:<26} {estado}")


if __name__ == "__main__":
    main()
