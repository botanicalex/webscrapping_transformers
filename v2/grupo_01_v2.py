"""
[V2] Grupo 1 — 3 departamentos simultáneos
  Antioquia  : elcolombiano  (rápido)
  Chocó      : choco7dias    (LENTO — ~35 % éxito, timeout 600 s)
  Vichada    : [] → El Tiempo (respaldo)
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
    departamentos=["Antioquia", "Chocó", "Vichada"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,        # usa DEPARTAMENTO_MIN_MENCIONES por dpto
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,               # None = usa TEMAS_BUSQUEDA global de scrappers.py
)

duracion = (time.time() - inicio) / 60
print(f"\n[V2] Grupo 1 completado en {duracion:.1f} minutos")
