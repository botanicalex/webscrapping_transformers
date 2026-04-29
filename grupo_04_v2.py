"""
[V2] Grupo 4 — 3 departamentos simultáneos
  Risaralda : eldiario      (rápido)
  Caquetá   : llanoalmundo  (2/3 — separado de Meta G3 y Guaviare G5)
  Putumayo  : [] → El Tiempo (respaldo; miputumayo bloqueado)
"""
from scrappers_v2 import *
import os
import time

FECHA_DESDE = "2023-01-01"
FECHA_HASTA = "2023-12-31"

# ── Términos de búsqueda ──────────────────────────────────────────────────────
# None = usa TEMAS_BUSQUEDA definido en scrappers.py (sección CONFIG).
# Para personalizar solo este grupo, reemplaza None con una lista, por ejemplo:
#   TEMAS = ["conflicto", "comunidades", "social"]
TEMAS = None

DIRECTORIO_SALIDA = "resultados"
os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)

inicio = time.time()

scrape_multiples_departamentos_v2(
    departamentos=["Risaralda", "Caquetá", "Putumayo"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\n[V2] Grupo 4 completado en {duracion:.1f} minutos")
