"""
scrappers_v4.py — curl_cffi.AsyncSession en lugar de aiohttp para descargas
══════════════════════════════════════════════════════════════════════════════

HIPÓTESIS
─────────────────────────────────────────────────────────────────────────────
Los TimeoutErrors masivos en LlanoAlMundo/LaVozDelCinaruco/ElQuindiano pueden
deberse a que el servidor detecta el TLS fingerprint de aiohttp/Python y limita
(o corta) la conexión antes de completar la respuesta.

curl_cffi.AsyncSession impersona Chrome 120 en el handshake TLS, presentando
el mismo ClientHello que un navegador real. Si el servidor filtra por TLS,
curl_cffi debería reducir los timeouts significativamente.

CAMBIO TÉCNICO
─────────────────────────────────────────────────────────────────────────────
_CurlDownloadMixin reemplaza los dos métodos de descarga de artículos:

  ANTES (aiohttp):
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(link, timeout=60) as response:
            html = await response.text()

  DESPUÉS (curl_cffi):
    semaphore = asyncio.Semaphore(5)      # mismo límite de concurrencia
    async with AsyncSession() as session:
        r = await session.get(link, timeout=60, impersonate="chrome120")
        html = r.text

NOTA WINDOWS: curl_cffi puede tener conflicto con ProactorEventLoop.
_CurlDownloadMixin._descargar_articulos() usa SelectorEventLoop en Windows.
"""

from scrappers import (
    ScraperElQuindiano, ScraperLlanoAlMundo, ScraperLaVozDelCinaruco,
    GestorScraping, _registrar_error,
    DEPARTAMENTO_PERIODICOS, DEPARTAMENTO_MIN_MENCIONES, TEMAS_BUSQUEDA,
)
import scrappers as _v1

from curl_cffi.requests import AsyncSession as CfAsyncSession
try:
    from curl_cffi import CurlError
except ImportError:
    CurlError = Exception   # fallback si la versión no lo exporta directamente

import asyncio, sys, time
import pandas as pd
from typing import List, Optional, Dict
from newspaper import Article


# ══════════════════════════════════════════════════════════════════════════════
# Mixin: reemplaza aiohttp por curl_cffi en la descarga de artículos
# ══════════════════════════════════════════════════════════════════════════════

class _CurlDownloadMixin:
    """
    Mixin que sobreescribe _descargar_articulo_async y _ejecutar_descargas_async
    para usar curl_cffi.AsyncSession con impersonación Chrome 120.

    Uso: class ScraperXV4(_CurlDownloadMixin, ScraperX): ...
    MRO: mixin primero → sus métodos tienen prioridad sobre ScraperX.
    """

    IMPERSONATE = "chrome120"   # perfil TLS
    CF_LIMIT    = 5             # concurrencia máxima (equivale a TCPConnector limit)

    async def _descargar_articulo_async(self, session: CfAsyncSession,
                                        info: tuple) -> Optional[Dict]:
        i, link = info
        try:
            r = await session.get(
                link,
                timeout   = 60,
                impersonate = self.IMPERSONATE,
            )
            html = r.text

            article = Article(link)
            article.html = html
            article.download_state = 2
            article.parse()   # CPU-bound, no IO

            if i % 50 == 0:
                print(f"  Descargados: {i} artículos")

            return {
                "periodico": self.nombre_periodico,
                "url":       link,
                "titulo":    article.title,
                "fecha":     (self._fechas.get(link, article.publish_date)
                              if hasattr(self, '_fechas') else article.publish_date),
                "texto":     article.text,
            }

        except Exception as e:
            # curl_cffi timeout: errno 28 (CURLE_OPERATION_TIMEDOUT) o mensaje "timed out"
            es_timeout = (
                isinstance(e, (asyncio.TimeoutError, TimeoutError))
                or "28" in str(e)
                or "timeout" in str(e).lower()
                or "timed out" in str(e).lower()
            )
            if es_timeout:
                _registrar_error(self.nombre_periodico, "TimeoutError")
            else:
                print(f"  ⚠ Error [{type(e).__name__}]: {e}")
                _registrar_error(self.nombre_periodico, type(e).__name__)
            return None

    async def _ejecutar_descargas_async(self, links: List[str]):
        links_enumerados = [(i, link) for i, link in enumerate(links, 1)]
        semaphore = asyncio.Semaphore(self.CF_LIMIT)

        async with CfAsyncSession(impersonate=self.IMPERSONATE) as session:
            async def _bounded(info):
                async with semaphore:
                    return await self._descargar_articulo_async(session, info)

            tareas   = [_bounded(info) for info in links_enumerados]
            resultados = await asyncio.gather(*tareas)

        return resultados

    def _descargar_articulos(self, links: List[str]) -> pd.DataFrame:
        """Override: usa SelectorEventLoop en Windows (curl_cffi incompatible con ProactorEventLoop)."""
        print(f"\nDescargando {len(links)} artículos [curl_cffi chrome120]...")
        if not links:
            return pd.DataFrame()

        # curl_cffi necesita SelectorEventLoop en Windows (ProactorEventLoop da
        # "loop is closed" o RuntimeError con los streams de libcurl)
        if sys.platform == 'win32':
            loop = asyncio.SelectorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            resultados = loop.run_until_complete(self._ejecutar_descargas_async(links))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        data   = [r for r in resultados if r is not None]
        fallos = len(links) - len(data)
        tasa   = len(data) / len(links) * 100
        nota_t = f" ({fallos} timeouts/errores)" if fallos else ""
        print(f"{len(data)} artículos descargados ({tasa:.1f}%){nota_t}")

        df = pd.DataFrame(data)
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce', utc=True).dt.tz_convert(None)
            fd = pd.Timestamp(self.fecha_desde)
            fh = pd.Timestamp(self.fecha_hasta) + pd.Timedelta(hours=23, minutes=59, seconds=59)
            mask = df['fecha'].isna() | ((df['fecha'] >= fd) & (df['fecha'] <= fh))
            fuera = (~mask).sum()
            if fuera > 0:
                print(f"  Filtro fecha: {fuera} artículos fuera de rango eliminados")
                df = df[mask].reset_index(drop=True)
        return df


# ══════════════════════════════════════════════════════════════════════════════
# V4 scrapers: mixin primero en MRO → métodos de descarga son de curl_cffi
# ══════════════════════════════════════════════════════════════════════════════

class ScraperElQuindianoV4(_CurlDownloadMixin, ScraperElQuindiano):
    """ElQuindiano con curl_cffi para descargas (timeout=60, concurrencia=10)."""
    CF_LIMIT = 10   # igual que TCPConnector(limit=10) original

    @property
    def nombre_periodico(self) -> str:
        return "El Quindiano"


class ScraperLlanoAlMundoV4(_CurlDownloadMixin, ScraperLlanoAlMundo):
    """LlanoAlMundo con curl_cffi para descargas (timeout=60, concurrencia=5)."""
    CF_LIMIT = 5    # igual que TCPConnector(limit=5) original

    @property
    def nombre_periodico(self) -> str:
        return "Llano al Mundo"


class ScraperLaVozDelCinarucoV4(_CurlDownloadMixin, ScraperLaVozDelCinaruco):
    """LaVozDelCinaruco con curl_cffi para descargas (timeout=60, concurrencia=5)."""
    CF_LIMIT = 5

    @property
    def nombre_periodico(self) -> str:
        return "La Voz del Cinaruco"


# ══════════════════════════════════════════════════════════════════════════════
# GestorScrapingV4 — swapea los tres scrapers mejorados
# ══════════════════════════════════════════════════════════════════════════════

class GestorScrapingV4(GestorScraping):
    SCRAPERS = {
        **GestorScraping.SCRAPERS,
        'elquindiano':      ScraperElQuindianoV4,
        'llanoalmundo':     ScraperLlanoAlMundoV4,
        'lavozdelcinaruco': ScraperLaVozDelCinarucoV4,
    }
