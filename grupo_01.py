"""
Grupo 1 — 3 departamentos simultáneos
  Antioquia  : elcolombiano  (rápido)
  Chocó      : choco7dias    (LENTO — ~35 % éxito, timeout 600 s)
  Vichada    : [] → El Tiempo (respaldo)
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
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[0],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 1 completado en {duracion:.1f} minutos")
