"""
V2 — las 26 hipotesis reescritas segun el patron validado en los experimentos 1-4.

REGLA DE TRANSFORMACION
  Quitar el marco metalinguistico. La hipotesis debe describir EL TERRITORIO O
  EL HECHO, no el documento.

    antes : "Este artículo menciona explícitamente la presencia de X en un territorio."
    despues: "En este territorio hay presencia de X."

  El modelo evalua si el texto *es un articulo que menciona algo*, cosa
  trivialmente cierta para cualquier noticia. Medido: con el formato metalinguistico
  el 78% de las noticias "implica" que menciona pinguinos emperador.

REGLAS SECUNDARIAS
  - Frase corta y declarativa (XNLI se entreno con hipotesis de ~10 tokens).
  - Sin "explicitamente" / "verificable" / "documentada": son instrucciones para
    un anotador humano, no proposiciones evaluables. Medido: aportan +0.03 de AUC.
  - Con tildes correctas: 4 hipotesis estaban sin acentuar ("danos", "contaminacion").
  - Se conserva la disyuncion cuando es sustantiva: medido que no es el problema
    principal (quitarla sola empeora el control absurdo).

DIFERENCIACION
  `exclusion_comunidades` y `deficit_participacion_comunitaria` median casi lo
  mismo. Aqui se separan: la primera es la EXIGENCIA de ser incluido, la segunda
  es la AUSENCIA de proceso participativo.
"""

EVENTOS = {
    "desplazamiento_forzado": "Hubo un desplazamiento forzado o éxodo de comunidades.",
    "reasentamiento": "Se realizó un reasentamiento o reubicación de población.",
    "protesta_social": "Hubo una protesta, manifestación, bloqueo o paro.",
    "amenaza_intimidacion": "Hubo amenazas, intimidación u hostigamiento contra personas.",
    "conflicto_territorial": "Hay una disputa por el control, el uso o la propiedad de un territorio.",
}

POSTURAS = {
    "rechazo_proyecto": "Hay oposición de comunidades o autoridades a un proyecto.",
    "derechos_vulnerados": "Se vulneraron los derechos de una comunidad.",
    "conflicto_activo": "Hay un conflicto activo en este territorio.",
    "resistencia_territorial": "Hay resistencia comunitaria en defensa del territorio o el medio ambiente.",
    # EXIGENCIA de inclusión (se diferencia de deficit_participacion_comunitaria)
    "exclusion_comunidades": "Las comunidades exigen ser consultadas o incluidas en las decisiones.",
}

INDICADORES = {
    # AUSENCIA de proceso participativo
    "deficit_participacion_comunitaria": "No hubo consulta ni participación de la comunidad en un proyecto o decisión.",
    "incentivos_economicos_inequitativos": "El reparto de compensaciones o regalías de un proyecto fue desigual.",
    "debilidad_institucional": "Las instituciones carecen de recursos o de capacidad para cumplir su función.",
    "danos_ambientales": "Hubo daños ambientales, contaminación o pérdida de biodiversidad.",
    "conflictos_socioambientales": "Hay un conflicto por el uso del territorio, el agua o los recursos naturales.",
    "violacion_derechos_humanos": "Se denunciaron violaciones de derechos humanos.",
    "exclusion_servicios_derechos": "Hay población sin acceso a servicios básicos o a sus derechos.",
    # Validada en exp1-exp4: AUC 0.6303 -> 0.8212
    "grupos_etnicos_existentes": "En este territorio hay comunidades étnicas o pueblos indígenas.",
    "movimientos_sociales": "Hay movilizaciones u organizaciones sociales activas.",
    "poblacion_afectada": "Hay comunidades o familias afectadas.",
    "exclusion_beneficios_economicos": "Una comunidad quedó excluida de los beneficios económicos de un proyecto.",
    "irregularidad_contractual": "Hubo irregularidades o corrupción en contratos públicos.",
    "zonas_proteccion_alimentaria": "Hay cultivos, tierras de siembra o producción de alimentos.",
    "dano_territorios": "Hubo destrucción, ocupación ilegal o despojo de territorios.",
    # Validada en exp1-exp4: AUC 0.7430 -> 0.8261
    "presencia_grupos_armados": "En este territorio hay presencia de grupos armados ilegales.",
    "amenaza_lideres": "Hubo amenazas o agresiones contra líderes sociales.",
}

TODAS = {**EVENTOS, **POSTURAS, **INDICADORES}
assert len(TODAS) == 26, f"Se esperaban 26 hipotesis, hay {len(TODAS)}"

# Pre-filtro reescrito. El original era el caso extremo del problema:
# metalinguistico + 8 disyuntos encadenados. Medido: anulaba el 33.6% de los
# positivos de plata de grupos etnicos.
HIPOTESIS_SOCIAL = "Hay un conflicto, una afectación o un riesgo que afecta a una comunidad."
UMBRAL_SOCIAL = 0.65

# ── Calibracion por articulo ────────────────────────────────────────────────
# Estiman el sesgo "si-decidor" de cada articulo. Dominios variados a proposito.
NULAS_CALIBRACION = [
    "En este territorio hay presencia de pingüinos emperador.",
    "En este territorio hay yacimientos de helio-3 lunar.",
    "En este territorio se practica la caligrafía medieval japonesa.",
    "En este territorio hay glaciares de metano líquido.",
]
# Reservada para evaluar honestamente (NO entra en la calibracion)
NULA_TEST = "En este territorio hay colonias de osos polares."
