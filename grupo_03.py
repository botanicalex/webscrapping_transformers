"""
Grupo 3 — 3 departamentos simultáneos
  Caldas  : bcnoticias    (rápido; separado de Tolima que también usa bcnoticias)
  Meta    : llanoalmundo  (1/3 — separado de Caquetá G4 y Guaviare G5)
  Bolívar : [] → El Tiempo (respaldo)
"""
from scrappers import *
import config_pipeline as cfg
import os
import time

FECHA_DESDE = cfg.FECHA_DESDE
FECHA_HASTA = cfg.FECHA_HASTA

TEMAS = None

DIRECTORIO_SALIDA = cfg.RUTA_CORPUS_PKL
os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)

inicio = time.time()

scrape_multiples_departamentos(
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[2],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 3 completado en {duracion:.1f} minutos")
