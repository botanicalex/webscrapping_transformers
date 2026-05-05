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
    departamentos=["Quindío", "Guaviare", "Amazonas"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,`n    modo_historico=True,`n)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 5 completado en {duracion:.1f} minutos")
# Quindío (elquindiano) + Guaviare (llanoalmundo) + Amazonas (El Tiempo) — 1 ET user ✓

