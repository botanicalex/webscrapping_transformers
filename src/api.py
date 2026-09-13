"""
API FastAPI que conecta el front HTML con el pipeline de Santiago (src/).

NO modifica la logica existente. Reutiliza, tal cual:
  - scrappers.scrape_municipio               (scraping en vivo)
  - Transformer_optimo.PipelineTransformers  (NLI 26 hipotesis V2)
  - radar.CalculadorRadar                    (bloques A-E, columnas binarias)
  - config_pipeline                          (cortes fijos Bajo/Medio/Alto)

Esta capa SOLO orquesta y le da al resultado la forma de JSON que espera el
front. Los cortes se leen de config_pipeline.py (fuente unica de esta rama:
Bajo < CORTE_BAJO_MEDIO_RADAR <= Medio < CORTE_MEDIO_ALTO_RADAR <= Alto), no se
hardcodean aqui.

Endpoints:
  POST /analizar        territorio + fechas -> radar completo (scrapea + NLI)
  GET  /lugares?q=...   autocompletado de municipios/departamentos via DIVIPOLA
  GET  /health          estado y cortes activos

Correr desde la raiz del proyecto:
    uvicorn src.api:app --host 0.0.0.0 --port 8000
o directamente:
    python src/api.py

ADVERTENCIA: /analizar scrapea en vivo y corre mDeBERTa. Una request puede
tardar varios minutos (el front tiene pantalla de loading). El modelo NLI se
carga UNA sola vez (perezoso, al primer request) y se reutiliza.
"""
import concurrent.futures
import json
import multiprocessing as mp
import os
import random
import sys
import unicodedata
from difflib import get_close_matches
from typing import List, Optional

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

# ── Rutas: src/ al path para que los imports por nombre de Santiago funcionen ─
DIR_SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR_SRC)

import config_pipeline as cfg          # noqa: E402
from radar import CalculadorRadar       # noqa: E402
from municipios_colombia import MUNICIPIOS_POR_DEPTO  # noqa: E402
import scrape_worker                    # noqa: E402  (scraping en subproceso; NO importa scrappers al cargar)

# El scraping corre en un subproceso 'spawn' (interprete fresco): asi el patron
# de event-loop de scrappers.py no desarma el loop de uvicorn, y ademas 'spawn'
# (no 'fork') evita heredar la sesion CUDA del modelo NLI ya cargado.
_MP_CTX = mp.get_context("spawn")

# ── Parametros de presentacion (ajustables, NO tocan el pipeline) ────────────
# Un articulo "apoya" un indicador si su score por articulo supera esto. Sirve
# solo para contar `arts` y para poblar la lista `articulos`; el `score` del
# indicador siempre es el MAX (agregacion de esta rama), sin este umbral.
UMBRAL_ARTICULO = 0.10
# Maximo de articulos por indicador que se devuelven al front.
MAX_ARTICULOS_POR_INDICADOR = 20

# ── Metadatos de los 5 bloques (nombre + color para el front) ────────────────
BLOQUES_META = {
    "A": {"nombre": "Derechos e Institucionalidad Formal", "color": "#3B82F6"},
    "B": {"nombre": "Violencia y Actores Armados",         "color": "#EF4444"},
    "C": {"nombre": "Debilidad Institucional / Economica", "color": "#F59E0B"},
    "D": {"nombre": "Afectacion Territorial y Poblacional","color": "#8B5CF6"},
    "E": {"nombre": "Participacion y Movilizacion Social",  "color": "#10B981"},
}
# CalculadorRadar.BLOQUES_PCA usa claves 'bloque_A'..'bloque_E'; mapeamos A..E.
BLOQUES_INDICADORES = {
    letra: CalculadorRadar.BLOQUES_PCA[f"bloque_{letra}"] for letra in "ABCDE"
}

# ── Colores/etiquetas del badge global por categoria ─────────────────────────
BADGE = {
    "Bajo":  {"label": "Riesgo bajo",  "color": "#10B981"},
    "Medio": {"label": "Riesgo medio", "color": "#F59E0B"},
    "Alto":  {"label": "Riesgo alto",  "color": "#EF4444"},
}

# ── Territorio -> periodicos ─────────────────────────────────────────────────
# Claves normalizadas (minusculas, sin tildes). Incluye los 4 lugares
# sub-departamentales conocidos y los 32 departamentos.
MAPA_TERRITORIO_PERIODICOS = {
    "paraguachon":        ["laguajirahoy", "eltiempo"],
    "maicao":             ["laguajirahoy", "eltiempo"],
    "guintiva":           ["boyaca7dias", "eltiempo"],
    "oicata":             ["boyaca7dias", "eltiempo"],
    "antioquia":          ["elcolombiano", "eltiempo"],
    "atlantico":          ["elheraldo", "eltiempo"],
    "bolivar":            ["eluniversal", "eltiempo"],
    "boyaca":             ["eldiarioboyaca", "ultimahoraboy", "eltiempo"],
    "caldas":             ["bcnoticias", "eltiempo"],
    "caqueta":            ["eltiempo"],
    "cauca":              ["diariodelcauca", "eltiempo"],
    "cesar":              ["cesarnoticias", "elpaisvallenato", "elpilon", "eltiempo"],
    "choco":              ["eltiempo"],
    "cordoba":            ["chicanoticias", "rionoticias", "eltiempo"],
    "cundinamarca":       ["eltiempo"],
    "guaviare":           ["marandua", "eltiempo"],
    "huila":              ["eltiempo"],
    "la guajira":         ["laguajirahoy", "eltiempo"],
    "magdalena":          ["santamartaaldia", "elheraldo", "eltiempo"],
    "meta":               ["llanoalmundo", "periodicodelmeta", "viveelmeta", "eltiempo"],
    "narino":             ["diariodelsur", "eltiempo"],
    "norte de santander": ["eltiempo"],
    "putumayo":           ["miputumayo", "eltiempo"],
    "quindio":            ["elquindiano", "quindionoticias", "eltiempo"],
    "risaralda":          ["elexpreso", "ciudadregion", "eltiempo"],
    "san andres":         ["archipielagopress", "eltiempo"],
    "santander":          ["corrillos", "eltiempo"],
    "sucre":              ["chicanoticias", "rionoticias", "eltiempo"],
    "tolima":             ["eltiempo"],
    "valle del cauca":    ["diariooccidente", "eltiempo"],
    "vaupes":             ["eltiempo"],
    "vichada":            ["elmorichal", "eltiempo"],
}
PERIODICOS_DEFECTO = ["eltiempo"]

# Solo las claves que son departamentos (para el emparejamiento por
# contenido cuando DIVIPOLA devuelve un nombre largo, p. ej. San Andres).
_DEPARTAMENTOS_MAPA = {
    k for k in MAPA_TERRITORIO_PERIODICOS
    if k not in {"paraguachon", "maicao", "guintiva", "oicata"}
}

# ── DIVIPOLA (DANE) — solo departamentos y municipios (no veredas) ───────────
DIVIPOLA_URL = "https://www.datos.gov.co/resource/gdxc-w37w.json"
DIVIPOLA_TIMEOUT = 15.0


def _slug(txt: str) -> str:
    t = unicodedata.normalize("NFD", str(txt).lower()).encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() else "_" for c in t).strip("_")


def _norm(txt: str) -> str:
    """Minusculas, sin tildes, espacios colapsados. Para casar contra el mapa."""
    t = unicodedata.normalize("NFD", str(txt).lower()).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.split()).strip()


def _municipios_del_departamento(nombre_depto: str) -> List[str]:
    """Lista de municipios (nombres presentables) del departamento, o [] si no
    coincide ninguna clave de MUNICIPIOS_POR_DEPTO (comparacion normalizada)."""
    objetivo = _norm(nombre_depto)
    for clave, municipios in MUNICIPIOS_POR_DEPTO.items():
        if _norm(clave) == objetivo:
            return municipios
    return []


def _titulo(txt: str) -> str:
    """DIVIPOLA devuelve en mayusculas; se presenta en Title Case."""
    return str(txt).strip().title()


def _termino_busqueda(territorio: str) -> str:
    """Quita el prefijo 'Municipio '/'Vereda ' — el filtro de scrappers usa
    solo la primera palabra del termino (ver scrape_lugares.py)."""
    t = territorio.strip()
    for prefijo in ("municipio ", "vereda "):
        if t.lower().startswith(prefijo):
            return t[len(prefijo):].strip()
    return t


def _categoria(valor: float) -> str:
    """Cortes fijos de ESTA rama, leidos de config_pipeline (no hardcodeados)."""
    if valor < cfg.CORTE_BAJO_MEDIO_RADAR:
        return "Bajo"
    if valor < cfg.CORTE_MEDIO_ALTO_RADAR:
        return "Medio"
    return "Alto"


def _nombre_bonito(col: str) -> str:
    return col.replace("_", " ").title()


# ── DIVIPOLA helpers ─────────────────────────────────────────────────────────
def _divipola_departamento(municipio: str) -> Optional[str]:
    """Departamento (crudo, mayusculas) al que pertenece un municipio, o None."""
    nombre = municipio.replace("'", "''")  # escape SoQL
    params = {
        "$select": "dpto",
        "$where": f"upper(nom_mpio) = upper('{nombre}')",
        "$limit": 1,
    }
    try:
        with httpx.Client(timeout=DIVIPOLA_TIMEOUT) as cliente:
            r = cliente.get(DIVIPOLA_URL, params=params)
            r.raise_for_status()
            filas = r.json()
    except Exception:
        return None
    if filas and filas[0].get("dpto"):
        return filas[0]["dpto"]
    return None


def _periodicos_de_departamento(dpto: str) -> List[str]:
    """Periodicos del departamento segun el mapa. Exacto, luego por contenido
    (nombres largos de DIVIPOLA, p. ej. 'Archipielago de San Andres...')."""
    clave = _norm(dpto)
    if clave in MAPA_TERRITORIO_PERIODICOS:
        return MAPA_TERRITORIO_PERIODICOS[clave]
    for k in _DEPARTAMENTOS_MAPA:
        if len(k) >= 7 and k in clave:
            return MAPA_TERRITORIO_PERIODICOS[k]
    return PERIODICOS_DEFECTO


def _resolver_periodicos(territorio: str, termino: str) -> List[str]:
    """Jerarquia pedida:
    a) territorio/termino en el mapa -> esos periodicos
    b) si no, DIVIPOLA -> departamento del municipio -> periodicos del depto
    c) si tampoco -> ['eltiempo']
    """
    for clave in (_norm(termino), _norm(territorio)):
        if clave in MAPA_TERRITORIO_PERIODICOS:
            return MAPA_TERRITORIO_PERIODICOS[clave]

    dpto = _divipola_departamento(termino)
    if dpto:
        return _periodicos_de_departamento(dpto)

    return PERIODICOS_DEFECTO


# ── Esquemas ─────────────────────────────────────────────────────────────────
class SolicitudAnalisis(BaseModel):
    territorio: str
    fecha_inicio: str
    fecha_fin: str
    # opcional: si el front ya sabe los periodicos, los fuerza y saltea el mapa.
    periodicos: Optional[List[str]] = None
    # opcional: departamento indicado por el usuario (dropdown del front) para
    # resolver los periodicos sin llamar a DIVIPOLA (util en texto libre/veredas).
    departamento_hint: Optional[str] = None
    # opcional: si True, saltea la validacion de municipio (boton "No, buscar igual").
    forzar_lugar: Optional[bool] = False


app = FastAPI(title="Radar de Riesgo Territorial — API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Garantiza CORS incluso en un 500 no controlado. Un error que escapa a los
    try/except sube a ServerErrorMiddleware (por fuera de CORSMiddleware) y llega
    al navegador SIN 'Access-Control-Allow-Origin', que aparece enmascarado como
    error CORS. Este handler corre dentro de ExceptionMiddleware, asi que la
    respuesta lleva el header explicito y el front ve el detalle real."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "*"},
    )

# ── Modelo NLI cargado al arrancar (no perezoso) ─────────────────────────────
# Se instancia al importar el modulo (hilo principal de uvicorn), no dentro del
# primer request. Cargar torch/CUDA en el thread del worker provocaba un 500 en
# /analizar aunque el pipeline funcionara al llamarlo directo en Python.
from Transformer_optimo import PipelineTransformers  # noqa: E402
_PIPELINE = PipelineTransformers()  # carga el modelo al arrancar la app


def _get_pipeline():
    return _PIPELINE


def _scrape_en_subproceso(termino, fecha_desde, fecha_hasta, periodicos):
    """Ejecuta scrape_worker.scrape en un proceso aparte ('spawn') y devuelve el
    DataFrame. Aisla el manejo de event loop de scrappers del loop de uvicorn.
    Corre dentro del generador SSE (que ya vive en un thread), asi que bloquear
    aca no afecta al event loop del server."""
    with concurrent.futures.ProcessPoolExecutor(max_workers=1, mp_context=_MP_CTX) as ex:
        fut = ex.submit(scrape_worker.scrape, termino, fecha_desde, fecha_hasta, periodicos)
        return fut.result()


@app.get("/health")
def health():
    return {
        "ok": True,
        "cortes": {
            "bajo_medio": cfg.CORTE_BAJO_MEDIO_RADAR,
            "medio_alto": cfg.CORTE_MEDIO_ALTO_RADAR,
        },
        "modelo_cargado": _PIPELINE is not None,
    }


@app.options("/analizar")
async def analizar_options(request: Request):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, ngrok-skip-browser-warning",
        },
    )


@app.options("/lugares")
async def lugares_options(request: Request):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, ngrok-skip-browser-warning",
        },
    )


# Cache en memoria de los municipios de DIVIPOLA (lista chica y estable). El LIKE
# de SoQL es sensible a tildes y nom_mpio las trae ("MEDELLÍN"); por eso se filtra
# en Python con _norm (sin tildes) en vez de en la query.
_MUNICIPIOS_CACHE = None


def _municipios_divipola():
    global _MUNICIPIOS_CACHE
    if _MUNICIPIOS_CACHE is None:
        with httpx.Client(timeout=DIVIPOLA_TIMEOUT) as cliente:
            r = cliente.get(DIVIPOLA_URL, params={
                "$select": "nom_mpio,dpto,tipo_municipio",
                "$limit": 1200,
            })
            r.raise_for_status()
            _MUNICIPIOS_CACHE = r.json()
    return _MUNICIPIOS_CACHE


@app.get("/lugares")
def lugares(q: str = Query(..., min_length=2, description="Texto a autocompletar")):
    """Autocompletado de municipios y departamentos via DIVIPOLA (DANE).
    DIVIPOLA guarda 'MEDELLÍN' con tilde y el LIKE de SoQL es sensible a acentos,
    asi que se filtra en Python con _norm (sin tildes). gdxc-w37w no incluye veredas."""
    try:
        todos = _municipios_divipola()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fallo DIVIPOLA: {e}")

    q_norm = _norm(q)
    filas = [f for f in todos if q_norm in _norm(f.get("nom_mpio", ""))]
    filas.sort(key=lambda f: str(f.get("nom_mpio", "")))
    filas = filas[:10]

    sugerencias, vistos = [], set()

    for fila in filas:
        mpio = fila.get("nom_mpio")
        dpto = fila.get("dpto")
        if not mpio or not dpto:
            continue
        # Municipio
        clave_m = ("mpio", _norm(mpio), _norm(dpto))
        if clave_m not in vistos:
            vistos.add(clave_m)
            sugerencias.append({
                "nombre": _titulo(mpio),
                "tipo": fila.get("tipo_municipio") or "Municipio",
                "departamento": _titulo(dpto),
            })
        # Departamento (solo si el texto casa con su nombre)
        if q_norm in _norm(dpto):
            clave_d = ("dpto", _norm(dpto))
            if clave_d not in vistos:
                vistos.add(clave_d)
                sugerencias.append({
                    "nombre": _titulo(dpto),
                    "tipo": "Departamento",
                    "departamento": _titulo(dpto),
                })

    # Departamentos primero cuando el match es directo, luego municipios.
    sugerencias.sort(key=lambda s: (s["tipo"] != "Departamento", s["nombre"]))
    return sugerencias


# Umbrales de las validaciones NLI y tope de la muestra.
UMBRAL_VALIDACION = 0.15          # tematica social (etapa 4)
UMBRAL_TERRITORIAL = 0.20         # relevancia territorial (etapa 3)
FRACCION_MIN_TERRITORIAL = 0.30   # etapa 3: al menos 30% de la muestra debe pasar
MAX_MUESTRA_VALIDACION = 20


@app.get("/analizar")
def analizar(
    territorio: str = Query(..., description="Lugar a analizar"),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    departamento_hint: Optional[str] = Query(None),
    forzar_lugar: bool = Query(False),
):
    """Analiza un territorio emitiendo el progreso por SSE (text/event-stream).
    Es GET (no POST) con los parametros en la query string para que el front
    pueda usar EventSource, que solo soporta GET y streamea mejor a traves de
    proxies como ngrok. Cada evento es una linea `data: {...}`. Las etapas 3 y 4
    validan con NLI sobre una muestra <=20; la etapa 8 trae el resultado final."""
    sol = SolicitudAnalisis(
        territorio=territorio,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        departamento_hint=departamento_hint,
        forzar_lugar=forzar_lugar,
    )

    def _sse(obj: dict) -> str:
        return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

    def eventos():
        termino = _termino_busqueda(sol.territorio)
        if sol.periodicos:
            periodicos = sol.periodicos
        elif sol.departamento_hint:
            periodicos = _periodicos_de_departamento(sol.departamento_hint)
        else:
            periodicos = _resolver_periodicos(sol.territorio, termino)

        # Validacion de lugar especifico contra los municipios del departamento
        # (DANE/DIVIPOLA). Solo aplica si hay lugar distinto del depto y no se
        # forzo la busqueda ("No, buscar igual").
        hint = sol.departamento_hint or ""
        es_lugar_especifico = bool(sol.territorio) and _norm(sol.territorio) != _norm(hint)
        piso_vereda = False   # True => se asume vereda: se exige un minimo de articulos
        if es_lugar_especifico and hint and not sol.forzar_lugar:
            municipios = _municipios_del_departamento(hint)
            norm_a_nombre = {_norm(m): m for m in municipios}
            objetivo = _norm(termino)
            if objetivo not in norm_a_nombre:   # no es un municipio exacto
                cercanos = get_close_matches(objetivo, list(norm_a_nombre.keys()), n=3, cutoff=0.6)
                if cercanos:
                    yield _sse({"sugerencia": [norm_a_nombre[c] for c in cercanos],
                                "msg": "¿Quisiste decir alguno de estos?"})
                    return
                # Sin municipio exacto ni sugerencias -> se asume vereda/corregimiento.
                piso_vereda = True

        # Etapa 1: scraping en vivo (en un subproceso aparte, ver
        # _scrape_en_subproceso: scrappers.py maneja su propio event loop y
        # apagaria el de uvicorn si corriera aca).
        yield _sse({"etapa": 1, "msg": "Conectando con los periódicos..."})
        try:
            df = _scrape_en_subproceso(termino, sol.fecha_inicio, sol.fecha_fin, periodicos)
        except Exception as e:
            yield _sse({"error": f"Fallo el scraping: {e}"})
            return

        n_art = 0 if (df is None or df.empty) else len(df)
        # Piso de veredas: si asumimos vereda y hay < 5 articulos, no hay cobertura.
        if piso_vereda and n_art < 5:
            yield _sse({"error": f"No se encontró cobertura de prensa para '{sol.territorio}' en {hint or sol.territorio}. Verifica el nombre o prueba con el departamento."})
            return
        if df is None or df.empty:
            yield _sse({"error": "No se encontraron noticias del territorio seleccionado en el período indicado"})
            return

        # El pipeline agrupa por 'departamento'; aqui es el territorio pedido.
        df = df.copy()
        df["departamento"] = sol.territorio
        for c in ["periodico", "titulo", "fecha", "texto", "url"]:
            if c not in df.columns:
                df[c] = None

        # Etapa 2: cantidad descargada
        yield _sse({"etapa": 2, "msg": "Descargando artículos...", "n": int(len(df))})

        pipe = _get_pipeline()
        textos = [t for t in df["texto"].fillna("").astype(str).tolist() if t.strip()]
        # Muestra <=20 (aleatoria) para que las validaciones sean rapidas.
        muestra = random.sample(textos, min(MAX_MUESTRA_VALIDACION, len(textos))) if textos else []

        # Etapa 3: relevancia territorial (NLI). La hipotesis usa el LUGAR
        # especifico cuando lo hay (distinto del depto); si no, el departamento.
        # Gate: al menos FRACCION_MIN_TERRITORIAL de la muestra sobre el umbral.
        yield _sse({"etapa": 3, "msg": "Validando relevancia territorial..."})
        hint = sol.departamento_hint or ""
        if sol.territorio and _norm(sol.territorio) != _norm(hint):
            lugar_ref = sol.territorio
        else:
            lugar_ref = hint or sol.territorio
        hip_terr = f"Este artículo habla sobre {lugar_ref}"
        ent_terr = pipe._nli_batch(muestra, hip_terr) if muestra else []
        n_terr = len(ent_terr)
        n_pasan = sum(1 for e in ent_terr if e >= UMBRAL_TERRITORIAL)
        avg_terr = (sum(ent_terr) / n_terr) if n_terr else 0.0
        _dbg = (f"Validación territorial: score promedio {avg_terr:.2f}, "
                f"pasaron {n_pasan}/{n_terr} artículos (umbral {int(FRACCION_MIN_TERRITORIAL * 100)}%)")
        print(f"[/analizar] {_dbg}")          # visible en los logs de Colab (api.log)
        yield _sse({"debug": _dbg})
        if n_terr == 0 or (n_pasan / n_terr) < FRACCION_MIN_TERRITORIAL:
            yield _sse({"error": "No se encontraron noticias del territorio seleccionado en el período indicado"})
            return

        # Etapa 4: tematica social (NLI, umbral UMBRAL_VALIDACION)
        yield _sse({"etapa": 4, "msg": "Validando temática social..."})
        hip_tema = "Este artículo trata temas sociales, conflicto, comunidades o derechos"
        ent_tema = pipe._nli_batch(muestra, hip_tema) if muestra else []
        if not any(e >= UMBRAL_VALIDACION for e in ent_tema):
            yield _sse({"error": "Las noticias encontradas no son de temática social o de conflicto"})
            return

        # Etapa 5: NLI completo (26 hipotesis V2)
        yield _sse({"etapa": 5, "msg": "Ejecutando análisis NLP..."})
        try:
            df_proc = pipe.procesar(df)
        except Exception as e:
            yield _sse({"error": f"Fallo el pipeline NLI: {e}"})
            return

        # Etapa 6/7: indicadores + armado de la respuesta
        yield _sse({"etapa": 6, "msg": "Calculando indicadores de riesgo..."})
        yield _sse({"etapa": 7, "msg": "Generando resultados..."})
        try:
            resultado = _construir_respuesta(sol, df_proc)
        except Exception as e:
            yield _sse({"error": f"Fallo al generar el resultado: {e}"})
            return

        # Etapa 8: resultado final
        yield _sse({"etapa": 8, "resultado": resultado})

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _respuesta_vacia(sol: SolicitudAnalisis) -> dict:
    bloques = [
        {
            "id": letra,
            "nombre": BLOQUES_META[letra]["nombre"],
            "color": BLOQUES_META[letra]["color"],
            "score": 0,
            "indicadores": [
                {"nombre": _nombre_bonito(col), "col": col, "score": 0.0, "arts": 0, "real": False}
                for col in BLOQUES_INDICADORES[letra]
            ],
        }
        for letra in "ABCDE"
    ]
    return {
        "lugar": sol.territorio,
        "fecha_inicio": sol.fecha_inicio,
        "fecha_fin": sol.fecha_fin,
        "n_articulos": 0,
        "fuentes": [],
        "badge_score": 0,
        "badge_label": BADGE["Bajo"]["label"],
        "badge_color": BADGE["Bajo"]["color"],
        "bloques": bloques,
        "articulos": {},
    }


def _construir_respuesta(sol: SolicitudAnalisis, df_proc: pd.DataFrame) -> dict:
    indicadores = [c for c in CalculadorRadar.COLUMNAS_BINARIAS if c in df_proc.columns]

    # score por indicador = MAX del score por articulo (agregacion de esta rama)
    max_por_indicador = {c: float(df_proc[c].astype(float).max()) for c in indicadores}
    radar_propio = float(sum(max_por_indicador.values()) / len(indicadores))
    categoria = _categoria(radar_propio)

    # articulos que apoyan cada indicador (score >= UMBRAL_ARTICULO), ordenados
    articulos, arts_por_indicador = {}, {}
    for c in indicadores:
        apoyan = df_proc[df_proc[c].astype(float) >= UMBRAL_ARTICULO]
        arts_por_indicador[c] = int(len(apoyan))
        top = apoyan.sort_values(c, ascending=False).head(MAX_ARTICULOS_POR_INDICADOR)
        articulos[c] = [
            {
                "titulo": str(r.get("titulo") or ""),
                "periodico": str(r.get("periodico") or ""),
                "fecha": str(r.get("fecha") or ""),
                "url": str(r.get("url") or ""),
                "score": float(round(float(r.get(c) or 0.0), 4)),
            }
            for _, r in top.iterrows()
        ]

    bloques = []
    for letra in "ABCDE":
        cols_b = [c for c in BLOQUES_INDICADORES[letra] if c in max_por_indicador]
        score_bloque = int(round((sum(max_por_indicador[c] for c in cols_b) / len(cols_b)) * 100)) if cols_b else 0
        bloques.append({
            "id": letra,
            "nombre": BLOQUES_META[letra]["nombre"],
            "color": BLOQUES_META[letra]["color"],
            "score": score_bloque,
            "indicadores": [
                {
                    "nombre": _nombre_bonito(c),
                    "col": c,
                    "score": float(round(max_por_indicador[c], 4)),
                    "arts": int(arts_por_indicador.get(c, 0)),
                    "real": bool(arts_por_indicador.get(c, 0) > 0),
                }
                for c in BLOQUES_INDICADORES[letra]
            ],
        })

    fuentes = sorted(str(p) for p in df_proc["periodico"].dropna().unique())

    return {
        "lugar": sol.territorio,
        "fecha_inicio": sol.fecha_inicio,
        "fecha_fin": sol.fecha_fin,
        "n_articulos": int(len(df_proc)),
        "fuentes": fuentes,
        "badge_score": int(round(radar_propio * 100)),
        "badge_label": BADGE[categoria]["label"],
        "badge_color": BADGE[categoria]["color"],
        "bloques": bloques,
        "articulos": articulos,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
