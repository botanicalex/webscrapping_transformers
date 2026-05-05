"""
Grupo 3 — 3 departamentos simultáneos
  Caldas  : bcnoticias    (rápido; separado de Tolima G11 que también usa bcnoticias)
  Meta    : llanoalmundo  (1/3 — separado de Caquetá G4 y Guaviare G5)
  Bolívar : [] → El Tiempo (respaldo)
"""
from scrappers import *
import os
import time

FECHA_DESDE = "2023-01-01"
FECHA_HASTA = "2023-12-31"

TEMAS = None

DIRECTORIO_SALIDA = "resultados"
os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)

inicio = time.time()

scrape_multiples_departamentos(
    departamentos=["Caldas", "Meta", "Bolívar"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
    modo_historico=True,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 3 completado en {duracion:.1f} minutos")
