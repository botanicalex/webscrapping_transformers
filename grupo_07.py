"""
Grupo 7 — 3 departamentos simultáneos
  Norte de Santander : enlacetelevision + corrillos + eltiempo  (Playwright + ET directo — datos 2023)
  Magdalena          : elpilon  (2/3 — separado de Cesar G6 y La Guajira G8)
  Guainía            : [] → El Tiempo  (respaldo; elmorichal caído)
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
    departamentos=["Norte de Santander", "Magdalena", "Guainía"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 7 completado en {duracion:.1f} minutos")
