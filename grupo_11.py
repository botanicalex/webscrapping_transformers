"""
Grupo 11 — 2 departamentos simultáneos
  Casanare : diariodecasanare + El Tiempo fallback  (movido desde G5)
  Tolima   : bcnoticias + El Tiempo  (separado de Caldas G3 que también usa bcnoticias)

  Nota: Quindío fue movido a G5 — Casanare caía siempre a El Tiempo y competía
  con Amazonas (también ET) en el grupo anterior. Con solo 2 dptos aquí, si ambos
  usan ET en algún momento la competencia es tolerable (sin un 3er ET user).
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
    departamentos=["Casanare", "Tolima"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
    modo_historico=True,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 11 completado en {duracion:.1f} minutos")
# Casanare (diariodecasanare+ET) + Tolima (bcnoticias+ET) — solo 2 deptos, 1 ET user activo a la vez ✓
