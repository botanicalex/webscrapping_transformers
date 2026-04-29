"""
[V2] Grupo 8 — 3 departamentos simultáneos
  Cundinamarca : eltiempo + portafolio + publimetro + larepublica  (Playwright)
  La Guajira   : elpilon  (3/3 — separado de Cesar G6 y Magdalena G7)
  Cauca        : diariodelcauca  (1/2 — separado de Huila G10)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
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

DIRECTORIO_SALIDA = os.path.join(os.path.dirname(__file__), "..", "resultados")
os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)

inicio = time.time()

scrape_multiples_departamentos_v2(
    departamentos=["Cundinamarca", "La Guajira", "Cauca"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\n[V2] Grupo 8 completado en {duracion:.1f} minutos")
