"""
Segunda ronda del plan 5ind MAX: solo reescritura de hipotesis (familia F1).

Regla del usuario (2026-09-23, regla 15 de CLAUDE.md): de cada indicador solo se cambia la
hipotesis; ni compuertas, ni min/restas de varias frases, ni columnas nuevas. Por eso cada
candidata es UNA frase y su score es la formula vigente de produccion
    s(h) = clip(clip(ent - sesgo, 0) * (1 - neu), 0, 1)
agregada por lugar con MAX.

Pre-registrado en experimentos/PREREG_5ind_MAX_r2.md: a partir del commit de congelamiento
NADA de este archivo cambia.

Candidatas por indicador (ademas de la vigente "vig", que es la linea base):
  N1, N2, N3 -> frases nuevas de esta ronda (se puntuan en GPU con su gemela)
  P1, P2     -> las parafrasis p1/p2 de la ronda 1, nunca evaluadas como frase unica (solo
                dentro de min() en V04); sus scores y gemelas ya estan en
                datos/scores/scores_5ind_atomicas_lugares.pkl
Gemela de objeto absurdo: mismo hueco por indicador que en la ronda 1, solo "osos polares".
Absurdo total: H.ABSURDO_TOTAL (= NULA_TEST), comun a todas.
"""
import hipotesis_5ind_max as H

INDICADORES_5 = H.INDICADORES_5

NUEVAS = {
    "exclusion_beneficios_economicos": {
        "N1": "La comunidad reclama regalías que no ha recibido por la explotación de un recurso.",
        "N2": "Una empresa no le pagó a la comunidad las compensaciones de un proyecto.",
        "N3": "Las regalías de una mina o de un pozo petrolero no llegan a la población local.",
        "N1_abs": "La comunidad reclama regalías que no ha recibido por un criadero de osos polares.",
        "N2_abs": "Una empresa no le pagó a la comunidad las compensaciones de un criadero de osos polares.",
        "N3_abs": "Las regalías de un criadero de osos polares no llegan a la población local.",
    },
    "rechazo_proyecto": {
        "N1": "La comunidad rechaza que construyan una mina, una represa o un parque eólico.",
        "N2": "Habitantes protestan para impedir la explotación minera o petrolera en su región.",
        "N3": "Pobladores exigen retirar un peaje, un relleno sanitario o una concesión.",
        "N1_abs": "La comunidad rechaza que construyan un criadero de osos polares.",
        "N2_abs": "Habitantes protestan para impedir un criadero de osos polares en su región.",
        "N3_abs": "Pobladores exigen retirar un criadero de osos polares.",
    },
    "desplazamiento_forzado": {
        "N1": "Familias fueron desplazadas de sus veredas por la violencia armada.",
        "N2": "Llegaron a la ciudad familias desplazadas por el conflicto armado.",
        "N3": "Personas tuvieron que dejar sus casas y sus tierras por amenazas o combates.",
        "N1_abs": "Familias fueron desplazadas de sus veredas por los osos polares.",
        "N2_abs": "Llegaron a la ciudad familias desplazadas por los osos polares.",
        "N3_abs": "Personas tuvieron que dejar sus casas y sus tierras por los osos polares.",
    },
    "conflicto_territorial": {
        "N1": "Grupos armados ilegales se enfrentan entre sí por el control de esta zona.",
        "N2": "Hay una guerra entre grupos criminales por el dominio de un territorio.",
        "N3": "Actores armados mantienen una disputa violenta y prolongada por unas tierras.",
        "N1_abs": "Grupos armados ilegales se enfrentan entre sí por el control de una colonia de osos polares.",
        "N2_abs": "Hay una guerra entre grupos criminales por el dominio de una colonia de osos polares.",
        "N3_abs": "Actores armados mantienen una disputa violenta y prolongada por una colonia de osos polares.",
    },
    "presencia_grupos_armados": {
        "N1": "Guerrilleros, disidentes de las FARC o paramilitares actúan en esta zona.",
        "N2": "Un grupo armado organizado, como el ELN o el Clan del Golfo, opera en la región.",
        "N3": "La población de esta zona vive bajo la presencia de guerrillas o paramilitares.",
        "N1_abs": "Osos polares actúan en esta zona.",
        "N2_abs": "Un grupo de osos polares opera en la región.",
        "N3_abs": "La población de esta zona vive bajo la presencia de osos polares.",
    },
}

# Candidatas: id -> clave. "vig" es la linea base (V01 de la ronda 1).
CANDIDATAS = ["N1", "N2", "N3", "P1", "P2"]


def texto(ind: str, clave: str) -> str:
    """Texto de la hipotesis (o gemela con sufijo _abs) de una candidata o de la vigente."""
    if clave in ("vig", "vig_abs"):
        return H.HIPOTESIS[ind][clave]
    if clave[0] == "P":  # P1/P2 = p1/p2 de la ronda 1
        return H.HIPOTESIS[ind][clave.lower()]
    return NUEVAS[ind][clave]


def hipotesis_gpu() -> dict:
    """{columna: texto} que hay que puntuar en GPU en la fase A (solo las N y sus gemelas)."""
    return {f"{ind}__{k}": h for ind, d in NUEVAS.items() for k, h in d.items()}


# Muestreo de EVALUACION para exclusion_beneficios_economicos (no es produccion ni variante):
# el top-k de su vigente no encontro ningun caso real en la ronda 1 (0 SI/SI en 565 + 94).
# Se juzgan todos los articulos cuya premisa visible (normalizada) contiene alguna de estas
# palabras, en el corpus nacional y en el de los 4 lugares.
REGEX_MUESTREO_EXCLUSION = r"regalia|(?<!caja de )compensaci|consulta previa|no (han|ha) recibido|indemniz"
