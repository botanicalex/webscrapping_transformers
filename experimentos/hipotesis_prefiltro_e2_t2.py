"""
Cribado sin jueces de los 11 indicadores restantes de la etapa 2 del pre-filtro por indicador.

Pre-registrado en experimentos/PREREG_prefiltro_indicador_e2_t2.md: a partir del commit de
pre-registro NADA de este archivo cambia. Las listas NO se copian: se leen de
hipotesis_prefiltro_e2.LISTAS_SOLO_APERTURA (congeladas en da30a63), sin retocar.
Las gemelas cambian el sujeto o destinatario humano del indicador por osos polares, como en el tramo 1.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipotesis_prefiltro_e2 as P  # noqa: E402

CRIBADO = [
    "resistencia_territorial",
    "exclusion_comunidades",
    "deficit_participacion_comunitaria",
    "incentivos_economicos_inequitativos",
    "conflictos_socioambientales",
    "exclusion_servicios_derechos",
    "grupos_etnicos_existentes",
    "movimientos_sociales",
    "irregularidad_contractual",
    "zonas_proteccion_alimentaria",
    "dano_territorios",
]

LISTAS = {ind: P.LISTAS_SOLO_APERTURA[ind] for ind in CRIBADO}

# Hipotesis vigentes (V2), iguales a src/Transformer_optimo.py.
HIPOTESIS = {
    "resistencia_territorial": "Hay resistencia comunitaria en defensa del territorio o el medio ambiente.",
    "exclusion_comunidades": "Las comunidades exigen ser consultadas o incluidas en las decisiones.",
    "deficit_participacion_comunitaria": "No hubo consulta ni participación de la comunidad en un proyecto o decisión.",
    "incentivos_economicos_inequitativos": "El reparto de compensaciones o regalías de un proyecto fue desigual.",
    "conflictos_socioambientales": "Hay un conflicto por el uso del territorio, el agua o los recursos naturales.",
    "exclusion_servicios_derechos": "Hay población sin acceso a servicios básicos o a sus derechos.",
    "grupos_etnicos_existentes": "En este territorio hay comunidades étnicas o pueblos indígenas.",
    "movimientos_sociales": "Hay movilizaciones u organizaciones sociales activas.",
    "irregularidad_contractual": "Hubo irregularidades o corrupción en contratos públicos.",
    "zonas_proteccion_alimentaria": "Hay cultivos, tierras de siembra o producción de alimentos.",
    "dano_territorios": "Hubo destrucción, ocupación ilegal o despojo de territorios.",
}

# Gemelas de objeto absurdo.
GEMELAS = {
    "resistencia_territorial": "Hay resistencia de los osos polares en defensa del territorio o el medio ambiente.",
    "exclusion_comunidades": "Los osos polares exigen ser consultados o incluidos en las decisiones.",
    "deficit_participacion_comunitaria": "No hubo consulta ni participación de los osos polares en un proyecto o decisión.",
    "incentivos_economicos_inequitativos": "El reparto de compensaciones o regalías entre los osos polares fue desigual.",
    "conflictos_socioambientales": "Hay un conflicto de los osos polares por el uso del territorio, el agua o los recursos naturales.",
    "exclusion_servicios_derechos": "Hay osos polares sin acceso a servicios básicos o a sus derechos.",
    "grupos_etnicos_existentes": "En este territorio hay comunidades de osos polares.",
    "movimientos_sociales": "Hay movilizaciones u organizaciones de osos polares activas.",
    "irregularidad_contractual": "Hubo irregularidades o corrupción en contratos con osos polares.",
    "zonas_proteccion_alimentaria": "Hay cultivos, tierras de siembra o producción de alimentos para osos polares.",
    "dano_territorios": "Hubo destrucción, ocupación ilegal o despojo de territorios de osos polares.",
}

# Umbrales del cribado (iguales a los del tramo 1).
TOL_C = 5e-5          # (c): con mascara >= sin mascara - TOL_C en las 4 comparaciones
BASE_DANE = -0.0913   # §6.2, a 4 decimales
BASE_TAM = 0.8640     # §6.3, a 4 decimales
MAX_LISTAS_NUEVAS = 3
SEMILLA = 20260930
