"""
Linea base (V0) de los experimentos: las 26 hipotesis EXACTAMENTE como estan hoy
en produccion (Transformer_optimo.py), incluidos los 4 cambios manuales que
hicieron el usuario y su profesora la semana del 2026-08-10.

No editar estas cadenas: son el punto de comparacion. Las variantes de los
experimentos se definen en archivos aparte.

Marcadas con  # MANUAL  las 4 modificadas a mano.
Marcadas con  # SIN_TILDES  las escritas sin acentuacion (candidatas a variante
de tokenizacion, ver eje 5 de la propuesta).
"""

EVENTOS = {
    "desplazamiento_forzado": "Este texto reporta que OCURRIÓ un desplazamiento forzado, expulsión o éxodo de comunidades",
    "reasentamiento": "Este texto reporta que SE REALIZÓ un reasentamiento, reubicación o traslado planificado de población",
    "protesta_social": "Este texto reporta que OCURRIÓ una protesta social, manifestación, bloqueo, movilización o paro",
    "amenaza_intimidacion": "Este texto reporta que OCURRIERON amenazas, intimidación, hostigamiento o violencia contra personas",
    "conflicto_territorial": "Este texto reporta una disputa activa y documentada por el control, uso o propiedad de un territorio o tierras específicas, con comunidades, grupos o actores plenamente identificados en conflicto directo entre sí por ese territorio.",
}

POSTURAS = {
    "rechazo_proyecto": "Este artículo reporta oposición explícita de comunidades, organizaciones o autoridades frente a un proyecto energético, minero, vial, ambiental o de infraestructura.",
    # MANUAL: + "e identifica el derecho o la afectación denunciada"
    "derechos_vulnerados": "Este artículo afirma explícitamente que se vulneraron derechos humanos, territoriales, colectivos, ambientales, étnicos o sociales de una comunidad o grupo poblacional identificado e identifica el derecho o la afectación denunciada.",
    "conflicto_activo": "Este artículo reporta un conflicto activo con hechos recientes como protestas, bloqueos, enfrentamientos, amenazas, denuncias o disputas territoriales.",
    # SIN_TILDES
    "resistencia_territorial": "Este texto expresa resistencia activa, conflictividad o reivindicacion del territorio, los recursos naturales o el medio ambiente frente a una amenaza concreta.",
    # SIN_TILDES
    "exclusion_comunidades": "Este texto exige participacion, consulta o inclusion porque las comunidades han sido excluidas de decisiones que las afectan directamente.",
}

INDICADORES = {
    # MANUAL: + "que la afecta"
    "deficit_participacion_comunitaria": "Este artículo denuncia explícitamente que comunidades, ciudadanos, veedurías u organizaciones sociales fueron excluidos de procesos de participación, consulta, socialización o toma de decisiones sobre un proyecto, obra, política pública o intervención territorial específica que la afecta.",
    # MANUAL: reescrita — de "son excluidas de los beneficios" a "distribucion inequitativa"
    "incentivos_economicos_inequitativos": "Este artículo reporta explícitamente una distribución inequitativa de compensaciones, regalías, pagos o beneficios económicos de un proyecto, identificando a una comunidad o población perjudicada.",
    "debilidad_institucional": "Este texto evidencia una debilidad institucional grave y documentada: entidades con déficit de recursos o incapacidad demostrada para cumplir su mandato.",
    # SIN_TILDES  (danos / contaminacion / perdida / degradacion)
    "danos_ambientales": "Este articulo reporta danos ambientales verificables, contaminacion, perdida de biodiversidad o degradacion de ecosistemas.",
    "conflictos_socioambientales": "Este artículo reporta disputas entre comunidades, empresas o instituciones relacionadas explícitamente con daños ambientales, uso del territorio, minería, agua, energía o infraestructura.",
    # SIN_TILDES
    "violacion_derechos_humanos": "Este texto reporta una denuncia formal o explicita de violaciones de derechos humanos, abusos o incumplimientos graves de acuerdos, presentada por comunidades, organizaciones o defensores identificados.",
    "exclusion_servicios_derechos": "Este texto describe brechas concretas de exclusión en acceso a servicios, derechos u oportunidades",
    "grupos_etnicos_existentes": "Este artículo menciona explícitamente comunidades étnicas, pueblos indígenas, comunidades afrodescendientes, raizales, palenqueras o grupos étnicos que tienen presencia o participación relevante en el territorio.",
    "movimientos_sociales": "Este texto reporta movilizaciones, protestas, paros, plantones o acciones colectivas convocadas por movimientos sociales, organizaciones comunitarias o plataformas ciudadanas en defensa de derechos, territorio o condiciones de vida.",
    "poblacion_afectada": "Este artículo reporta explícitamente comunidades, familias o grupos poblacionales afectados negativamente por violencia, conflicto, desastre, proyecto o decisión institucional.",
    # MANUAL: reescrita — ahora exige comunidad "identificada" y proyecto "especifico"
    "exclusion_beneficios_economicos": "Este artículo reporta explícitamente que una comunidad o población identificada fue excluida de compensaciones, regalías, empleo, pagos u otros beneficios económicos generados por un proyecto o actividad productiva específica.",
    "irregularidad_contractual": "Este texto reporta irregularidades, sobreprecios, corrupción, desvío de fondos, favoritismos o incumplimientos detectados en contratos, compras o adjudicaciones públicas de obras, servicios o proyectos financiados por el Estado.",
    "zonas_proteccion_alimentaria": "Este texto menciona cultivos, tierras de siembra, parcelas agrícolas, producción de alimentos, acceso a comida, soberanía alimentaria o seguridad alimentaria de familias o comunidades rurales.",
    "dano_territorios": "Este texto reporta destrucción, ocupación ilegal, contaminación o despojo de territorios, tierras o recursos naturales pertenecientes a comunidades o pueblos identificados, causado por actores externos, actividades extractivas o proyectos específicos.",
    "presencia_grupos_armados": "Este artículo menciona explícitamente la presencia, acción, control o intervención de grupos armados ilegales en un territorio.",
    "amenaza_lideres": "Este texto reporta amenazas directas, hostigamiento, asesinato, desaparición o agresión física contra líderes sociales, defensores de derechos humanos o líderes comunitarios identificados por nombre o cargo.",
}

# Las 26 en un solo dict, en el mismo orden en que las recorre produccion
TODAS = {**EVENTOS, **POSTURAS, **INDICADORES}
assert len(TODAS) == 26, f"Se esperaban 26 hipotesis, hay {len(TODAS)}"

# Pre-filtro de relevancia social
UMBRAL_SOCIAL = 0.65
HIPOTESIS_SOCIAL = (
    "Este texto reporta conflictos, afectaciones, riesgos, protestas, vulneraciones de derechos, "
    "tensiones comunitarias, impactos territoriales o problemas institucionales que afectan a "
    "comunidades o poblaciones."
)

# Las 4 tocadas a mano la semana pasada
MODIFICADAS_MANUAL = [
    "derechos_vulnerados",
    "deficit_participacion_comunitaria",
    "incentivos_economicos_inequitativos",
    "exclusion_beneficios_economicos",
]

# Hipotesis escritas sin tildes (candidatas a problema de tokenizacion)
SIN_TILDES = [
    "resistencia_territorial",
    "exclusion_comunidades",
    "danos_ambientales",
    "violacion_derechos_humanos",
]


# ── Estandar de plata por palabras clave ─────────────────────────────────────
# Recuperado del bloque NER que se desactivo el 2026-06-24 en Transformer_optimo.py
# (self.ref_entidades). Sirve como etiquetado automatico de alta precision para
# comparar variantes entre si — NO como verdad absoluta.
KEYWORDS_SILVER = {
    "grupos_etnicos_existentes": {
        "indígena", "indigena", "afrodescendiente", "afrocolombiano",
        "raizal", "palenquero", "resguardo", "cabildo",
    },
    "presencia_grupos_armados": {
        "eln", "farc", "disidencias", "epl", "auc", "agc",
        "clan del golfo", "guerrilla", "paramilitar",
    },
}

# Control negativo: mismo formato que las hipotesis reales, contenido absurdo.
# Si esto puntua alto, el formato infla los scores con independencia del contenido.
HIPOTESIS_CONTROL_ABSURDO = (
    "Este artículo menciona explícitamente la presencia, acción, control o intervención "
    "de pingüinos emperador en un territorio."
)
