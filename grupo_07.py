"""
Grupo 7 — 3 departamentos simultáneos  [REBALANCEADO]
  Boyacá    : eltiempo directo  (solo ET — pero acompañado de scrapers ligeros)
  Magdalena : elpilon  (2/3 — separado de Cesar G6 y La Guajira G8)
  Guainía   : [] → El Tiempo (respaldo; elmorichal caído)

  Rebalanceo vs versión anterior (Norte de Santander + Magdalena + Guainía):
    Norte de Santander fue movido a G6 con Santander (ambos usan ET parcialmente).
    Boyacá (solo ET) + Guainía (solo ET) se serializan via semáforo — aceptable
    porque Magdalena (elpilon) no usa ET y es rápido.
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
    departamentos=["Boyacá", "Magdalena", "Guainía"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
    modo_historico=True,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 7 completado en {duracion:.1f} minutos")
