"""
Worker de scraping para correr en un proceso APARTE.

scrappers.py es "dueño" de su event loop: crea/reemplaza/cierra loops con
asyncio.new_event_loop() + set_event_loop() + loop.close() + set_event_loop(None)
y aplica nest_asyncio, ademas de usar Playwright (async). Ese patron esta pensado
para ejecutarse como script suelto. Corrido DENTRO de uvicorn (que ya tiene su
propio event loop) desarma el loop del server y este se apaga limpio.

La solucion es ejecutar el scraping en un subproceso 'spawn' (interprete fresco,
sin el event loop de uvicorn ni la sesion CUDA del proceso principal). Este modulo
es el punto de entrada del subproceso: NO importa api.py ni torch, asi que el
spawn no vuelve a cargar el modelo NLI. `scrappers` se importa de forma diferida
dentro de la funcion (arrastra playwright/aiohttp), no al importar el modulo.
"""
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)


def scrape(termino, fecha_desde, fecha_hasta, periodicos):
    """Corre scrappers.scrape_municipio y devuelve el DataFrame (picklable).
    Se ejecuta en el subproceso; el import de scrappers ocurre aca."""
    import scrappers as sc
    return sc.scrape_municipio(
        municipio=termino,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        periodicos=periodicos,
        min_menciones=1,
    )
