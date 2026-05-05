#!/usr/bin/env python3
"""
health_check.py — Verifica el estado de cada scraper del pipeline.

Corre cada scraper con su término representativo del departamento de cobertura,
ventana de 90 días (últimos 3 meses), y reporta:

  Status:
    OK            arts > 0, tiempo < 120s
    Lento         arts > 0, tiempo ≥ 120s
    Sin_resultados arts == 0, HTTP=200, sin excepción
                  (scraper funciona; sin contenido para ese término/período)
    Roto          excepción, HTTP ≠ 200, o timeout

  Campos JSON por scraper:
    status, arts, tiempo_s, tipo, http_status, error

Genera health_report.json e imprime resumen visual en consola.

Uso:
    python health_check.py                      # todos los scrapers
    python health_check.py elcolombiano         # solo uno
    python health_check.py --tipo wp_api        # todos de un tipo
    python health_check.py --output reporte.json
"""

import sys
import os
import json
import time
import argparse
import warnings
import requests as _requests
from datetime import date, timedelta
from concurrent.futures import (
    ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout
)

warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Importar pipeline ─────────────────────────────────────────────────────────
try:
    import scrappers as _s
    SCRAPERS = _s.GestorScraping.SCRAPERS
    SCRAPERS_PLAYWRIGHT = _s.GestorScraping.SCRAPERS_PLAYWRIGHT
except Exception as exc:
    print(f"ERROR al importar scrappers: {exc}")
    sys.exit(1)

# ── Parámetros globales ───────────────────────────────────────────────────────
FECHA_HASTA = date.today().isoformat()
FECHA_DESDE = (date.today() - timedelta(days=90)).isoformat()

# Timeouts base (segundos)
TIMEOUT_FAST       = 120   # scrapers requests/API normales
TIMEOUT_PLAYWRIGHT = 180   # scrapers Playwright (Chromium)
UMBRAL_LENTO       = 60    # arts > 0 pero tardó ≥ 60s → Lento

# Timeouts extra para scrapers confirmados lentos
TIMEOUT_POR_SCRAPER: dict[str, int] = {
    "eltiempo":         200,   # curl_cffi ~113s para 76 arts con sem=5; dar margen
    "miputumayo":       180,   # servidor muy lento (<20% éxito con 90s)
    "lavozdelcinaruco": 180,   # servidor lento confirmado
    "diariodelsur":     300,   # servidor muy lento; Nariño + Huila
    "portafolio":       300,   # ~10s/página × 15 páginas = 150s solo en links
}


def _timeout_para(pid: str) -> int:
    """Timeout en segundos para un scraper específico."""
    if pid in TIMEOUT_POR_SCRAPER:
        return TIMEOUT_POR_SCRAPER[pid]
    return TIMEOUT_PLAYWRIGHT if pid in SCRAPERS_PLAYWRIGHT else TIMEOUT_FAST


# ── Término representativo por scraper ───────────────────────────────────────
# Usa el departamento principal de cobertura para simular búsqueda real.
TERMINO_POR_SCRAPER: dict[str, str] = {
    # Eje Cafetero / Antioquia
    "eldiario":               "Risaralda conflicto",
    "elcolombiano":           "Antioquia conflicto",
    "bcnoticias":             "Caldas conflicto",
    "elquindiano":            "Quindío conflicto",
    # Suroccidente / Pacífico
    "elpais":                 "Valle del Cauca conflicto",
    "diariooccidente":        "Valle del Cauca conflicto",
    "diariodelsur":           "Nariño conflicto",
    "diariodelcauca":         "Cauca conflicto",
    "choco7dias":             "Chocó conflicto",
    # Orinoquía / Amazonía
    "llanoalmundo":           "Meta conflicto",
    "diariodecasanare":       "Casanare conflicto",
    "lavozdelcinaruco":       "Arauca conflicto",
    "elmorichal":             "Vichada conflicto",
    "miputumayo":             "Putumayo conflicto",
    # Central (Bogotá / Nacionales)
    "eltiempo":               "Colombia conflicto",
    "larepublica":            "Colombia economía",
    "portafolio":             "Colombia economía",
    "publimetro":             "Colombia noticias",
    "verdadabierta":          "Colombia conflicto",
    # Caribe
    "elheraldo":              "Atlántico conflicto",
    "eluniversal":            "Bolívar conflicto",
    "elpilon":                "Cesar conflicto",
    "elmeridiano":            "Córdoba conflicto",
    # Nororiente
    "vanguardia":             "Santander conflicto",
    "tronchandosinfronteras": "Catatumbo conflicto",
    "enlacetelevision":       "Norte de Santander conflicto",
    "corrillos":              "Nariño conflicto",
}

# ── Tipo tecnológico por scraper ──────────────────────────────────────────────
# Leído del atributo TIPO de cada clase (Mejora 5).
TIPO_POR_SCRAPER: dict[str, str] = {
    pid: getattr(cls, 'TIPO', 'html_static')
    for pid, cls in SCRAPERS.items()
}

# URL base para chequeo de conectividad (scrapers sin BASE_URL explícito)
_BASE_URL_OVERRIDE: dict[str, str] = {
    "elcolombiano": "https://www.elcolombiano.com",
    "eltiempo":     "https://www.eltiempo.com",
    "elheraldo":    "https://www.elheraldo.co",
    "larepublica":  "https://www.larepublica.co",
}

# Statuses válidos (para ordenar en el resumen)
_STATUS_ORDEN = ["OK", "Lento", "Sin_resultados", "Roto"]


# ── Utilidades ────────────────────────────────────────────────────────────────

def _get_base_url(pid: str) -> str | None:
    if pid in _BASE_URL_OVERRIDE:
        return _BASE_URL_OVERRIDE[pid]
    cls = SCRAPERS.get(pid)
    return getattr(cls, "BASE_URL", None) if cls else None


def _http_status(pid: str) -> int | None:
    """HEAD/GET rápido al BASE_URL; devuelve código HTTP o None si falla."""
    url = _get_base_url(pid)
    if not url:
        return None
    headers = {"User-Agent": "Mozilla/5.0 (health-check/1.0)"}
    try:
        r = _requests.head(url, timeout=8, allow_redirects=True, headers=headers)
        return r.status_code
    except Exception:
        pass
    try:
        r = _requests.get(url, timeout=8, allow_redirects=True, headers=headers)
        return r.status_code
    except Exception:
        return None


def _site_accesible(pid: str, http_status: int | None) -> bool:
    """
    Determina si el sitio está accesible.
    Usa el http_status ya obtenido; si es None (no determinado), intenta de nuevo.
    """
    if http_status is not None:
        return 200 <= http_status < 400
    # Segunda oportunidad si el status no se obtuvo antes
    s = _http_status(pid)
    return s is not None and 200 <= s < 400


def _make_timeout_result(pid: str, elapsed: float, timeout_s: int) -> dict:
    return {
        "status":      "Roto",
        "arts":        0,
        "tiempo_s":    round(elapsed, 1),
        "tipo":        TIPO_POR_SCRAPER.get(pid, "html_static"),
        "http_status": None,
        "error":       f"Timeout después de {timeout_s}s — scraper no respondió",
    }


def _make_error_result(pid: str, elapsed: float, exc: Exception,
                       http_status: int | None = None) -> dict:
    return {
        "status":      "Roto",
        "arts":        0,
        "tiempo_s":    round(elapsed, 1),
        "tipo":        TIPO_POR_SCRAPER.get(pid, "html_static"),
        "http_status": http_status,
        "error":       f"{type(exc).__name__}: {str(exc)[:300]}",
    }


def _print_result(pid: str, result: dict) -> None:
    _icons = {
        "OK":             "✅",
        "Lento":          "⚠️ ",
        "Sin_resultados": "⚪",
        "Roto":           "❌",
    }
    icon = _icons.get(result["status"], "❓")
    http = f"  HTTP={result['http_status']}" if result["http_status"] else ""
    err  = f"  → {result['error'][:60]}" if result.get("error") else ""
    status_str = result["status"]
    print(f"  {icon} {pid:<25} {status_str:<14}  "
          f"{result['arts']:>3} arts  {result['tiempo_s']:>6.1f}s"
          f"{http}{err}")


# ── Runner por scraper ────────────────────────────────────────────────────────

def _run_scraper(pid: str) -> dict:
    """
    Ejecuta un scraper completo y devuelve métricas.
    Siempre devuelve un dict — nunca lanza excepción al llamador.

    Lógica de status:
      OK            arts > 0, elapsed < UMBRAL_LENTO
      Lento         arts > 0, elapsed ≥ UMBRAL_LENTO
      Sin_resultados arts == 0, sin excepción, sitio accesible (HTTP 200)
      Roto          excepción | sitio inaccesible | timeout (en wrapper)
    """
    scraper_cls = SCRAPERS[pid]
    termino     = TERMINO_POR_SCRAPER.get(pid, "Colombia conflicto")
    tipo        = TIPO_POR_SCRAPER.get(pid, "html_static")

    # Chequeo de conectividad ANTES del scrape (independiente del contenido)
    http_status = _http_status(pid)

    t0 = time.perf_counter()
    try:
        scraper = scraper_cls(termino, FECHA_DESDE, FECHA_HASTA)
        df = scraper.scrape()
        elapsed = time.perf_counter() - t0

        arts = len(df)

        if arts > 0:
            status = "Lento" if elapsed >= UMBRAL_LENTO else "OK"
            error  = None
        else:
            # 0 artículos: distinguir scraper roto de sitio sin contenido
            if _site_accesible(pid, http_status):
                # Sitio responde HTTP 200 → el scraper funciona,
                # simplemente no hay artículos con este término en 90 días
                status = "Sin_resultados"
                error  = f"0 arts en 90 días para '{termino}' (sitio HTTP {http_status} OK)"
            else:
                # Sitio no accesible → scraper realmente roto
                status = "Roto"
                error  = (f"0 arts y sitio inaccesible "
                          f"(HTTP={http_status})")

        return {
            "status":      status,
            "arts":        arts,
            "tiempo_s":    round(elapsed, 1),
            "tipo":        tipo,
            "http_status": http_status,
            "error":       error,
        }

    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return _make_error_result(pid, elapsed, exc, http_status)


# ── Ejecución paralela / secuencial ──────────────────────────────────────────

def _run_fast_batch(targets: list[str]) -> dict[str, dict]:
    """Corre scrapers no-Playwright en paralelo (hasta 6 workers)."""
    resultados: dict[str, dict] = {}
    if not targets:
        return resultados

    # Timeout global del batch = el más largo entre los targets + buffer
    batch_timeout = max(_timeout_para(p) for p in targets) + 30

    print(f"\n  [Paralelos — {len(targets)} scrapers, hasta 6 workers]\n")

    with ThreadPoolExecutor(max_workers=6) as pool:
        fut_to_pid = {pool.submit(_run_scraper, pid): pid for pid in targets}

        try:
            for future in as_completed(fut_to_pid, timeout=batch_timeout):
                pid = fut_to_pid[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = _make_error_result(pid, 0.0, exc)
                resultados[pid] = result
                _print_result(pid, result)

        except FutureTimeout:
            for fut, pid in fut_to_pid.items():
                if pid not in resultados:
                    t = _timeout_para(pid)
                    result = _make_timeout_result(pid, t, t)
                    resultados[pid] = result
                    _print_result(pid, result)

    return resultados


def _run_playwright_batch(targets: list[str]) -> dict[str, dict]:
    """Corre scrapers Playwright de forma secuencial."""
    resultados: dict[str, dict] = {}
    if not targets:
        return resultados

    print(f"\n  [Playwright — {len(targets)} scrapers, secuencial]\n")

    for pid in targets:
        print(f"  🎭 {pid:<25} corriendo...")
        t0 = time.perf_counter()
        timeout = _timeout_para(pid)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_scraper, pid)
                try:
                    result = future.result(timeout=timeout)
                except FutureTimeout:
                    elapsed = time.perf_counter() - t0
                    result  = _make_timeout_result(pid, elapsed, timeout)
                except Exception as exc:
                    elapsed = time.perf_counter() - t0
                    result  = _make_error_result(pid, elapsed, exc)
        except Exception as exc:
            result = _make_error_result(pid, time.perf_counter() - t0, exc)

        resultados[pid] = result
        _print_result(pid, result)

    return resultados


# ── Resumen y JSON ────────────────────────────────────────────────────────────

def _construir_resumen(resultados: dict[str, dict]) -> dict:
    by_status: dict[str, list[str]] = {s: [] for s in _STATUS_ORDEN}
    for pid, r in resultados.items():
        st = r["status"]
        if st in by_status:
            by_status[st].append(pid)

    por_tipo: dict[str, dict] = {}
    for pid, r in resultados.items():
        t  = r.get("tipo", "desconocido")
        st = r["status"].lower().replace("_resultados", "")  # sin_resultados→sin
        if t not in por_tipo:
            por_tipo[t] = {"ok": 0, "lento": 0, "sin_resultados": 0, "roto": 0}
        key = r["status"].lower()
        if key in por_tipo[t]:
            por_tipo[t][key] += 1

    return {
        "total":          len(resultados),
        "ok":             len(by_status["OK"]),
        "lento":          len(by_status["Lento"]),
        "sin_resultados": len(by_status["Sin_resultados"]),
        "roto":           len(by_status["Roto"]),
        "por_tipo":       por_tipo,
    }


def _imprimir_resumen(resumen: dict, resultados: dict[str, dict]) -> None:
    by_status: dict[str, list[str]] = {s: [] for s in _STATUS_ORDEN}
    for pid, r in resultados.items():
        st = r["status"]
        if st in by_status:
            by_status[st].append(pid)

    def _fmt(names: list[str], max_show: int = 10) -> str:
        if not names:
            return "—"
        if len(names) <= max_show:
            return ", ".join(names)
        return ", ".join(names[:max_show]) + f" (+{len(names) - max_show} más)"

    sep = "=" * 65
    print(f"\n{sep}")
    print(f"  HEALTH REPORT — {date.today()}  |  {FECHA_DESDE} → {FECHA_HASTA}")
    print(sep)
    print(f"  ✅ OK             ({resumen['ok']:>2}): {_fmt(by_status['OK'])}")
    print(f"  ⚠️  Lento          ({resumen['lento']:>2}): {_fmt(by_status['Lento'])}")
    print(f"  ⚪ Sin_resultados  ({resumen['sin_resultados']:>2}): "
          f"{_fmt(by_status['Sin_resultados'])}")
    print(f"  ❌ Roto           ({resumen['roto']:>2}): {_fmt(by_status['Roto'])}")

    if resumen["roto"] > 0:
        print(f"\n  Scrapers Rotos — detalle:")
        for pid in by_status["Roto"]:
            r = resultados[pid]
            print(f"    {pid:<25} HTTP={r['http_status']}  "
                  f"{(r.get('error') or '')[:60]}")

    print(f"\n  Por tipo:")
    for tipo, stats in sorted(resumen["por_tipo"].items()):
        barra = ("✅" * stats.get("ok", 0)
                 + "⚠️ " * stats.get("lento", 0)
                 + "⚪" * stats.get("sin_resultados", 0)
                 + "❌" * stats.get("roto", 0))
        print(f"    {tipo:<14}: OK={stats.get('ok',0)}  "
              f"Lento={stats.get('lento',0)}  "
              f"Sin={stats.get('sin_resultados',0)}  "
              f"Roto={stats.get('roto',0)}  {barra}")
    print(sep)


# ── CLI principal ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Health check del pipeline de scraping colombiano",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "scraper", nargs="?",
        help="ID de scraper específico (ej: elcolombiano)",
    )
    parser.add_argument(
        "--tipo",
        choices=["wp_api", "html_static", "playwright", "queryly_api"],
        help="Filtrar por tipo tecnológico",
    )
    parser.add_argument(
        "--output", default="health_report.json",
        help="Archivo JSON de salida (default: health_report.json)",
    )
    args = parser.parse_args()

    # ── Selección de targets ──────────────────────────────────────────────────
    todos = list(SCRAPERS.keys())

    if args.scraper:
        if args.scraper not in SCRAPERS:
            print(f"ERROR: '{args.scraper}' no existe.")
            print(f"Disponibles: {', '.join(sorted(todos))}")
            sys.exit(1)
        targets = [args.scraper]

    elif args.tipo:
        targets = [p for p in todos if TIPO_POR_SCRAPER.get(p) == args.tipo]
        if not targets:
            print(f"ERROR: No hay scrapers de tipo '{args.tipo}'.")
            sys.exit(1)

    else:
        targets = todos

    # ── Separar en grupos ─────────────────────────────────────────────────────
    playwright_targets = [p for p in targets if p in SCRAPERS_PLAYWRIGHT]
    fast_targets       = [p for p in targets if p not in SCRAPERS_PLAYWRIGHT]

    print(f"\nHealth check: {len(targets)} scrapers")
    print(f"  Periodo   : {FECHA_DESDE} → {FECHA_HASTA} (90 días)")
    print(f"  Timeouts  : {TIMEOUT_FAST}s (rápidos) / {TIMEOUT_PLAYWRIGHT}s (Playwright) "
          f"/ {max(TIMEOUT_POR_SCRAPER.values())}s (lentos: "
          f"{', '.join(TIMEOUT_POR_SCRAPER)})")
    print(f"  Umbral    : Lento si arts>0 y tiempo ≥ {UMBRAL_LENTO}s")
    print(f"  Status    : OK | Lento | Sin_resultados (HTTP 200, 0 arts) | Roto")

    t_inicio = time.perf_counter()

    resultados  = _run_fast_batch(fast_targets)
    resultados.update(_run_playwright_batch(playwright_targets))

    t_total = time.perf_counter() - t_inicio

    resumen = _construir_resumen(resultados)
    _imprimir_resumen(resumen, resultados)

    print(f"  Tiempo total: {t_total:.0f}s  ({t_total/60:.1f} min)")

    reporte = {
        "fecha":          date.today().isoformat(),
        "periodo":        f"{FECHA_DESDE} → {FECHA_HASTA}",
        "tiempo_total_s": round(t_total, 1),
        "scrapers":       resultados,
        "resumen":        resumen,
    }
    output_path = os.path.abspath(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"  Reporte: {output_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
