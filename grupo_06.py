"""
Grupo 6 — 3 departamentos simultáneos  [REBALANCEADO]
  Santander         : enlacetelevision + corrillos + eltiempo  (ET como 1 de 3 scrapers)
  Norte de Santander: enlacetelevision + corrillos + eltiempo  (ET como 1 de 3 scrapers)
  Cesar             : elpilon  (separado de Magdalena G7 y La Guajira G8)

  Rebalanceo vs versión anterior (Santander + Cesar + Boyacá):
    Santander y Norte de Santander usan ET solo como respaldo parcial — se turnan
    via semáforo. Boyacá (solo ET) fue movido a G7 con compañía ligera.
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
    departamentos=["Santander", "Norte de Santander", "Cesar"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida=DIRECTORIO_SALIDA,
    temas=TEMAS,
    modo_historico=True,
)

duracion = (time.time() - inicio) / 60
print(f"\nGrupo 6 completado en {duracion:.1f} minutos")
