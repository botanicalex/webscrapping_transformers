"""
Grupo 10 — 3 departamentos simultáneos
  Sucre               : elmeridiano  (2/2 — separado de Córdoba G9)
  Huila               : diariodelcauca + diariodelsur  (resuelto: Cauca→G8, Nariño→G9)
  San Andrés y Prov.  : eltiempo directo
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
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[9],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 10 completado en {duracion:.1f} minutos")
