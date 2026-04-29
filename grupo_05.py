"""
Grupo 5 — 3 departamentos simultáneos
  Quindío  : elquindiano       (rápido)
  Guaviare : llanoalmundo      (3/3 — separado de Meta G3 y Caquetá G4)
  Amazonas : [] → El Tiempo    (respaldo; miputumayo bloqueado)

  Nota: Casanare fue movido a G11 — cuando Casanare y Amazonas corrían juntos
  en este grupo ambos caían a El Tiempo (diariodecasanare insuficiente) y
  competían por el mismo servidor, retornando 0 artículos para los dos.
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
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[4],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 5 completado en {duracion:.1f} minutos")
