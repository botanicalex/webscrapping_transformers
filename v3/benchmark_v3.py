"""
benchmark_v3.py — Compara v1 vs v3 para ScraperVanguardia y ScraperTrochandoSinFronteras

Métricas medidas:
  Vanguardia:       HTTP status, artículos encontrados, tiempo total
  TrochandoSF:      tiempo de parseo HTML por página (BS4 vs selectolax),
                    artículos encontrados, tiempo total de scrape

Corrida rápida: enero 2023, 1 término ('Santander conflicto' para Vanguardia,
'Arauca social' para Trochando — términos que históricamente traen resultados).
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scrappers import ScraperVanguardia, ScraperTrochandoSinFronteras
from scrappers_v3 import ScraperVanguardiaV3, ScraperTrochandoSinFronterasV3

from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

import requests as _requests


# ─────────────────────────────────────────────────────────────────────────────
# Config del benchmark
# ─────────────────────────────────────────────────────────────────────────────
FECHA_DESDE = "2023-01-01"
FECHA_HASTA = "2023-01-31"
TERMINO_VANGUARDIA  = "Santander conflicto"
TERMINO_TROCHANDO   = "Arauca social"

SEP = "=" * 66


def titulo(s):
    print(f"\n{SEP}")
    print(f"  {s}")
    print(SEP)


def resultado(label, valor, unidad=""):
    print(f"  {label:<40} {valor} {unidad}")


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK 1 — ScraperVanguardia: requests vs curl_cffi
# ══════════════════════════════════════════════════════════════════════════════

titulo("BENCHMARK 1 — Vanguardia: requests vs curl_cffi (TLS fingerprint)")

# ── V1: requests ─────────────────────────────────────────────────────────────
print("\n[V1 - requests]")
t0 = time.perf_counter()
v1 = ScraperVanguardia(TERMINO_VANGUARDIA, FECHA_DESDE, FECHA_HASTA)

# Hacer solo la primera llamada a la API para medir HTTP status
status_v1 = None
try:
    data_v1 = v1._consultar_api(endindex=0)
    total_v1 = int(data_v1.get("metadata", {}).get("total", 0))
    status_v1 = 200
    print(f"  HTTP status: 200 OK  |  Total resultados Queryly: {total_v1}")
except Exception as e:
    status_v1 = getattr(getattr(e, 'response', None), 'status_code', '?')
    print(f"  HTTP status: {status_v1}  |  Error: {e}")
    total_v1 = 0

# Scrape completo solo si la API respondió
arts_v1 = 0
t_scrape_v1 = 0
if total_v1 > 0:
    t_s = time.perf_counter()
    df_v1 = v1.scrape()
    t_scrape_v1 = time.perf_counter() - t_s
    arts_v1 = len(df_v1)
    print(f"  Artículos obtenidos: {arts_v1}  |  Tiempo scrape: {t_scrape_v1:.1f}s")
else:
    print(f"  Sin resultados — omitiendo scrape completo.")

t_v1_total = time.perf_counter() - t0

# ── V3: curl_cffi ─────────────────────────────────────────────────────────────
print("\n[V3 - curl_cffi chrome120]")
t0 = time.perf_counter()
v3 = ScraperVanguardiaV3(TERMINO_VANGUARDIA, FECHA_DESDE, FECHA_HASTA)

status_v3 = None
try:
    data_v3 = v3._consultar_api(endindex=0)
    total_v3 = int(data_v3.get("metadata", {}).get("total", 0))
    status_v3 = 200
    print(f"  HTTP status: 200 OK  |  Total resultados Queryly: {total_v3}")
except Exception as e:
    status_v3 = getattr(getattr(e, 'response', None), 'status_code', '?')
    print(f"  HTTP status: {status_v3}  |  Error: {e}")
    total_v3 = 0

arts_v3 = 0
t_scrape_v3 = 0
if total_v3 > 0:
    t_s = time.perf_counter()
    df_v3 = v3.scrape()
    t_scrape_v3 = time.perf_counter() - t_s
    arts_v3 = len(df_v3)
    print(f"  Artículos obtenidos: {arts_v3}  |  Tiempo scrape: {t_scrape_v3:.1f}s")
else:
    print(f"  Sin resultados — omitiendo scrape completo.")

t_v3_total = time.perf_counter() - t0

# ── Resumen Vanguardia ────────────────────────────────────────────────────────
print(f"\n{'─'*66}")
print(f"  {'':35} {'V1 (requests)':>12}  {'V3 (curl_cffi)':>14}")
print(f"{'─'*66}")
print(f"  {'HTTP status primera llamada':35} {str(status_v1):>12}  {str(status_v3):>14}")
print(f"  {'Total resultados en Queryly':35} {total_v1:>12}  {total_v3:>14}")
print(f"  {'Artículos descargados':35} {arts_v1:>12}  {arts_v3:>14}")
if t_scrape_v1 > 0 and t_scrape_v3 > 0:
    mejora = ((t_scrape_v1 - t_scrape_v3) / t_scrape_v1 * 100)
    print(f"  {'Tiempo scrape (s)':35} {t_scrape_v1:>12.1f}  {t_scrape_v3:>14.1f}")
    print(f"  {'Mejora tiempo':35} {'':>12}  {mejora:>+13.1f}%")
print(f"{'─'*66}")

if status_v1 != 200 and status_v3 == 200:
    print("\n  ✓ curl_cffi RESOLVIO el 403 de Vanguardia")
elif status_v1 == 200 and status_v3 == 200:
    print("\n  ✓ Ambas versiones responden 200 — Queryly API no bloquea por TLS")
elif status_v3 != 200:
    print("\n  ✗ curl_cffi NO resolvió el problema")


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK 2 — TrochandoSinFronteras: BS4 vs selectolax (parseo HTML puro)
# ══════════════════════════════════════════════════════════════════════════════

titulo("BENCHMARK 2 — TrochandoSF: BeautifulSoup vs selectolax (parseo HTML)")

# Descargar una página real de Trochando para el benchmark de parseo
print(f"\n  Descargando página de prueba (Trochando / '{TERMINO_TROCHANDO}')...")
URL_TEST = f"https://trochandosinfronteras.info/?s={TERMINO_TROCHANDO.replace(' ', '+')}"
HEADERS = ScraperTrochandoSinFronteras.HEADERS

try:
    r = _requests.get(URL_TEST, headers=HEADERS, timeout=20)
    html_test = r.text
    print(f"  HTTP {r.status_code} — {len(html_test):,} chars descargados")
except Exception as e:
    print(f"  Error descargando página de prueba: {e}")
    html_test = None

# Benchmark de parseo puro: N iteraciones sobre el mismo HTML
N_ITER = 200
if html_test:
    print(f"\n  Benchmark parseo ({N_ITER} iteraciones sobre el mismo HTML):")

    # BS4
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        soup = BeautifulSoup(html_test, "html.parser")
        _ = soup.find("a", class_="last")
        _ = soup.find("div", class_=lambda c: c and "tdi_96" in c)
    t_bs4 = (time.perf_counter() - t0) / N_ITER * 1000

    # selectolax
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        tree = HTMLParser(html_test)
        _ = list(tree.css("a.last"))
        _ = next((d for d in tree.css("div[class]")
                  if "tdi_96" in (d.attributes.get("class") or "")), None)
    t_sl = (time.perf_counter() - t0) / N_ITER * 1000

    speedup = t_bs4 / t_sl if t_sl > 0 else float('inf')
    print(f"\n  {'':35} {'BS4 (ms/pág)':>12}  {'selectolax (ms/pág)':>20}")
    print(f"  {'─'*66}")
    print(f"  {'Tiempo medio de parseo':35} {t_bs4:>12.2f}  {t_sl:>20.2f}")
    print(f"  {'Speedup selectolax':35} {'':>12}  {speedup:>19.1f}x")

# Scrape completo v1 vs v3 (con límite bajo para el benchmark)
print(f"\n  Scrape completo (max_articulos=50, '{TERMINO_TROCHANDO}'):")

print("\n  [V1 - BeautifulSoup]")
t0 = time.perf_counter()
t1_sf = ScraperTrochandoSinFronteras(TERMINO_TROCHANDO, FECHA_DESDE, FECHA_HASTA, max_articulos=50)
df_t1 = t1_sf.scrape()
t_t1 = time.perf_counter() - t0
arts_t1 = len(df_t1)
print(f"  → {arts_t1} artículos en {t_t1:.1f}s")

print("\n  [V3 - selectolax]")
t0 = time.perf_counter()
t3_sf = ScraperTrochandoSinFronterasV3(TERMINO_TROCHANDO, FECHA_DESDE, FECHA_HASTA, max_articulos=50)
df_t3 = t3_sf.scrape()
t_t3 = time.perf_counter() - t0
arts_t3 = len(df_t3)
print(f"  → {arts_t3} artículos en {t_t3:.1f}s")

mejora_t = ((t_t1 - t_t3) / t_t1 * 100) if t_t1 > 0 else 0
print(f"\n{'─'*66}")
print(f"  {'':35} {'V1 (BS4)':>12}  {'V3 (selectolax)':>15}")
print(f"{'─'*66}")
print(f"  {'Artículos encontrados':35} {arts_t1:>12}  {arts_t3:>15}")
print(f"  {'Tiempo scrape total (s)':35} {t_t1:>12.1f}  {t_t3:>15.1f}")
print(f"  {'Mejora tiempo':35} {'':>12}  {mejora_t:>+14.1f}%")
print(f"{'─'*66}")

if html_test:
    print(f"\n  Parseo HTML (benchmark puro): {speedup:.1f}x más rápido con selectolax")

print(f"\n{SEP}")
print("  BENCHMARK COMPLETADO")
print(f"{SEP}\n")
