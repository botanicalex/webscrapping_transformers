"""
Grupo 6 — 3 departamentos simultáneos
  Santander : enlacetelevision + corrillos + eltiempo  (Playwright + ET directo — datos 2023)
  Cesar     : elpilon  (1/3 — separado de Magdalena G7 y La Guajira G8)
  Boyacá    : eltiempo directo
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
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[5],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 6 completado en {duracion:.1f} minutos")
