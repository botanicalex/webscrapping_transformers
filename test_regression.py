"""Test de regresión: Meta + Arauca, 1-15 enero 2023 — verifica que curl_cffi no rompe nada."""
import os, time, sys
os.makedirs("resultados", exist_ok=True)
sys.path.insert(0, os.path.dirname(__file__))

from scrappers import scrape_multiples_departamentos, _errores_run

FECHA_DESDE = "2023-01-01"
FECHA_HASTA = "2023-01-15"

_errores_run.clear()
t0 = time.time()

scrape_multiples_departamentos(
    departamentos=["Meta", "Arauca"],
    fecha_desde=FECHA_DESDE,
    fecha_hasta=FECHA_HASTA,
    min_menciones=None,
    directorio_salida="resultados",
    temas=None,
)

duracion = (time.time() - t0) / 60
print(f"\n{'='*60}")
print(f"TEST REGRESION completado en {duracion:.1f} minutos")
print(f"{'='*60}")

# Contar errores por tipo
from collections import Counter
tipos = Counter(e['tipo'] for e in _errores_run)
timeouts = tipos.get('TimeoutError', 0)
otros    = sum(v for k, v in tipos.items() if k != 'TimeoutError')
total_e  = len(_errores_run)

print(f"\nReporte de errores (1-15 enero 2023):")
print(f"  TimeoutErrors  : {timeouts}")
print(f"  Otros errores  : {otros}")
print(f"  Total eventos  : {total_e}")

# Cargar resultados
import glob, pickle
for dept in ["meta", "arauca"]:
    pkls = glob.glob(f"resultados/df_corpus_{dept}.pkl")
    if pkls:
        with open(pkls[0], "rb") as f:
            df = pickle.load(f)
        print(f"\n  {dept.capitalize():12} : {len(df):4} artículos")
    else:
        print(f"\n  {dept.capitalize():12} : sin pkl")

if timeouts == 0:
    print("\n  ✓ CERO TimeoutErrors — curl_cffi funcionando correctamente")
elif timeouts < 10:
    print(f"\n  ~ {timeouts} TimeoutErrors — tolerable para 15 días de datos")
else:
    print(f"\n  ✗ {timeouts} TimeoutErrors — revisar curl_cffi o timeouts")
print()
