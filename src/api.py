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
  POST /validar         solo FILTRO 1 (territorial), sin scrapear ni NLI
  GET  /lugares?q=...   autocompletado de municipios/departamentos (tabla local)
  GET  /health          estado y cortes activos

FILTRO 1 (territorial): antes de scrapear se valida que el texto escrito sea un
territorio real del departamento elegido, contra `validacion_territorial.py`
(tabla local del DANE). Si no lo es, se corta ahi: no hay scraping ni NLI.

SIN DEPENDENCIA DE RED: la version anterior consultaba DIVIPOLA
(datos.gov.co/resource/gdxc-w37w.json) en /lugares y para resolver el
departamento de un municipio. Si esa API se caia, se caia el autocompletado y
la validacion. Ahora todo sale de `municipios_colombia.py`, que es ese mismo
dataset ya congelado en el repo (32 departamentos, 1121 municipios).

Correr desde la raiz del proyecto:
    uvicorn src.api:app --host 0.0.0.0 --port 8000
o directamente:
    python src/api.py

ADVERTENCIA: /analizar scrapea en vivo y corre mDeBERTa. Una request puede
tardar varios minutos (el front tiene pantalla de loading). El modelo NLI se
carga UNA sola vez AL ARRANCAR la app (no perezoso: instanciarlo dentro del
thread del worker daba un 500 por conflicto CUDA/torch) y se reutiliza. Por eso
uvicorn tarda varios minutos en responder /health la primera vez.
"""
import os
import sys
import unicodedata
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

# ── Rutas: src/ al path para que los imports por nombre de Santiago funcionen ─
DIR_SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR_SRC)

import config_pipeline as cfg          # noqa: E402
from radar import CalculadorRadar       # noqa: E402
import validacion_territorial as vt     # noqa: E402

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
# contenido cuando llega un nombre largo, p. ej. San Andres).
_DEPARTAMENTOS_MAPA = {
    k for k in MAPA_TERRITORIO_PERIODICOS
    if k not in {"paraguachon", "maicao", "guintiva", "oicata"}
}

# ── Helpers de texto ─────────────────────────────────────────────────────────
# _norm y la limpieza de prefijos viven en validacion_territorial (unica fuente).
_norm = vt.norm
_termino_busqueda = vt.limpiar_termino


def _slug(txt: str) -> str:
    t = unicodedata.normalize("NFD", str(txt).lower()).encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() else "_" for c in t).strip("_")


def _categoria(valor: float) -> str:
    """Cortes fijos de ESTA rama, leidos de config_pipeline (no hardcodeados)."""
    if valor < cfg.CORTE_BAJO_MEDIO_RADAR:
        return "Bajo"
    if valor < cfg.CORTE_MEDIO_ALTO_RADAR:
        return "Medio"
    return "Alto"


def _nombre_bonito(col: str) -> str:
    return col.replace("_", " ").title()


# ── Resolucion de departamento (tabla local, sin red) ────────────────────────
def _departamento_de_municipio(municipio: str) -> Optional[str]:
    """Departamento al que pertenece un municipio, o None si no existe o si es
    homonimo de varios (ahi hace falta que el usuario elija: no se adivina,
    que es lo que hacia el $limit=1 de DIVIPOLA)."""
    deptos = vt.departamentos_de_municipio(municipio)
    return deptos[0] if len(deptos) == 1 else None


def _periodicos_de_departamento(dpto: str) -> List[str]:
    """Periodicos del departamento segun el mapa. Exacto, luego por contenido
    (por si llega un nombre largo, p. ej. 'Archipielago de San Andres...')."""
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
    b) si no, tabla local -> departamento del municipio -> periodicos del depto
    c) si tampoco -> ['eltiempo']
    """
    for clave in (_norm(termino), _norm(territorio)):
        if clave in MAPA_TERRITORIO_PERIODICOS:
            return MAPA_TERRITORIO_PERIODICOS[clave]

    dpto = _departamento_de_municipio(termino)
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
    # resolver los periodicos y validar el territorio (util en texto libre/veredas).
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
    """Autocompletado de municipios y departamentos contra la tabla local del
    DANE (`municipios_colombia.py`). Antes esto pegaba a DIVIPOLA en cada
    pulsacion: si datos.gov.co se caia, el campo dejaba de sugerir. Ahora es un
    lookup en memoria — instantaneo y sin red."""
    return vt.autocompletar(q)


@app.post("/validar")
def validar(sol: SolicitudAnalisis):
    """FILTRO 1 aislado: valida el territorio sin scrapear ni cargar el NLI.
    Permite que el front avise al instante, antes de lanzar un /analizar que
    tarda minutos. /analizar aplica esta misma validacion igual, asi que
    llamar aqui es opcional."""
    r = vt.validar_territorio(sol.territorio, sol.departamento_hint,
                              bool(sol.forzar_lugar))
    return {
        "valido": r.valido,
        "tipo": r.tipo,
        "territorio": r.nombre_oficial or r.termino,
        "departamento": r.departamento,
        "sugerencia": r.sugerencias,
        "msg": r.mensaje,
        "exige_cobertura": r.exige_cobertura,
        "forzable": r.forzable,
    }


@app.post("/analizar")
def analizar(sol: SolicitudAnalisis):
    """Analiza un territorio y devuelve el radar como JSON (POST sincrono).
    Aplica primero el FILTRO 1 (territorial, tabla local): si el texto no es un
    territorio del departamento elegido corta antes de scrapear — con
    {"sugerencia": [...]} si hay candidatos parecidos, o 422 si no. Un lugar
    forzado (vereda/corregimiento) pasa pero exige cobertura minima."""
    import scrappers as sc  # import diferido: arrastra playwright/aiohttp

    # ── FILTRO 1: territorial. Tabla local, sin red, antes de scrapear nada. ──
    val = vt.validar_territorio(sol.territorio, sol.departamento_hint,
                                bool(sol.forzar_lugar))
    if not val.valido:
        # Con sugerencias se responde 200 (el front muestra "¿quisiste decir?");
        # sin ellas es un rechazo duro y se corta con 422.
        if val.sugerencias:
            return {"sugerencia": val.sugerencias, "msg": val.mensaje}
        # Rechazo duro. `forzable` le dice al front si tiene sentido ofrecer
        # "buscar igual" (solo cuando el territorio no figura en la tabla, p. ej.
        # una vereda). detail sigue siendo string: el front viejo no se rompe.
        # Header CORS explicito, igual que global_exception_handler (un 422 que
        # sube sin el header llega al navegador como error CORS enmascarado).
        return JSONResponse(
            status_code=422,
            content={"detail": val.mensaje, "forzable": val.forzable},
            headers={"Access-Control-Allow-Origin": "*"},
        )

    termino = val.termino               # nombre oficial ya normalizado
    piso_vereda = val.exige_cobertura   # lugar forzado => piso de cobertura

    if sol.periodicos:
        periodicos = sol.periodicos
    elif val.departamento:
        periodicos = _periodicos_de_departamento(val.departamento)
    else:
        periodicos = _resolver_periodicos(sol.territorio, termino)
    hint = val.departamento or sol.departamento_hint or ""

    # Scraping en vivo. El endpoint es un `def` sincrono, asi que FastAPI lo corre
    # en un threadpool: el manejo de event loop de scrappers no toca el de uvicorn.
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

    n_art = 0 if (df is None or df.empty) else len(df)
    if piso_vereda and n_art < 5:
        raise HTTPException(status_code=422, detail=f"No se encontró cobertura de prensa para '{sol.territorio}' en {hint or sol.territorio}. Verifica el nombre o prueba con el departamento.")
    if df is None or df.empty:
        raise HTTPException(status_code=422, detail="No se encontraron noticias del territorio seleccionado en el período indicado")

    # El pipeline agrupa por 'departamento'; aqui es el territorio pedido.
    df = df.copy()
    df["departamento"] = sol.territorio
    for c in ["periodico", "titulo", "fecha", "texto", "url"]:
        if c not in df.columns:
            df[c] = None

    try:
        df_proc = _get_pipeline().procesar(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo el pipeline NLI: {e}")

    return _construir_respuesta(sol, df_proc)


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
