"""
Grupo 8 — 3 departamentos simultáneos
  Cundinamarca : eltiempo + portafolio + publimetro + larepublica  (Playwright)
  La Guajira   : elpilon  (3/3 — separado de Cesar G6 y Magdalena G7)
  Cauca        : diariodelcauca  (1/2 — separado de Huila G10)
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
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[7],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 8 completado en {duracion:.1f} minutos")
