"""
scrappers_v2.py — Estrategia V2: timeout corto para scrapers problemáticos
+ complemento central garantizado cuando total < MIN_COMPLEMENTO arts.

DIFERENCIAS VS V1 (scrappers.py)
─────────────────────────────────────────────────────────────────────────────
1. SCRAPERS_PROBLEMATICOS → timeout 60 s en lugar de 300-600 s.
   Si un scraper fallón tarda más de 60 s, lo saltamos sin perder tiempo.

2. Lógica de complemento siempre activa:
   · Local ≥ MIN_LOCAL (20 arts) → conservar + complementar con central
                                    si total < MIN_COMPLEMENTO (100 arts)
   · Local < MIN_LOCAL (20 arts) → saltar local, ir directo a central

3. _PERIODICOS_CENTRAL_V2 = ['eltiempo'] — sin las2orillas (demasiado lento).

USO
─────────────────────────────────────────────────────────────────────────────
    from scrappers_v2 import scrape_departamento_v2, scrape_multiples_departamentos_v2

    df = scrape_departamento_v2('Arauca', '2023-01-01', '2023-12-31')

    scrape_multiples_departamentos_v2(
        departamentos=['Arauca', 'Cesar', 'Risaralda'],
        fecha_desde='2023-01-01',
        fecha_hasta='2023-01-31',
        directorio_salida='resultados',
    )
"""

# ── Importar TODO lo necesario de v1 ─────────────────────────────────────────
import scrappers as _v1

# Clases e infraestructura
from scrappers import (
    GestorScraping,
    DEPARTAMENTO_PERIODICOS,
    DEPARTAMENTO_MIN_MENCIONES,
    TEMAS_BUSQUEDA,
)

# Tipos y librerías
import os
import time
import unicodedata
import contextlib
import concurrent.futures
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional


# ── Categorización de scrapers (basada en resultados de corridas reales) ─────

SCRAPERS_CONFIABLES: frozenset = frozenset({
    # Funcionaron bien: traen artículos con timeouts normales
    'elcolombiano',       # G1 Antioquia — robusto
    'elpais',             # G2 Valle del Cauca — robusto
    'diariooccidente',    # G2 Valle del Cauca — 1 timeout ocasional, tolerable
    'eldiario',           # G4 Risaralda — rápido cuando hay contenido reciente
    'bcnoticias',         # G3/G11 Caldas/Tolima — robusto
    'elquindiano',        # G5 Quindío — mejorado con timeout=45s
    'diariodelcauca',     # G8/G10 — robusto
    'diariodelsur',       # G9/G10 — robusto
    'elpilon',            # G6/G7/G8 — Playwright pero estable
    'elmeridiano',        # G9/G10 — robusto
    'diariodecasanare',   # G11 — robusto
    'miputumayo',         # lento pero trae resultados (ya tiene timeout=600s)
})

SCRAPERS_PROBLEMATICOS: frozenset = frozenset({
    # Fallan frecuentemente o producen muy pocos artículos
    'llanoalmundo',            # 422 TimeoutErrors — Meta/Caquetá/Guaviare muy afectados
    'lavozdelcinaruco',        # 598 TimeoutErrors — Arauca casi vacío
    'tronchandosinfronteras',  # 0 arts para casi todos los términos históricos
    'choco7dias',              # lento, pocos resultados
    'enlacetelevision',        # 192 RuntimeErrors (antes del fix) + lento
    'corrillos',               # 234 RuntimeErrors (antes del fix) + lento
    'portafolio',              # Playwright lento, contenido económico estrecho
    'publimetro',              # Playwright lento, pocos resultados regionales
})

# ── Umbrales V2 ───────────────────────────────────────────────────────────────
_V2_MIN_LOCAL       = 20    # arts mínimos del local para considerarlo útil
_V2_MIN_COMPLEMENTO = 100   # arts totales; por debajo → complementar siempre
_V2_TIMEOUT_PROB    = 60    # s — timeout para scrapers problemáticos
_V2_PERIODICOS_CENTRAL = ['eltiempo']   # sin las2orillas


# ═════════════════════════════════════════════════════════════════════════════
# GestorScrapingV2 — igual que GestorScraping pero con timeout diferenciado
# ═════════════════════════════════════════════════════════════════════════════

class GestorScrapingV2(GestorScraping):
    """
    Subclase de GestorScraping que aplica timeouts diferenciados:
      · SCRAPERS_PROBLEMATICOS → _V2_TIMEOUT_PROB (60 s)
      · nacionales (eltiempo, las2orillas) → 480 s
      · lentos (miputumayo, lavozdelcinaruco) → 600 s  [ya cubierto por PROBLEMATICOS]
      · resto → 300 s
    """

    def scrape_multiples(self, periodicos: List[str],
                         callback=None,
                         min_menciones: int = 3) -> pd.DataFrame:
        """Override de scrape_multiples con timeout diferenciado para scrapers problemáticos."""

        # ── Validar y separar en grupos ──────────────────────────────────────
        validos, invalidos = [], []
        for p in periodicos:
            (validos if p in self.SCRAPERS else invalidos).append(p)
        for p in invalidos:
            print(f"  Periódico '{p}' no disponible.")

        playwright_ids   = [p for p in validos if p in self.SCRAPERS_PLAYWRIGHT]
        rate_limited_ids = [p for p in validos
                            if p in self.SCRAPERS_RATE_LIMITED
                            and p not in self.SCRAPERS_PLAYWRIGHT]
        fast_ids         = [p for p in validos
                            if p not in self.SCRAPERS_PLAYWRIGHT
                            and p not in self.SCRAPERS_RATE_LIMITED]

        print(f"\n  [V2] Estrategia de scraping para '{self.termino}':")
        if fast_ids:
            print(f"    Paralelos rapidos   ({self._MAX_WORKERS_FAST}w): {fast_ids}")
        if rate_limited_ids:
            print(f"    Paralelos limitados ({self._MAX_WORKERS_RATE_LIMITED}w): {rate_limited_ids}")
        if playwright_ids:
            print(f"    Playwright secuencial: {playwright_ids}")

        dataframes: List[pd.DataFrame] = []

        _NACIONALES = frozenset({'eltiempo', 'las2orillas'})
        _LENTOS     = frozenset({'miputumayo', 'lavozdelcinaruco'})

        def _run_one(periodico_id: str) -> tuple:
            scraper_class = self.SCRAPERS[periodico_id]
            if periodico_id == 'las2orillas':
                ctx = _v1._las2orillas_semaphore
            elif periodico_id == 'eltiempo':
                ctx = _v1._eltiempo_semaphore
            else:
                ctx = contextlib.nullcontext()

            _min_rel = 1 if periodico_id in _NACIONALES else min_menciones

            # ── CAMBIO V2: timeout corto para scrapers problemáticos ──────────
            if periodico_id in _NACIONALES:
                _timeout = 480
            elif periodico_id in SCRAPERS_PROBLEMATICOS:
                _timeout = _V2_TIMEOUT_PROB   # 60 s — fallamos rápido
            elif periodico_id in _LENTOS:
                _timeout = 600
            else:
                _timeout = 300

            def _ejecutar():
                with ctx:
                    scraper = scraper_class(self.termino, self.fecha_desde, self.fecha_hasta)
                    df = scraper.scrape()
                    if not df.empty and _min_rel > 0:
                        df = self._filtrar_relevancia(df, _min_rel)
                    return df

            with ThreadPoolExecutor(max_workers=1) as _exec:
                _future = _exec.submit(_ejecutar)
                try:
                    df = _future.result(timeout=_timeout)
                    if df.empty:
                        print(f"  ℹ  {periodico_id}: 0 artículos encontrados")
                    return periodico_id, df
                except concurrent.futures.TimeoutError:
                    mins = _timeout // 60
                    tag = " [PROBLEMATICO — timeout corto]" if periodico_id in SCRAPERS_PROBLEMATICOS else ""
                    print(f"  ⏱  {periodico_id}: timeout {mins} min{tag} — saltando")
                    _v1._registrar_error(periodico_id, 'ScraperTimeout')
                    return periodico_id, pd.DataFrame()
                except Exception as e:
                    print(f"  ✗ Error en {periodico_id}: {e}")
                    _v1._registrar_error(periodico_id, type(e).__name__)
                    return periodico_id, pd.DataFrame()

        def _collect(future_map: dict):
            for future in as_completed(future_map):
                pid, df = future.result()
                if not df.empty:
                    dataframes.append(df)
                if callback:
                    callback(pid, df)

        # FASE 1A: scrapers rápidos en paralelo
        if fast_ids:
            w = min(len(fast_ids), self._MAX_WORKERS_FAST)
            with ThreadPoolExecutor(max_workers=w, thread_name_prefix="fast_v2") as pool:
                futures = {pool.submit(_run_one, pid): pid for pid in fast_ids}
                _collect(futures)

        # FASE 1B: scrapers rate-limited en paralelo (pool propio)
        if rate_limited_ids:
            w = min(len(rate_limited_ids), self._MAX_WORKERS_RATE_LIMITED)
            with ThreadPoolExecutor(max_workers=w, thread_name_prefix="rl_v2") as pool:
                futures = {pool.submit(_run_one, pid): pid for pid in rate_limited_ids}
                _collect(futures)

        # FASE 2: Playwright serializado
        for pid in playwright_ids:
            with _v1._playwright_lock:
                _, df = _run_one(pid)
            if not df.empty:
                dataframes.append(df)
            if callback:
                callback(pid, df)

        if dataframes:
            df_final = self._unificar_dataframes(dataframes)
            self._mostrar_resumen(df_final)
            return df_final
        else:
            print("No se pudo obtener ningún artículo")
            return pd.DataFrame(columns=['periodico', 'titulo', 'fecha', 'texto', 'url'])


# ═════════════════════════════════════════════════════════════════════════════
# scrape_periodicos_v2 — igual que scrape_periodicos pero usa GestorScrapingV2
# ═════════════════════════════════════════════════════════════════════════════

def scrape_periodicos_v2(termino: str, fecha_desde: str, fecha_hasta: str,
                         periodicos: List[str] = None,
                         region: str = None,
                         min_menciones: int = 3) -> pd.DataFrame:
    """Wrapper de scrape_periodicos que usa GestorScrapingV2 (timeouts diferenciados)."""
    gestor = GestorScrapingV2(termino, fecha_desde, fecha_hasta)
    if periodicos is not None:
        lista_final = periodicos
    elif region is not None:
        lista_final = gestor.periodicos_por_region(region)
        if not lista_final:
            return pd.DataFrame(columns=['periodico', 'titulo', 'fecha', 'texto', 'url'])
        print(f"Region '{region}': {len(lista_final)} periodicos → {lista_final}")
    else:
        lista_final = gestor.periodicos_disponibles()
    return gestor.scrape_multiples(lista_final, min_menciones=min_menciones)


# ═════════════════════════════════════════════════════════════════════════════
# _buscar_multi_termino_v2 — igual que v1 pero usa scrape_periodicos_v2
# ═════════════════════════════════════════════════════════════════════════════

def _buscar_multi_termino_v2(territorio: str, fecha_desde: str, fecha_hasta: str,
                              periodicos: List[str], min_menciones: int,
                              temas: List[str]) -> pd.DataFrame:
    """Multi-término con GestorScrapingV2."""
    print(f"\n{'='*60}")
    print(f"[V2] BUSQUEDA MULTI-TERMINO: {territorio} | {fecha_desde} -> {fecha_hasta}")
    print(f"Terminos ({len(temas)} en paralelo): {[f'{territorio} {t}' for t in temas]}")
    print(f"{'='*60}")

    def _buscar_tema(tema: str) -> tuple:
        termino = f"{territorio} {tema}"
        print(f"\n-- Buscando: '{termino}' --")
        try:
            df_tema = scrape_periodicos_v2(
                termino=termino,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                periodicos=periodicos,
                min_menciones=min_menciones,
            )
        except Exception as e:
            print(f"  ✗ Error en '{termino}': {e}")
            return tema, pd.DataFrame()

        if not df_tema.empty:
            df_tema = df_tema.copy()
            df_tema['terminos_encontrado'] = tema
            print(f"   -> {len(df_tema)} articulos relevantes")
        else:
            print(f"   -> Sin resultados")
        return tema, df_tema

    resultados_por_termino: Dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=len(temas), thread_name_prefix="tema_v2") as pool:
        futures = {pool.submit(_buscar_tema, tema): tema for tema in temas}
        for future in as_completed(futures):
            tema, df_tema = future.result()
            if not df_tema.empty:
                resultados_por_termino[tema] = df_tema

    if not resultados_por_termino:
        return pd.DataFrame()

    df_todos = pd.concat(resultados_por_termino.values(), ignore_index=True)
    terminos_por_url = (
        df_todos.groupby('url')['terminos_encontrado']
        .apply(lambda x: ', '.join(sorted(set(x))))
        .reset_index()
    )
    df_dedup = (
        df_todos
        .drop(columns=['terminos_encontrado'])
        .drop_duplicates(subset=['url'], keep='first')
        .merge(terminos_por_url, on='url', how='left')
        .sort_values('fecha', ascending=False)
        .reset_index(drop=True)
    )

    total_antes = len(df_todos)
    total_dedup = len(df_dedup)
    print(f"\n{'='*60}")
    print(f"[V2] RESUMEN -- {territorio}")
    print(f"{'='*60}")
    for tema in temas:
        if tema in resultados_por_termino:
            print(f"  {territorio} {tema:<15}: {len(resultados_por_termino[tema]):>4}")
        else:
            print(f"  {territorio} {tema:<15}:    0")
    print(f"{'─'*40}")
    print(f"Total antes de deduplicar : {total_antes:>4}")
    print(f"Duplicados eliminados     : {total_antes - total_dedup:>4}")
    print(f"Articulos unicos finales  : {total_dedup:>4}")
    if df_dedup['fecha'].notna().any():
        print(f"Rango de fechas: {df_dedup['fecha'].min():%Y-%m-%d} -> "
              f"{df_dedup['fecha'].max():%Y-%m-%d}")
    print(f"{'='*60}\n")
    return df_dedup


# ═════════════════════════════════════════════════════════════════════════════
# scrape_departamento_v2 — ESTRATEGIA NUEVA
# ═════════════════════════════════════════════════════════════════════════════

def scrape_departamento_v2(departamento: str,
                           fecha_desde: str,
                           fecha_hasta: str,
                           periodicos: List[str] = None,
                           min_menciones: int = None,
                           temas: List[str] = None) -> pd.DataFrame:
    """
    Estrategia V2:

    1. Corre scrapers locales con GestorScrapingV2 (timeout 60s para problemáticos).
    2. Evalúa resultado local:
       · Local ≥ MIN_LOCAL (20 arts)  →  conserva local
       · Local <  MIN_LOCAL (20 arts) →  descarta local, va directo a central
    3. Complemento central (eltiempo) si total < MIN_COMPLEMENTO (100 arts).
       El complemento SIEMPRE corre cuando el total queda por debajo del umbral,
       a diferencia de v1 que solo lo activaba si local < 50.

    Returns: DataFrame deduplicado con columnas estándar + 'departamento' + 'terminos_encontrado'.
    """
    _temas = temas if temas is not None else TEMAS_BUSQUEDA

    if min_menciones is None:
        min_menciones = DEPARTAMENTO_MIN_MENCIONES.get(departamento, 3)
        print(f"  [V2] Umbral de menciones para {departamento}: {min_menciones} (automatico)")

    if periodicos is None:
        periodicos = DEPARTAMENTO_PERIODICOS.get(departamento)
        if not periodicos:
            print(f"  [V2] '{departamento}': sin scrapers locales → directo a central.")
            periodicos = []
        else:
            # Clasificar scrapers locales
            problematicos_activos = [p for p in periodicos if p in SCRAPERS_PROBLEMATICOS]
            confiables_activos    = [p for p in periodicos if p in SCRAPERS_CONFIABLES]
            otros                 = [p for p in periodicos
                                     if p not in SCRAPERS_PROBLEMATICOS
                                     and p not in SCRAPERS_CONFIABLES]
            print(f"  [V2] Periodicos para {departamento}:")
            print(f"       Confiables   : {confiables_activos}")
            print(f"       Problematicos: {problematicos_activos} (timeout={_V2_TIMEOUT_PROB}s)")
            if otros:
                print(f"       Otros        : {otros}")

    # ── FASE 1: scrapers locales con GestorScrapingV2 ────────────────────────
    df_local = pd.DataFrame()
    if periodicos:
        df_local = _buscar_multi_termino_v2(
            departamento, fecha_desde, fecha_hasta,
            periodicos, min_menciones, _temas
        )

    n_local = len(df_local)

    # ── Decisión V2 ──────────────────────────────────────────────────────────
    if n_local < _V2_MIN_LOCAL:
        # Local insuficiente (< 20) — ir directo a central sin mezclar basura
        if periodicos:
            print(f"\n  [V2] Local insuficiente: {n_local} arts < {_V2_MIN_LOCAL} "
                  f"— descartando local, directo a central.")
        df_base = pd.DataFrame()
    else:
        # Local útil — conservar
        print(f"\n  [V2] Local util: {n_local} arts >= {_V2_MIN_LOCAL} — conservando.")
        df_base = df_local

    # ── FASE 2: complemento central si total < MIN_COMPLEMENTO ──────────────
    total_actual = len(df_base)

    if total_actual < _V2_MIN_COMPLEMENTO:
        # Excluir scrapers locales ya usados del respaldo
        periodicos_ya_usados = set(periodicos or [])
        central_disponible = [
            p for p in _V2_PERIODICOS_CENTRAL
            if p not in periodicos_ya_usados
        ]

        if central_disponible:
            print(f"  [V2] Total actual {total_actual} < {_V2_MIN_COMPLEMENTO} "
                  f"— complementando con: {central_disponible}")
            df_central = _buscar_multi_termino_v2(
                departamento, fecha_desde, fecha_hasta,
                central_disponible, 1,   # umbral=1 para nacionales
                _temas
            )
            if not df_central.empty:
                df_base = (
                    pd.concat([df_base, df_central], ignore_index=True)
                    .drop_duplicates(subset=['url'])
                    .sort_values('fecha', ascending=False)
                    .reset_index(drop=True)
                )
                print(f"  [V2] Total con complemento: {len(df_base)} arts")
            else:
                print(f"  [V2] Sin resultados adicionales en central.")
    else:
        print(f"  [V2] Total {total_actual} >= {_V2_MIN_COMPLEMENTO} "
              f"— no necesita complemento central.")

    if not df_base.empty:
        df_base['departamento'] = departamento
    else:
        return pd.DataFrame(columns=[
            'periodico', 'titulo', 'fecha', 'texto', 'url',
            'departamento', 'terminos_encontrado'
        ])

    return df_base


# ═════════════════════════════════════════════════════════════════════════════
# scrape_multiples_departamentos_v2 — orquestador paralelo V2
# ═════════════════════════════════════════════════════════════════════════════

def scrape_multiples_departamentos_v2(departamentos: List[str],
                                      fecha_desde: str,
                                      fecha_hasta: str,
                                      min_menciones: int = None,
                                      max_paralelos: int = 3,
                                      directorio_salida: str = ".",
                                      temas: List[str] = None) -> pd.DataFrame:
    """
    Versión V2 de scrape_multiples_departamentos.

    Usa scrape_departamento_v2 (timeout corto para problemáticos,
    complemento central siempre cuando total < 100).
    """
    global _v1
    _v1._errores_run = []

    resultados: Dict[str, pd.DataFrame] = {}
    errores: List[str] = []
    _lock = threading.Lock()

    simultaneos = min(max_paralelos, len(departamentos))
    print(f"\n[V2] CORRIENDO {len(departamentos)} DEPARTAMENTOS "
          f"({simultaneos} EN PARALELO)")
    print(f"     Periodo : {fecha_desde}  ->  {fecha_hasta}")
    print(f"     Deptos  : {' | '.join(departamentos)}")
    print(f"     Timeout problematicos: {_V2_TIMEOUT_PROB}s | "
          f"Min local: {_V2_MIN_LOCAL} | Min complemento: {_V2_MIN_COMPLEMENTO}")
    print(f"{'─'*60}")

    def _nombre_archivo(dep: str) -> str:
        normalizado = unicodedata.normalize('NFD', dep.lower())
        sin_tildes = normalizado.encode('ascii', 'ignore').decode('ascii')
        return f"df_corpus_v2_{sin_tildes.replace(' ', '_')}.pkl"

    def _procesar_dep(dep: str) -> None:
        t0 = time.time()
        print(f"\n{'='*60}\n[V2] INICIO  [{dep}]\n{'='*60}")
        try:
            df_dep = scrape_departamento_v2(
                departamento=dep,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                min_menciones=min_menciones,
                temas=temas,
            )
            mins = (time.time() - t0) / 60
            if not df_dep.empty:
                os.makedirs(directorio_salida, exist_ok=True)
                ruta = os.path.join(directorio_salida, _nombre_archivo(dep))
                df_dep.to_pickle(ruta)
                print(f"\n[V2] FIN [{dep}] {mins:.1f} min — "
                      f"{len(df_dep)} arts — {ruta}")
                with _lock:
                    resultados[dep] = df_dep
            else:
                print(f"\n[V2] FIN [{dep}] {mins:.1f} min — sin artículos")
        except Exception as e:
            mins = (time.time() - t0) / 60
            msg = f"[{dep}] Error: {e}"
            print(f"\n[V2] ERROR [{dep}] {mins:.1f} min — {e}")
            import traceback; traceback.print_exc()
            with _lock:
                errores.append(msg)

    with ThreadPoolExecutor(max_workers=max_paralelos,
                            thread_name_prefix="depto_v2") as pool:
        futures = {pool.submit(_procesar_dep, dep): dep for dep in departamentos}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                dep = futures[future]
                print(f"  [V2] Excepcion inesperada en {dep}: {e}")

    if errores:
        print(f"\n  Departamentos con error ({len(errores)}):")
        for msg in errores:
            print(f"   {msg}")

    if not resultados:
        print("[V2] Sin artículos en ningún departamento.")
        return pd.DataFrame()

    df_final = pd.concat(
        [resultados[dep] for dep in departamentos if dep in resultados],
        ignore_index=True,
    )

    print(f"\n{'='*60}")
    print(f"[V2] RESUMEN TOTAL — {len(departamentos)} departamentos "
          f"({len(resultados)} con datos, {len(errores)} con error)")
    print(f"Total artículos únicos: {len(df_final)}")
    print(f"\nPor departamento:")
    print(df_final['departamento'].value_counts().to_string())
    print(f"{'='*60}\n")

    _v1._imprimir_reporte_errores(len(departamentos))
    return df_final
