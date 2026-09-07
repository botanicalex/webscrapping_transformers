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
import os
import sys
import unicodedata
from typing import List, Optional

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# ── Rutas: src/ al path para que los imports por nombre de Santiago funcionen ─
DIR_SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR_SRC)

import config_pipeline as cfg          # noqa: E402
from radar import CalculadorRadar       # noqa: E402

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


app = FastAPI(title="Radar de Riesgo Territorial — API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ── Modelo NLI cargado al arrancar (no perezoso) ─────────────────────────────
# Se instancia al importar el modulo (hilo principal de uvicorn), no dentro del
# primer request. Cargar torch/CUDA en el thread del worker provocaba un 500 en
# /analizar aunque el pipeline funcionara al llamarlo directo en Python.
from Transformer_optimo import PipelineTransformers  # noqa: E402
_PIPELINE = PipelineTransformers()  # carga el modelo al arrancar la app


def _get_pipeline():
    return _PIPELINE


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
            "Access-Control-Allow-Methods": "POST, OPTIONS",
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


@app.get("/lugares")
def lugares(q: str = Query(..., min_length=2, description="Texto a autocompletar")):
    """Autocompletado de municipios y departamentos via DIVIPOLA (DANE).
    Nota: gdxc-w37w no incluye veredas."""
    params = {"$q": q, "$limit": 30}
    try:
        with httpx.Client(timeout=DIVIPOLA_TIMEOUT) as cliente:
            r = cliente.get(DIVIPOLA_URL, params=params)
            r.raise_for_status()
            filas = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fallo DIVIPOLA: {e}")

    q_norm = _norm(q)
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


@app.post("/analizar")
def analizar(sol: SolicitudAnalisis):
    import scrappers as sc  # import diferido: arrastra playwright/aiohttp

    termino = _termino_busqueda(sol.territorio)
    periodicos = sol.periodicos or _resolver_periodicos(sol.territorio, termino)

    # 1. Scraping en vivo del territorio
    try:
        df = sc.scrape_municipio(
            municipio=termino,
            fecha_desde=sol.fecha_inicio,
            fecha_hasta=sol.fecha_fin,
            periodicos=periodicos,
            min_menciones=1,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fallo el scraping: {e}")

    if df is None or df.empty:
        return _respuesta_vacia(sol)

    # El pipeline agrupa por 'departamento'; aqui es el territorio pedido.
    df = df.copy()
    df["departamento"] = sol.territorio
    for c in ["periodico", "titulo", "fecha", "texto", "url"]:
        if c not in df.columns:
            df[c] = None

    # 2. NLI (26 hipotesis V2). Modelo reutilizado.
    try:
        df_proc = _get_pipeline().procesar(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo el pipeline NLI: {e}")

    return _construir_respuesta(sol, df_proc)


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
    radar_propio = sum(max_por_indicador.values()) / len(indicadores)
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
                "score": round(float(r.get(c) or 0.0), 4),
            }
            for _, r in top.iterrows()
        ]

    bloques = []
    for letra in "ABCDE":
        cols_b = [c for c in BLOQUES_INDICADORES[letra] if c in max_por_indicador]
        score_bloque = round((sum(max_por_indicador[c] for c in cols_b) / len(cols_b)) * 100) if cols_b else 0
        bloques.append({
            "id": letra,
            "nombre": BLOQUES_META[letra]["nombre"],
            "color": BLOQUES_META[letra]["color"],
            "score": score_bloque,
            "indicadores": [
                {
                    "nombre": _nombre_bonito(c),
                    "col": c,
                    "score": round(max_por_indicador[c], 4),
                    "arts": arts_por_indicador.get(c, 0),
                    "real": arts_por_indicador.get(c, 0) > 0,
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
        "badge_score": round(radar_propio * 100),
        "badge_label": BADGE[categoria]["label"],
        "badge_color": BADGE[categoria]["color"],
        "bloques": bloques,
        "articulos": articulos,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
