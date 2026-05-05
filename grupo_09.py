"""
Grupo 9 — 3 departamentos simultáneos
  Córdoba : elmeridiano  (1/2 — separado de Sucre G10)
  Nariño  : diariodelsur (1/2 — separado de Huila G10)
  Vaupés  : eltiempo directo
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
    departamentos=["Córdoba", "Nariño", "Vaupés"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
    modo_historico=True,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 9 completado en {duracion:.1f} minutos")
