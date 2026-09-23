"""
Hipotesis atomicas, regex y gemelas absurdas del experimento de 5 indicadores bajo MAX.

Fuente unica de textos para exp_5ind_max_atomicas.py (GPU) y exp_5ind_max_variantes.py
(offline). Pre-registrado en experimentos/PREREG_5ind_MAX.md: a partir del commit de
pre-registro NADA de este archivo cambia.

Claves atomicas por indicador:
  vig, gpt, nue          -> F1 (frase unica)
  p1, p2                 -> paráfrasis; F4 = min(nue, p1, p2)
  A1, A2                 -> F2 = min(A1, A2)
  c1, c2, c3             -> confusores de F3
Gemelas de objeto absurdo (osos polares, NULA_TEST): mismas claves con sufijo "_abs".
Para F2 solo se gemela la pieza indicada en PIEZA_F2_ABS.
Absurdo total (comun a todas): ABSURDO_TOTAL.
"""
import re
import unicodedata

INDICADORES_5 = [
    "exclusion_beneficios_economicos",
    "rechazo_proyecto",
    "desplazamiento_forzado",
    "conflicto_territorial",
    "presencia_grupos_armados",
]

# Iguales a src/Transformer_optimo.py (regla 4: nunca incluir NULA_TEST aqui).
NULAS_CALIBRACION = [
    "En este territorio hay presencia de pingüinos emperador.",
    "En este territorio hay yacimientos de helio-3 lunar.",
    "En este territorio se practica la caligrafía medieval japonesa.",
    "En este territorio hay glaciares de metano líquido.",
]

ABSURDO_TOTAL = "En este territorio hay colonias de osos polares."  # = NULA_TEST

HIPOTESIS = {
    "exclusion_beneficios_economicos": {
        "vig": "Una comunidad quedó excluida de los beneficios económicos de un proyecto.",
        "gpt": "Una comunidad no recibió beneficios, regalías o compensaciones de un proyecto.",
        "nue": "Una comunidad reclama regalías o compensaciones que no recibió.",
        "p1": "Una comunidad denuncia que no le pagaron las compensaciones de un proyecto.",
        "p2": "Los beneficios económicos de un proyecto no llegaron a la comunidad.",
        "A1": "Un proyecto genera regalías o compensaciones.",
        "A2": "Una comunidad reclama dinero que no ha recibido.",
        "c1": "Hay población sin acceso a servicios básicos.",
        "c2": "Se deportó o expulsó a una persona.",
        "c3": "Se encontraron cuerpos de personas desaparecidas.",
        "vig_abs": "Una comunidad quedó excluida de los beneficios económicos de un criadero de osos polares.",
        "gpt_abs": "Una comunidad no recibió beneficios, regalías o compensaciones de un criadero de osos polares.",
        "nue_abs": "Una comunidad reclama regalías o compensaciones de un criadero de osos polares que no recibió.",
        "p1_abs": "Una comunidad denuncia que no le pagaron las compensaciones de un criadero de osos polares.",
        "p2_abs": "Los beneficios económicos de un criadero de osos polares no llegaron a la comunidad.",
        "A1_abs": "Un criadero de osos polares genera regalías o compensaciones.",
    },
    "rechazo_proyecto": {
        "vig": "Hay oposición de comunidades o autoridades a un proyecto.",
        "gpt": "Una comunidad se opuso a la ejecución de un proyecto específico.",
        "nue": "Una comunidad se opone a una obra o proyecto minero, energético o vial.",
        "p1": "Habitantes rechazan la construcción de una obra.",
        "p2": "Una comunidad protesta contra un proyecto minero o energético.",
        "A1": "Hay oposición comunitaria.",
        "A2": "Se discute un proyecto minero, energético o de infraestructura.",
        "c1": "Hubo una protesta por falta de servicios públicos.",
        "c2": "Trabajadores protestaron por sus condiciones laborales.",
        "c3": "Una comunidad expulsó a militares o policías.",
        "vig_abs": "Hay oposición de comunidades o autoridades a un criadero de osos polares.",
        "gpt_abs": "Una comunidad se opuso a la ejecución de un criadero de osos polares.",
        "nue_abs": "Una comunidad se opone a un criadero de osos polares.",
        "p1_abs": "Habitantes rechazan la construcción de un criadero de osos polares.",
        "p2_abs": "Una comunidad protesta contra un criadero de osos polares.",
        "A2_abs": "Se discute un criadero de osos polares.",
    },
    "desplazamiento_forzado": {
        "vig": "Hubo un desplazamiento forzado o éxodo de comunidades.",
        "gpt": "Personas o comunidades fueron obligadas a abandonar su territorio.",
        "nue": "Familias huyeron de su territorio por la violencia.",
        "p1": "Hubo familias desplazadas por el conflicto armado.",
        "p2": "Personas abandonaron sus hogares por amenazas de grupos armados.",
        "A1": "Personas abandonaron sus hogares.",
        "A2": "Hubo violencia o amenazas de grupos armados.",
        "c1": "Hay riesgo o amenaza de desplazamiento.",
        "c2": "Llegaron migrantes venezolanos.",
        "c3": "Hubo amenazas contra personas.",
        "vig_abs": "Hubo un desplazamiento forzado o éxodo de comunidades por los osos polares.",
        "gpt_abs": "Personas o comunidades fueron obligadas a abandonar su territorio por los osos polares.",
        "nue_abs": "Familias huyeron de su territorio por los osos polares.",
        "p1_abs": "Hubo familias desplazadas por los osos polares.",
        "p2_abs": "Personas abandonaron sus hogares por los osos polares.",
        "A2_abs": "Hubo violencia o amenazas de osos polares.",
    },
    "conflicto_territorial": {
        "vig": "Hay una disputa por el control, el uso o la propiedad de un territorio.",
        "gpt": "Dos o más actores disputan el control, uso o propiedad de un territorio.",
        "nue": "Hay enfrentamientos violentos por el control de un territorio.",
        "p1": "Grupos armados se disputan el control de un territorio.",
        "p2": "Dos grupos se enfrentan con armas por unas tierras.",
        "A1": "Hay enfrentamientos armados o violentos.",
        "A2": "Dos grupos se disputan un territorio.",
        "c1": "Hubo una protesta o un bloqueo de vías.",
        "c2": "Hubo amenazas contra una persona.",
        "c3": "Hay un debate político o electoral.",
        "vig_abs": "Hay una disputa por el control, el uso o la propiedad de una colonia de osos polares.",
        "gpt_abs": "Dos o más actores disputan el control, uso o propiedad de una colonia de osos polares.",
        "nue_abs": "Hay enfrentamientos violentos por el control de una colonia de osos polares.",
        "p1_abs": "Grupos armados se disputan el control de una colonia de osos polares.",
        "p2_abs": "Dos grupos se enfrentan con armas por una colonia de osos polares.",
        "A2_abs": "Dos grupos se disputan una colonia de osos polares.",
    },
    "presencia_grupos_armados": {
        "vig": "En este territorio hay presencia de grupos armados ilegales.",
        "gpt": "Un grupo armado ilegal identificado opera en este territorio.",
        "nue": "En este territorio operan guerrillas, disidencias o grupos paramilitares.",
        "p1": "El ELN, las disidencias o el Clan del Golfo tienen presencia en esta zona.",
        "p2": "Hay presencia de guerrilla o paramilitares en este territorio.",
        "A1": "En este territorio hay presencia de grupos armados ilegales.",  # = vig
        "A2": "Hay un conflicto armado en este territorio.",
        "c1": "Hubo un homicidio o un robo.",
        "c2": "La policía capturó a una persona por porte ilegal de armas.",
        "c3": "Una banda delincuencial cometió hurtos.",
        "vig_abs": "En este territorio hay presencia de osos polares.",
        "gpt_abs": "Un grupo de osos polares identificado opera en este territorio.",
        "nue_abs": "En este territorio operan osos polares.",
        "p1_abs": "Los osos polares tienen presencia en esta zona.",
        "p2_abs": "Hay presencia de osos polares en este territorio.",
        "A1_abs": "En este territorio hay presencia de osos polares.",  # = vig_abs
    },
}

# Pieza de F2 que se reemplaza por su gemela de objeto absurdo.
PIEZA_F2_ABS = {
    "exclusion_beneficios_economicos": "A1",
    "rechazo_proyecto": "A2",
    "desplazamiento_forzado": "A2",
    "conflicto_territorial": "A2",
    "presencia_grupos_armados": "A1",
}

# Compuerta lexica F5: se evalua sobre la PREMISA VISIBLE (solo `texto`, truncado a
# TOKENS_PREMISA tokens, ver premisa_visible), en minusculas y sin tildes.
REGEX_F5 = {
    "exclusion_beneficios_economicos":
        r"regalia|(?<!caja de )compensaci|indemniz|contraprestaci|beneficios? econ|inversion social|empleo local",
    "rechazo_proyecto":
        r"proyecto|\bobras?\b|mineria|\bmina\b|eolic|hidroelectric|represa|relleno sanitario|peaje"
        r"|concesion|licencia ambiental|exploracion|fracking|puerto",
    "desplazamiento_forzado":
        r"desplaz|\bhuy(o|e|en|eron|endo)\b|\bhuir\b|exodo|abandonar(on)? sus (casas|hogares|tierras|veredas)",
    "conflicto_territorial":
        r"disput\w* (por|de|el|la) (el |la )?(control|territorio|dominio|zona|tierras?|predios?)|disputa territorial"
        r"|enfrentamient|\bcombates?\b(?! (a|al|contra)\b)|control territorial|invasion de (tierras|predios)|lindero"
        r"|guerra entre|confrontaci",
    "presencia_grupos_armados":
        r"\beln\b|farc|disidencia|clan del golfo|\bagc\b|\begc\b|autodefensas|\bacsn\b|pachenca"
        r"|paramilitar|guerrill|segunda marquetalia|estado mayor central|\bemc\b"
        r"|\bfrente \d+|\bfrentes? (guerriller|disidente|de las farc|del eln)",
}


# Tokens de premisa que el NLI ve con la hipotesis mas larga del experimento
# (512 - 3 especiales - tokens de esa hipotesis). Lo fija premisa_visible().
MAX_LENGTH = 512


def premisa_visible(textos, tokenizer, hipotesis) -> list:
    """Cuerpo truncado a lo que el NLI ve junto a la hipotesis mas larga. Es la
    premisa del juez y la de la compuerta F5."""
    n_hip = max(len(tokenizer(h, add_special_tokens=False)["input_ids"]) for h in hipotesis)
    n = MAX_LENGTH - 3 - n_hip
    out = []
    for t in textos:
        ids = tokenizer(str(t), add_special_tokens=False)["input_ids"][:n]
        out.append(tokenizer.decode(ids, skip_special_tokens=True))
    return out


def normalizar(txt: str) -> str:
    return unicodedata.normalize("NFKD", str(txt).lower()).encode("ascii", "ignore").decode("ascii")


def compuerta(textos, indicador: str):
    pat = re.compile(REGEX_F5[indicador])
    return [1.0 if pat.search(normalizar(t)) else 0.0 for t in textos]


def hipotesis_unicas() -> dict:
    """{clave_columna: texto} sin duplicados de texto (A1 de grupos armados = vig)."""
    out, vistos = {}, {}
    for ind, d in HIPOTESIS.items():
        for k, h in d.items():
            col = f"{ind}__{k}"
            if h in vistos:
                continue
            vistos[h] = col
            out[col] = h
    out["ABSURDO_TOTAL"] = ABSURDO_TOTAL
    for i, h in enumerate(NULAS_CALIBRACION):
        out[f"NULA_CAL_{i}"] = h
    return out


def columna(ind: str, clave: str) -> str:
    """Nombre de columna en el pkl de scores para (indicador, clave), resolviendo duplicados."""
    h = HIPOTESIS[ind][clave]
    for col, txt in hipotesis_unicas().items():
        if txt == h:
            return col
    raise KeyError((ind, clave))
