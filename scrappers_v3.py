"""
scrappers_v3.py — Mejoras tecnológicas experimentales
══════════════════════════════════════════════════════════════════════════════

MEJORA 1 — curl_cffi en ScraperVanguardia (y scrapers síncronos problemáticos)
    requests.Session() → curl_cffi.requests.Session(impersonate="chrome120")

    curl_cffi imita el TLS fingerprint del navegador Chrome.
    Objetivo: resolver HTTP 403 en Vanguardia que bloquea user-agents de scripts.
    API idéntica a requests → cambio quirúrgico en __init__.

MEJORA 2 — selectolax en ScraperTrochandoSinFronteras
    BeautifulSoup("html.parser") → selectolax.parser.HTMLParser()

    selectolax: parser C puro, ~30x más rápido que lxml, ~100x vs html.parser.
    Impacto real en scrapers que parsean decenas de páginas por término.

USO
────────────────────────────────────────────────────────────────────────────
    from scrappers_v3 import scrape_departamento_v3

    df = scrape_departamento_v3('Santander', '2023-01-01', '2023-01-31')

BENCHMARK
    python v3/benchmark_v3.py
"""

# ── Importar base v1 ──────────────────────────────────────────────────────────
from scrappers import (
    ScraperPeriodico, ScraperVanguardia, ScraperTrochandoSinFronteras,
    GestorScraping, scrape_departamento, scrape_multiples_departamentos,
    DEPARTAMENTO_PERIODICOS, DEPARTAMENTO_MIN_MENCIONES, TEMAS_BUSQUEDA,
    _registrar_error, _playwright_lock, _eltiempo_semaphore,
    _buscar_multi_termino,
)
import scrappers as _v1

# ── Nuevas dependencias ───────────────────────────────────────────────────────
from curl_cffi import requests as cf_requests
from selectolax.parser import HTMLParser as _HTMLParser
from urllib.parse import quote as _url_quote

# ── Librerías estándar (ya importadas vía scrappers, re-export explícito) ─────
import sys, os, time, math, json, asyncio, threading, contextlib
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import aiohttp


# ══════════════════════════════════════════════════════════════════════════════
# MEJORA 1 — ScraperVanguardiaV3: curl_cffi con TLS fingerprint Chrome120
# ══════════════════════════════════════════════════════════════════════════════

class ScraperVanguardiaV3(ScraperVanguardia):
    """
    Vanguardia con curl_cffi en lugar de requests.

    El 403 de Vanguardia ocurre porque requests expone un TLS fingerprint
    de Python puro, detectado por los WAF modernos. curl_cffi usa libcurl
    parcheado para emitir el mismo TLS ClientHello que Chrome 120.
    """

    IMPERSONATE = "chrome120"   # perfil TLS a imitar

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str):
        # Inicializar atributos del abuelo (ScraperPeriodico) sin su session
        ScraperPeriodico.__init__(self, termino, fecha_desde, fecha_hasta)

        # ── CAMBIO: curl_cffi Session con impersonation ───────────────────────
        self.session = cf_requests.Session(impersonate=self.IMPERSONATE)
        self.session.headers.update(self.HEADERS)

        # Atributos propios de ScraperVanguardia
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    @property
    def nombre_periodico(self) -> str:
        return "Vanguardia"          # mismo nombre para compatibilidad de corpus

    def _construir_url_api(self, endindex: int) -> str:
        """Idéntico al padre pero usa urllib.parse.quote (sin dep. de requests)."""
        termino_encoded = _url_quote(self.termino)
        params = (
            f"queryly_key={self.QUERYLY_KEY}"
            f"&query={termino_encoded}"
            f"&endindex={endindex}"
            f"&batchsize={self.BATCH_SIZE}"
            f"&callback=searchPage.resultcallback"
            f"&showfaceted=true"
            f"&extendeddatafields=creator,imageresizer,promo_image"
            f"&timezoneoffset=300"
        )
        return f"{self.API_URL}?{params}"

    # _consultar_api, _procesar_items, scrape, _descargar_articulo_async
    # se heredan de ScraperVanguardia sin cambios — usan self.session.get()
    # que ahora apunta a curl_cffi.Session.get().


# ══════════════════════════════════════════════════════════════════════════════
# MEJORA 2 — ScraperTrochandoSinFronterasV3: selectolax en lugar de BS4
# ══════════════════════════════════════════════════════════════════════════════

class ScraperTrochandoSinFronterasV3(ScraperTrochandoSinFronteras):
    """
    TrochandoSinFronteras con selectolax para parseo HTML.

    Cambios vs v1:
    - _sl_total_paginas(html)   → reemplaza _obtener_total_paginas(soup)
    - _sl_extraer_links(html)   → reemplaza _extraer_links_pagina(soup)
    - scrape()                  → crea HTMLParser en lugar de BeautifulSoup

    selectolax usa un motor C (Modest) que evita el overhead de Python puro
    de html.parser y el parsing completo del árbol DOM de lxml.
    """

    @property
    def nombre_periodico(self) -> str:
        return "Trochando Sin Fronteras"   # mismo nombre para corpus

    # ── selectolax: obtener total de páginas ─────────────────────────────────

    def _sl_total_paginas(self, html: str) -> int:
        """selectolax equivalente de _obtener_total_paginas(soup)."""
        tree = _HTMLParser(html)
        total_paginas_sitio = 1

        # <a class="last" title="N"> — enlace a última página
        for a in tree.css("a.last"):
            t = a.attributes.get("title", "")
            if t and t.isdigit():
                total_paginas_sitio = int(t)
                break
        else:
            # Fallback: mayor número en links de paginación
            nums = []
            for a in tree.css("a.page"):
                t = (a.text(strip=True) or "")
                if t.isdigit():
                    nums.append(int(t))
            if nums:
                total_paginas_sitio = max(nums)

        max_paginas_por_limite = math.ceil(self.max_articulos / 10)
        total_paginas = min(total_paginas_sitio, max_paginas_por_limite)

        print(f"  Total páginas en sitio: {total_paginas_sitio} | "
              f"Límite: {self.max_articulos} arts → recorriendo {total_paginas} páginas")
        return total_paginas

    # ── selectolax: extraer links de una página ──────────────────────────────

    def _sl_extraer_links(self, html: str) -> List[str]:
        """selectolax equivalente de _extraer_links_pagina(soup)."""
        tree = _HTMLParser(html)
        links = []

        # Columna principal: div con clase que incluye 'tdi_96'
        scope = tree
        for div in tree.css("div[class]"):
            cls = div.attributes.get("class", "")
            if "tdi_96" in cls:
                scope = div
                break

        for modulo in scope.css("div.td-module-container"):
            h3 = modulo.css_first("h3.td-module-title")
            if not h3:
                continue
            a = h3.css_first("a")
            if not a:
                continue
            href = (a.attributes.get("href") or "").strip()
            if not href or self.DOMINIO not in href:
                continue

            # Fecha desde <time class="td-module-date" datetime="...">
            fecha = None
            time_tag = modulo.css_first("time.td-module-date")
            if time_tag:
                dt_str = time_tag.attributes.get("datetime", "")
                if dt_str:
                    fecha = self._parsear_fecha_trochando(dt_str)

            self._fechas_cache[href] = fecha
            links.append(href)

        return links

    # ── Override scrape() usando selectolax ──────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()} [v3:selectolax]")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  Límite de artículos: {self.max_articulos}")

        # Primera página con retry
        html_p1 = None
        for intento in range(3):
            try:
                url_p1 = self._construir_url_busqueda(pagina=1)
                r = self.session.get(url_p1, timeout=20)
                r.raise_for_status()
                html_p1 = r.text
                break
            except Exception as e:
                if intento < 2:
                    espera = (intento + 1) * 5
                    print(f"  Intento {intento+1}/3 fallido (primera página) — esperando {espera}s...")
                    time.sleep(espera)
                else:
                    print(f"  Error al cargar primera página: {e}")
                    _registrar_error(self.nombre_periodico, 'PrimeraPagina')
                    return pd.DataFrame()

        # ── CAMBIO: selectolax en lugar de BeautifulSoup ─────────────────────
        total_paginas = self._sl_total_paginas(html_p1)
        links_en_rango = []
        errores_consecutivos = 0
        paginas_vacias_consecutivas = 0

        for pagina in range(1, total_paginas + 1):
            try:
                if pagina == 1:
                    html = html_p1
                else:
                    url = self._construir_url_busqueda(pagina=pagina)
                    html = None
                    for intento in range(3):
                        try:
                            r = self.session.get(url, timeout=25)
                            r.raise_for_status()
                            html = r.text
                            break
                        except Exception:
                            espera = 5 * (intento + 1)
                            print(f"  Intento {intento+1}/3 fallido en pág {pagina} — "
                                  f"esperando {espera}s...")
                            time.sleep(espera)

                    if html is None:
                        errores_consecutivos += 1
                        print(f"  Página {pagina} descartada tras 3 intentos.")
                        if errores_consecutivos >= 5:
                            print("  5 páginas consecutivas fallidas — deteniendo.")
                            break
                        continue

                errores_consecutivos = 0

                # ── selectolax para extraer links ────────────────────────────
                links_pagina = self._sl_extraer_links(html)
                print(f"  Página {pagina}/{total_paginas}: {len(links_pagina)} artículos")

                n_antes = len(links_en_rango)
                for link in links_pagina:
                    fecha = self._fechas_cache.get(link)
                    if fecha is None:
                        links_en_rango.append(link)
                        continue
                    if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                        links_en_rango.append(link)

                nuevos = len(links_en_rango) - n_antes
                if nuevos == 0 and links_pagina:
                    paginas_vacias_consecutivas += 1
                    if paginas_vacias_consecutivas >= 3:
                        print(f"  3 páginas consecutivas sin artículos en rango — deteniendo.")
                        break
                else:
                    paginas_vacias_consecutivas = 0

                time.sleep(1.5)

            except Exception as e:
                print(f"  Error en página {pagina}: {e}")
                errores_consecutivos += 1
                if errores_consecutivos >= 5:
                    print("  5 páginas consecutivas fallidas — deteniendo.")
                    break

        links_en_rango = list(dict.fromkeys(links_en_rango))
        print(f"  Total links únicos en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)


# ══════════════════════════════════════════════════════════════════════════════
# GestorScrapingV3 — swapea los dos scrapers mejorados
# ══════════════════════════════════════════════════════════════════════════════

class GestorScrapingV3(GestorScraping):
    """GestorScraping con ScraperVanguardiaV3 y ScraperTrochandoSinFronterasV3."""

    SCRAPERS = {
        **GestorScraping.SCRAPERS,           # hereda todos los scrapers de v1
        'vanguardia':              ScraperVanguardiaV3,
        'tronchandosinfronteras':  ScraperTrochandoSinFronterasV3,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Funciones públicas de v3
# ══════════════════════════════════════════════════════════════════════════════

def scrape_periodicos_v3(termino, fecha_desde, fecha_hasta,
                         periodicos=None, region=None, min_menciones=3):
    """scrape_periodicos usando GestorScrapingV3."""
    gestor = GestorScrapingV3(termino, fecha_desde, fecha_hasta)
    if periodicos is not None:
        lista = periodicos
    elif region is not None:
        lista = gestor.periodicos_por_region(region)
    else:
        lista = gestor.periodicos_disponibles()
    return gestor.scrape_multiples(lista, min_menciones=min_menciones)


def _buscar_multi_termino_v3(territorio, fecha_desde, fecha_hasta,
                              periodicos, min_menciones, temas):
    """_buscar_multi_termino usando scrape_periodicos_v3."""
    import threading
    print(f"\n{'='*60}")
    print(f"[V3] BUSQUEDA MULTI-TERMINO: {territorio} | {fecha_desde} -> {fecha_hasta}")
    print(f"Terminos ({len(temas)} en paralelo): {[f'{territorio} {t}' for t in temas]}")
    print(f"{'='*60}")

    resultados: Dict[str, pd.DataFrame] = {}

    def _buscar_tema(tema):
        termino = f"{territorio} {tema}"
        print(f"\n-- [V3] Buscando: '{termino}' --")
        try:
            df = scrape_periodicos_v3(termino, fecha_desde, fecha_hasta,
                                      periodicos=periodicos,
                                      min_menciones=min_menciones)
        except Exception as e:
            print(f"  ✗ Error en '{termino}': {e}")
            return tema, pd.DataFrame()
        if not df.empty:
            df = df.copy()
            df['terminos_encontrado'] = tema
            print(f"   -> {len(df)} articulos relevantes")
        else:
            print(f"   -> Sin resultados")
        return tema, df

    with ThreadPoolExecutor(max_workers=len(temas), thread_name_prefix="tema_v3") as pool:
        futures = {pool.submit(_buscar_tema, t): t for t in temas}
        for f in as_completed(futures):
            tema, df = f.result()
            if not df.empty:
                resultados[tema] = df

    if not resultados:
        return pd.DataFrame()

    df_todos = pd.concat(resultados.values(), ignore_index=True)
    terminos_por_url = (
        df_todos.groupby('url')['terminos_encontrado']
        .apply(lambda x: ', '.join(sorted(set(x))))
        .reset_index()
    )
    df_dedup = (
        df_todos.drop(columns=['terminos_encontrado'])
        .drop_duplicates(subset=['url'], keep='first')
        .merge(terminos_por_url, on='url', how='left')
        .sort_values('fecha', ascending=False)
        .reset_index(drop=True)
    )
    return df_dedup


def scrape_departamento_v3(departamento, fecha_desde, fecha_hasta,
                           periodicos=None, min_menciones=None,
                           min_articulos=50, usar_respaldo=True,
                           temas=None):
    """scrape_departamento usando GestorScrapingV3."""
    _temas = temas or TEMAS_BUSQUEDA
    if min_menciones is None:
        min_menciones = DEPARTAMENTO_MIN_MENCIONES.get(departamento, 3)
        print(f"  [V3] Umbral menciones para {departamento}: {min_menciones}")

    if periodicos is None:
        periodicos = DEPARTAMENTO_PERIODICOS.get(departamento) or []
        if periodicos:
            print(f"  [V3] Periódicos para {departamento}: {periodicos}")
        else:
            print(f"  [V3] '{departamento}': sin scrapers locales → respaldo directo.")

    df = _buscar_multi_termino_v3(departamento, fecha_desde, fecha_hasta,
                                   periodicos, min_menciones, _temas)

    if usar_respaldo and len(df) < min_articulos:
        respaldo = [p for p in _v1._PERIODICOS_RESPALDO if p not in periodicos]
        if respaldo:
            print(f"\n  [V3] Solo {len(df)} arts — respaldo: {respaldo}")
            df_r = _buscar_multi_termino_v3(departamento, fecha_desde, fecha_hasta,
                                             respaldo, min_menciones, _temas)
            if not df_r.empty:
                df = (pd.concat([df, df_r], ignore_index=True)
                        .drop_duplicates(subset=['url'])
                        .sort_values('fecha', ascending=False)
                        .reset_index(drop=True))
                print(f"  [V3] Total con respaldo: {len(df)} arts")

    if not df.empty:
        df['departamento'] = departamento
    else:
        return pd.DataFrame(columns=[
            'periodico', 'titulo', 'fecha', 'texto', 'url',
            'departamento', 'terminos_encontrado'
        ])
    return df
