"""
Grupo 11 — 2 departamentos simultáneos  (32 % 3 == 2)
  Casanare : diariodecasanare + El Tiempo fallback  (movido desde G5)
  Tolima   : bcnoticias + El Tiempo  (separado de Caldas G3 que también usa bcnoticias)

  Nota: Quindío fue movido a G5 — Casanare caía siempre a El Tiempo y competía
  con Amazonas (también ET) en el grupo anterior. Con solo 2 dptos aquí, si ambos
  usan ET en algún momento la competencia es tolerable (sin un 3er ET user).
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
    departamentos=cfg.GRUPOS_DEPARTAMENTOS[10],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 11 completado en {duracion:.1f} minutos")
