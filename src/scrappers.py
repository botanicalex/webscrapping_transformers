# scrappers.py — Pipeline de webscraping de periódicos colombianos
# Extraído del notebook Webscraping_Transformers_Optimizados_(2).ipynb
# Proyecto FNCE — UPB


# ── IMPORTS ──────────────────────────────────────────────────────────────────

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import contextlib
import threading
import time
import os
import unicodedata
import math
import re

import requests
import urllib3
import aiohttp
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
from newspaper import Article, Config
import json

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import asyncio
import nest_asyncio
import sys

# En Windows, SelectorEventLoop no soporta subprocess (necesario para Playwright).
# ProactorEventLoopPolicy garantiza que todos los event loops nuevos —incluidos los
# creados en threads de ThreadPoolExecutor— usen ProactorEventLoop.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
import pandas as pd
import urllib.parse
from urllib.parse import urlparse


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN — editar estos valores antes de correr el script
# ══════════════════════════════════════════════════════════════════════════════

import config_pipeline as cfg

FECHA_DESDE = cfg.FECHA_DESDE
FECHA_HASTA = cfg.FECHA_HASTA
TEMAS_BUSQUEDA = cfg.TEMAS_BUSQUEDA
GRUPOS_DEPARTAMENTOS = cfg.GRUPOS_DEPARTAMENTOS
MIN_ARTICULOS_RESPALDO = cfg.MIN_ARTICULOS_RESPALDO
RUTA_CORPUS_PKL = cfg.RUTA_CORPUS_PKL

# ── BUCLE DE EJECUCIÓN ────────────────────────────────────────────────────────
# Descomenta y ejecuta este bloque para correr todos los departamentos:
#
# import os
# DIRECTORIO_SALIDA = "resultados"
# os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)
#
# for i, grupo in enumerate(GRUPOS_DEPARTAMENTOS, 1):
#     print(f"\n{'#'*60}")
#     print(f"# GRUPO {i}/{len(GRUPOS_DEPARTAMENTOS)}: {grupo}")
#     print(f"{'#'*60}")
#     scrape_multiples_departamentos(
#         departamentos=grupo,
#         fecha_desde=FECHA_DESDE,
#         fecha_hasta=FECHA_HASTA,
#         min_menciones=None,        # usa DEPARTAMENTO_MIN_MENCIONES automáticamente
#         directorio_salida=DIRECTORIO_SALIDA,
#     )

# ══════════════════════════════════════════════════════════════════════════════

# Config de newspaper4k con el mismo workaround SSL/MITM (Norton) que ya se le
# aplica a requests.Session y aiohttp — ver 08_log_decisiones.md [2026-08-30].
# Article() usa su propio requests.Session interno, AJENO a self.session, así
# que el fix anterior no lo cubría: cualquier dominio interceptado por Norton
# fallaba con CERTIFICATE_VERIFY_FAILED en la descarga de CADA artículo aunque
# la búsqueda (que sí usa self.session) funcionara. Confirmado en El País Cali
# (Valle del Cauca), ver 08_log_decisiones.md [2026-08-31].
# timeout 7s (default de newspaper) -> 20s: occidente.co responde en 10-12s
# normal para sus páginas de artículo, igual que para la búsqueda — con 7s el
# 40% de las descargas fallaba por pura estrechez del timeout, no por un sitio
# caído. Mismo hallazgo, misma solución que el timeout de búsqueda paginada.
_NEWSPAPER_CONFIG = Config()
_NEWSPAPER_CONFIG.requests_params = {**_NEWSPAPER_CONFIG.requests_params, "verify": False, "timeout": 20}

# ── BASE CLASS ───────────────────────────────────────────────────────────────

class ScraperPeriodico(ABC):
    """Clase base abs para webscrapping de periódicos"""

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str):
        """
        Args:
            termino: Término de búsqueda
            fecha_desde: Fecha inicio (YYYY-MM-DD)
            fecha_hasta: Fecha fin (YYYY-MM-DD)
        """
        self.termino = termino
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta
        self.session = requests.Session()
        # Mismo MITM de Norton que ScraperElTiempo/ScraperWordPressAPI ya parchaban
        # por separado (ver contexto/08_log_decisiones.md, 2026-08-30): sin esto,
        # cualquier scraper basado en requests.Session falla con
        # CERTIFICATE_VERIFY_FAILED. Se aplica en la base para cubrirlos a todos.
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session.headers.update({
        })

    @property
    @abstractmethod
    def nombre_periodico(self) -> str:
        """Nombre del periódico"""
        pass

    @abstractmethod
    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        """Construye la URL de búsqueda para una página específica"""
        pass

    @abstractmethod
    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        """Obtiene el total de páginas de resultados"""
        pass

    @abstractmethod
    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """Extrae los links de artículos de una página"""
        pass

    def scrape(self) -> pd.DataFrame:
        """Método principal de scraping (común para todos)"""
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")

        # Obtener total de páginas
        try:
            url_inicial = self._construir_url_busqueda(pagina=1)
            # timeout=10 -> 20: occidente.co (Diario Occidente) responde en 10-12s
            # normalmente (medido 2026-08-31, red real, sin señal de estar caído
            # ni de rate-limiting), asi que 10s fallaba por pura estrechez, no por
            # un problema real. Mas generoso, nunca perjudica a un sitio rapido.
            r = self.session.get(url_inicial, timeout=20)
            soup = BeautifulSoup(r.content, 'html.parser')
            total_paginas = self._obtener_total_paginas(soup)
            print(f"Total de páginas: {total_paginas}")
        except Exception as e:
            print(f"Error obteniendo páginas: {e}")
            return pd.DataFrame()

        # Recolectar links de todas las páginas
        links = self._recolectar_links(total_paginas)

        if not links:
            print("No se encontraron links")
            return pd.DataFrame()

        # Descargar artículos
        df = self._descargar_articulos(links)
        return df

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        """Recolecta links de todas las páginas"""
        links = []

        for pagina in range(1, total_paginas + 1):
            if pagina % 5 == 0 or pagina == 1:
                print(f"Recolectando links: página {pagina}/{total_paginas}")

            try:
                url = self._construir_url_busqueda(pagina)
                r = self.session.get(url, timeout=10)
                soup = BeautifulSoup(r.content, 'html.parser')
                links_pagina = self._extraer_links_pagina(soup)
                links.extend(links_pagina)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"Error en página {pagina}: {e}")
                continue

        # Eliminar duplicados
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    def _descargar_articulo_individual(self, info: tuple) -> Optional[Dict]:
        """Descarga un artículo individual"""
        i, link = info
        try:
            article = Article(link, config=_NEWSPAPER_CONFIG)
            article.download()
            article.parse()

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": article.publish_date,
                "texto": article.text
            }
        except:
            return None

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        """Descarga artículos en paralelo"""
        print(f"\nDescargando {len(links)} artículos...")

        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]

        with ThreadPoolExecutor(max_workers=25) as executor:
            resultados = list(executor.map(self._descargar_articulo_individual, links_enumerados))

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")

        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            # Normalizar timezone → naive UTC para comparación uniforme.
            # newspaper4k devuelve Timestamps offset-aware (ej: -05:00 COL);
            # tz_convert(None) convierte a UTC y luego elimina el tz.
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            # Cubrir el día completo de fecha_hasta (artículos a las 23:59 COL)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df


# ── SCRAPERS: EJE CAFETERO + ANTIOQUIA ───────────────────────────────────────

class ScraperElDiario(ScraperPeriodico):
    REGION = "eje_cafetero_antioquia"
    """Scraper específico para El Diario (Pereira)"""

    BASE_URL = "https://www.eldiario.com.co"

    MESES = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    @property
    def nombre_periodico(self) -> str:
        return "El Diario"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}&paged={pagina}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        try:
            script_content = soup.find_all('script', string=re.compile('max_num_pages'))
            for script in script_content:
                match = re.search(r'max_num_pages\s*=\s*"(\d+)"', script.string)
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return 1

    def _parsear_fecha_articulo(self, texto_fecha: str) -> Optional[datetime]:
        """Convierte 'marzo 3, 2026' a datetime"""
        try:
            match = re.search(
                r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', texto_fecha.lower().strip()
            )
            if match:
                mes_str, dia, año = match.group(1), int(match.group(2)), int(match.group(3))
                mes = self.MESES.get(mes_str)
                if mes:
                    return datetime(año, mes, dia)
        except Exception:
            pass
        return None

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []
        fecha_desde_dt = datetime.strptime(self.fecha_desde, '%Y-%m-%d')
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, '%Y-%m-%d')

        for pagina in range(1, total_paginas + 1):
            if pagina % 5 == 0 or pagina == 1:
                print(f"Recolectando links: página {pagina}/{total_paginas}")

            try:
                url = self._construir_url_busqueda(pagina)
                r = self.session.get(url, timeout=10)
                soup = BeautifulSoup(r.content, 'html.parser')

                contenedor = soup.find(id='tdi_89') or soup.find('div', class_=re.compile(r'tdb_loop'))
                if not contenedor:
                    continue

                modulos = contenedor.find_all(class_='td_module_wrap')

                for modulo in modulos:
                    fecha_elem = modulo.find('time')
                    fecha_art = None
                    if fecha_elem:
                        datetime_attr = fecha_elem.get('datetime', '')
                        if datetime_attr:
                            try:
                                fecha_art = datetime.fromisoformat(datetime_attr[:10])
                            except Exception:
                                pass
                        if not fecha_art:
                            fecha_art = self._parsear_fecha_articulo(fecha_elem.get_text())

                    a = modulo.find('a', rel='bookmark', href=True)
                    if not a:
                        continue

                    href = a['href']
                    if not href.startswith(self.BASE_URL):
                        continue
                    if any(x in href for x in ['/categoria/', '/author/', '/page/', '/?']):
                        continue

                    if fecha_art is None:
                        links.append(href)
                    elif fecha_art > fecha_hasta_dt:
                        continue
                    elif fecha_desde_dt <= fecha_art <= fecha_hasta_dt:
                        links.append(href)
                    elif fecha_art < fecha_desde_dt:
                        print(f"  Artículos anteriores a {self.fecha_desde}, deteniendo en página {pagina}")
                        links = list(dict.fromkeys(links))
                        print(f"Total de links únicos: {len(links)}")
                        return links

                time.sleep(0.1)

            except Exception as e:
                print(f"Error en página {pagina}: {e}")
                continue

        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

class ScraperElColombiano(ScraperPeriodico):
    REGION = "eje_cafetero_antioquia"
    """Scraper específico para El Colombiano"""

    @property
    def nombre_periodico(self) -> str:
        return "El Colombiano"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        desde = datetime.strptime(self.fecha_desde, '%Y-%m-%d').strftime('%Y%m%d')
        hasta = datetime.strptime(self.fecha_hasta, '%Y-%m-%d').strftime('%Y%m%d')

        return (f"https://www.elcolombiano.com/busquedas/-/search/{self.termino}/"
               f"false/false/{desde}/{hasta}/date/true/true/0/0/meta/0/0/0/{pagina}")

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        try:
            search_header = soup.find('div', class_='searchHeader')
            if search_header:
                h2 = search_header.find('h2')
                if h2:
                    texto = h2.text.strip()
                    match = re.search(r'\((\d+)\s+resultados?\)', texto)
                    if match:
                        total_articulos = int(match.group(1))
                        return math.ceil(total_articulos / 12)
        except:
            pass

        return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        links = []
        articulos = soup.find_all('div', class_='div_iter_url')

        for articulo in articulos:
            link_elem = articulo.get('data-urldestination')
            if link_elem and link_elem != '/':
                link_completo = "https://www.elcolombiano.com" + link_elem
                links.append(link_completo)

        return links

class ScraperBCNoticias(ScraperPeriodico):
    REGION = "eje_cafetero_antioquia"
    BASE_URL = "https://www.bcnoticias.com.co"

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)

    @property
    def nombre_periodico(self) -> str:
        return "BC Noticias"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        if pagina == 1:
            return f"{self.BASE_URL}/?s={self.termino}"
        return f"{self.BASE_URL}/page/{pagina}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        try:
            pag = soup.find('div', class_='page-nav')
            if pag:
                span = pag.find('span', class_='pages')
                if span:
                    match = re.search(r'Página \d+ de (\d+)', span.get_text())
                    if match:
                        return int(match.group(1))
        except Exception:
            pass
        return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        links = []
        for modulo in soup.find_all('div', class_=lambda c: c and 'td_module_wrap' in c):
            a = modulo.find('a', rel='bookmark')
            if a and a['href'].startswith(self.BASE_URL):
                links.append(a['href'])
        return links

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []
        fecha_desde_dt = datetime.strptime(self.fecha_desde, '%Y-%m-%d')
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, '%Y-%m-%d')

        for pagina in range(1, total_paginas + 1):
            if pagina % 5 == 0 or pagina == 1:
                print(f"Recolectando links: página {pagina}/{total_paginas}")

            try:
                url = self._construir_url_busqueda(pagina)
                r = self.session.get(url, timeout=10)
                soup = BeautifulSoup(r.content, 'html.parser')

                if pagina == 1:
                    total_paginas = self._obtener_total_paginas(soup)
                    print(f"Total de páginas: {total_paginas}")

                modulos = soup.find_all('div', class_=lambda c: c and 'td_module_wrap' in c)
                if not modulos:
                    print(f"  Sin resultados en página {pagina}, deteniendo")
                    break

                parar = False
                for modulo in modulos:
                    time_elem = modulo.find('time')
                    fecha_art = None
                    if time_elem:
                        try:
                            fecha_art = datetime.fromisoformat(time_elem['datetime'][:10])
                        except Exception:
                            pass

                    a = modulo.find('a', rel='bookmark')
                    if not a:
                        continue
                    href = a['href']

                    if fecha_art is None:
                        links.append(href)
                    elif fecha_art > fecha_hasta_dt:
                        continue
                    elif fecha_desde_dt <= fecha_art <= fecha_hasta_dt:
                        links.append(href)
                    elif fecha_art < fecha_desde_dt:
                        print(f"  Artículos anteriores a {self.fecha_desde}, deteniendo en página {pagina}")
                        parar = True
                        break

                if parar:
                    break

                time.sleep(0.1)

            except Exception as e:
                print(f"Error en página {pagina}: {e}")
                continue

        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

class ScraperElQuindiano(ScraperPeriodico):
    REGION = "eje_cafetero_antioquia"

    BASE_URL = "https://elquindiano.com"
    API_URL = "https://elquindiano.com/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}  # url → fecha

    @property
    def nombre_periodico(self) -> str:
        return "El Quindiano"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df


# ── SCRAPERS: SUROCCIDENTE / PACÍFICO ────────────────────────────────────────

class ScraperElPaisCali(ScraperPeriodico):
    REGION = "suroccidente"
    """Scraper específico para El País (Cali)"""

    BASE_URL = "https://www.elpais.com.co"
    API_URL = "https://api.queryly.com/json.aspx"
    QUERYLY_KEY = "90ca15cd05a84124"
    BATCH_SIZE = 20

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.session.headers.update({
            'User-Agent': 'python-requests/2.31.0',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

    @property
    def nombre_periodico(self) -> str:
        return "El País Cali"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/buscador/?query={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _parsear_fecha_articulo(self, texto_fecha: str) -> Optional[datetime]:
        if not texto_fecha:
            return None
        try:
            # Formato: "Mar 02, 2026"
            return datetime.strptime(texto_fecha.strip(), '%b %d, %Y')
        except Exception:
            pass
        try:
            return datetime.fromisoformat(texto_fecha[:10])
        except Exception:
            pass
        return None

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        return []  # No se usa, la API devuelve los links directamente

    def _fetch_api(self, endindex: int) -> Optional[dict]:
        try:
            r = self.session.get(
                self.API_URL,
                params={
                    "queryly_key": self.QUERYLY_KEY,
                    "query": self.termino,
                    "endindex": endindex,
                    "batchsize": self.BATCH_SIZE,
                    "showfaceted": "true",
                    "extendeddatafields": "creator,imageresizer,promo_image",
                    "timezoneoffset": "300",
                    "sort": "date",
                },
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"  Error API: {e}")
        return None

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []
        fecha_desde_dt = datetime.strptime(self.fecha_desde, '%Y-%m-%d')
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, '%Y-%m-%d')
        endindex = 0
        pagina = 1

        while True:
            if pagina % 5 == 0 or pagina == 1:
                print(f"Recolectando links: página {pagina} (endindex={endindex})")

            data = self._fetch_api(endindex)
            if not data:
                print("  Error al obtener datos de la API")
                break

            items = data.get('items', [])
            if not items:
                print("  No hay más artículos")
                break

            parar = False
            for item in items:
                fecha_str = item.get('pubdate') or item.get('date') or item.get('pubDate', '')
                fecha_art = self._parsear_fecha_articulo(fecha_str)

                href = item.get('link') or item.get('url') or item.get('permalink', '')
                if not href:
                    continue
                if not href.startswith('http'):
                    href = self.BASE_URL + href

                if fecha_art is None:
                    links.append(href)
                elif fecha_art > fecha_hasta_dt:
                    continue
                elif fecha_desde_dt <= fecha_art <= fecha_hasta_dt:
                    links.append(href)
                elif fecha_art < fecha_desde_dt:
                    print(f"  Artículos anteriores a {self.fecha_desde}, deteniendo")
                    parar = True
                    break

            if parar:
                break

            total = data.get('metadata', {}).get('total', 0)
            endindex += self.BATCH_SIZE
            if endindex >= total:
                print(f"  Se agotaron los resultados (total: {total})")
                break

            pagina += 1
            time.sleep(0.1)

        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

class ScraperDiarioOccidente(ScraperPeriodico):
    REGION = "suroccidente"
    """Scraper específico para Diario Occidente (Cali)"""

    BASE_URL = "https://occidente.co"

    MESES = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    @property
    def nombre_periodico(self) -> str:
        return "Diario Occidente"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        if pagina == 1:
            return f"{self.BASE_URL}/?s={self.termino}"
        return f"{self.BASE_URL}/page/{pagina}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        try:
            paginacion = soup.find('div', class_='pagination')
            if paginacion:
                # Buscar solo en el span "Página X de Y"
                span = paginacion.find('span', string=re.compile(r'Página'))
                if span:
                    match = re.search(r'Página \d+ de (\d+)', span.get_text())
                    if match:
                        return int(match.group(1))
        except Exception:
            pass
        return 1

    def _parsear_fecha_articulo(self, texto_fecha: str) -> Optional[datetime]:
        """Convierte 'martes 24 de febrero, 2026' o 'febrero 24, 2026' a datetime"""
        if not texto_fecha:
            return None
        try:
            texto = texto_fecha.lower().strip()
            # Formato: "martes 24 de febrero, 2026" o "24 de febrero, 2026"
            match = re.search(r'(\d{1,2})\s+de\s+(\w+)[,\s]+(\d{4})', texto)
            if match:
                dia = int(match.group(1))
                mes_str = match.group(2)
                año = int(match.group(3))
                mes = self.MESES.get(mes_str)
                if mes:
                    return datetime(año, mes, dia)
            # Formato alternativo: "febrero 2, 2026"
            match = re.search(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', texto)
            if match:
                mes_str = match.group(1)
                dia = int(match.group(2))
                año = int(match.group(3))
                mes = self.MESES.get(mes_str)
                if mes:
                    return datetime(año, mes, dia)
        except Exception:
            pass
        return None

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []
        fecha_desde_dt = datetime.strptime(self.fecha_desde, '%Y-%m-%d')
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, '%Y-%m-%d')
        paginas_vacias_consecutivas = 0   # parada anticipada por fecha

        for pagina in range(1, total_paginas + 1):
            if pagina % 5 == 0 or pagina == 1:
                print(f"Recolectando links: página {pagina}/{total_paginas}")

            try:
                url = self._construir_url_busqueda(pagina)
                # timeout=10 -> 25: medido 2026-08-31 contra la red real, occidente.co
                # responde en 10-12s normalmente para busquedas paginadas — no es un
                # sitio caido ni con rate-limiting, solo lento. Con 10s la mayoria de
                # las paginas fallaban (Read timed out) y se saltaban en silencio sin
                # reintento, perdiendo articulos reales. Ver 08_log_decisiones.md.
                r = self.session.get(url, timeout=25)
                soup = BeautifulSoup(r.content, 'html.parser')

                main = soup.find('div', class_='main-content') or soup
                bloques = main.find_all('div', class_=lambda c: c and 'border-bottom-1px-solid-gray' in c)

                if not bloques:
                    print(f"  Sin resultados en página {pagina}, deteniendo")
                    break

                n_antes = len(links)
                hay_mas_recientes = False   # algún artículo posterior a fecha_hasta

                for bloque in bloques:
                    # Fecha
                    fecha_art = None
                    time_elem = bloque.find('time')
                    if time_elem:
                        dt_attr = time_elem.get('datetime', '')
                        if dt_attr:
                            try:
                                fecha_art = datetime.fromisoformat(dt_attr[:10])
                            except Exception:
                                pass
                        if not fecha_art:
                            fecha_art = self._parsear_fecha_articulo(time_elem.get_text())
                    if not fecha_art:
                        fecha_art = self._parsear_fecha_articulo(bloque.get_text())

                    # Link
                    a = bloque.find('a', href=True)
                    if not a:
                        continue
                    href = a['href']
                    if not href.startswith(self.BASE_URL):
                        continue

                    if fecha_art is None:
                        links.append(href)
                    elif fecha_art > fecha_hasta_dt:
                        hay_mas_recientes = True   # aún antes del rango, no contar como vacía
                        continue
                    elif fecha_desde_dt <= fecha_art <= fecha_hasta_dt:
                        links.append(href)
                    elif fecha_art < fecha_desde_dt:
                        # NO se detiene aquí: la búsqueda de WordPress ordena por
                        # relevancia, no por fecha — un artículo de 2020 puede
                        # aparecer en la página 1 intercalado con otros de 2026
                        # (medido 2026-08-31, ver 08_log_decisiones.md). Parar en
                        # el primero que se ve descarta páginas con artículos en
                        # rango todavía por recorrer. Se ignora y se sigue; la
                        # parada real es la de abajo (3 páginas sin nada nuevo).
                        continue

                # Parada anticipada: 3 páginas seguidas con artículos pero ninguno en rango
                # (solo cuando ya no hay artículos más nuevos que el rango — flag hay_mas_recientes)
                nuevos = len(links) - n_antes
                if nuevos == 0 and bloques and not hay_mas_recientes:
                    paginas_vacias_consecutivas += 1
                    if paginas_vacias_consecutivas >= 3:
                        print(f"  3 páginas sin artículos en rango — deteniendo.")
                        break
                else:
                    paginas_vacias_consecutivas = 0

                time.sleep(0.1)

            except Exception as e:
                print(f"Error en página {pagina}: {e}")
                continue

        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

import warnings
try:
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except ImportError:
    pass  # bs4 < 4.12.0 no tiene esta advertencia

class ScraperDiarioDelSur(ScraperPeriodico):
    REGION = "suroccidente"
    BASE_URL = "https://www.diariodelsur.com.co"

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        original_get = self.session.get
        def get_con_timeout(*args, **kwargs):
            kwargs.setdefault('timeout', 30)
            return original_get(*args, **kwargs)
        self.session.get = get_con_timeout

    @property
    def nombre_periodico(self) -> str:
        return "Diario del Sur"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/feed/?s={self.termino}&paged={pagina}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        try:
            nav = soup.find('nav', class_='pagination')
            if nav:
                nums = []
                for a in nav.find_all('a'):
                    try:
                        nums.append(int(a.get_text(strip=True)))
                    except ValueError:
                        continue
                if nums:
                    return max(nums)
        except Exception:
            pass
        return 1

    def _parsear_fecha_articulo(self, texto_fecha: str) -> Optional[datetime]:
        if not texto_fecha:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(texto_fecha.strip()).replace(tzinfo=None)
        except Exception:
            pass
        return None

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []
        fecha_desde_dt = datetime.strptime(self.fecha_desde, '%Y-%m-%d')
        fecha_hasta_dt = datetime.strptime(self.fecha_hasta, '%Y-%m-%d')

        try:
            r_html = self.session.get(f"{self.BASE_URL}/?s={self.termino}", timeout=30)
            soup_html = BeautifulSoup(r_html.content, 'html.parser')
            total_paginas = self._obtener_total_paginas(soup_html)
            print(f"Total de páginas: {total_paginas}")
        except Exception as e:
            print(f"Error obteniendo total páginas: {e}")
            total_paginas = 1

        for pagina in range(1, total_paginas + 1):
            if pagina % 5 == 0 or pagina == 1:
                print(f"Recolectando links: página {pagina}/{total_paginas}")

            try:
                r = self.session.get(self._construir_url_busqueda(pagina), timeout=30)
                soup = BeautifulSoup(r.content, 'lxml-xml')

                items = soup.find_all('item')
                if not items:
                    print(f"  Sin artículos en página {pagina}, deteniendo")
                    break

                parar = False
                for item in items:
                    pub_date = item.find('pubDate')
                    fecha_art = self._parsear_fecha_articulo(pub_date.get_text() if pub_date else '')

                    guid = item.find('guid')
                    href = guid.get_text(strip=True) if guid else ''
                    if not href or not href.startswith(self.BASE_URL):
                        continue

                    if fecha_art is None:
                        links.append(href)
                    elif fecha_art > fecha_hasta_dt:
                        continue
                    elif fecha_desde_dt <= fecha_art <= fecha_hasta_dt:
                        links.append(href)
                    elif fecha_art < fecha_desde_dt:
                        print(f"  Artículos anteriores a {self.fecha_desde}, deteniendo en página {pagina}")
                        parar = True
                        break

                if parar:
                    break

                # Sin sleep en el camino exitoso — el sitio aguanta bien sin throttling.
                # Solo esperamos ante errores para no saturar tras un fallo.

            except Exception as e:
                print(f"Error en página {pagina}: {e}")
                time.sleep(2)
                continue

        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        links = self._recolectar_links(999)
        if not links:
            print("No se encontraron links")
            return pd.DataFrame()
        return self._descargar_articulos(links)

class ScraperDiarioDelCauca(ScraperPeriodico):
    REGION = "suroccidente"
    BASE_URL = "https://diariodelcauca.com.co"
    API_URL = "https://diariodelcauca.com.co/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}
        original_get = self.session.get
        def get_con_timeout(*args, **kwargs):
            kwargs.setdefault('timeout', 30)
            return original_get(*args, **kwargs)
        self.session.get = get_con_timeout

    @property
    def nombre_periodico(self) -> str:
        return "Diario del Cauca"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df

class ScraperChoco7Dias(ScraperPeriodico):
    REGION = "suroccidente"

    BASE_URL = "https://choco7dias.com"
    API_URL = "https://choco7dias.com/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}

    @property
    def nombre_periodico(self) -> str:
        return "Chocó 7 Días"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=30) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        # choco7dias.com es lento — 5 conexiones evitan timeouts masivos con limit=50
        connector = aiohttp.TCPConnector(limit=5, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df


# ── SCRAPERS: ORINOQUÍA / AMAZONÍA ───────────────────────────────────────────

class ScraperLlanoAlMundo(ScraperPeriodico):
    REGION = "orinoquia_amazonia"
    BASE_URL = "https://llanoalmundo.com"
    API_URL = "https://llanoalmundo.com/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}

    @property
    def nombre_periodico(self) -> str:
        return "Llano al Mundo"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _descargar_articulos_serial(self, links: List[str]) -> pd.DataFrame:
        """Descarga secuencial con rate limiting gentil (LlanoAlMundo)."""
        print(f"\nDescargando {len(links)} artículos...")
        data = []
        for i, link in enumerate(links, 1):
            resultado = self._descargar_articulo_individual((i, link))
            if resultado:
                data.append(resultado)
            time.sleep(0.5)

        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=30) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        # llanoalmundo.com responde con "Database Error" cuando se satura — limit=5 evita rate limiting
        connector = aiohttp.TCPConnector(limit=5, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df

class ScraperDiarioDeCasanare(ScraperPeriodico):
    REGION = "orinoquia_amazonia"
    BASE_URL = "https://www.diariodecasanare.com"
    API_URL = "https://www.diariodecasanare.com/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}

    @property
    def nombre_periodico(self) -> str:
        return "Diario de Casanare"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=30) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        # diariodecasanare.com es un servidor lento — 5 conexiones concurrentes
        # reducen los TimeoutError que ocurrían con limit=50
        connector = aiohttp.TCPConnector(limit=5, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df

class ScraperLaVozDelCinaruco(ScraperPeriodico):
    REGION = "orinoquia_amazonia"
    BASE_URL = "https://lavozdelcinaruco.com"
    API_URL = "https://lavozdelcinaruco.com/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}

    @property
    def nombre_periodico(self) -> str:
        return "La Voz del Cinaruco"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=30) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        # lavozdelcinaruco.com es un servidor lento — 5 conexiones concurrentes
        # evitan el 93 % de TimeoutError que ocurría con limit=50
        connector = aiohttp.TCPConnector(limit=5, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df

class ScraperElMorichal(ScraperPeriodico):
    REGION = "orinoquia_amazonia"
    BASE_URL = "https://elmorichal.com"
    API_URL = "https://elmorichal.com/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}

    @property
    def nombre_periodico(self) -> str:
        return "El Morichal"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df

class ScraperMiPutumayo(ScraperPeriodico):
    REGION = "orinoquia_amazonia"

    BASE_URL = "https://miputumayo.com.co"
    API_URL = "https://miputumayo.com.co/wp-json/wp/v2/posts"
    PER_PAGE = 100

    def __init__(self, termino, fecha_desde, fecha_hasta):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self._fechas = {}

    @property
    def nombre_periodico(self) -> str:
        return "Mi Putumayo"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return f"{self.BASE_URL}/?s={self.termino}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # Requerido por la clase base pero no se usa — la lógica está en _recolectar_links
        return []

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []

        # Concurrencia con asyncio y aiohttp
        async def fetch_wp_pages():
            # Mismo MITM de Norton que ScraperElTiempo ya parchaba (ver contexto/
            # 08_log_decisiones.md, 2026-08-30). Sin esto, aiohttp falla con
            # CERTIFICATE_VERIFY_FAILED igual que requests sin verify=False.
            conector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=conector) as session:
                # Primera página para obtener X-WP-TotalPages
                try:
                    params = {
                        "search": self.termino, "per_page": self.PER_PAGE, "page": 1,
                        "orderby": "date", "order": "desc",
                        "after": f"{self.fecha_desde}T00:00:00", "before": f"{self.fecha_hasta}T23:59:59"
                    }
                    async with session.get(self.API_URL, params=params, timeout=15) as r:
                        if r.status != 200:
                            return []
                        total_pags = int(r.headers.get('X-WP-TotalPages', 1))
                        data = await r.json()
                        links_pagina = [post.get('link') for post in data if post.get('link')]
                        # Cache fechas
                        for post in data:
                            if post.get('link') and post.get('date'):
                                try:
                                    self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                except Exception:
                                    pass
                        links_todas = []
                        links_todas.extend(links_pagina)

                        if total_pags > 1:
                            print(f"Recolectando links de {total_pags} páginas concurrentemente...")

                            async def fetch_page(p):
                                try:
                                    p_params = params.copy()
                                    p_params["page"] = p
                                    async with session.get(self.API_URL, params=p_params, timeout=15) as rp:
                                        if rp.status == 200:
                                            p_data = await rp.json()
                                            for post in p_data:
                                                if post.get('link') and post.get('date'):
                                                    try:
                                                        self._fechas[post['link']] = datetime.fromisoformat(post['date'])
                                                    except:
                                                        pass
                                            return [post.get('link') for post in p_data if post.get('link')]
                                except Exception:
                                    pass
                                return []

                            tareas = [fetch_page(p) for p in range(2, total_pags + 1)]
                            res = await asyncio.gather(*tareas)
                            for r_pag in res:
                                links_todas.extend(r_pag)

                        return links_todas
                except Exception as e:
                    print(f"Error inicial: {e}")
                    return []

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            links = loop.run_until_complete(fetch_wp_pages())
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=30) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas.get(link, article.publish_date) if hasattr(self, '_fechas') else article.publish_date,
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        # miputumayo.com.co es lento — 5 conexiones reducen el 86% de TimeoutError con limit=50
        connector = aiohttp.TCPConnector(limit=5, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)

        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (
                df['fecha'].isna() |
                ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt))
            )
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)

        return df


# ── SCRAPERS: CENTRAL (BOGOTÁ) ───────────────────────────────────────────────

class ScraperElTiempo(ScraperPeriodico):
    REGION = "central"
    """Scraper específico para El Tiempo"""

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str):
        super().__init__(termino, fecha_desde, fecha_hasta)
        # eltiempo.com verifica con un cert MITM inyectado por el antivirus local
        # (Norton SSL/TLS scanning), no confiable para el cadena raiz de Python.
        # Se desactiva verify solo para este scraper.
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @property
    def nombre_periodico(self) -> str:
        return "El Tiempo"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        url_base = (f'https://www.eltiempo.com/buscar/?q={self.termino}'
                   f'&articleTypes=especial_modular,especial-tipo-d,default,gallery,'
                   f'video_detail,play_video_detail,premium,opinion,obituario,carta,'
                   f'podcast,editorial,foro,caricatura,infografia'
                   f'&from={self.fecha_desde}&until={self.fecha_hasta}')

        if pagina > 1:
            url_base += f'&page={pagina}'

        return url_base

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        pagination = soup.find('nav', class_='c-pagination')

        if pagination:
            numeros = []
            for link in pagination.find_all('a'):
                texto = link.text.strip()
                if texto.isdigit():
                    numeros.append(int(texto))

            if numeros:
                return max(numeros)

        return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        links = []
        articulos = soup.find_all('article', class_='c-article')

        for articulo in articulos:
            link_elem = articulo.find('a', class_='page-link', href=True)
            if link_elem:
                link_completo = "https://www.eltiempo.com" + link_elem['href']
                links.append(link_completo)

        return links

    def _descargar_articulo_individual(self, info: tuple) -> Optional[Dict]:
        """Igual que la base, pero con verify=False (mismo MITM de Norton
        que afecta la busqueda tambien rompe newspaper.Article, que usa su
        propia sesion global de requests)."""
        i, link = info
        try:
            config = Config()
            config.requests_params = {**config.requests_params, "verify": False}
            article = Article(link, config=config)
            article.download()
            article.parse()

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": article.publish_date,
                "texto": article.text
            }
        except:
            return None

class ScraperLaRepublica(ScraperPeriodico):
    REGION = "central"
    """Scraper específico para La República (usa Playwright Async)"""

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str, max_cargas: int = 30):
        """
        Args:
            termino: Término de búsqueda
            fecha_desde: Fecha inicio (YYYY-MM-DD)
            fecha_hasta: Fecha fin (YYYY-MM-DD)
            max_cargas: Límite de veces que se hace clic en "VER MÁS" (default: 30)
        """
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_cargas = max_cargas

        # Permitir event loops anidados en Colab
        nest_asyncio.apply()

    @property
    def nombre_periodico(self) -> str:
        return "La República"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        """Construye URL de búsqueda con filtros de fecha"""
        # Formatear fechas para La República
        from_date = datetime.strptime(self.fecha_desde, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00-05:00")
        to_date = datetime.strptime(self.fecha_hasta, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00-05:00")

        # URL encode
        from_date = from_date.replace(":", "%3A")
        to_date = to_date.replace(":", "%3A")
        term = urllib.parse.quote(self.termino)

        return f"https://www.larepublica.co/buscar?term={term}&from={from_date}&to={to_date}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        """No aplica para La República (usa botón VER MÁS)"""
        return self.max_cargas if self.max_cargas else 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """Extrae enlaces de los resultados visibles"""
        enlaces = []

        try:
            resultados = soup.find_all('a', class_='result')

            for resultado in resultados:
                href = resultado.get('href', '')
                if href:
                    url = f"https://www.larepublica.co{href}" if not href.startswith('http') else href
                    enlaces.append(url)

        except Exception as e:
            print(f"Error al extraer enlaces: {e}")

        return enlaces

    async def _recolectar_links_async(self, total_paginas: int) -> List[str]:
        """Recolecta links usando Playwright Async con botón VER MÁS"""
        links = []
        cargas = 0

        async with async_playwright() as p:
            # Lanzar navegador
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )

            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = await context.new_page()

            try:
                # Cargar página inicial
                url = self._construir_url_busqueda()

                await page.goto(url, wait_until='domcontentloaded', timeout=30000)

                # Esperar a que carguen los resultados iniciales
                try:
                    await page.wait_for_selector('a.result', timeout=10000)
                except PlaywrightTimeout:
                    print("⚠️ No se encontraron resultados")
                    await browser.close()
                    return []

                # Extraer enlaces iniciales
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')
                links_iniciales = self._extraer_links_pagina(soup)
                links.extend(links_iniciales)


                # Hacer clic en "VER MÁS" repetidamente
                while True:
                    # Verificar límite de cargas
                    if self.max_cargas and cargas >= self.max_cargas:

                        break

                    try:
                        # Buscar botón "VER MÁS"
                        ver_mas_button = page.locator('button.button a.btn.analisisSect:has-text("VER MÁS")')

                        # Verificar si el botón existe
                        if await ver_mas_button.count() == 0:

                            break

                        # Scroll al botón
                        await ver_mas_button.scroll_into_view_if_needed()
                        await page.wait_for_timeout(1000)

                        # Click en el botón
                        await ver_mas_button.click()
                        cargas += 1

                        # Esperar a que carguen nuevos resultados
                        await page.wait_for_timeout(3000)

                        # Extraer nuevos enlaces
                        html = await page.content()
                        soup = BeautifulSoup(html, 'html.parser')
                        enlaces_actuales = self._extraer_links_pagina(soup)

                        # Filtrar solo los nuevos
                        urls_existentes = set(links)
                        nuevos = [url for url in enlaces_actuales if url not in urls_existentes]

                        if nuevos:
                            links.extend(nuevos)

                        else:
                            break

                    except Exception as e:
                        print(f"\n✅ No se pudo hacer clic en 'VER MÁS': {e}")
                        break

            finally:
                await browser.close()

        # Eliminar duplicados
        links = list(dict.fromkeys(links))
        return links

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        """Wrapper sincrónico para el método async (override del método base)"""
        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._recolectar_links_async(total_paginas))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

class ScraperPortafolio(ScraperPeriodico):
    REGION = "central"
    """
    Scraper para Portafolio (portafolio.co).

    - HTML estático: requests + BeautifulSoup (sin Playwright)
    - Paginación por &page=N, máximo 20 artículos por página
    - Total de resultados en <p class="search__title">
    - Links relativos en <a class="page-link"> dentro de <article>
    - Fecha en <time class="c-article__date" datetime="YYYY-MM-DDTHH:MM:SS">
    - Filtro de anuncios: se excluyen links externos (syndicatedsearch, goog, etc.)
    - Parámetro max_articulos para limitar resultados (default: 300)
    """

    BASE_URL = "https://www.portafolio.co"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.portafolio.co/",
    }

    def __init__(
        self,
        termino: str,
        fecha_desde: str,
        fecha_hasta: str,
        max_articulos: int = 300,
    ):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_articulos = max_articulos
        self.session.headers.update(self.HEADERS)
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "Portafolio"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        termino_encoded = requests.utils.quote(self.termino)
        # sort=display_date:desc es el parámetro estándar de Arc XP para ordenar
        # resultados por fecha descendente en vez de por relevancia.
        # Si el parámetro no es reconocido por el buscador, se ignora silenciosamente
        # y los resultados vuelven a ser por relevancia (limitación conocida del sitio).
        url = f"{self.BASE_URL}/buscar/?q={termino_encoded}&sort=display_date:desc"
        if pagina > 1:
            url += f"&page={pagina}"
        return url

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        try:
            p = soup.find("p", class_="search__title")
            if not p:
                return 1
            texto = p.get_text(strip=True)
            numeros = re.findall(r"\d+", texto.replace(".", "").replace(",", ""))
            if not numeros:
                return 1
            total = int(numeros[0])
            total_limitado = min(total, self.max_articulos)
            paginas = math.ceil(total_limitado / 20)
            print(f"  Total resultados: {total} | Límite: {self.max_articulos} "
                  f"| Páginas a recorrer: {paginas}")
            return paginas
        except Exception:
            return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        links = []
        articulos = soup.find_all("article", class_="c-article")

        for articulo in articulos:
            a = articulo.find("a", class_="page-link")
            if not a:
                continue

            href = a.get("href", "").strip()
            if not href:
                continue

            if href.startswith("http") and self.BASE_URL not in href:
                continue

            link_completo = self.BASE_URL + href if href.startswith("/") else href

            time_tag = articulo.find("time", class_="c-article__date")
            fecha = None
            if time_tag and time_tag.get("datetime"):
                fecha = self._parsear_fecha_portafolio(time_tag["datetime"])

            self._fechas_cache[link_completo] = fecha
            links.append(link_completo)

        return links

    # ── Parseo de fecha ────────────────────────────────────────────────────

    def _parsear_fecha_portafolio(self, datetime_str: str) -> Optional[datetime]:
        """
        Parsea el atributo datetime del tag <time>.
        Formatos esperados:
          "2023-04-15T10:30:00-05:00"
          "2023-04-15T10:30:00"
          "2023-04-15"
        Retorna datetime sin zona horaria.
        """
        if not datetime_str:
            return None

        datetime_str = datetime_str.strip()

        # Intentar con zona horaria
        for fmt in [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]:
            try:
                dt = datetime.strptime(datetime_str[:len(fmt) + 5], fmt)
                # Quitar timezone si existe
                return dt.replace(tzinfo=None)
            except ValueError:
                continue

        # Fallback: tomar solo la parte de fecha
        try:
            return datetime.strptime(datetime_str[:10], "%Y-%m-%d")
        except ValueError:
            return None

    # ── Override de scrape() ────────────────────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  Límite de artículos: {self.max_articulos}")

        # Retry primera página (SSL drops o timeouts intermitentes)
        soup_p1 = None
        for intento in range(3):
            try:
                url_p1 = self._construir_url_busqueda(pagina=1)
                r = self.session.get(url_p1, timeout=15)
                r.raise_for_status()
                soup_p1 = BeautifulSoup(r.text, "html.parser")
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

        total_paginas = self._obtener_total_paginas(soup_p1)
        links_en_rango = []

        for pagina in range(1, total_paginas + 1):
            try:
                if pagina == 1:
                    soup = soup_p1
                else:
                    url = self._construir_url_busqueda(pagina=pagina)
                    r = self.session.get(url, timeout=15)
                    r.raise_for_status()
                    soup = BeautifulSoup(r.text, "html.parser")

                links_pagina = self._extraer_links_pagina(soup)
                print(f"  Página {pagina}/{total_paginas}: {len(links_pagina)} artículos")

                for link in links_pagina:
                    fecha = self._fechas_cache.get(link)
                    if fecha is None:
                        links_en_rango.append(link)
                        continue
                    if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                        links_en_rango.append(link)

                time.sleep(0.1)

            except Exception as e:
                print(f"  Error en página {pagina}: {e}")
                continue

        links_en_rango = list(dict.fromkeys(links_en_rango))
        print(f"  Total links únicos en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        df = self._descargar_articulos(links_en_rango)

        # Filtro post-descarga: El Tiempo a veces devuelve artículos fuera del rango
        # (links sin fecha en _fechas_cache se incluyen sin verificar la fecha real)
        if not df.empty and 'fecha' in df.columns:
            antes = len(df)
            df = df[df['fecha'].apply(lambda f:
                f is None or not hasattr(f, 'year') or
                (self._fecha_desde_dt <= f <= self._fecha_hasta_dt)
            )]
            filtrados = antes - len(df)
            if filtrados > 0:
                print(f"  Filtro fecha post-descarga: {filtrados} artículos fuera de rango eliminados")

        return df

    # ── Descargas asíncronas ────────────────────────────────────────────────

    async def _descargar_articulo_async(
        self, session: aiohttp.ClientSession, info: tuple
    ) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                # corregido: usar _fechas_cache en vez de _fechas
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text,
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [
                self._descargar_articulo_async(session, info)
                for info in links_enumerados
            ]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df

class ScraperPublimetro(ScraperPeriodico):
    """
    Scraper para Publimetro Colombia (publimetro.co).

    Usa Google Custom Search Engine (CSE) — requiere Playwright para:
    - Escribir el término en el input de búsqueda
    - Esperar a que Google CSE cargue los resultados
    - Navegar por páginas haciendo clic en los números de página

    - Sin paginación por URL: navegación por botones numerados de Google CSE
    - Fecha extraída del breadcrumb: <span> › YYYY/MM/DD</span>
    - Links absolutos — filtrar /tags/ y dominios externos
    - max_articulos para limitar resultados (default: 300)
    """
    REGION = "central"
    BASE_URL     = "https://www.publimetro.co"
    SEARCH_URL   = "https://www.publimetro.co/buscador/"
    DOMINIO      = "publimetro.co"

    def __init__(
        self,
        termino: str,
        fecha_desde: str,
        fecha_hasta: str,
        max_articulos: int = 300,
    ):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_articulos = max_articulos
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "Publimetro"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return self.SEARCH_URL

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 1  # No aplica — manejado por Playwright

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae links desde <a class="gs-title"> dentro de <div class="gsc-webResult">.
        Cachea fecha desde el breadcrumb › YYYY/MM/DD.
        Filtra /tags/ y dominios externos.
        """
        links = []
        vistos = set()

        resultados = soup.find_all("div", class_="gsc-webResult")

        for resultado in resultados:
            a = resultado.find("a", class_="gs-title")
            if not a:
                continue

            href = a.get("href", "").strip()
            if not href:
                continue

            if self.DOMINIO not in href:
                continue
            if "/tags/" in href:
                continue
            if href in vistos:
                continue
            vistos.add(href)

            # Extraer fecha del breadcrumb: › YYYY/MM/DD
            fecha = None
            spans = resultado.find_all("span")
            for span in spans:
                texto = span.get_text(strip=True)
                match = re.search(r"›\s*(\d{4}/\d{2}/\d{2})", texto)
                if match:
                    fecha = self._parsear_fecha_publimetro(match.group(1))
                    break

            self._fechas_cache[href] = fecha
            links.append(href)

        return links

    # ── Parseo de fecha ────────────────────────────────────────────────────

    def _parsear_fecha_publimetro(self, fecha_str: str) -> Optional[datetime]:
        """
        Parsea fechas en formato "YYYY/MM/DD" extraídas del breadcrumb.
        Retorna datetime o None si no puede parsear.
        """
        if not fecha_str:
            return None
        try:
            return datetime.strptime(fecha_str.strip(), "%Y/%m/%d")
        except ValueError:
            return None

    # ── Playwright: búsqueda + paginación por clics ─────────────────────────

    def _get_links_con_playwright(self) -> List[str]:
        import nest_asyncio
        nest_asyncio.apply()

        async def _fetch():
            todos_links  = []
            recolectados = 0

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page    = await browser.new_page()

                print(f"  Cargando buscador: {self.SEARCH_URL}")
                # Timeout aumentado a 60s para sitios lentos
                await page.goto(
                    self.SEARCH_URL, wait_until="domcontentloaded", timeout=60000
                )

                input_selector = "input.gsc-input"
                await page.wait_for_selector(input_selector, timeout=15000)
                await page.fill(input_selector, self.termino)
                await page.keyboard.press("Enter")

                await page.wait_for_selector("div.gsc-webResult", timeout=20000)
                await page.wait_for_load_state("domcontentloaded", timeout=20000)

                pagina_num = 1
                while recolectados < self.max_articulos:
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    if pagina_num == 1:
                        info = soup.find("div", class_="gsc-result-info")
                        if info:
                            print(f"  {info.get_text(strip=True)}")

                    links_pagina = self._extraer_links_pagina(soup)
                    print(f"  Página {pagina_num}: {len(links_pagina)} artículos")
                    todos_links.extend(links_pagina)
                    recolectados += len(links_pagina)

                    if recolectados >= self.max_articulos:
                        print(f"  Límite de {self.max_articulos} artículos alcanzado.")
                        break

                    siguiente_pagina = pagina_num + 1
                    btn_selector = (
                        f"div.gsc-cursor-page[aria-label='Page {siguiente_pagina}']"
                    )
                    btn   = page.locator(btn_selector)
                    count = await btn.count()

                    if count == 0:
                        print("  Sin más páginas disponibles.")
                        break

                    await btn.first.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                    await page.wait_for_selector(
                        "div.gsc-webResult", timeout=15000
                    )
                    pagina_num += 1

                await browser.close()
            return todos_links

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_fetch())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    # ── Override de scrape() ────────────────────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  Límite de artículos: {self.max_articulos}")

        try:
            todos_links = self._get_links_con_playwright()
        except Exception as e:
            print(f"  Error en Playwright: {e}")
            return pd.DataFrame()

        links_unicos = list(dict.fromkeys(todos_links))
        print(f"  Links únicos recolectados: {len(links_unicos)}")

        # Filtrar por rango de fechas
        links_en_rango = []
        for link in links_unicos:
            fecha = self._fechas_cache.get(link)
            if fecha is None:
                links_en_rango.append(link)
                continue
            if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                links_en_rango.append(link)

        print(f"  Links en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)

    # ── Descargas asíncronas ────────────────────────────────────────────────

    async def _descargar_articulo_async(
        self, session: aiohttp.ClientSession, info: tuple
    ) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                # corregido: usar _fechas_cache en vez de _fechas
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text,
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [
                self._descargar_articulo_async(session, info)
                for info in links_enumerados
            ]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df

class ScraperLas2Orillas(ScraperPeriodico):
    """
    Scraper para Las2Orillas (las2orillas.co).

    - HTML estático: requests + BeautifulSoup (sin Playwright)
    - Paginación por URL: https://www.las2orillas.co/page/N/?s=termino
    - Total de páginas extraído del último <a class="page-numbers">
    - 8 artículos por página
    - Links absolutos en <h4 class="entry-title title"> > <a>
    - Fecha en <a href="...las2orillas.co/YYYY/MM/...">mes DD, YYYY</a>
    - Filtro: solo links dentro de las2orillas.co sin /contacto-comercial/,
      /wp-content/, /c/, /author/, /page/, /category/
    - max_articulos para limitar resultados (default: 300)
    """
    REGION = "central"
    BASE_URL   = "https://www.las2orillas.co"
    DOMINIO    = "las2orillas.co"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.las2orillas.co/",
    }

    PATHS_EXCLUIDOS = (
        "/contacto-comercial/",
        "/wp-content/",
        "/author/",
        "/category/",
        "/c/",
        "/page/",
        "/tag/",
    )

    MESES_ES = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }

    def __init__(
        self,
        termino: str,
        fecha_desde: str,
        fecha_hasta: str,
        max_articulos: int = 300,
    ):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_articulos = max_articulos
        self.session.headers.update(self.HEADERS)
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "Las2Orillas"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        termino_encoded = requests.utils.quote(self.termino).replace("%20", "+")
        if pagina == 1:
            return f"{self.BASE_URL}/?s={termino_encoded}"
        return f"{self.BASE_URL}/page/{pagina}/?s={termino_encoded}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        try:
            paginas = soup.find_all("a", class_="page-numbers")
            numeros = []
            for a in paginas:
                texto = a.get_text(strip=True)
                if texto.isdigit():
                    numeros.append(int(texto))

            if not numeros:
                return 1

            total_paginas_sitio  = max(numeros)
            max_paginas_por_limite = min(math.ceil(self.max_articulos / 8), 30)
            total_paginas = min(total_paginas_sitio, max_paginas_por_limite)

            print(f"  Total páginas en sitio: {total_paginas_sitio} | "
                  f"Límite: {self.max_articulos} arts / máx 30 páginas → recorriendo {total_paginas} páginas")
            return total_paginas
        except Exception:
            return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        links = []
        articulos = soup.find_all("article", class_="mg-posts-sec-post")

        for articulo in articulos:
            h4 = articulo.find("h4", class_="entry-title")
            if not h4:
                continue

            a = h4.find("a")
            if not a:
                continue

            href = a.get("href", "").strip()
            if not href:
                continue

            if self.DOMINIO not in href:
                continue
            if any(path in href for path in self.PATHS_EXCLUIDOS):
                continue

            fecha = None
            span_fecha = articulo.find("span", class_="mg-blog-date")
            if span_fecha:
                a_fecha = span_fecha.find("a")
                if a_fecha:
                    texto_fecha = a_fecha.get_text(strip=True)
                    fecha = self._parsear_fecha_las2orillas(texto_fecha)

            self._fechas_cache[href] = fecha
            links.append(href)

        return links

    # ── Parseo de fecha ────────────────────────────────────────────────────

    def _parsear_fecha_las2orillas(self, texto: str) -> Optional[datetime]:
        """
        Parsea fechas en formato español: "agosto 13, 2024" o "agosto 13 2024".
        Retorna datetime o None si no puede parsear.
        """
        if not texto:
            return None

        texto = texto.lower().strip().replace(",", "")
        partes = texto.split()

        if len(partes) < 3:
            return None

        try:
            mes_str = partes[0]
            dia     = int(partes[1])
            anio    = int(partes[2])
            mes     = self.MESES_ES.get(mes_str)

            if mes is None:
                return None

            return datetime(anio, mes, dia)
        except (ValueError, IndexError):
            return None

    # ── Override de scrape() ────────────────────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  Límite de artículos: {self.max_articulos}")

        # Retry primera página — Las2Orillas sufre SSL drops y timeouts intermitentes
        soup_p1 = None
        for intento in range(3):
            try:
                url_p1 = self._construir_url_busqueda(pagina=1)
                r = self.session.get(url_p1, timeout=30)
                r.raise_for_status()
                soup_p1 = BeautifulSoup(r.text, "html.parser")
                break
            except Exception as e:
                if intento < 2:
                    espera = (intento + 1) * 8
                    print(f"  Intento {intento+1}/3 fallido (primera página) — esperando {espera}s...")
                    time.sleep(espera)
                else:
                    print(f"  Error al cargar primera página: {e}")
                    _registrar_error(self.nombre_periodico, 'PrimeraPagina')
                    return pd.DataFrame()

        total_paginas = self._obtener_total_paginas(soup_p1)
        links_en_rango = []
        errores_consecutivos = 0

        for pagina in range(1, total_paginas + 1):
            try:
                if pagina == 1:
                    soup = soup_p1
                else:
                    url = self._construir_url_busqueda(pagina=pagina)

                    respuesta = None
                    for intento in range(3):
                        try:
                            r = self.session.get(url, timeout=30)
                            r.raise_for_status()
                            respuesta = r
                            break
                        except Exception:
                            espera = 5 * (intento + 1)
                            print(f"  Intento {intento+1}/3 fallido en página {pagina} "
                                  f"— esperando {espera}s...")
                            time.sleep(espera)

                    if respuesta is None:
                        errores_consecutivos += 1
                        print(f"  Página {pagina} descartada tras 3 intentos.")
                        if errores_consecutivos >= 5:
                            print("  5 páginas consecutivas fallidas — deteniendo.")
                            break
                        continue

                    errores_consecutivos = 0
                    soup = BeautifulSoup(respuesta.text, "html.parser")

                links_pagina = self._extraer_links_pagina(soup)
                print(f"  Página {pagina}/{total_paginas}: {len(links_pagina)} artículos")

                for link in links_pagina:
                    fecha = self._fechas_cache.get(link)
                    if fecha is None:
                        links_en_rango.append(link)
                        continue
                    if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                        links_en_rango.append(link)

                # 3s elimina el rate-limit que causaba 5s de penalidad por página
                time.sleep(3)

            except Exception as e:
                print(f"  Error en página {pagina}: {e}")
                errores_consecutivos += 1
                if errores_consecutivos >= 5:
                    print("  5 páginas consecutivas fallidas — deteniendo.")
                    break
                continue

        links_en_rango = list(dict.fromkeys(links_en_rango))
        print(f"  Total links únicos en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)

    # ── Descargas asíncronas ────────────────────────────────────────────────

    async def _descargar_articulo_async(
        self, session: aiohttp.ClientSession, info: tuple
    ) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                # corregido: usar _fechas_cache en vez de _fechas
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text,
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [
                self._descargar_articulo_async(session, info)
                for info in links_enumerados
            ]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df


# ── SCRAPERS: CARIBE ─────────────────────────────────────────────────────────

class ScraperElHeraldo(ScraperPeriodico):
    """Scraper específico para El Heraldo (usa Playwright Async)"""
    REGION = "caribe"

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str, max_paginas: int = 30):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_paginas = max_paginas
        self.inicio_rango = datetime.strptime(fecha_desde, '%Y-%m-%d')
        self.fin_rango = datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)

        # Permitir event loops anidados en Colab
        nest_asyncio.apply()

    @property
    def nombre_periodico(self) -> str:
        return "El Heraldo"

    def _parse_spanish_date(self, date_str: str) -> Optional[datetime]:
        """Convierte fecha en formato español a datetime"""
        meses_es = {
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
            'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }

        match = re.search(r'(\d{1,2})\s+(\w{3})\s+(\d{4})', date_str.lower())

        if match:
            dia, mes_abbr, anio = match.groups()
            mes_num = meses_es.get(mes_abbr)

            if mes_num:
                try:
                    return datetime.strptime(f"{dia.zfill(2)}/{mes_num}/{anio}", '%d/%m/%Y')
                except ValueError:
                    return None
        return None

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        """Construye URL de búsqueda"""
        keywords_url = self.termino.replace(" ", "%20").replace(",", "%2C")
        return f"https://www.elheraldo.co/buscador/?query={keywords_url}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        """No aplica para El Heraldo (usa carga dinámica)"""
        return self.max_paginas if self.max_paginas else 999

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """Extrae enlaces con filtrado por fecha"""
        enlaces = []

        try:
            items = soup.find_all('div', class_='queryly_item_row')

            for item in items:
                link_element = item.find('a')
                if link_element and link_element.get('href'):
                    href = link_element['href']
                    url_completa = f"https://www.elheraldo.co{href}" if not href.startswith('http') else href

                    # Extraer y filtrar por fecha
                    fecha_div = item.find('div', style=lambda value: value and 'color:#555' in value)
                    fecha_texto = fecha_div.get_text(strip=True) if fecha_div else ""

                    parsed_date = self._parse_spanish_date(fecha_texto)

                    if parsed_date and self.inicio_rango <= parsed_date <= self.fin_rango:
                        enlaces.append(url_completa)

        except Exception as e:
            print(f"Error al extraer enlaces: {e}")

        return enlaces

    async def _recolectar_links_async(self, total_paginas: int) -> List[str]:
        """Recolecta links usando Playwright Async"""
        links = []
        pagina = 1

        async with async_playwright() as p:
            # Lanzar navegador
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )

            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = await context.new_page()

            try:
                # Cargar página inicial
                url = self._construir_url_busqueda()
                print(f"  [ElHeraldo] Cargando: {url}")

                await page.goto(url, wait_until='domcontentloaded', timeout=30000)

                while True:

                    # Esperar a que carguen los resultados
                    try:
                        await page.wait_for_selector('.queryly_item_row', timeout=10000)
                    except PlaywrightTimeout:
                        # Diagnóstico: el selector no apareció — mostrar fragmento del DOM
                        html_diag = await page.content()
                        print(f"  [ElHeraldo] ⚠️  Selector '.queryly_item_row' no encontrado en página {pagina}")
                        print(f"  [ElHeraldo] Primeros 500 chars del DOM: {html_diag[:500]}")
                        break

                    # Extraer HTML y parsear
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Diagnóstico: cuántos items hay en el DOM antes del filtro de fecha
                    items_dom = soup.find_all('div', class_='queryly_item_row')
                    links_pagina = self._extraer_links_pagina(soup)
                    print(f"  [ElHeraldo] Página {pagina}: {len(items_dom)} items en DOM → "
                          f"{len(links_pagina)} links dentro del rango de fechas")

                    if links_pagina:
                        links.extend(links_pagina)

                    else:
                        None

                    # Verificar límite de páginas
                    if self.max_paginas and pagina >= self.max_paginas:
                        break

                    # Buscar botón "Siguiente"
                    try:
                        next_button = page.locator('a.next_btn')

                        # Verificar si el botón existe
                        if await next_button.count() == 0:
                            break

                        # Scroll al botón
                        await next_button.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)

                        # Click en el botón
                        await next_button.click()

                        # Esperar a que cargue nuevo contenido
                        await page.wait_for_timeout(2000)

                        pagina += 1

                    except Exception as e:
                        print(f"\n✅ No se pudo hacer clic en 'Siguiente': {e}")
                        break

            finally:
                await browser.close()

        # Eliminar duplicados
        links = list(dict.fromkeys(links))
        print(f"Total de links únicos: {len(links)}")
        return links

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        """Wrapper sincrónico para el método async (override del método base)"""
        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._recolectar_links_async(total_paginas))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

class ScraperElUniversal(ScraperPeriodico):
    """
    Scraper para El Universal (eluniversal.com.co).

    Usa Queryly API con sort=date para orden cronológico descendente.
    Búsqueda binaria para saltar directamente a la página del rango,
    evitando recorrer cientos de páginas de artículos más recientes.
    """

    BASE_URL = "https://www.eluniversal.com.co"
    QUERYLY_KEY = "83abeafa666b4fc1"
    BATCH_SIZE = 20
    REGION = "caribe"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.eluniversal.com.co/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    }

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.session.headers.update(self.HEADERS)
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._total_resultados: Optional[int] = None

    @property
    def nombre_periodico(self) -> str:
        return "El Universal"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        endindex = (pagina - 1) * self.BATCH_SIZE
        params = {
            "queryly_key": self.QUERYLY_KEY,
            "initialized": "1",
            "query": self.termino,
            "endindex": endindex,
            "batchsize": self.BATCH_SIZE,
            "callback": "",
            "extendeddatafields": "creator,imageresizer,promo_image",
            "timezoneoffset": "300",
            "sort": "date",
        }
        req = requests.Request("GET", "https://api.queryly.com/v4/search.aspx", params=params)
        return req.prepare().url

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        if self._total_resultados is None:
            return 1
        return math.ceil(self._total_resultados / self.BATCH_SIZE)

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        return getattr(self, "_links_pagina_actual", [])

    # ── Búsqueda binaria ────────────────────────────────────────────────────

    def _encontrar_pagina_inicio(self, total_paginas: int) -> int:
        """
        Búsqueda binaria para encontrar la primera página que toca
        el rango de fechas. Encuentra el punto en ~log2(total_paginas)
        requests en lugar de recorrer secuencialmente desde la página 1.
        """
        izq, der = 1, total_paginas
        resultado = total_paginas

        print(f"  Buscando página de inicio (búsqueda binaria sobre {total_paginas} páginas)...")

        while izq <= der:
            mid = (izq + der) // 2
            try:
                url = self._construir_url_busqueda(mid)
                r = self.session.get(url, timeout=15)
                items, _ = self._parsear_respuesta_queryly(r.text)
                fechas = [self._parsear_fecha_queryly(i.get("pubdate", "")) for i in items]
                fechas_validas = [f for f in fechas if f]

                if not fechas_validas:
                    der = mid - 1
                    continue

                f_min = min(fechas_validas)
                f_max = max(fechas_validas)

                print(f"    Página {mid:>4}: {f_min.strftime('%Y-%m-%d')} → {f_max.strftime('%Y-%m-%d')}")

                if f_max < self._fecha_desde_dt:
                    # Página completamente anterior al rango — buscar más atrás
                    resultado = mid
                    der = mid - 1
                elif f_min > self._fecha_hasta_dt:
                    # Página completamente posterior al rango — avanzar
                    izq = mid + 1
                else:
                    # Página toca el rango — puede haber inicio más atrás
                    resultado = mid
                    der = mid - 1

                time.sleep(0.2)

            except Exception as e:
                print(f"  [búsqueda binaria] Error en página {mid}: {e}")
                izq = mid + 1

        # Margen de seguridad de 2 páginas para no perder artículos del borde
        pagina_inicio = max(1, resultado - 2)
        print(f"  Página de inicio encontrada: {pagina_inicio}")
        return pagina_inicio

    # ── Recolección de links ────────────────────────────────────────────────

    def _recolectar_links(self, total_paginas: int) -> List[str]:
        links = []
        pagina_inicio = self._encontrar_pagina_inicio(total_paginas)
        paginas_consecutivas_viejas = 0

        for pagina in range(pagina_inicio, total_paginas + 1):
            if pagina % 10 == 0 or pagina == pagina_inicio:
                print(f"  Recolectando links: página {pagina}/{total_paginas}")

            try:
                url = self._construir_url_busqueda(pagina)
                r = self.session.get(url, timeout=15)
                items, _ = self._parsear_respuesta_queryly(r.text)

                if not items:
                    print(f"  Página {pagina}: sin resultados, deteniendo.")
                    break

                links_pagina, _ = self._filtrar_links_por_fecha(items)
                links.extend(links_pagina)

                fechas = [self._parsear_fecha_queryly(i.get("pubdate", "")) for i in items]
                fechas_validas = [f for f in fechas if f]

                if fechas_validas:
                    if max(fechas_validas) < self._fecha_desde_dt:
                        paginas_consecutivas_viejas += 1
                        if paginas_consecutivas_viejas >= 2:
                            print(f"  Artículos anteriores al rango. Deteniendo en página {pagina}.")
                            break
                    else:
                        paginas_consecutivas_viejas = 0

                time.sleep(0.3)

            except Exception as e:
                print(f"  Error en página {pagina}: {e}")
                continue

        links = list(dict.fromkeys(links))
        print(f"Total de links únicos en rango de fechas: {len(links)}")
        return links

    # ── scrape() ────────────────────────────────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")

        try:
            url_inicial = self._construir_url_busqueda(pagina=1)
            print(f"  [ElUniversal] URL Queryly: {url_inicial}")
            r = self.session.get(url_inicial, timeout=15)
            print(f"  [ElUniversal] HTTP {r.status_code} | Content-Type: {r.headers.get('Content-Type','?')}")
            _, total = self._parsear_respuesta_queryly(r.text)
            total_paginas = math.ceil(total / self.BATCH_SIZE)
            print(f"  Total artículos en Queryly: {total:,} | Páginas estimadas: {total_paginas}")
        except Exception as e:
            print(f"  Error obteniendo total de resultados: {e}")
            return pd.DataFrame()

        links = self._recolectar_links(total_paginas)

        if not links:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links)

    # ── Métodos auxiliares ──────────────────────────────────────────────────

    def _parsear_respuesta_queryly(self, texto: str):
        match = re.search(r"JSON\.parse\('(.+?)'\);", texto, re.DOTALL)
        if not match:
            # Diagnóstico: mostrar qué devolvió la API para identificar el cambio de formato
            print(f"  [ElUniversal] ⚠️  JSON no encontrado en respuesta Queryly")
            print(f"  [ElUniversal] HTTP status code no disponible aquí — ver respuesta raw:")
            print(f"  [ElUniversal] Primeros 400 chars: {texto[:400]}")
            raise ValueError("No se encontró JSON en la respuesta de Queryly")
        raw_json = match.group(1).encode("utf-8").decode("unicode_escape")
        data = json.loads(raw_json)
        items = data.get("items", [])
        total = data.get("metadata", {}).get("total", 0)
        if self._total_resultados is None:
            self._total_resultados = total
        return items, total

    def _filtrar_links_por_fecha(self, items: list):
        links_en_rango = []
        fuera_de_rango = 0
        for item in items:
            link_relativo = item.get("link", "")
            if not self._es_link_articulo(link_relativo):
                continue
            fecha_articulo = self._parsear_fecha_queryly(item.get("pubdate", ""))
            if fecha_articulo is None:
                links_en_rango.append(self.BASE_URL + link_relativo)
                continue
            if self._fecha_desde_dt <= fecha_articulo <= self._fecha_hasta_dt:
                links_en_rango.append(self.BASE_URL + link_relativo)
            else:
                fuera_de_rango += 1
        return links_en_rango, fuera_de_rango

    def _es_link_articulo(self, link: str) -> bool:
        if not link or not link.startswith("/") or link.startswith("http"):
            return False
        segmentos = [s for s in link.strip("/").split("/") if s]
        if len(segmentos) < 4:
            return False
        try:
            año = int(segmentos[1])
            return 2000 <= año <= 2030
        except (ValueError, IndexError):
            return False

    @staticmethod
    def _parsear_fecha_queryly(pubdate: str) -> Optional[datetime]:
        if not pubdate:
            return None
        meses_es = {
            "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
            "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
            "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec"
        }
        pubdate_norm = pubdate.strip()
        for es, en in meses_es.items():
            pubdate_norm = re.sub(rf"\b{es}\b", en, pubdate_norm, flags=re.IGNORECASE)
        for fmt in ["%b %d, %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(pubdate_norm, fmt)
            except ValueError:
                continue
        return None

class ScraperElPilon(ScraperPeriodico):
    """
    Scraper para El Pilón (elpilon.com.co).

    - Búsqueda: ?q=termino (una sola página, máximo 15 artículos)
    - Sin paginación
    - HTML dinámico — Playwright para renderizar Next.js
    - Fecha extraída del <time datetime="..."> en la página de resultados
    - Links relativos → se completan con BASE_URL
    - Sin filtro de fechas nativo — postprocesamiento
    """

    BASE_URL = "https://elpilon.com.co"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Referer": "https://elpilon.com.co/",
    }
    REGION = "caribe"

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.session.headers.update(self.HEADERS)
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "El Pilón"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        """
        El Pilón solo tiene una página de resultados.
        El parámetro 'pagina' se ignora — siempre retorna la misma URL.
        """
        termino_encoded = requests.utils.quote(self.termino, safe="")
        return f"{self.BASE_URL}/buscar?q={termino_encoded}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        """El Pilón no tiene paginación — siempre es 1 página."""
        return 1

    def _parsear_fecha_iso(self, datetime_str: str) -> Optional[datetime]:
        """Parsea datetime ISO 8601 del atributo datetime del <time>
        (ej: '2024-01-15T10:30:00-05:00') → datetime sin timezone."""
        try:
            dt = datetime.fromisoformat(datetime_str)
            return dt.replace(tzinfo=None)
        except Exception:
            return None

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        links = []
        vistos = set()

        for time_tag in soup.find_all("time", datetime=re.compile(r"^\d{4}-\d{2}-\d{2}T")):
            contenedor = time_tag.find_parent("div")
            if not contenedor:
                continue

            a_titulo = None
            for a in contenedor.find_all("a", href=True):
                href = a.get("href", "")
                segmentos = [s for s in href.strip("/").split("/") if s]
                if href.startswith("/") and len(segmentos) >= 2:
                    a_titulo = a
                    break

            if not a_titulo:
                continue

            href = a_titulo.get("href").strip()
            link_completo = self.BASE_URL + href

            if link_completo in vistos:
                continue
            vistos.add(link_completo)

            fecha = self._parsear_fecha_iso(time_tag.get("datetime", ""))
            self._fechas_cache[link_completo] = fecha
            links.append(link_completo)

        return links

    # ── Playwright: wait_until corregido a domcontentloaded ─────────────────

    def _get_html_con_playwright(self, url: str) -> str:
        async def _fetch(url):
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                # FIX: "networkidle" como wait_until causa timeout en Next.js al inicio.
                # Solución: domcontentloaded primero, luego esperar networkidle para que
                # React/Next.js complete las llamadas API y renderice los artículos.
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                try:
                    # Esperar a que React termine de renderizar los resultados de búsqueda
                    await page.wait_for_load_state("networkidle", timeout=12000)
                except Exception:
                    # Si networkidle no llega en 12s, esperar 5s fijos como fallback
                    await page.wait_for_timeout(5000)
                html = await page.content()
                await browser.close()
                return html

        _loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        try:
            return _loop.run_until_complete(_fetch(url))
        finally:
            _loop.close()
            asyncio.set_event_loop(None)

    # ── scrape(): código duplicado eliminado ────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  [INFO] Máximo 15 artículos por búsqueda (limitación del sitio)")
        print(f"  [INFO] Usando Playwright — sitio Next.js (contenido dinámico)")

        try:
            url = self._construir_url_busqueda()
            html = self._get_html_con_playwright(url)
            soup = BeautifulSoup(html, "html.parser")
            links_todos = self._extraer_links_pagina(soup)
            print(f"  Links encontrados: {len(links_todos)}")
        except Exception as e:
            print(f"  Error obteniendo artículos: {e}")
            return pd.DataFrame()

        links_en_rango = []
        for link in links_todos:
            fecha = self._fechas_cache.get(link)
            if fecha is None:
                links_en_rango.append(link)
                continue
            if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                links_en_rango.append(link)

        print(f"  Links en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)

    # ── Descargas asíncronas ─────────────────────────────────────────────────

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text
            }
        except Exception as e:
            print(f"  Error descargando [{type(e).__name__}] {link}: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df

# ── SCRAPERS: WORDPRESS REST API ─────────────────────────────────────────────

class ScraperWordPressAPI(ScraperPeriodico):
    """Base para sitios WordPress con API REST publica (/wp-json/wp/v2/posts).
    Filtra por termino de busqueda Y por rango de fechas en el servidor
    (after/before), y trae el articulo completo en el mismo JSON -> no
    requiere newspaper.Article para descargar cada pagina aparte."""

    BASE_URL: str = ""  # override en subclase, sin barra final
    PER_PAGE: int = 100  # bajar si el servidor es lento
    TIMEOUT: int = 30
    REINTENTOS: int = 3

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str):
        super().__init__(termino, fecha_desde, fecha_hasta)
        # Mismo MITM de Norton que afecta a eltiempo.com (ver ScraperElTiempo):
        # el antivirus local reemplaza el cert y no esta en el trust store de
        # Python. curl funciona porque usa el almacen de Windows.
        self.session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        return ""  # no se usa, ver scrape() override

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 1  # no se usa

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        return []  # no se usa

    @staticmethod
    def _limpiar_html(html: str) -> str:
        return BeautifulSoup(html or "", "html.parser").get_text(separator=" ", strip=True)

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        termino = urllib.parse.quote(self.termino)
        after = f"{self.fecha_desde}T00:00:00"
        before = f"{self.fecha_hasta}T23:59:59"
        base = (f"{self.BASE_URL}/wp-json/wp/v2/posts"
                f"?search={termino}&after={after}&before={before}"
                f"&per_page={self.PER_PAGE}")

        articulos, pagina, total_paginas = [], 1, None
        while True:
            r = None
            for intento in range(1, self.REINTENTOS + 1):
                try:
                    r = self.session.get(f"{base}&page={pagina}", timeout=self.TIMEOUT)
                    break
                except Exception as e:
                    if intento == self.REINTENTOS:
                        print(f"Error obteniendo pagina {pagina}: {e}")
                    else:
                        time.sleep(2 * intento)
            if r is None:
                break
            if r.status_code != 200:
                print(f"HTTP {r.status_code} en pagina {pagina}")
                break
            if total_paginas is None:
                total_paginas = int(r.headers.get("X-WP-TotalPages", "1") or "1")
                print(f"Total de paginas: {total_paginas}")
            posts = r.json()
            if not posts:
                break
            for post in posts:
                articulos.append({
                    "periodico": self.nombre_periodico,
                    "url": post.get("link", ""),
                    "titulo": self._limpiar_html(post.get("title", {}).get("rendered", "")),
                    "fecha": post.get("date"),
                    "texto": self._limpiar_html(post.get("content", {}).get("rendered", "")),
                })
            if pagina >= total_paginas:
                break
            pagina += 1
            time.sleep(0.3)

        print(f"Total de articulos: {len(articulos)}")
        df = pd.DataFrame(articulos)
        if not df.empty:
            df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        return df


class ScraperDiarioDelNorte(ScraperWordPressAPI):
    REGION = "caribe"
    BASE_URL = "https://diariodelnorte.net"

    @property
    def nombre_periodico(self) -> str:
        return "Diario del Norte"


class ScraperLaGuajiraHoy(ScraperWordPressAPI):
    REGION = "caribe"
    BASE_URL = "https://laguajirahoy.com"
    PER_PAGE = 20   # servidor lento: con 100 por pagina agota el timeout
    TIMEOUT = 60

    @property
    def nombre_periodico(self) -> str:
        return "La Guajira Hoy"


class ScraperBoyaca7Dias(ScraperWordPressAPI):
    REGION = "central"
    BASE_URL = "https://boyaca7dias.com.co"

    @property
    def nombre_periodico(self) -> str:
        return "Boyacá 7 Días"

class ScraperElMeridiano(ScraperPeriodico):
    """
    Scraper para El Meridiano (elmeridiano.co).

    El sitio cubre dos regiones: Córdoba y Sucre. Se recorren ambas
    búsquedas y se deduplicam los links resultantes.

    - Sitio Next.js — requiere Playwright para renderizar contenido
    - Sin paginación por URL: el botón "Siguiente" es JavaScript puro
      → se hace clic programáticamente con Playwright
    - Máximo 5 artículos por página
    - Fecha extraída del <p> con formato "Sección • DD/MM/YYYY"
    - Links relativos → se completan con BASE_URL
    """

    BASE_URL = "https://elmeridiano.co"
    REGIONES = ["cordoba", "sucre"]
    REGION = "caribe"

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str, max_paginas: int = 30):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_paginas = max_paginas
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "El Meridiano"

    def _construir_url_busqueda(self, pagina: int = 1, region: str = "cordoba") -> str:
        termino_encoded = requests.utils.quote(self.termino)
        return f"{self.BASE_URL}/busqueda?q={termino_encoded}&site={region}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae links desde <a class="block p-4 border...">.
        Si el selector original falla (0 resultados), hace fallback
        buscando cualquier <a> con href de artículo válido.
        """
        links = []

        # Intento 1: selector original con clases Tailwind
        articulos = soup.find_all(
            "a",
            class_=lambda c: c and "block" in c and "border" in c and "rounded-lg" in c
        )

        # Intento 2: fallback — cualquier <a> con href que parezca artículo
        if not articulos:
            articulos = [
                a for a in soup.find_all("a", href=True)
                if self._es_link_articulo_meridiano(a.get("href", ""))
            ]

        for a in articulos:
            href = a.get("href", "").strip()
            if not href or not href.startswith("/"):
                continue

            link_completo = self.BASE_URL + href

            fecha = None
            for p in a.find_all("p"):
                texto = p.get_text(strip=True)
                if "•" in texto:
                    fecha = self._parsear_fecha_meridiano(texto)
                    break

            self._fechas_cache[link_completo] = fecha
            links.append(link_completo)

        return links

    def _es_link_articulo_meridiano(self, href: str) -> bool:
        """Valida que el href parezca un artículo y no una sección."""
        if not href or not href.startswith("/"):
            return False
        segmentos = [s for s in href.strip("/").split("/") if s]
        return len(segmentos) >= 2

    # ── Playwright: wait_until corregido a domcontentloaded ─────────────────

    def _get_links_con_playwright(self, region: str) -> List[str]:
        async def _fetch():
            links_region = []

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                url = self._construir_url_busqueda(region=region)
                print(f"    [{region.upper()}] Cargando: {url}")

                # FIX: "networkidle" causa timeout en Next.js — usar "domcontentloaded"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                pagina_num = 1
                while True:
                    if pagina_num > self.max_paginas:
                        print(f"    [{region.upper()}] Límite de {self.max_paginas} páginas alcanzado.")
                        break

                    # Esperar artículos con timeout generoso
                    try:
                        await page.wait_for_selector("a.block", timeout=10000)
                    except Exception:
                        print(f"    [{region.upper()}] Página {pagina_num}: sin artículos (timeout selector)")
                        break

                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")
                    links_pagina = self._extraer_links_pagina(soup)
                    print(f"    [{region.upper()}] Página {pagina_num}: {len(links_pagina)} artículos")
                    links_region.extend(links_pagina)

                    # Buscar botón "Siguiente" habilitado
                    btn_siguiente = page.locator("button:has-text('Siguiente'):not([disabled])")
                    count = await btn_siguiente.count()

                    if count == 0:
                        print(f"    [{region.upper()}] Sin más páginas")
                        break

                    await btn_siguiente.first.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    pagina_num += 1

                await browser.close()
            return links_region

        _loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        try:
            return _loop.run_until_complete(_fetch())
        finally:
            _loop.close()
            asyncio.set_event_loop(None)

    # ── Override de scrape() ────────────────────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  [INFO] Recorriendo ambas regiones: Córdoba y Sucre")

        todos_los_links = []
        for region in self.REGIONES:
            try:
                links_region = self._get_links_con_playwright(region)
                todos_los_links.extend(links_region)
            except Exception as e:
                print(f"  Error en región {region}: {e}")
                continue

        links_unicos = list(dict.fromkeys(todos_los_links))
        print(f"\n  Links totales (sin duplicados de URL): {len(links_unicos)}")

        links_en_rango = []
        for link in links_unicos:
            fecha = self._fechas_cache.get(link)
            if fecha is None:
                links_en_rango.append(link)
                continue
            if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                links_en_rango.append(link)

        print(f"  Links en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        df = self._descargar_articulos(links_en_rango)

        if not df.empty and "titulo" in df.columns:
            antes = len(df)
            df = df.drop_duplicates(subset=["titulo"], keep="first")
            eliminados = antes - len(df)
            if eliminados > 0:
                print(f"  Duplicados por título eliminados: {eliminados}")

        return df

    # ── Descargas asíncronas ─────────────────────────────────────────────────

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text
            }
        except Exception as e:
            print(f"  Error descargando [{type(e).__name__}] {link}: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df


# ── SCRAPERS: NORORIENTE ─────────────────────────────────────────────────────

class ScraperVanguardia(ScraperPeriodico):
    """
    Scraper para Vanguardia (vanguardia.com).

    Usa Queryly como motor de búsqueda externo (igual que El Universal).
    La API retorna JSONP — se extrae el JSON embebido con regex.

    - API: api.queryly.com con queryly_key=71d6147f75ed47b0
    - Paginación: endindex avanza de 20 en 20
    - Links relativos → se completan con BASE_URL
    - Fecha en campo 'pubdate': formato "Apr 22, 2024"
    - Filtro de fechas por postprocesamiento (Queryly no filtra por fecha)
    """

    BASE_URL        = "https://www.vanguardia.com"
    QUERYLY_KEY     = "71d6147f75ed47b0"
    BATCH_SIZE      = 20
    API_URL         = "https://api.queryly.com/json.aspx"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.vanguardia.com/",
    }

    REGION = "nororiente"

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.session.headers.update(self.HEADERS)
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "Vanguardia"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        """No se usa directamente — la paginación se maneja por endindex en la API."""
        return self.BASE_URL

    def _construir_url_api(self, endindex: int) -> str:
        termino_encoded = requests.utils.quote(self.termino)
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

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        # No aplica — paginación manejada directamente en scrape()
        return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        # No aplica — extracción desde JSON de la API
        return []

    # ── Lógica principal: consumir API Queryly ──────────────────────────────

    def _consultar_api(self, endindex: int) -> dict:
      url = self._construir_url_api(endindex)
      r = self.session.get(url, timeout=15)
      r.raise_for_status()

      # Respuesta JSONP: try{ searchPage.resultcallback({...}); } catch(e){}
      # raw_decode parsea el JSON y descarta el ')' sobrante al final
      inicio = r.text.find("(")
      if inicio == -1:
          raise ValueError(f"Respuesta inesperada de Queryly: {r.text[:200]}")

      decoder = json.JSONDecoder()
      data, _ = decoder.raw_decode(r.text, inicio + 1)
      return data

    def _procesar_items(self, items: list) -> List[str]:
        """
        Extrae links del batch de items y cachea fechas.
        Retorna lista de URLs absolutas.
        """
        links = []
        for item in items:
            href = item.get("link", "").strip()
            if not href:
                continue

            # Completar link relativo
            link_completo = self.BASE_URL + href if href.startswith("/") else href

            # Parsear y cachear fecha
            fecha = self._parsear_fecha_queryly(item.get("pubdate", ""))
            self._fechas_cache[link_completo] = fecha
            links.append(link_completo)

        return links

    def _parsear_fecha_queryly(self, pubdate: str) -> Optional[datetime]:
        """
        Parsea la fecha del campo 'pubdate' de la API Queryly.
        Formato esperado: "Apr 22, 2024"
        """
        if not pubdate:
            return None
        try:
            return datetime.strptime(pubdate.strip(), "%b %d, %Y")
        except ValueError:
            pass
        # Intentar formato alternativo con hora: "Apr 22, 2024 10:30 AM"
        try:
            return datetime.strptime(pubdate.strip()[:12], "%b %d, %Y")
        except ValueError:
            pass
        return None

    # ── Override de scrape() ────────────────────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")

        # Primera llamada para obtener total de resultados
        try:
            data = self._consultar_api(endindex=0)
            total = int(data.get("metadata", {}).get("total", 0))
            print(f"  Total de resultados en Queryly: {total}")
        except Exception as e:
            print(f"  Error en primera consulta a la API: {e}")
            return pd.DataFrame()

        if total == 0:
            print("  No se encontraron resultados.")
            return pd.DataFrame()

        # Recolectar links paginando
        links_en_rango = []
        detener = False

        MAX_RESULTADOS = 300

        for endindex in range(0, min(total, MAX_RESULTADOS), self.BATCH_SIZE):
            if detener:
                break

            try:
                if endindex > 0:
                    data = self._consultar_api(endindex)

                items = data.get("items", [])
                if not items:
                    break

                links_batch = self._procesar_items(items)
                pagina_actual = endindex // self.BATCH_SIZE + 1
                print(f"  Página {pagina_actual}: {len(links_batch)} artículos")

                for link in links_batch:
                    fecha = self._fechas_cache.get(link)

                    if fecha is None:
                        links_en_rango.append(link)
                        continue

                    if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                        links_en_rango.append(link)

                time.sleep(0.3)

            except Exception as e:
                print(f"  Error en endindex={endindex}: {e}")
                continue

        links_en_rango = list(dict.fromkeys(links_en_rango))
        print(f"  Total links únicos en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)

    # ── Override de _descargar_articulo_individual (newspaper4k) ────────────

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                # corregido: Vanguardia usa _fechas_cache (no _fechas)
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df

class ScraperTrochandoSinFronteras(ScraperPeriodico):
    """
    Scraper para Trochando Sin Fronteras (trochandosinfronteras.info).

    - HTML estático: requests + BeautifulSoup (sin Playwright)
    - Paginación por URL: /page/N/?s=termino
    - Total de páginas desde <a class="last" title="N">N</a>
    - 10 artículos por página
    - Links en <h3 class="entry-title td-module-title"> > <a>
    - Solo dentro de <div class="tdi_96 ..."> (columna principal, no sidebar)
    - Fecha en <time class="entry-date updated td-module-date" datetime="...">
    - max_articulos para limitar resultados (default: 300)
    """

    BASE_URL = "https://trochandosinfronteras.info"
    DOMINIO  = "trochandosinfronteras.info"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://trochandosinfronteras.info/",
    }

    REGION = "nororiente"

    def __init__(
        self,
        termino: str,
        fecha_desde: str,
        fecha_hasta: str,
        max_articulos: int = 300,
    ):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_articulos = max_articulos
        self.session.headers.update(self.HEADERS)
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "Trochando Sin Fronteras"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        termino_encoded = requests.utils.quote(self.termino).replace("%20", "+")
        if pagina == 1:
            return f"{self.BASE_URL}/?s={termino_encoded}"
        return f"{self.BASE_URL}/page/{pagina}/?s={termino_encoded}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        """
        Extrae el total de páginas desde <a class="last" title="N">.
        Limita según max_articulos (10 artículos por página).
        """
        try:
            a_last = soup.find("a", class_="last")
            if a_last and a_last.get("title", "").isdigit():
                total_paginas_sitio = int(a_last["title"])
            else:
                # Fallback: buscar el número más alto en page-numbers
                nums = []
                for a in soup.find_all("a", class_="page"):
                    t = a.get_text(strip=True)
                    if t.isdigit():
                        nums.append(int(t))
                total_paginas_sitio = max(nums) if nums else 1

            max_paginas_por_limite = math.ceil(self.max_articulos / 10)
            total_paginas = min(total_paginas_sitio, max_paginas_por_limite)

            print(f"  Total páginas en sitio: {total_paginas_sitio} | "
                  f"Límite: {self.max_articulos} arts → recorriendo {total_paginas} páginas")
            return total_paginas
        except Exception:
            return 1

    def _parsear_fecha_trochando(self, datetime_str: str) -> Optional[datetime]:
        """Parsea datetime ISO 8601 del atributo datetime del <time>
        (ej: '2024-01-15T10:30:00-05:00') → datetime sin timezone."""
        try:
            dt = datetime.fromisoformat(datetime_str)
            return dt.replace(tzinfo=None)
        except Exception:
            return None

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae links SOLO desde la columna principal (tdi_96),
        ignorando el sidebar (tdi_99).
        Cachea fecha desde el atributo datetime del <time>.
        """
        links = []

        # Buscar la columna principal por clase parcial 'tdi_96'
        columna_principal = soup.find(
            "div",
            class_=lambda c: c and "tdi_96" in c
        )

        if not columna_principal:
            # Fallback: usar todo el soup si no se encuentra la columna
            columna_principal = soup

        modulos = columna_principal.find_all("div", class_="td-module-container")

        for modulo in modulos:
            # Link desde el título
            h3 = modulo.find("h3", class_="td-module-title")
            if not h3:
                continue

            a = h3.find("a")
            if not a:
                continue

            href = a.get("href", "").strip()
            if not href or self.DOMINIO not in href:
                continue

            # Fecha desde datetime="YYYY-MM-DDTHH:MM:SS-05:00"
            fecha = None
            time_tag = modulo.find("time", class_="td-module-date")
            if time_tag and time_tag.get("datetime"):
                fecha = self._parsear_fecha_trochando(time_tag["datetime"])

            self._fechas_cache[href] = fecha
            links.append(href)

        return links

    # ── Override de scrape() con retry + backoff ────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  Límite de artículos: {self.max_articulos}")

        # Retry primera página — SSL drops intermitentes
        soup_p1 = None
        for intento in range(3):
            try:
                url_p1 = self._construir_url_busqueda(pagina=1)
                r = self.session.get(url_p1, timeout=20)
                r.raise_for_status()
                soup_p1 = BeautifulSoup(r.text, "html.parser")
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

        total_paginas = self._obtener_total_paginas(soup_p1)
        links_en_rango = []
        errores_consecutivos = 0
        paginas_vacias_consecutivas = 0   # parada anticipada por fecha

        for pagina in range(1, total_paginas + 1):
            try:
                if pagina == 1:
                    soup = soup_p1
                else:
                    url = self._construir_url_busqueda(pagina=pagina)

                    respuesta = None
                    for intento in range(3):
                        try:
                            r = self.session.get(url, timeout=25)
                            r.raise_for_status()
                            respuesta = r
                            break
                        except Exception:
                            espera = 5 * (intento + 1)
                            print(f"  Intento {intento+1}/3 fallido en página {pagina} — esperando {espera}s...")
                            time.sleep(espera)

                    if respuesta is None:
                        errores_consecutivos += 1
                        print(f"  Página {pagina} descartada tras 3 intentos.")
                        if errores_consecutivos >= 5:
                            print("  5 páginas consecutivas fallidas — deteniendo scraping.")
                            break
                        continue

                    errores_consecutivos = 0
                    soup = BeautifulSoup(respuesta.text, "html.parser")

                links_pagina = self._extraer_links_pagina(soup)
                print(f"  Página {pagina}/{total_paginas}: {len(links_pagina)} artículos")

                n_antes = len(links_en_rango)
                for link in links_pagina:
                    fecha = self._fechas_cache.get(link)
                    if fecha is None:
                        links_en_rango.append(link)
                        continue
                    if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                        links_en_rango.append(link)

                # Parada anticipada: 3 páginas seguidas sin artículos en rango
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
                    print("  5 páginas consecutivas fallidas — deteniendo scraping.")
                    break
                continue

        links_en_rango = list(dict.fromkeys(links_en_rango))
        print(f"  Total links únicos en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)

    # ── Override de _descargar_articulo_individual (newspaper4k) ────────────

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            async with session.get(link, timeout=15) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                # corregido: TrochandoSinFronteras usa _fechas_cache (no _fechas)
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df

class ScraperEnlaceTelevision(ScraperPeriodico):
    """
    Scraper para Enlace Televisión (enlacetelevision.com).

    - Scroll infinito con botón "More Posts" → requiere Playwright
    - Sin paginación por URL ni total de resultados
    - Links en <li class="mvp-blog-story-wrap"> > <a rel="bookmark">
    - Fecha relativa en <span class="mvp-cd-date">: "4 meses ago", "2 días ago"
      → se calcula restando el tiempo a datetime.now()
    - Parada anticipada: cuando todas las fechas de una carga son anteriores
      a fecha_desde, se detiene el scraping
    - max_articulos para limitar resultados (default: 300)
    """

    BASE_URL   = "https://enlacetelevision.com"
    SEARCH_URL = "https://enlacetelevision.com/?s={termino}"
    DOMINIO    = "enlacetelevision.com"
    REGION = "nororiente"

    def __init__(
        self,
        termino: str,
        fecha_desde: str,
        fecha_hasta: str,
        max_articulos: int = 300,
    ):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_articulos = max_articulos
        self._fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
        self._fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        self._fechas_cache: Dict[str, Optional[datetime]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "Enlace Television"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        termino_encoded = requests.utils.quote(self.termino).replace("%20", "+")
        return f"{self.BASE_URL}/?s={termino_encoded}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        return 1  # No aplica — manejado por Playwright

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae links desde <li class="mvp-blog-story-wrap"> > <a rel="bookmark">.
        Cachea fecha aproximada calculada desde el texto relativo.
        """
        links = []

        items = soup.find_all("li", class_="mvp-blog-story-wrap")

        for item in items:
            a = item.find("a", rel="bookmark")
            if not a:
                continue

            href = a.get("href", "").strip()
            if not href or self.DOMINIO not in href:
                continue

            # Fecha relativa desde <span class="mvp-cd-date">
            fecha = None
            span_fecha = item.find("span", class_="mvp-cd-date")
            if span_fecha:
                texto = span_fecha.get_text(strip=True)
                fecha = self._parsear_fecha_relativa(texto)

            self._fechas_cache[href] = fecha
            links.append(href)

        return links

    # ── Parseo de fecha relativa ────────────────────────────────────────────

    def _parsear_fecha_relativa(self, texto: str) -> Optional[datetime]:
        """
        Parsea fechas relativas del tipo '4 meses ago', '2 días ago',
        '1 año ago', '3 semanas ago', '5 horas ago'.
        Retorna datetime aproximado restando el tiempo a datetime.now().
        """
        if not texto:
            return None

        texto = texto.lower().strip()
        ahora = datetime.now()

        try:
            partes = texto.split()
            if len(partes) < 2:
                return None

            numero = int(partes[0])
            unidad = partes[1]

            if 'año' in unidad or 'ano' in unidad:
                return ahora - timedelta(days=numero * 365)
            elif 'mes' in unidad:
                return ahora - timedelta(days=numero * 30)
            elif 'semana' in unidad:
                return ahora - timedelta(weeks=numero)
            elif 'día' in unidad or 'dia' in unidad:
                return ahora - timedelta(days=numero)
            elif 'hora' in unidad:
                return ahora - timedelta(hours=numero)
            elif 'minuto' in unidad:
                return ahora - timedelta(minutes=numero)
            else:
                return None
        except (ValueError, IndexError):
            return None

    # ── Playwright: scroll infinito con "More Posts" ────────────────────────

    def _get_links_con_playwright(self) -> List[str]:
        import nest_asyncio
        nest_asyncio.apply()

        async def _fetch():
            todos_links   = []
            links_vistos  = set()
            recolectados  = 0
            url_busqueda  = self._construir_url_busqueda()

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page    = await browser.new_page()

                print(f"  Cargando: {url_busqueda}")
                await page.goto(url_busqueda, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector("li.mvp-blog-story-wrap", timeout=15000)

                MAX_CARGAS = 30
                carga_num = 1
                while recolectados < self.max_articulos:
                    if carga_num > MAX_CARGAS:
                        print(f"  Límite de {MAX_CARGAS} cargas alcanzado — deteniendo.")
                        break

                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    links_pagina = self._extraer_links_pagina(soup)

                    links_nuevos = [l for l in links_pagina if l not in links_vistos]
                    links_vistos.update(links_nuevos)

                    print(f"  Carga {carga_num}: {len(links_nuevos)} artículos nuevos")

                    # Parada anticipada — corregido: comparar datetime con datetime
                    if links_nuevos:
                        fechas_nuevas = [
                            self._fechas_cache.get(l)
                            for l in links_nuevos
                            if self._fechas_cache.get(l) is not None
                        ]
                        if fechas_nuevas and all(f < self._fecha_desde_dt for f in fechas_nuevas):
                            print("  Todos los artículos nuevos son anteriores a fecha_desde — deteniendo.")
                            todos_links.extend(links_nuevos)
                            break

                    todos_links.extend(links_nuevos)
                    recolectados = len(todos_links)

                    if recolectados >= self.max_articulos:
                        print(f"  Límite de {self.max_articulos} artículos alcanzado.")
                        break

                    btn = page.locator("a.mvp-inf-more-but")
                    count = await btn.count()
                    if count == 0:
                        print("  Botón 'More Posts' no encontrado — fin del contenido.")
                        break

                    is_visible = await btn.first.is_visible()
                    if not is_visible:
                        print("  Botón 'More Posts' oculto — fin del contenido.")
                        break

                    await btn.first.scroll_into_view_if_needed()
                    await btn.first.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    await asyncio.sleep(1.5)
                    carga_num += 1

                await browser.close()
            return todos_links

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_fetch())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    # ── Override de scrape() ────────────────────────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  Límite de artículos: {self.max_articulos}")

        try:
            todos_links = self._get_links_con_playwright()
        except Exception as e:
            print(f"  Error en Playwright: {e}")
            return pd.DataFrame()

        links_unicos = list(dict.fromkeys(todos_links))
        print(f"  Links únicos recolectados: {len(links_unicos)}")

        # Filtrar por rango de fechas — corregido: comparar datetime con datetime
        links_en_rango = []
        for link in links_unicos:
            fecha = self._fechas_cache.get(link)
            if fecha is None:
                links_en_rango.append(link)
                continue
            if self._fecha_desde_dt <= fecha <= self._fecha_hasta_dt:
                links_en_rango.append(link)

        print(f"  Links en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)

    # ── Descargas asíncronas ────────────────────────────────────────────────

    async def _descargar_articulo_async(self, session: aiohttp.ClientSession, info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            # timeout GRANULAR (no total=15): con TCPConnector(limit=10) y muchos
            # links en un solo asyncio.gather, un timeout total cuenta la espera en
            # cola por una conexion libre, no solo la descarga — con lotes grandes
            # esa cola supera 15s aunque el sitio responda en ~2-3s cada vez, dando
            # TimeoutError que en realidad son de cola, no de red lenta (medido
            # 2026-08-31 contra Corrillos: 68/132 fallos con timeout=15 total, 0/132
            # con este cambio en un lote de 800 — ver 08_log_decisiones.md).
            timeout_dl = aiohttp.ClientTimeout(total=None, sock_connect=20, sock_read=20)
            async with session.get(link, timeout=timeout_dl) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [self._descargar_articulo_async(session, info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df

class ScraperCorrillos(ScraperPeriodico):
    """
    Scraper para Corrillos (corrillos.com.co).

    - HTML estático: requests + BeautifulSoup (sin Playwright)
    - Paginación por URL: /page/N/?s=termino
    - Total de páginas desde el último <a class="page-numbers"> con número
    - 10 artículos por página
    - Links en <h2 class="post-title theme_blog_post__Title"> > <a>
    - Solo dentro de <div class="col-lg-8 col-md-12"> (columna principal)
    - Fecha en <span class="post-meta-date post_post_item_Date">: "agosto 13, 2024"
    - Formato de fecha de salida: "YYYY-MM-DD"
    - max_articulos=2000 (200 páginas) para alcanzar datos históricos 2023 desde 2026.
      El early-stop basado en fecha ya maneja la parada eficiente: solo se detiene
      cuando los artículos son ANTERIORES a fecha_desde, no cuando son más recientes.
      ~200 páginas × 1s sleep = ~3-4 min adicionales por término — costo razonable.
    """

    BASE_URL = "https://www.corrillos.com.co"
    DOMINIO  = "corrillos.com.co"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.corrillos.com.co/",
    }

    MESES_ES = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }

    REGION = "nororiente"

    def __init__(
        self,
        termino: str,
        fecha_desde: str,
        fecha_hasta: str,
        max_articulos: int = 2000,  # 300 → 2000: necesario para alcanzar datos históricos 2023
    ):
        super().__init__(termino, fecha_desde, fecha_hasta)
        self.max_articulos = max_articulos
        self.session.headers.update(self.HEADERS)
        self._fechas_cache: Dict[str, Optional[str]] = {}

    # ── Contrato abstracto ──────────────────────────────────────────────────

    @property
    def nombre_periodico(self) -> str:
        return "Corrillos"

    def _construir_url_busqueda(self, pagina: int = 1) -> str:
        termino_encoded = requests.utils.quote(self.termino).replace("%20", "+")
        if pagina == 1:
            return f"{self.BASE_URL}/?s={termino_encoded}"
        return f"{self.BASE_URL}/page/{pagina}/?s={termino_encoded}"

    def _obtener_total_paginas(self, soup: BeautifulSoup) -> int:
        """
        Extrae el total de páginas desde el mayor número en <a class="page-numbers">.
        Limita según max_articulos (10 artículos por página).
        """
        try:
            numeros = []
            for a in soup.find_all("a", class_="page-numbers"):
                texto = a.get_text(strip=True)
                if texto.isdigit():
                    numeros.append(int(texto))

            total_paginas_sitio = max(numeros) if numeros else 1
            max_paginas_por_limite = math.ceil(self.max_articulos / 10)
            total_paginas = min(total_paginas_sitio, max_paginas_por_limite)

            print(f"  Total páginas en sitio: {total_paginas_sitio} | "
                  f"Límite: {self.max_articulos} arts → recorriendo {total_paginas} páginas")
            return total_paginas
        except Exception:
            return 1

    def _extraer_links_pagina(self, soup: BeautifulSoup) -> List[str]:
        """
        Extrae links SOLO desde <div class="col-lg-8 col-md-12"> (columna principal).
        Cachea fecha desde <span class="post-meta-date post_post_item_Date">.
        """
        links = []

        columna = soup.find("div", class_=lambda c: c and "col-lg-8" in c and "col-md-12" in c)
        if not columna:
            columna = soup

        articulos = columna.find_all("article")

        for articulo in articulos:
            h2 = articulo.find("h2", class_="post-title")
            if not h2:
                continue

            a = h2.find("a")
            if not a:
                continue

            href = a.get("href", "").strip()
            if not href or self.DOMINIO not in href:
                continue

            fecha = None
            span_fecha = articulo.find("span", class_="post-meta-date")
            if span_fecha:
                texto = span_fecha.get_text(strip=True)
                fecha = self._parsear_fecha_corrillos(texto)

            self._fechas_cache[href] = fecha
            links.append(href)

        return links

    # ── Parseo de fecha ────────────────────────────────────────────────────

    def _parsear_fecha_corrillos(self, texto: str) -> Optional[str]:
        """
        Parsea fechas en formato español: "agosto 13, 2024" o "agosto 13 de 2024".
        Retorna string "YYYY-MM-DD" o None si no puede parsear.
        """
        if not texto:
            return None

        texto = texto.lower().strip()

        # Limpiar " de " entre día y año
        texto = texto.replace(" de ", " ")

        # Quitar comas
        texto = texto.replace(",", "")

        partes = texto.split()
        if len(partes) < 3:
            return None

        try:
            mes_str = partes[0]
            dia     = int(partes[1])
            anio    = int(partes[2])
            mes     = self.MESES_ES.get(mes_str)

            if mes is None:
                return None

            return f"{anio:04d}-{mes:02d}-{dia:02d}"
        except (ValueError, IndexError):
            return None

    # ── Override de scrape() con retry + backoff ────────────────────────────

    def scrape(self) -> pd.DataFrame:
        print(f"WEBSCRAPING {self.nombre_periodico.upper()}")
        print(f"  Término: '{self.termino}' | Rango: {self.fecha_desde} → {self.fecha_hasta}")
        print(f"  Límite de artículos: {self.max_articulos}")

        # Retry primera página — SSL drops intermitentes
        soup_p1 = None
        for intento in range(3):
            try:
                url_p1 = self._construir_url_busqueda(pagina=1)
                r = self.session.get(url_p1, timeout=20)
                r.raise_for_status()
                soup_p1 = BeautifulSoup(r.text, "html.parser")
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

        total_paginas = self._obtener_total_paginas(soup_p1)
        links_en_rango = []
        errores_consecutivos = 0
        paginas_vacias_consecutivas = 0   # parada anticipada por fecha

        for pagina in range(1, total_paginas + 1):
            try:
                if pagina == 1:
                    soup = soup_p1
                else:
                    url = self._construir_url_busqueda(pagina=pagina)

                    respuesta = None
                    for intento in range(3):
                        try:
                            r = self.session.get(url, timeout=25)
                            r.raise_for_status()
                            respuesta = r
                            break
                        except Exception:
                            espera = 5 * (intento + 1)
                            print(f"  Intento {intento+1}/3 fallido en página {pagina} "
                                  f"— esperando {espera}s...")
                            time.sleep(espera)

                    if respuesta is None:
                        errores_consecutivos += 1
                        print(f"  Página {pagina} descartada tras 3 intentos.")
                        if errores_consecutivos >= 5:
                            print("  5 páginas consecutivas fallidas — deteniendo.")
                            break
                        continue

                    errores_consecutivos = 0
                    soup = BeautifulSoup(respuesta.text, "html.parser")

                links_pagina = self._extraer_links_pagina(soup)
                print(f"  Página {pagina}/{total_paginas}: {len(links_pagina)} artículos")

                n_antes = len(links_en_rango)
                hay_mas_recientes = False
                for link in links_pagina:
                    fecha = self._fechas_cache.get(link)
                    if fecha is None:
                        links_en_rango.append(link)
                        continue
                    if fecha > self.fecha_hasta:
                        hay_mas_recientes = True
                        continue
                    if self.fecha_desde <= fecha <= self.fecha_hasta:
                        links_en_rango.append(link)
                    elif fecha < self.fecha_desde:
                        pass  # artículo antiguo, no incluir

                # Parada anticipada: 3 páginas seguidas sin artículos en rango
                nuevos = len(links_en_rango) - n_antes
                if nuevos == 0 and links_pagina and not hay_mas_recientes:
                    paginas_vacias_consecutivas += 1
                    if paginas_vacias_consecutivas >= 3:
                        print(f"  3 páginas consecutivas sin artículos en rango — deteniendo.")
                        break
                else:
                    paginas_vacias_consecutivas = 0

                time.sleep(1.0)

            except Exception as e:
                print(f"  Error en página {pagina}: {e}")
                errores_consecutivos += 1
                if errores_consecutivos >= 5:
                    print("  5 páginas consecutivas fallidas — deteniendo.")
                    break
                continue

        links_en_rango = list(dict.fromkeys(links_en_rango))
        print(f"  Total links únicos en rango de fechas: {len(links_en_rango)}")

        if not links_en_rango:
            print("  No se encontraron artículos en el rango de fechas indicado.")
            return pd.DataFrame()

        return self._descargar_articulos(links_en_rango)

    # ── Descargas asíncronas ────────────────────────────────────────────────

    async def _descargar_articulo_async(
        self, session: aiohttp.ClientSession, info: tuple
    ) -> Optional[Dict]:
        i, link = info
        try:
            # timeout GRANULAR (no total=15): con TCPConnector(limit=10) y muchos
            # links en un solo asyncio.gather, un timeout total cuenta la espera en
            # cola por una conexion libre, no solo la descarga — con lotes grandes
            # esa cola supera 15s aunque el sitio responda en ~2-3s cada vez, dando
            # TimeoutError que en realidad son de cola, no de red lenta (medido
            # 2026-08-31 contra Corrillos: 68/132 fallos con timeout=15 total, 0/132
            # con este cambio en un lote de 800 — ver 08_log_decisiones.md).
            timeout_dl = aiohttp.ClientTimeout(total=None, sock_connect=20, sock_read=20)
            async with session.get(link, timeout=timeout_dl) as response:
                html = await response.text()

            from newspaper import Article
            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()  # sync — article.parse es CPU-bound (~1-10ms), no IO; evita RuntimeError con ProactorEventLoop en threads secundarios (Python 3.14)

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url": link,
                "titulo": article.title,
                # corregido: usar _fechas_cache en vez de _fechas
                "fecha": self._fechas_cache.get(link, article.publish_date),
                "texto": article.text,
            }
        except (asyncio.TimeoutError, TimeoutError):
            _registrar_error(self.nombre_periodico, "TimeoutError")
            return None
        except Exception as e:
            print(f"  ⚠ Error [{type(e).__name__}]: {e}")
            _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Norton MITM, ver 08_log_decisiones.md 2026-08-30
        async with aiohttp.ClientSession(connector=connector) as session:
            tareas = [
                self._descargar_articulo_async(session, info)
                for info in links_enumerados
            ]
            resultados = await asyncio.gather(*tareas)
        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        print(f"\nDescargando {len(links)} artículos (Optimizados con Asincronía)...")
        if not links:
            return pd.DataFrame()

        loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        nota_t = f" ({fallos} timeouts)" if fallos else ""
        print(f"{len(data)} artículos descargados exitosamente ({len(data)/len(links)*100:.1f}%){nota_t}")
        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fecha_desde_dt = pd.Timestamp(self.fecha_desde)
            fecha_hasta_dt = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = (df['fecha'].isna() | ((df['fecha'] >= fecha_desde_dt) & (df['fecha'] <= fecha_hasta_dt)))
            fuera_rango = (~mask).sum()
            if fuera_rango > 0:
                print(f"  Filtro fecha: {fuera_rango} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df


# ── GESTOR + FUNCIONES DE BÚSQUEDA ──────────────────────────────────────────

class GestorScraping:
    """Gestiona el webscraping de múltiples periódicos"""

    SCRAPERS = {
        # Eje Cafetero + Antioquia
        'eldiario': ScraperElDiario,
        'elcolombiano': ScraperElColombiano,
        'bcnoticias': ScraperBCNoticias,
        'elquindiano': ScraperElQuindiano,
        # Suroccidente (Pacífico)
        'elpais': ScraperElPaisCali,
        'diariooccidente': ScraperDiarioOccidente,
        'diariodelsur': ScraperDiarioDelSur,
        'diariodelcauca': ScraperDiarioDelCauca,
        'choco7dias': ScraperChoco7Dias,
        # Orinoquía / Amazonía
        'llanoalmundo': ScraperLlanoAlMundo,
        'diariodecasanare': ScraperDiarioDeCasanare,
        'lavozdelcinaruco': ScraperLaVozDelCinaruco,
        'elmorichal': ScraperElMorichal,
        'miputumayo': ScraperMiPutumayo,
        # Central (Bogotá)
        'eltiempo': ScraperElTiempo,
        'larepublica': ScraperLaRepublica,
        'portafolio': ScraperPortafolio,
        'publimetro': ScraperPublimetro,
        'las2orillas': ScraperLas2Orillas,
        # Caribe
        'elheraldo': ScraperElHeraldo,
        'eluniversal': ScraperElUniversal,
        'elpilon': ScraperElPilon,
        'elmeridiano': ScraperElMeridiano,
        # WordPress REST API
        'diariodelnorte': ScraperDiarioDelNorte,
        'laguajirahoy': ScraperLaGuajiraHoy,
        'boyaca7dias': ScraperBoyaca7Dias,
        # Nororiente
        'vanguardia': ScraperVanguardia,
        'tronchandosinfronteras': ScraperTrochandoSinFronteras,
        'enlacetelevision': ScraperEnlaceTelevision,
        'corrillos': ScraperCorrillos,
    }

    # Scrapers que usan Playwright (cada uno lanza un Chromium completo).
    # No paralelizar entre sí — en Windows se agota la memoria con 2+ instancias.
    # Las2Orillas usa requests+BS4 (sin Playwright) → no va aquí.
    SCRAPERS_PLAYWRIGHT: frozenset = frozenset({
        'larepublica', 'portafolio', 'publimetro',
        'elheraldo', 'elpilon', 'elmeridiano',
        'tronchandosinfronteras', 'enlacetelevision', 'corrillos',
    })

    # Scrapers con rate limiting estricto en el servidor.
    # Las2Orillas: concurrencia global controlada por _las2orillas_semaphore(2).
    SCRAPERS_RATE_LIMITED: frozenset = frozenset({'eltiempo', 'las2orillas'})

    # Máximo de workers para cada grupo en scrape_multiples()
    _MAX_WORKERS_FAST = 8
    _MAX_WORKERS_RATE_LIMITED = 1   # El Tiempo: 1 worker local + semáforo global(2)

    def __init__(self, termino: str, fecha_desde: str, fecha_hasta: str,
                 territorio: str = None):
        self.termino = termino
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta
        # Nombre del territorio (departamento/municipio) para el filtro de
        # relevancia. Si no se pasa explicito, se infiere de la primera
        # palabra de `termino` — correcto solo para territorios de una sola
        # palabra. Ver contexto/08_log_decisiones.md [2026-08-30]: con nombres
        # compuestos ("La Guajira", "Norte de Santander", "Valle del Cauca",
        # "San Andrés y Providencia") esa inferencia daba "la"/"norte"/"valle"/
        # "san" — palabras genéricas que no filtraban nada.
        self.territorio = (territorio if territorio is not None else termino.split()[0]).lower()

    @classmethod
    def periodicos_disponibles(cls) -> List[str]:
        return list(cls.SCRAPERS.keys())

    # ── FILTRO DE RELEVANCIA ──────────────────────────────────────────────────

    def _es_relevante(self, texto: str, titulo: str,
                      min_menciones: int = 3) -> bool:
        territorio = self.territorio
        texto_lower  = (texto  or "").lower()
        titulo_lower = (titulo or "").lower()
        menciones_texto = texto_lower.count(territorio)
        bonus_titulo    = 2 if territorio in titulo_lower else 0
        return (menciones_texto + bonus_titulo) >= min_menciones

    def _filtrar_relevancia(self, df: pd.DataFrame,
                             min_menciones: int = 3) -> pd.DataFrame:
        if df.empty:
            return df
        mascara = df.apply(
            lambda row: self._es_relevante(
                row.get('texto', ''),
                row.get('titulo', ''),
                min_menciones,
            ),
            axis=1
        )
        df_filtrado = df[mascara].reset_index(drop=True)
        descartados = len(df) - len(df_filtrado)
        print(f"   Filtro relevancia ({self.territorio}, "
              f"umbral={min_menciones}): "
              f"{len(df)} → {len(df_filtrado)} artículos "
              f"({descartados} descartados)")
        return df_filtrado

    # ─────────────────────────────────────────────────────────────────────────

    def scrape_multiples(self, periodicos: List[str],
                         callback=None,
                         min_menciones: int = 3) -> pd.DataFrame:
        """
        Ejecuta scrapers en dos fases:

        FASE 1 — Paralela (ThreadPoolExecutor):
          · Scrapers requests/aiohttp normales  → hasta _MAX_WORKERS_FAST workers
          · Scrapers con rate limiting (eltiempo) → hasta _MAX_WORKERS_RATE_LIMITED workers
          Los dos sub-grupos corren en paralelo entre sí pero con pools separados.

        FASE 2 — Secuencial:
          · Scrapers Playwright (scroll infinito, Chromium).
          No se paralelizan: cada instancia lanza un browser completo y en
          Windows se agota la memoria con 2+ instancias simultáneas.
        """
        # ── Validar y separar en grupos ───────────────────────────────────────
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

        print(f"\n  Estrategia de scraping para '{self.termino}':")
        if fast_ids:
            print(f"    Paralelos rápidos   ({self._MAX_WORKERS_FAST}w): {fast_ids}")
        if rate_limited_ids:
            print(f"    Paralelos limitados ({self._MAX_WORKERS_RATE_LIMITED}w): {rate_limited_ids}")
        if playwright_ids:
            print(f"    Playwright secuencial              : {playwright_ids}")

        dataframes: List[pd.DataFrame] = []

        # Periódicos nacionales: umbral de relevancia reducido a 1 porque la
        # búsqueda por término ya garantiza pertinencia temática y el artículo
        # no siempre repite el nombre del departamento en el cuerpo.
        _NACIONALES = frozenset({'eltiempo', 'las2orillas'})

        # Scrapers en servidores muy lentos que necesitan más tiempo que el
        # default de 300s. Confirmado por auditoría abril 2026: MiPutumayo
        # y LaVozDelCinaruco tienen tasas de éxito <20% con 300s.
        _LENTOS = frozenset({'miputumayo', 'lavozdelcinaruco'})

        def _run_one(periodico_id: str) -> tuple:
            scraper_class = self.SCRAPERS[periodico_id]
            # Semáforos globales para scrapers con rate limiting severo.
            if periodico_id == 'las2orillas':
                ctx = _las2orillas_semaphore
            elif periodico_id == 'eltiempo':
                ctx = _eltiempo_semaphore
            else:
                ctx = contextlib.nullcontext()

            # Periódicos nacionales usan umbral 1: el término de búsqueda ya
            # garantiza relevancia sin necesitar menciones adicionales del depto.
            _min_rel = 1 if periodico_id in _NACIONALES else min_menciones

            # Timeouts por categoría de scraper:
            #   480s → nacionales (El Tiempo, Las2Orillas): rate limiting
            #   600s → servidores lentos (MiPutumayo, LaVozDelCinaruco): ~14% éxito con 300s
            #   300s → resto
            _timeout = (480 if periodico_id in _NACIONALES
                        else 600 if periodico_id in _LENTOS
                        else 300)

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
                        print(f"  ℹ️  {periodico_id}: 0 artículos encontrados")
                    return periodico_id, df
                except concurrent.futures.TimeoutError:
                    mins = _timeout // 60
                    print(f"  ⏱️  {periodico_id}: timeout después de {mins} min — saltando")
                    _registrar_error(periodico_id, 'ScraperTimeout')
                    return periodico_id, pd.DataFrame()
                except Exception as e:
                    print(f"  ✗ Error en {periodico_id}: {e}")
                    _registrar_error(periodico_id, type(e).__name__)
                    return periodico_id, pd.DataFrame()

        def _collect(future_map: dict):
            """Recoge resultados de un pool a medida que terminan."""
            for future in as_completed(future_map):
                pid, df = future.result()
                if not df.empty:
                    dataframes.append(df)
                if callback:
                    callback(pid, df)

        # ── FASE 1A: scrapers rápidos en paralelo ─────────────────────────────
        if fast_ids:
            w = min(len(fast_ids), self._MAX_WORKERS_FAST)
            with ThreadPoolExecutor(max_workers=w, thread_name_prefix="scraper_fast") as pool:
                futures = {pool.submit(_run_one, pid): pid for pid in fast_ids}
                _collect(futures)

        # ── FASE 1B: scrapers con rate limiting en paralelo (pool propio) ─────
        if rate_limited_ids:
            w = min(len(rate_limited_ids), self._MAX_WORKERS_RATE_LIMITED)
            with ThreadPoolExecutor(max_workers=w, thread_name_prefix="scraper_rl") as pool:
                futures = {pool.submit(_run_one, pid): pid for pid in rate_limited_ids}
                _collect(futures)

        # ── FASE 2: scrapers Playwright — serializados globalmente ──────────────
        # _playwright_lock impide que dos Chromium corran al mismo tiempo aunque
        # este método sea llamado concurrentemente (ej: términos en paralelo).
        for pid in playwright_ids:
            with _playwright_lock:
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

    def _unificar_dataframes(self, dataframes: List[pd.DataFrame]) -> pd.DataFrame:
        df_final = pd.concat(dataframes, ignore_index=True)
        columnas_requeridas = ['periodico', 'titulo', 'fecha', 'texto', 'url']
        for col in columnas_requeridas:
            if col not in df_final.columns:
                df_final[col] = None
        df_final = df_final[columnas_requeridas]
        df_final['fecha'] = pd.to_datetime(df_final['fecha'], errors='coerce', utc=True)
        df_final['fecha'] = df_final['fecha'].dt.tz_localize(None)
        df_final = df_final.sort_values('fecha', ascending=False).reset_index(drop=True)
        return df_final

    def _mostrar_resumen(self, df: pd.DataFrame):
        print(f"\n{'='*50}")
        print(f"RESUMEN FINAL")
        print(f"{'='*50}")
        print(f"Total de artículos: {len(df)}")
        print(f"\nPor periódico:")
        print(df['periodico'].value_counts().to_string())
        if df['fecha'].notna().any():
            print(f"\nRango de fechas:")
            print(f"  Desde: {df['fecha'].min():%Y-%m-%d}")
            print(f"  Hasta: {df['fecha'].max():%Y-%m-%d}")
        print(f"{'='*50}\n")

    @classmethod
    def regiones_disponibles(cls) -> List[str]:
        regiones = set()
        for scraper_class in cls.SCRAPERS.values():
            region = getattr(scraper_class, "REGION", None)
            if region:
                regiones.add(region)
        return sorted(regiones)

    @classmethod
    def periodicos_por_region(cls, region: str) -> List[str]:
        return [
            clave
            for clave, scraper_class in cls.SCRAPERS.items()
            if getattr(scraper_class, "REGION", None) == region
        ]


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE BÚSQUEDA
# ══════════════════════════════════════════════════════════════════════════════

def scrape_periodicos(termino: str, fecha_desde: str, fecha_hasta: str,
                      periodicos: List[str] = None,
                      region: str = None,
                      min_menciones: int = 3,
                      territorio: str = None) -> pd.DataFrame:
    """Función base para webscraping con filtro de relevancia integrado.

    `territorio`: nombre completo del departamento/municipio para el filtro
    de relevancia (puede ser de varias palabras, ej. "La Guajira"). Si no se
    pasa, `GestorScraping` cae a la primera palabra de `termino` — correcto
    solo para territorios de una palabra.
    """
    gestor = GestorScraping(termino, fecha_desde, fecha_hasta, territorio=territorio)
    if periodicos is not None:
        lista_final = periodicos
    elif region is not None:
        lista_final = gestor.periodicos_por_region(region)
        if not lista_final:
            print(f"No se encontraron periódicos para la región '{region}'.")
            return pd.DataFrame(columns=['periodico', 'titulo', 'fecha', 'texto', 'url'])
        print(f"Región '{region}': {len(lista_final)} periódicos → {lista_final}")
    else:
        lista_final = gestor.periodicos_disponibles()
    return gestor.scrape_multiples(lista_final, min_menciones=min_menciones)


def _buscar_multi_termino(territorio: str, fecha_desde: str, fecha_hasta: str,
                          periodicos: List[str], min_menciones: int,
                          temas: List[str]) -> pd.DataFrame:
    """
    Función interna compartida por scrape_municipio y scrape_departamento.

    Los temas corren en paralelo (ThreadPoolExecutor).
    - Scrapers rápidos (requests/aiohttp): concurrencia total entre temas.
    - Scrapers Playwright: serializados vía _playwright_lock dentro de
      scrape_multiples, así nunca hay dos Chromium simultáneos aunque
      distintos temas los necesiten al mismo tiempo.

    El resultado final es idéntico al secuencial: DataFrame deduplicado
    por URL con columna 'terminos_encontrado'.
    """
    print(f"\n{'='*60}")
    print(f"BUSQUEDA MULTI-TERMINO: {territorio} | {fecha_desde} -> {fecha_hasta}")
    print(f"Terminos ({len(temas)} en paralelo): {[f'{territorio} {t}' for t in temas]}")
    print(f"{'='*60}")

    def _buscar_tema(tema: str) -> tuple:
        termino = f"{territorio} {tema}"
        print(f"\n-- Buscando: '{termino}' --")
        try:
            df_tema = scrape_periodicos(
                termino=termino,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                periodicos=periodicos,
                min_menciones=min_menciones,
                territorio=territorio,
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

    # Todos los temas en paralelo; el número de workers se adapta al largo de TEMAS_BUSQUEDA
    resultados_por_termino: Dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=len(temas), thread_name_prefix="tema") as pool:
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
    print(f"RESUMEN -- {territorio}")
    print(f"{'='*60}")
    # Resumen en el orden original de TEMAS_BUSQUEDA, no en el orden de llegada de futures
    for tema in temas:
        if tema in resultados_por_termino:
            print(f"  {territorio} {tema:<15}: {len(resultados_por_termino[tema]):>4}")
        else:
            print(f"  {territorio} {tema:<15}:    0")
    print(f"{'─'*40}")
    print(f"Total antes de deduplicar : {total_antes:>4}")
    print(f"Duplicados eliminados     : {total_antes - total_dedup:>4}")
    print(f"Articulos unicos finales  : {total_dedup:>4}")
    print(f"\nCobertura por termino:")
    cobertura = df_dedup['terminos_encontrado'].str.split(', ').explode().value_counts()
    for tema, n in cobertura.items():
        print(f"  {tema:<15}: {n}")
    if df_dedup['fecha'].notna().any():
        print(f"\nRango de fechas: {df_dedup['fecha'].min():%Y-%m-%d} -> "
              f"{df_dedup['fecha'].max():%Y-%m-%d}")
    print(f"{'='*60}\n")

    return df_dedup


# Periódicos centrales de respaldo cuando el corpus local es insuficiente
# Las2Orillas excluido del respaldo: rate-limita cada página individualmente
# y multiplica el tiempo cuando se usa como fallback para muchos departamentos.
_PERIODICOS_RESPALDO = ['eltiempo']

# Umbral mínimo de artículos antes de activar el respaldo
_MIN_ARTICULOS_RESPALDO = cfg.MIN_ARTICULOS_RESPALDO

# Lock global: garantiza que solo un scraper Playwright (Chromium) corra a la vez,
# incluso cuando múltiples términos se buscan en paralelo.
_playwright_lock = threading.Lock()

# Semáforo global para Las2Orillas: no usa Playwright pero es rate-limited.
# Máximo 1 instancia simultánea a nivel global (términos + departamentos).
_las2orillas_semaphore = threading.Semaphore(1)

# Semáforo global para El Tiempo: servidor lento que se satura con >2 queries
# simultáneas. Limita a 2 instancias concurrentes a nivel global.
_eltiempo_semaphore    = threading.Semaphore(2)

# ── REGISTRO DE ERRORES (reporte al final de scrape_multiples_departamentos) ──
_errores_run: list = []          # lista de dicts {periodico, tipo}
_errores_lock = threading.Lock()

def _registrar_error(periodico: str, tipo: str) -> None:
    """Registra un error de scraping para el reporte final de la corrida."""
    with _errores_lock:
        _errores_run.append({'periodico': periodico, 'tipo': tipo})


def scrape_municipio(municipio: str, fecha_desde: str, fecha_hasta: str,
                     periodicos: List[str] = None,
                     region: str = None,
                     min_menciones: int = 3) -> pd.DataFrame:
    """
    Busca artículos de un municipio usando 5 términos temáticos y
    deduplica por URL. Agrega columna 'terminos_encontrado'.
    """
    if periodicos is None and region is not None:
        gestor = GestorScraping.__new__(GestorScraping)
        periodicos = gestor.periodicos_por_region(region)

    df = _buscar_multi_termino(municipio, fecha_desde, fecha_hasta,
                                periodicos, min_menciones, TEMAS_BUSQUEDA)
    if not df.empty:
        df['municipio'] = municipio
    return df


# ── MAPEO DEPARTAMENTO → PERIÓDICOS ──────────────────────────────────────────

DEPARTAMENTO_PERIODICOS = {
    # ── Cobertura local directa ───────────────────────────────────────────────
    'Antioquia':              ['elcolombiano'],
    'Risaralda':              ['eldiario'],
    'Caldas':                 ['bcnoticias'],
    'Quindío':                ['elquindiano'],
    'Valle del Cauca':        ['elpais', 'diariooccidente'],
    'Nariño':                 ['diariodelsur'],
    'Cauca':                  ['diariodelcauca'],
    'Chocó':                  ['choco7dias'],
    'Meta':                   ['llanoalmundo'],
    'Casanare':               ['diariodecasanare'],
    'Arauca':                 ['lavozdelcinaruco', 'tronchandosinfronteras'],
    'Vichada':                [],             # elmorichal: sitio caído permanentemente (Cannot connect to host elmorichal.com:443) → respaldo directo
    'Putumayo':               [],          # miputumayo: 100% TimeoutError → respaldo directo
    'Cundinamarca':           ['eltiempo', 'larepublica', 'portafolio', 'publimetro'],
    'Atlántico':              [],          # ElHeraldo: cambió estructura del buscador (abril 2026) → respaldo directo
    'Bolívar':                [],          # ElUniversal: API Queryly retorna HTTP 403 (abril 2026) → respaldo directo
    'Cesar':                  ['elpilon'],
    'Córdoba':                ['elmeridiano'],
    'Santander':              ['enlacetelevision', 'corrillos', 'eltiempo'],
    # enlacetelevision/corrillos: buenos para contenido reciente pero no alcanzan 2023
    # con max_articulos=300 (los 300 slots se llenan con artículos de 2024-2026).
    # eltiempo añadido directamente para garantizar cobertura histórica 2023.
    # ── Cobertura compartida (mismo periódico que dept. vecino) ──────────────
    'Sucre':                  ['elmeridiano'],
    # ── Vecinos geográficos ───────────────────────────────────────────────────
    'Norte de Santander':     ['enlacetelevision', 'corrillos', 'eltiempo'],
    # misma razón que Santander ↑
    'Magdalena':              ['elpilon'],  # elheraldo roto; queda elpilon (Cesar vecino)
    'Boyacá':                 ['boyaca7dias', 'eltiempo'],  # vanguardia: API Queryly 403 (abril 2026)
    'Tolima':                 ['eltiempo', 'bcnoticias'],
    'Huila':                  ['diariodelcauca', 'diariodelsur'],
    'La Guajira':             ['diariodelnorte', 'laguajirahoy', 'elpilon'],  # elheraldo roto
    'Caquetá':                ['llanoalmundo'],  # miputumayo bloqueado
    'Guaviare':               ['llanoalmundo'],  # miputumayo bloqueado
    'Amazonas':               [],          # miputumayo bloqueado → respaldo directo
    'Guainía':                [],             # elmorichal: sitio caído permanentemente → respaldo directo
    # ── Sin cobertura local — centrales nacionales ────────────────────────────
    'Vaupés':                 ['eltiempo'],  # las2orillas: rate-limiting severo
    'San Andrés y Providencia': ['eltiempo'],  # las2orillas: rate-limiting severo
}





def scrape_departamento(departamento: str,
                        fecha_desde: str,
                        fecha_hasta: str,
                        periodicos: List[str] = None,
                        min_menciones: int = None,
                        min_articulos: int = _MIN_ARTICULOS_RESPALDO,
                        usar_respaldo: bool = True,
                        temas: List[str] = None) -> pd.DataFrame:
    """
    Busca artículos de un departamento usando los términos temáticos definidos
    en TEMAS_BUSQUEDA (o los que se pasen en `temas`) y deduplica por URL.
    Usa automáticamente los scrapers del departamento según DEPARTAMENTO_PERIODICOS.

    El umbral de menciones se determina automáticamente por departamento
    usando DEPARTAMENTO_MIN_MENCIONES (3 para departamentos grandes,
    2 para pequeños), pero puede sobreescribirse con min_menciones.

    Si el corpus resultante tiene menos de `min_articulos`, activa búsqueda
    de respaldo en El Tiempo y Las2Orillas (cobertura nacional).

    Args:
        departamento:  Nombre del departamento (ej: 'Antioquia')
        fecha_desde:   Fecha inicio (YYYY-MM-DD)
        fecha_hasta:   Fecha fin (YYYY-MM-DD)
        periodicos:    Lista de claves de scrapers. Si es None, usa los del
                       mapeo DEPARTAMENTO_PERIODICOS.
        min_menciones: Mínimo de menciones del departamento en el texto.
                       Si es None, usa el valor de DEPARTAMENTO_MIN_MENCIONES.
                       Default: None (automático).
        min_articulos: Umbral mínimo. Si el corpus queda por debajo,
                       se activa el respaldo. Default: 50.
        usar_respaldo: Activar búsqueda en periódicos centrales si el
                       corpus local es insuficiente. Default: True.
        temas:         Lista de palabras clave de búsqueda (ej: ["conflicto",
                       "social"]). Si es None, usa TEMAS_BUSQUEDA global.

    Returns:
        DataFrame deduplicado con columnas estándar + 'departamento' +
        'terminos_encontrado'.
    """
    # Usar temas locales o los globales configurados en TEMAS_BUSQUEDA
    _temas = temas if temas is not None else TEMAS_BUSQUEDA

    # Determinar umbral automáticamente si no se pasa explícitamente
    if min_menciones is None:
        min_menciones = DEPARTAMENTO_MIN_MENCIONES.get(departamento, 3)
        print(f"  Umbral de menciones para {departamento}: {min_menciones} (automático)")

    if periodicos is None:
        periodicos = DEPARTAMENTO_PERIODICOS.get(departamento)
        if not periodicos:   # None o lista vacía → sin scrapers locales
            print(f"  '{departamento}': sin scrapers locales activos → respaldo directo.")
            periodicos = []
        else:
            print(f"  Periódicos para {departamento}: {periodicos}")

    # Búsqueda principal en periódicos locales
    df = _buscar_multi_termino(departamento, fecha_desde, fecha_hasta,
                                periodicos, min_menciones, _temas)

    # Respaldo automático si el corpus es insuficiente
    if usar_respaldo and len(df) < min_articulos:
        # No repetir scrapers que ya se usaron
        respaldo_disponible = [
            p for p in _PERIODICOS_RESPALDO if p not in periodicos
        ]

        if respaldo_disponible:
            print(f"\n  Solo {len(df)} artículos para {departamento} "
                  f"(mínimo recomendado: {min_articulos})")
            print(f"  Activando búsqueda de respaldo en: {respaldo_disponible}")

            df_respaldo = _buscar_multi_termino(
                departamento, fecha_desde, fecha_hasta,
                respaldo_disponible, min_menciones, _temas
            )

            if not df_respaldo.empty:
                df = (
                    pd.concat([df, df_respaldo], ignore_index=True)
                    .drop_duplicates(subset=['url'])
                    .sort_values('fecha', ascending=False)
                    .reset_index(drop=True)
                )
                print(f"  ✓ Total con respaldo: {len(df)} artículos")
            else:
                print(f"  Sin resultados adicionales en periódicos de respaldo.")

    if not df.empty:
        df['departamento'] = departamento
    else:
        return pd.DataFrame(columns=[
            'periodico', 'titulo', 'fecha', 'texto', 'url',
            'departamento', 'terminos_encontrado'
        ])

    return df


def scrape_multiples_departamentos(departamentos: List[str],
                                   fecha_desde: str,
                                   fecha_hasta: str,
                                   min_menciones: int = 3,
                                   min_articulos: int = cfg.MIN_ARTICULOS_RESPALDO,
                                   usar_respaldo: bool = True,
                                   max_paralelos: int = 3,
                                   directorio_salida: str = cfg.RUTA_CORPUS_PKL,
                                   temas: List[str] = None) -> pd.DataFrame:
    """
    Corre scrape_departamento() para hasta max_paralelos departamentos en simultáneo.

    Comportamiento:
    - Scrapers rápidos (requests/aiohttp): concurrencia total dentro y entre deptos.
    - Scrapers Playwright: serializados por _playwright_lock — nunca más de un
      Chromium activo, sin importar cuántos departamentos corran en paralelo.
    - Cada departamento guarda su pkl tan pronto termina, sin esperar a los demás.
    - Si un departamento falla, el error se loguea y los demás continúan.

    Args:
        departamentos:      Lista de nombres de departamentos.
        fecha_desde:        Fecha inicio (YYYY-MM-DD).
        fecha_hasta:        Fecha fin (YYYY-MM-DD).
        min_menciones:      Umbral de relevancia. Default: 3.
        min_articulos:      Umbral mínimo para activar respaldo. Default: 50.
        usar_respaldo:      Búsqueda en periódicos centrales si hay pocos artículos.
        max_paralelos:      Máx. departamentos simultáneos. Default: 3.
        directorio_salida:  Carpeta donde guardar los pkl. Default: directorio actual.
        temas:              Lista de palabras clave de búsqueda. Si es None, usa
                            TEMAS_BUSQUEDA definido en la sección CONFIG.
    """
    # Reiniciar registro de errores para esta corrida
    global _errores_run
    _errores_run = []

    resultados: Dict[str, pd.DataFrame] = {}
    errores: List[str] = []
    status_dict: Dict[str, Dict] = {}
    _lock = threading.Lock()

    # ── Banner de inicio ──────────────────────────────────────────────────────
    simultaneos = min(max_paralelos, len(departamentos))
    print(f"\n{'▶'*3} CORRIENDO {len(departamentos)} DEPARTAMENTOS "
          f"({simultaneos} EN PARALELO) {'◀'*3}")
    print(f"    Periodo : {fecha_desde}  →  {fecha_hasta}")
    print(f"    Deptos  : {' | '.join(departamentos)}")
    print(f"{'─'*60}")
    _t_inicio_total = time.time()

    def _nombre_archivo(dep: str) -> str:
        """Convierte nombre de departamento a nombre de archivo seguro."""
        normalizado = unicodedata.normalize('NFD', dep.lower())
        sin_tildes = normalizado.encode('ascii', 'ignore').decode('ascii')
        return f"df_corpus_{sin_tildes.replace(' ', '_')}.pkl"

    def _procesar_dep(dep: str) -> None:
        t0 = time.time()
        print(f"\n{'━'*60}"
              f"\n▶ INICIO  [{dep}]"
              f"\n{'━'*60}")
        try:
            df_dep = scrape_departamento(
                departamento=dep,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                min_menciones=min_menciones,
                min_articulos=min_articulos,
                usar_respaldo=usar_respaldo,
                temas=temas,
            )
            mins = (time.time() - t0) / 60
            if not df_dep.empty:
                # Guardar pkl inmediatamente, sin esperar a los demás departamentos
                ruta = os.path.join(directorio_salida, _nombre_archivo(dep))
                df_dep.to_pickle(ruta)
                print(f"\n✓ FIN  [{dep}]  {mins:.1f} min  →  {len(df_dep)} artículos  →  {ruta}")
                with _lock:
                    resultados[dep] = df_dep
                    status_dict[dep] = {'articulos': len(df_dep), 'errores': None, 'archivo_generado': ruta}
            else:
                print(f"\n⚠ FIN  [{dep}]  {mins:.1f} min  →  sin artículos")
                with _lock:
                    status_dict[dep] = {'articulos': 0, 'errores': None, 'archivo_generado': None}
        except Exception as e:
            mins = (time.time() - t0) / 60
            msg = f"[{dep}] Error: {e}"
            print(f"\n✗ ERROR  [{dep}]  {mins:.1f} min  →  {e}")
            with _lock:
                errores.append(msg)
                status_dict[dep] = {'articulos': 0, 'errores': str(e), 'archivo_generado': None}

    with ThreadPoolExecutor(max_workers=max_paralelos,
                            thread_name_prefix="depto") as pool:
        futures = {pool.submit(_procesar_dep, dep): dep for dep in departamentos}
        for future in as_completed(futures):
            dep = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"  ✗ Excepción inesperada en {dep}: {e}")

    if errores:
        print(f"\n⚠  Departamentos con error ({len(errores)}):")
        for msg in errores:
            print(f"   {msg}")

    if not resultados:
        print("Sin artículos en ningún departamento.")
        return pd.DataFrame(), {}

    # Concatenar en el orden original de la lista
    df_final = pd.concat(
        [resultados[dep] for dep in departamentos if dep in resultados],
        ignore_index=True,
    )

    print(f"\n{'='*60}")
    print(f"RESUMEN TOTAL — {len(departamentos)} departamentos "
          f"({len(resultados)} con datos, {len(errores)} con error)")
    print(f"{'='*60}")
    print(f"Total artículos únicos: {len(df_final)}")
    print(f"\nPor departamento:")
    print(df_final['departamento'].value_counts().to_string())
    print(f"{'='*60}\n")

    # ── REPORTE DE ERRORES ────────────────────────────────────────────────────
    _imprimir_reporte_errores(len(departamentos))

    return df_final


def _imprimir_reporte_errores(n_departamentos: int) -> None:
    """Imprime un resumen consolidado de todos los errores de la corrida."""
    sep = '═' * 66
    print(f"\n{sep}")
    print(f"  REPORTE DE ERRORES — {n_departamentos} departamentos procesados")
    print(sep)

    if not _errores_run:
        print("  ✓ Sin errores registrados en esta corrida.")
        print(f"{sep}\n")
        return

    # Agrupar por (periodico, tipo) y contar
    conteos: dict = {}
    for ev in _errores_run:
        clave = (ev['periodico'], ev['tipo'])
        conteos[clave] = conteos.get(clave, 0) + 1

    # Ordenar: PrimeraPagina primero, luego por conteo desc, luego por nombre
    def _orden(item):
        (per, tipo), cnt = item
        prioridad = 0 if tipo == 'PrimeraPagina' else 1
        return (prioridad, -cnt, per)

    filas = sorted(conteos.items(), key=_orden)

    # Tabla
    col1, col2, col3 = 26, 30, 10
    print(f"  {'Periódico':<{col1}} {'Tipo de error':<{col2}} {'N':>{col3}}")
    print(f"  {'-'*col1} {'-'*col2} {'-'*col3}")

    periodicos_con_error = set()
    for (per, tipo), cnt in filas:
        periodicos_con_error.add(per)
        if tipo == 'PrimeraPagina':
            nota = '  ← primera página no cargó'
        elif cnt >= 200:
            nota = '  ← posible bloqueo total'
        elif cnt >= 50:
            nota = '  ← muchos fallos'
        else:
            nota = ''
        print(f"  {per:<{col1}} {tipo:<{col2}} {cnt:>{col3}}{nota}")

    total_errores = sum(conteos.values())
    print(f"\n  Total eventos de error : {total_errores}")
    print(f"  Periódicos afectados   : {len(periodicos_con_error)}")
    print(f"{sep}\n")


# ── UMBRAL DE MENCIONES RECOMENDADO POR DEPARTAMENTO ─────────────────────────
# Departamentos grandes con alto volumen periodístico: umbral 3
# Departamentos pequeños o con baja cobertura mediática: umbral 2

DEPARTAMENTO_MIN_MENCIONES = {
    # Umbral 3 — departamentos grandes / buena cobertura
    'Antioquia':                3,
    'Cundinamarca':             3,
    'Valle del Cauca':          3,
    'Atlántico':                3,
    'Bolívar':                  3,
    'Santander':                3,
    # Umbral 2 — departamentos pequeños / baja cobertura mediática
    'Risaralda':                2,
    'Caldas':                   2,
    'Quindío':                  2,
    'Nariño':                   2,
    'Cauca':                    2,
    'Chocó':                    2,
    'Meta':                     2,
    'Casanare':                 2,
    'Arauca':                   2,
    'Vichada':                  2,
    'Putumayo':                 2,
    'Cesar':                    2,
    'Córdoba':                  2,
    # Umbral 2 — cobertura compartida / vecinos geográficos / sin cobertura local
    'Sucre':                    2,
    'Norte de Santander':       2,
    'Magdalena':                2,
    'Boyacá':                   2,
    'Tolima':                   2,
    'Huila':                    2,
    'La Guajira':               2,
    'Caquetá':                  2,
    'Guaviare':                 2,
    'Amazonas':                 2,
    'Guainía':                  2,
    'Vaupés':                   2,
    'San Andrés y Providencia': 2,
}


def scrape_departamentos_status(config: dict) -> dict:
    """
    Función de alto nivel que recibe configuración y devuelve estado por departamento.

    Args:
        config: Diccionario con configuración. Claves opcionales:
            - fecha_desde: str, default FECHA_DESDE
            - fecha_hasta: str, default FECHA_HASTA
            - temas: list, default TEMAS_BUSQUEDA
            - departamentos: list, default todos los departamentos de GRUPOS_DEPARTAMENTOS
            - min_menciones: int, default 3
            - min_articulos: int, default MIN_ARTICULOS_RESPALDO
            - usar_respaldo: bool, default True
            - max_paralelos: int, default 3
            - directorio_salida: str, default RUTA_CORPUS_PKL

    Returns:
        dict: Estado por departamento con claves:
            - articulos: int, número de artículos
            - errores: str or None, mensaje de error si ocurrió
            - archivo_generado: str or None, ruta del archivo generado
    """
    # Extraer parámetros de config con defaults
    fecha_desde = config.get('fecha_desde', FECHA_DESDE)
    fecha_hasta = config.get('fecha_hasta', FECHA_HASTA)
    temas = config.get('temas', TEMAS_BUSQUEDA)
    departamentos = config.get('departamentos', [dep for grupo in GRUPOS_DEPARTAMENTOS for dep in grupo])
    min_menciones = config.get('min_menciones', 3)
    min_articulos = config.get('min_articulos', MIN_ARTICULOS_RESPALDO)
    usar_respaldo = config.get('usar_respaldo', True)
    max_paralelos = config.get('max_paralelos', 3)
    directorio_salida = config.get('directorio_salida', RUTA_CORPUS_PKL)

    # Llamar a la función de scraping y obtener el status
    _, status = scrape_multiples_departamentos(
        departamentos=departamentos,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        min_menciones=min_menciones,
        min_articulos=min_articulos,
        usar_respaldo=usar_respaldo,
        max_paralelos=max_paralelos,
        directorio_salida=directorio_salida,
        temas=temas
    )

    return status
