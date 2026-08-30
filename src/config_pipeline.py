"""
Configuracion central del pipeline.

Todas las etapas (scraping, transformers, radar, metricas) leen de aqui.
Las rutas son relativas a la raiz de `desarrollo/`, que es desde donde se
ejecutan los scripts.
"""

FECHA_DESDE = "2023-01-01"
FECHA_HASTA = "2023-12-31"

TEMAS_BUSQUEDA = [
    "conflicto",
    "comunidades",
    "institucional",
    "derechos",
    "social",
]

# ─────────────────────────────────────────────────────────────────────────────
# GRUPOS DE SCRAPING
#
# Se corren de a 3 departamentos simultaneos con `python src/correr_grupo.py N`
# (N es 1-based). La agrupacion NO es arbitraria: esta ajustada a mano para que
# dos departamentos que dependen del MISMO periodico no compitan por el mismo
# servidor en la misma tanda. Leer estas notas antes de reordenar.
#
#  G1  Antioquia: elcolombiano (rapido) | Choco: choco7dias (LENTO, ~35% exito,
#      timeout 600s) | Vichada: sin scraper local -> respaldo El Tiempo
#  G2  Valle del Cauca: elpais + diariooccidente | Arauca: lavozdelcinaruco +
#      tronchandosinfronteras (LENTO, timeout 600s) | Atlantico: -> El Tiempo
#  G3  Caldas: bcnoticias (separado de Tolima G11, que tambien usa bcnoticias)
#      Meta: llanoalmundo (1/3) | Bolivar: -> El Tiempo
#  G4  Risaralda: eldiario | Caqueta: llanoalmundo (2/3) | Putumayo: -> El
#      Tiempo (miputumayo bloqueado)
#  G5  Quindio: elquindiano | Guaviare: llanoalmundo (3/3) | Amazonas: ->
#      El Tiempo (miputumayo bloqueado)
#      NOTA: Casanare se movio a G11. Cuando Casanare y Amazonas corrian juntos
#      aqui, ambos caian a El Tiempo, competian por el mismo servidor y
#      devolvian 0 articulos los dos.
#  G6  Santander: enlacetelevision + corrillos + eltiempo (Playwright + ET
#      directo para cobertura 2023) | Cesar: elpilon (1/3) | Boyaca: eltiempo
#  G7  Norte de Santander: enlacetelevision + corrillos + eltiempo |
#      Magdalena: elpilon (2/3) | Guainia: -> El Tiempo (elmorichal caido)
#  G8  Cundinamarca: eltiempo + portafolio + publimetro + larepublica
#      (Playwright) | La Guajira: elpilon (3/3) | Cauca: diariodelcauca (1/2)
#  G9  Cordoba: elmeridiano (1/2) | Narino: diariodelsur (1/2) | Vaupes: eltiempo
#  G10 Sucre: elmeridiano (2/2) | Huila: diariodelcauca + diariodelsur |
#      San Andres: eltiempo
#  G11 Casanare: diariodecasanare + respaldo El Tiempo (movido desde G5) |
#      Tolima: bcnoticias + El Tiempo (separado de Caldas G3)
#      Solo 2 departamentos porque 32 % 3 == 2.
#
# llanoalmundo se reparte 1/3 entre G3, G4 y G5; elpilon 1/3 entre G6, G7 y G8;
# elmeridiano 1/2 entre G9 y G10. Esa separacion es intencional.
# ─────────────────────────────────────────────────────────────────────────────
GRUPOS_DEPARTAMENTOS = [
    ["Antioquia", "Chocó", "Vichada"],
    ["Valle del Cauca", "Arauca", "Atlántico"],
    ["Caldas", "Meta", "Bolívar"],
    ["Risaralda", "Caquetá", "Putumayo"],
    ["Quindío", "Guaviare", "Amazonas"],
    ["Santander", "Cesar", "Boyacá"],
    ["Norte de Santander", "Magdalena", "Guainía"],
    ["Cundinamarca", "La Guajira", "Cauca"],
    ["Córdoba", "Nariño", "Vaupés"],
    ["Sucre", "Huila", "San Andrés y Providencia"],
    ["Casanare", "Tolima"],
]

# Umbral por debajo del cual se activa la busqueda de respaldo en El Tiempo
MIN_ARTICULOS_RESPALDO = 50

# ── Rutas (relativas a la raiz de desarrollo/) ───────────────────────────────
RUTA_CORPUS_PKL = "datos/corpus"        # entrada: df_corpus_*.pkl
RUTA_SALIDA_PIPELINE = "resultados"     # salida del pipeline
RUTA_REFERENCIA = "datos/referencia"    # radar oficial DANE
RUTA_SCORES = "datos/scores"            # matrices de scores cacheadas

ARCHIVO_COMPARACION_EXCEL = "datos/referencia/comparacion_radares.xlsx"
ARCHIVO_COMPARACION_V3 = "datos/referencia/comparacion_radares_V3.xlsx"

DIRECTORIO_GRAFICOS_METRICAS = "resultados/graficos_metricas"
PREFIJO_RESULTADO_COMPARACION = "resultado_comparacion_radares"
# Renombrado: antes era "experimentos", que colisiona con la carpeta de codigo
# experimentos/ en la raiz del proyecto.
DIRECTORIO_EXPERIMENTOS = "resultados/experimentos"
ARCHIVO_METRICAS_ACUMULADO = "resultados/metricas_experimentos.xlsx"
