"""
Grupo 10 — 3 departamentos simultáneos
  Sucre               : elmeridiano  (2/2 — separado de Córdoba G9)
  Huila               : diariodelcauca + diariodelsur  (resuelto: Cauca→G8, Nariño→G9)
  San Andrés y Prov.  : eltiempo directo
"""
from scrappers import *
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

scrape_multiples_departamentos(
    departamentos=["Sucre", "Huila", "San Andrés y Providencia"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,`n    modo_historico=True,`n)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 10 completado en {duracion:.1f} minutos")

