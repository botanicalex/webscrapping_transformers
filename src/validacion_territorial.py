"""
Validacion territorial (FILTRO 1) — 100% local, sin llamadas de red.

Reemplaza las consultas a DIVIPOLA (datos.gov.co) por lookups contra
`municipios_colombia.MUNICIPIOS_POR_DEPTO`, que ES el mismo dataset del DANE
(gdxc-w37w) ya congelado en el repo: 32 departamentos, 1121 municipios. La API
publica podia caerse y dejar la demo sin autocompletado ni validacion; la tabla
local no.

Que hace este filtro: antes de scrapear nada, verifica que el texto escrito
corresponda a un territorio real del departamento elegido. Si no corresponde,
la peticion se corta aqui — no se scrapea y no se corre el modelo NLI.

Que NO hace: no verifica que los articulos scrapeados hablen de ese territorio
(eso es el problema de Amazonas: el departamento existe y las noticias son
sociales, pero hablan del rio). Eso es un chequeo distinto, sobre el corpus.

Veredas y corregimientos: DIVIPOLA no los incluye (gdxc-w37w solo llega a
municipio), asi que un lugar sub-municipal NUNCA va a figurar en la tabla. Para
no romper el caso de uso central del proyecto (Paraguachon, y en general bajar
la escala), un lugar que no figura se rechaza con un mensaje explicito pero se
puede forzar con `forzar=True` (boton "No, buscar igual" del front). Cuando se
fuerza, el resultado queda marcado con `exige_cobertura=True` para que la capa
de arriba aplique un piso minimo de articulos.

Sin dependencias externas: solo stdlib + municipios_colombia.
"""
import unicodedata
from dataclasses import dataclass, field
from difflib import get_close_matches
from typing import Dict, List, Optional, Tuple

from municipios_colombia import MUNICIPIOS_POR_DEPTO

# Prefijos que el usuario puede escribir y que no son parte del nombre.
PREFIJOS = ("municipio ", "vereda ", "corregimiento ", "ciudad ", "depto ",
            "departamento ")

# Umbral de similitud para "quisiste decir". 0.6 es el que ya usaba api.py.
CUTOFF_SUGERENCIAS = 0.6
MAX_SUGERENCIAS = 3


def norm(txt: str) -> str:
    """Minusculas, sin tildes, espacios colapsados. Unica forma de comparar."""
    t = unicodedata.normalize("NFD", str(txt).lower())
    t = t.encode("ascii", "ignore").decode("ascii")
    return " ".join(t.split()).strip()


def limpiar_termino(territorio: str) -> str:
    """Quita prefijos tipo 'Municipio ' / 'Vereda ' del texto escrito."""
    t = str(territorio).strip()
    bajo = t.lower()
    for prefijo in PREFIJOS:
        if bajo.startswith(prefijo):
            return t[len(prefijo):].strip()
    return t


# ── Indices construidos una sola vez al importar ─────────────────────────────
# norm(departamento) -> nombre oficial
_IDX_DEPTOS: Dict[str, str] = {norm(d): d for d in MUNICIPIOS_POR_DEPTO}

# norm(municipio) -> [(nombre oficial, departamento oficial), ...]
# Es una lista porque hay homonimos reales: "Albania" existe en La Guajira y en
# Caqueta; "Villanueva" en cuatro departamentos. DIVIPOLA con $limit=1 devolvia
# uno arbitrario — aqui la ambiguedad se hace explicita.
_IDX_MUNICIPIOS: Dict[str, List[Tuple[str, str]]] = {}
for _dpto, _municipios in MUNICIPIOS_POR_DEPTO.items():
    for _m in _municipios:
        _IDX_MUNICIPIOS.setdefault(norm(_m), []).append((_m, _dpto))

# norm(municipio) -> nombre oficial (para presentar; el primero alcanza porque
# los homonimos comparten la grafia).
_NOMBRE_MUNICIPIO: Dict[str, str] = {
    k: v[0][0] for k, v in _IDX_MUNICIPIOS.items()
}

TOTAL_DEPARTAMENTOS = len(_IDX_DEPTOS)
TOTAL_MUNICIPIOS = sum(len(v) for v in MUNICIPIOS_POR_DEPTO.values())


# ── Consultas basicas ────────────────────────────────────────────────────────
def departamento_oficial(texto: str) -> Optional[str]:
    """Nombre oficial del departamento si el texto es uno, si no None."""
    if not texto:
        return None
    return _IDX_DEPTOS.get(norm(texto))


def municipios_del_departamento(departamento: str) -> List[str]:
    """Municipios del departamento (nombres oficiales), o [] si no existe."""
    oficial = departamento_oficial(departamento)
    return list(MUNICIPIOS_POR_DEPTO[oficial]) if oficial else []


def departamentos_de_municipio(municipio: str) -> List[str]:
    """Departamentos donde existe ese municipio. Vacio si no existe; mas de uno
    si es homonimo."""
    return [d for _, d in _IDX_MUNICIPIOS.get(norm(municipio), [])]


def es_municipio_de(municipio: str, departamento: str) -> bool:
    oficial = departamento_oficial(departamento)
    if not oficial:
        return False
    return oficial in departamentos_de_municipio(municipio)


def _cercanos(objetivo: str, candidatos: List[str]) -> List[str]:
    """'Quisiste decir' sobre nombres normalizados, devolviendo los oficiales."""
    mapa = {norm(c): c for c in candidatos}
    claves = get_close_matches(norm(objetivo), list(mapa),
                               n=MAX_SUGERENCIAS, cutoff=CUTOFF_SUGERENCIAS)
    return [mapa[k] for k in claves]


# ── Resultado de la validacion ───────────────────────────────────────────────
@dataclass
class ResultadoValidacion:
    """tipo: 'departamento' | 'municipio' | 'sublugar' | 'invalido'

    - valido=True  -> seguir (scrapear y, si pasa el filtro tematico, NLI)
    - valido=False -> cortar. `sugerencias` no vacio => pantalla "quisiste decir".
    - exige_cobertura=True -> es un lugar forzado (vereda/corregimiento): la capa
      de arriba debe exigir un minimo de articulos antes de puntuar.
    - forzable=True -> el rechazo se puede saltar con forzar=True porque el
      territorio NO figura en la tabla (posible vereda/corregimiento). Es False
      cuando el texto esta vacio o cuando existe pero en OTRO departamento: ahi
      forzar scrapearia prensa equivocada, el usuario debe corregir el dropdown.
    """
    valido: bool
    tipo: str
    termino: str                      # texto ya limpio, el que se manda a scrapear
    nombre_oficial: Optional[str] = None
    departamento: Optional[str] = None
    sugerencias: List[str] = field(default_factory=list)
    mensaje: str = ""
    exige_cobertura: bool = False
    forzable: bool = False


def validar_territorio(territorio: str,
                       departamento_hint: Optional[str] = None,
                       forzar: bool = False) -> ResultadoValidacion:
    """FILTRO 1. Decide si `territorio` es un territorio real y, cuando hay
    `departamento_hint`, si pertenece a ESE departamento.

    Orden de decision:
      1. es el nombre de un departamento            -> valido
      2. hay hint y es municipio de ese depto       -> valido
      3. hay hint y se parece a uno de sus municipios -> sugerencias
      4. hay hint y es municipio de OTRO depto      -> invalido, se dice cual
      5. no figura                                  -> invalido (o sublugar si forzar)
      6. sin hint: se resuelve por municipio (si es unico)
    """
    termino = limpiar_termino(territorio)
    if not termino:
        return ResultadoValidacion(
            valido=False, tipo="invalido", termino="",
            mensaje="Escribe un territorio para analizar.",
        )

    hint_oficial = departamento_oficial(departamento_hint) if departamento_hint else None

    # 1. El texto es un departamento.
    depto_directo = departamento_oficial(termino)
    if depto_directo:
        return ResultadoValidacion(
            valido=True, tipo="departamento", termino=depto_directo,
            nombre_oficial=depto_directo, departamento=depto_directo,
        )

    deptos_del_termino = departamentos_de_municipio(termino)

    if hint_oficial:
        # 2. Municipio del departamento elegido: el caso bueno.
        if hint_oficial in deptos_del_termino:
            return ResultadoValidacion(
                valido=True, tipo="municipio",
                termino=_NOMBRE_MUNICIPIO[norm(termino)],
                nombre_oficial=_NOMBRE_MUNICIPIO[norm(termino)],
                departamento=hint_oficial,
            )

        # 3. Se parece a un municipio del departamento elegido.
        sugerencias = _cercanos(termino, MUNICIPIOS_POR_DEPTO[hint_oficial])
        if sugerencias and not forzar:
            return ResultadoValidacion(
                valido=False, tipo="invalido", termino=termino,
                departamento=hint_oficial, sugerencias=sugerencias,
                mensaje="¿Quisiste decir alguno de estos?",
            )

        # 4. Existe, pero en otro departamento. Rechazo NO forzable: forzar aqui
        #    scrapearia la prensa del departamento equivocado. Se ignora forzar y
        #    se devuelve el 422 igual (el usuario debe corregir el dropdown).
        if deptos_del_termino:
            otros = ", ".join(deptos_del_termino)
            return ResultadoValidacion(
                valido=False, tipo="invalido", termino=termino,
                departamento=hint_oficial,
                mensaje=(f"'{termino}' no es un territorio de {hint_oficial}. "
                         f"Figura en: {otros}."),
            )

        # 5. No figura en la tabla del DANE.
        if forzar:
            return ResultadoValidacion(
                valido=True, tipo="sublugar", termino=termino,
                nombre_oficial=termino, departamento=hint_oficial,
                exige_cobertura=True,
                mensaje=("Lugar no oficial (posible vereda o corregimiento): "
                         "se exige cobertura minima de prensa."),
            )
        return ResultadoValidacion(
            valido=False, tipo="invalido", termino=termino,
            departamento=hint_oficial, forzable=True,
            mensaje=(f"'{termino}' no figura como municipio de {hint_oficial} "
                     f"en la division oficial del DANE, que solo llega a nivel "
                     f"municipal. Puede ser una vereda o un corregimiento."),
        )

    # ── Sin departamento indicado ────────────────────────────────────────────
    # 6a. Municipio unico: se infiere el departamento.
    if len(deptos_del_termino) == 1:
        return ResultadoValidacion(
            valido=True, tipo="municipio",
            termino=_NOMBRE_MUNICIPIO[norm(termino)],
            nombre_oficial=_NOMBRE_MUNICIPIO[norm(termino)],
            departamento=deptos_del_termino[0],
        )

    # 6b. Homonimo: hace falta que el usuario elija el departamento.
    if len(deptos_del_termino) > 1:
        nombre = _NOMBRE_MUNICIPIO[norm(termino)]
        return ResultadoValidacion(
            valido=False, tipo="invalido", termino=termino,
            sugerencias=[f"{nombre} ({d})" for d in deptos_del_termino],
            mensaje=(f"'{nombre}' existe en varios departamentos. "
                     f"Indica cual."),
        )

    # 6c. No figura en ningun lado.
    if forzar:
        return ResultadoValidacion(
            valido=True, tipo="sublugar", termino=termino,
            nombre_oficial=termino, exige_cobertura=True,
            mensaje=("Lugar no oficial (posible vereda o corregimiento): "
                     "se exige cobertura minima de prensa."),
        )

    candidatos = list(_NOMBRE_MUNICIPIO.values()) + list(MUNICIPIOS_POR_DEPTO)
    sugerencias = _cercanos(termino, candidatos)
    if sugerencias:
        return ResultadoValidacion(
            valido=False, tipo="invalido", termino=termino,
            sugerencias=sugerencias,
            mensaje="¿Quisiste decir alguno de estos?",
        )
    return ResultadoValidacion(
        valido=False, tipo="invalido", termino=termino, forzable=True,
        mensaje=(f"'{termino}' no figura en la division territorial oficial "
                 f"del DANE (32 departamentos, {TOTAL_MUNICIPIOS} municipios)."),
    )


# ── Autocompletado local (reemplazo de /lugares contra DIVIPOLA) ─────────────
def autocompletar(q: str, limite: int = 10) -> List[dict]:
    """Sugerencias para el campo Territorio. Mismo formato que devolvia la
    version DIVIPOLA: {nombre, tipo, departamento}. Los departamentos van
    primero. `tipo` es siempre 'Municipio' o 'Departamento' (la tabla local no
    guarda 'Area no municipalizada', que era lo unico que aportaba
    tipo_municipio)."""
    q_norm = norm(q)
    if not q_norm:
        return []

    sugerencias: List[dict] = []

    # Departamentos cuyo nombre contiene el texto.
    for clave, oficial in _IDX_DEPTOS.items():
        if q_norm in clave:
            sugerencias.append({
                "nombre": oficial,
                "tipo": "Departamento",
                "departamento": oficial,
            })

    # Municipios cuyo nombre contiene el texto (una entrada por departamento,
    # para que los homonimos se puedan distinguir en el desplegable).
    municipios: List[dict] = []
    for clave, pares in _IDX_MUNICIPIOS.items():
        if q_norm in clave:
            for nombre, dpto in pares:
                municipios.append({
                    "nombre": nombre,
                    "tipo": "Municipio",
                    "departamento": dpto,
                })

    # Los que empiezan por el texto valen mas que los que solo lo contienen
    # ("anti" -> Antioquia antes que Atlantico, que tambien lo contiene).
    orden = lambda s: (not norm(s["nombre"]).startswith(q_norm),
                       s["nombre"], s["departamento"])
    municipios.sort(key=orden)
    sugerencias.sort(key=orden)

    return (sugerencias + municipios)[:limite]
