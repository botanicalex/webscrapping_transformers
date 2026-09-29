"""
Listas de objeto, hipotesis y gemelas absurdas de la etapa 2 del pre-filtro por indicador.

Pre-registrado en experimentos/PREREG_prefiltro_indicador_e2.md: a partir del commit de
pre-registro NADA de este archivo cambia. Las listas son las del borrador
experimentos/PLAN_prefiltro_indicador_etapa2.md §3, copiadas sin retocar; se escribieron solo con
el texto de cada hipotesis, sin mirar puntajes, juicios ni articulos.

La compuerta se evalua sobre la premisa visible normalizada (minusculas, sin tildes), igual que
REGEX_F5 y PREFILTRO_OBJETO: normalizar() y premisa_visible() de hipotesis_5ind_max.
"""

# Tramo 1 (6 indicadores): los unicos que se evaluan con (a)-(d).
TRAMO_1 = [
    "reasentamiento",
    "amenaza_lideres",
    "amenaza_intimidacion",
    "protesta_social",
    "violacion_derechos_humanos",
    "danos_ambientales",
]

# Hipotesis vigentes (V2), iguales a src/Transformer_optimo.py.
HIPOTESIS = {
    "reasentamiento": "Se realizó un reasentamiento o reubicación de población.",
    "amenaza_lideres": "Hubo amenazas o agresiones contra líderes sociales.",
    "amenaza_intimidacion": "Hubo amenazas, intimidación u hostigamiento contra personas.",
    "protesta_social": "Hubo una protesta, manifestación, bloqueo o paro.",
    "violacion_derechos_humanos": "Se denunciaron violaciones de derechos humanos.",
    "danos_ambientales": "Hubo daños ambientales, contaminación o pérdida de biodiversidad.",
}

# Gemelas de objeto absurdo: el objeto del indicador cambiado por osos polares.
GEMELAS = {
    "reasentamiento": "Se realizó un reasentamiento o reubicación de osos polares.",
    "amenaza_lideres": "Hubo amenazas o agresiones contra osos polares.",
    "amenaza_intimidacion": "Hubo amenazas, intimidación u hostigamiento contra osos polares.",
    "protesta_social": "Hubo una protesta, manifestación, bloqueo o paro de osos polares.",
    "violacion_derechos_humanos": "Se denunciaron violaciones de los derechos de los osos polares.",
    "danos_ambientales": "Hubo daños ambientales, contaminación o pérdida de biodiversidad por los osos polares.",
}

# Listas del tramo 1.
LISTAS_TRAMO_1 = {
    "reasentamiento":
        r"reasent|reubic|relocaliz|traslado de (familias|comunidades|poblacion)",
    "protesta_social":
        r"protest|manifestaci|bloqueo|\bparos?\b|marcha|asonada|movilizaci|huelga|cacerolazo|planton",
    "amenaza_intimidacion":
        r"amenaz|intimid|hostig|panfleto|extorsi|acoso|coaccion",
    "danos_ambientales":
        r"contaminaci|derrame|vertimiento|deforestaci|\btala\b|erosi|incendio forestal|biodiversidad|mineria ilegal"
        r"|mercurio|sequia|ecosistema|fauna|humedal|paramo|dano ambiental|impacto ambiental|residuos",
    "violacion_derechos_humanos":
        r"derechos humanos|\bddhh\b|masacre|homicidio|asesinat|desaparici|tortura|violaci\w* sexual"
        r"|ejecucion extrajudicial|falsos positivos|detencion arbitraria|reclutamiento|secuestro|lesa humanidad"
        r"|defensoria del pueblo|personeria",
    "amenaza_lideres":
        r"\blider|lideresa|defensor(es|a|as)? (de|del|de la)|dirigente|vocero|firmante de paz|reclamante|activista",
}

# Los otros 11 concretos del borrador: solo se reporta su tasa de apertura (no deciden nada).
LISTAS_SOLO_APERTURA = {
    "resistencia_territorial":
        r"resistencia|defensa del (territorio|agua|ambiente|medio ambiente)|guardia (indigena|cimarrona|campesina)"
        r"|\bminga\b|consulta popular|zona de reserva campesina",
    "exclusion_comunidades":
        r"consulta previa|consult|particip|exig\w* (ser )?(escuchad|incluid|consultad)|concertaci|socializaci",
    "deficit_participacion_comunitaria":
        r"consulta previa|consult|particip|exig\w* (ser )?(escuchad|incluid|consultad)|concertaci|socializaci",
    "incentivos_economicos_inequitativos":
        r"regalia|compensaci|reparto|inequitativ|desigual|beneficios? econ|contraprestaci|inversion social",
    "conflictos_socioambientales":
        r"mineri|hidroelectric|represa|fracking|petrole|hidrocarbur|extractiv|monocultivo|palma de aceite"
        r"|licencia ambiental|recursos? naturales|\bagua\b|\brio\b|acueducto|paramo|humedal",
    "exclusion_servicios_derechos":
        r"acueducto|agua potable|alcantarillado|energia electrica|servicios? publicos?|servicio de salud|hospital"
        r"|puesto de salud|escuela|colegio|educaci|vivienda|saneamiento|sin (agua|luz|energia|salud|acceso)"
        r"|desnutrici|hambre",
    "grupos_etnicos_existentes":
        r"indigena|\bafro|raizal|palenquer|\brom\b|gitan|resguardo|cabildo|comunidades? negras?|consejo comunitario"
        r"|etnic|etnia|wayuu|embera|\bnasa\b|misak|arhuaco|kogui|wiwa|\bawa\b|pijao|zenu|nukak|tikuna|kankuamo",
    "movimientos_sociales":
        r"movilizaci|organizaci\w* (social|comunitaria|campesina|indigena|de base)|movimiento social|sindicat"
        r"|junta de accion comunal|colectivo|plataforma|veedur|asociaci\w* de|\bminga\b|\bparo\b|marcha",
    "irregularidad_contractual":
        r"contrat|licitaci|corrupci|sobrecosto|peculado|interventoria|adjudicaci|soborno|cohecho"
        r"|detrimento patrimonial|procuradur|contralori|elefante blanco|obra inconclusa"
        r"|investigaci\w* (disciplinaria|fiscal)",
    "zonas_proteccion_alimentaria":
        r"cultiv|siembra|cosecha|agricult|agropecuari|alimentari|seguridad alimentaria|campesin|ganad|pesca"
        r"|piscicult|maiz|arroz|\bpapa\b|\bcafe\b|platano|\byuca\b|frijol|\bfinca|parcela|huerta",
    "dano_territorios":
        r"despojo|usurpaci|ocupaci\w* (ilegal|de hecho)|invasion|desalojo|destrucci|deforest|apropiaci"
        r"|acaparamiento|baldio|restituci|predios?|tierras",
}

# Techo de apertura: una lista que abre en mas de esta fraccion de los 11.439 articulos
# nacionales (premisa visible con la hipotesis de su indicador) pasa sin filtro.
TECHO_APERTURA = 0.50

# Tope de listas nuevas admitidas en el tramo 1.
MAX_LISTAS_NUEVAS = 3

SEMILLA = 20260929
