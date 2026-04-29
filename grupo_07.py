"""
Grupo 7 — 3 departamentos simultáneos
  Norte de Santander : enlacetelevision + corrillos + eltiempo  (Playwright + ET directo — datos 2023)
  Magdalena          : elpilon  (2/3 — separado de Cesar G6 y La Guajira G8)
  Guainía            : [] → El Tiempo  (respaldo; elmorichal caído)
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
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[6],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 7 completado en {duracion:.1f} minutos")
