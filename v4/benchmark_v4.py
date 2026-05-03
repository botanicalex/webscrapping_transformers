"""
benchmark_v4.py — aiohttp vs curl_cffi en descargas de artículos

Mide para LlanoAlMundo (el scraper con más timeouts: 422 en corridas históricas):
  - Artículos descargados exitosamente
  - Número de timeouts/errores
  - Tiempo total de descarga
  - Tasa de éxito (%)

Si curl_cffi mejora la tasa de éxito, aplicar a todos los scrapers
con _descargar_articulo_async.

Corrida: Meta conflicto / enero 2023 (rango corto para benchmark rápido).
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import scrappers as v1
from scrappers_v4 import ScraperLlanoAlMundoV4, ScraperLaVozDelCinarucoV4


FECHA_DESDE = "2023-01-01"
FECHA_HASTA = "2023-01-31"
SEP = "=" * 70


def titulo(s):
    print(f"\n{SEP}\n  {s}\n{SEP}")


def correr_scraper(scraper_cls, termino, label):
    """Corre un scraper y devuelve (artículos, timeouts, tiempo_s)."""
    # Capturar errores registrados antes de la corrida
    errores_antes = len(v1._errores_run)

    t0 = time.perf_counter()
    scraper = scraper_cls(termino, FECHA_DESDE, FECHA_HASTA)
    df = scraper.scrape()
    t_total = time.perf_counter() - t0

    # Contar TimeoutErrors registrados en esta corrida
    errores_nuevos = [e for e in v1._errores_run[errores_antes:]
                      if e.get('tipo') == 'TimeoutError']
    n_timeouts = len(errores_nuevos)

    n_arts = len(df)
    tasa = (n_arts / max(n_arts + n_timeouts, 1)) * 100

    print(f"\n  [{label}] Resultado: {n_arts} arts | {n_timeouts} timeouts | "
          f"tasa éxito ~{tasa:.0f}% | {t_total:.1f}s")
    return n_arts, n_timeouts, t_total


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK 1 — LlanoAlMundo: aiohttp vs curl_cffi
# ══════════════════════════════════════════════════════════════════════════════

titulo("BENCHMARK 1 — LlanoAlMundo: aiohttp vs curl_cffi (Meta, enero 2023)")

TERMINO = "Meta conflicto"

# Reiniciar errores
v1._errores_run = []

print(f"\n  Término: '{TERMINO}' | {FECHA_DESDE} → {FECHA_HASTA}")
print(f"\n[V1 - aiohttp + TCPConnector(limit=5)]")
arts_v1, to_v1, t_v1 = correr_scraper(v1.ScraperLlanoAlMundo, TERMINO, "V1 aiohttp")

print(f"\n[V4 - curl_cffi AsyncSession(impersonate=chrome120, limit=5)]")
arts_v4, to_v4, t_v4 = correr_scraper(ScraperLlanoAlMundoV4, TERMINO, "V4 curl_cffi")

# Resumen
tasa_v1 = arts_v1 / max(arts_v1 + to_v1, 1) * 100
tasa_v4 = arts_v4 / max(arts_v4 + to_v4, 1) * 100
mejora_arts    = arts_v4 - arts_v1
mejora_timeouts= to_v1   - to_v4
mejora_tasa    = tasa_v4 - tasa_v1

print(f"\n{'─'*70}")
print(f"  {'':40} {'V1 (aiohttp)':>12}  {'V4 (curl_cffi)':>14}")
print(f"{'─'*70}")
print(f"  {'Artículos descargados':40} {arts_v1:>12}  {arts_v4:>14}")
print(f"  {'TimeoutErrors':40} {to_v1:>12}  {to_v4:>14}  "
      f"({'↓' if mejora_timeouts > 0 else '↑'}{abs(mejora_timeouts):+d})")
print(f"  {'Tasa de éxito (arts / arts+timeouts)':40} {tasa_v1:>11.0f}%  {tasa_v4:>13.0f}%  "
      f"({mejora_tasa:+.0f}pp)")
print(f"  {'Tiempo total (s)':40} {t_v1:>12.1f}  {t_v4:>14.1f}")
print(f"{'─'*70}")

if mejora_tasa > 5:
    print(f"\n  ✓ curl_cffi MEJORA la tasa de éxito (+{mejora_tasa:.0f}pp) — recomienda migración")
elif mejora_tasa > 0:
    print(f"\n  ~ Mejora marginal (+{mejora_tasa:.0f}pp) — revisar con muestra más grande")
else:
    print(f"\n  ✗ curl_cffi NO mejora — los timeouts son de red/servidor, no de TLS fingerprint")


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK 2 — LaVozDelCinaruco: aiohttp vs curl_cffi
# ══════════════════════════════════════════════════════════════════════════════

titulo("BENCHMARK 2 — LaVozDelCinaruco: aiohttp vs curl_cffi (Arauca, enero 2023)")

TERMINO2 = "Arauca conflicto"
v1._errores_run = []

print(f"\n  Término: '{TERMINO2}' | {FECHA_DESDE} → {FECHA_HASTA}")
print(f"\n[V1 - aiohttp + TCPConnector(limit=5)]")
arts2_v1, to2_v1, t2_v1 = correr_scraper(v1.ScraperLaVozDelCinaruco, TERMINO2, "V1 aiohttp")

print(f"\n[V4 - curl_cffi AsyncSession(chrome120, limit=5)]")
arts2_v4, to2_v4, t2_v4 = correr_scraper(ScraperLaVozDelCinarucoV4, TERMINO2, "V4 curl_cffi")

tasa2_v1 = arts2_v1 / max(arts2_v1 + to2_v1, 1) * 100
tasa2_v4 = arts2_v4 / max(arts2_v4 + to2_v4, 1) * 100

print(f"\n{'─'*70}")
print(f"  {'':40} {'V1 (aiohttp)':>12}  {'V4 (curl_cffi)':>14}")
print(f"{'─'*70}")
print(f"  {'Artículos descargados':40} {arts2_v1:>12}  {arts2_v4:>14}")
print(f"  {'TimeoutErrors':40} {to2_v1:>12}  {to2_v4:>14}")
print(f"  {'Tasa de éxito':40} {tasa2_v1:>11.0f}%  {tasa2_v4:>13.0f}%  "
      f"({tasa2_v4 - tasa2_v1:+.0f}pp)")
print(f"  {'Tiempo total (s)':40} {t2_v1:>12.1f}  {t2_v4:>14.1f}")
print(f"{'─'*70}")


# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN Y RECOMENDACIÓN
# ══════════════════════════════════════════════════════════════════════════════

print(f"\n{SEP}")
print("  VEREDICTO FINAL")
print(f"{SEP}")

mejora_llano  = tasa_v4  - tasa_v1
mejora_cinaruco = tasa2_v4 - tasa2_v1
mejora_media  = (mejora_llano + mejora_cinaruco) / 2

if mejora_media > 10:
    print(f"""
  curl_cffi RESUELVE el problema de timeouts:
    LlanoAlMundo    : {mejora_llano:+.0f}pp de tasa de éxito
    LaVozDelCinaruco: {mejora_cinaruco:+.0f}pp de tasa de éxito

  RECOMENDACIÓN: aplicar _CurlDownloadMixin a TODOS los scrapers
  con _descargar_articulo_async (20+ scrapers en scrappers.py).
  Hacerlo en una sola edición global en lugar de clase por clase.
""")
elif mejora_media > 0:
    print(f"""
  Mejora marginal ({mejora_media:+.0f}pp promedio).
  Los timeouts son probablemente de red/servidor, no de TLS fingerprint.
  Mantener aiohttp — curl_cffi no justifica el cambio.
""")
else:
    print(f"""
  Sin mejora. Los timeouts son de red/servidor (latencia, ancho de banda,
  rate limiting por IP). TLS fingerprint no es el factor bloqueante.
  Seguir con aiohttp + timeout=60s + limit=5.
""")

print(f"{SEP}\n")
