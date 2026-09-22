"""Los validadores mecánicos de la puerta G1a (RF-CAL-01 a RF-CAL-07, RF-CAL-12).

**Mecánicos en el contraste, no en la extracción** (`verification.md` §6.2). Lo
que la prosa afirma lo extrae el Continuista, que es un modelo y por tanto una
señal con varianza; lo que estas funciones hacen es contrastar esas afirmaciones
contra el grafo, el estado y el esquema, y eso sí es determinista.

La consecuencia hay que tenerla presente al leer esto: **una afirmación que el
Continuista no extraiga no llega nunca al contraste que la habría rechazado.**
Los falsos negativos siguen sin medirse (`verification.md` §6.3).

Cada función recibe datos explícitos y no toca la base: se prueban sin montarla,
y eso es lo que permite tener un caso por regla en vez de un caso por capa.
"""

import re

from pydantic import BaseModel, ConfigDict

from app.features.calidad.defectos import CodigoDeDefecto, Defecto, citar


class Afirmacion(BaseModel):
    """Lo que el Continuista dice que la prosa afirma, con su pasaje."""

    model_config = ConfigDict(frozen=True)

    cita: str
    sujeto: str = ""
    objeto: str = ""
    atributo: str = ""
    valor: str = ""
    lugar: str = ""
    momento: int = 0


# --- RF-CAL-01: la ficha declara giro de valor (EST-01) ----------------------


def validar_giro_de_valor(
    valor_entrada: str, valor_salida: str, texto: str, version_texto_id: str
) -> list[Defecto]:
    """Se valida la **ficha**, no que la prosa entregue el giro.

    Que el giro esté *entregado* es juicio, y el juicio es G1b. Confundirlos
    haría que este validador rechazara escenas correctas por no saber leerlas.
    """
    if valor_entrada and valor_salida and valor_entrada != valor_salida:
        return []
    return [
        citar(
            texto,
            texto[:40].strip() or texto,
            CodigoDeDefecto.EST_01,
            version_texto_id,
            detalle=f"la escena entra y sale en '{valor_entrada}'",
        )
    ]


# --- RF-CAL-02: nivel de calor por lista de términos (SEG-01) ----------------

# D-05. Lexica y conservadora a proposito: no entiende el texto -eso es juicio-,
# cierra el camino facil. La parte que falta es la **I** que firma una persona
# (D-09). Las listas son acumulativas: lo prohibido en `sensual` lo esta tambien
# en `puerta_cerrada`.
TERMINOS_POR_ENCIMA: dict[str, tuple[str, ...]] = {
    "puerta_cerrada": ("desnud", "gemi", "jadea", "caricia intima"),
    "sensual": ("penetr", "orgasm", "embesti"),
    "abierto": (),
    "explicito": (),
}
_ESCALA = ("puerta_cerrada", "sensual", "abierto", "explicito")


def _vetados(nivel: str) -> tuple[str, ...]:
    if nivel not in _ESCALA:
        return ()
    hasta = _ESCALA.index(nivel)
    return tuple(t for n in _ESCALA[hasta:] for t in TERMINOS_POR_ENCIMA[n])


def validar_nivel_de_calor(
    texto: str, nivel_declarado: str, version_texto_id: str
) -> list[Defecto]:
    """RG-10. Se rechaza aunque el texto sea bueno: el nivel es una promesa al
    lector y se incumple en las dos direcciones (`domain-knowledge.md` §8.5)."""
    bajo = texto.lower()
    for termino in _vetados(nivel_declarado):
        posicion = bajo.find(termino)
        if posicion >= 0:
            return [
                citar(
                    texto,
                    texto[posicion : posicion + len(termino)],
                    CodigoDeDefecto.SEG_01,
                    version_texto_id,
                    detalle=(
                        f"termino por encima del nivel declarado '{nivel_declarado}'"
                    ),
                )
            ]
    return []


# --- RF-CAL-04: continuidad física y temporal (CON-01) ----------------------


def validar_continuidad_fisica(
    afirmaciones: list[Afirmacion],
    tiempos_de_viaje: dict[tuple[str, str], int],
    texto: str,
    version_texto_id: str,
) -> list[Defecto]:
    """RG-04. Dos casos: estar en dos sitios a la vez, o llegar antes de lo que
    permite el `tiempo_de_viaje` declarado en la biblia (RF-OBR-02)."""
    defectos: list[Defecto] = []
    por_sujeto: dict[str, list[Afirmacion]] = {}
    for a in afirmaciones:
        if a.sujeto and a.lugar:
            por_sujeto.setdefault(a.sujeto, []).append(a)

    for sujeto, apariciones in por_sujeto.items():
        apariciones.sort(key=lambda a: a.momento)
        for previa, siguiente in zip(apariciones, apariciones[1:], strict=False):
            if previa.lugar == siguiente.lugar:
                continue
            transcurrido = siguiente.momento - previa.momento
            necesario = tiempos_de_viaje.get((previa.lugar, siguiente.lugar))
            if transcurrido == 0:
                detalle = (
                    f"{sujeto} esta en {previa.lugar} y {siguiente.lugar} a la vez"
                )
            elif necesario is not None and transcurrido < necesario:
                detalle = (
                    f"{sujeto} va de {previa.lugar} a {siguiente.lugar} en "
                    f"{transcurrido}, y el tiempo de viaje declarado es {necesario}"
                )
            else:
                continue
            defectos.append(
                citar(
                    texto,
                    siguiente.cita,
                    CodigoDeDefecto.CON_01,
                    version_texto_id,
                    detalle=detalle,
                )
            )
    return defectos


# --- RF-CAL-05: conocimiento sin `sabe_desde` anterior (CON-03) -------------


def validar_conocimiento(
    afirmaciones: list[Afirmacion],
    conocimientos: dict[str, list[str]],
    texto: str,
    version_texto_id: str,
) -> list[Defecto]:
    """RG-01. `conocimientos` viene del estado en T, derivado de `testigos[]`
    (RF-CAN-11): estar en una escena no es haberse enterado."""
    return [
        citar(
            texto,
            a.cita,
            CodigoDeDefecto.CON_03,
            version_texto_id,
            detalle=f"{a.sujeto} usa '{a.objeto}' sin sabe_desde anterior",
        )
        for a in afirmaciones
        if a.sujeto and a.objeto and a.objeto not in conocimientos.get(a.sujeto, [])
    ]


# --- RF-CAL-06: contradicción de canon (CAN-01) -----------------------------


class HechoDeCanon(BaseModel):
    model_config = ConfigDict(frozen=True)

    hc_id: str
    entidad: str
    atributo: str
    valor: str
    orden_discurso: int


def validar_canon(
    afirmaciones: list[Afirmacion],
    canon: list[HechoDeCanon],
    texto: str,
    version_texto_id: str,
) -> list[Defecto]:
    """RG-03. Arbitraje por `orden_discurso`: **prevalece el hecho de menor
    orden** y el otro es el defecto. Lo escrito antes gana, porque el lector ya
    lo leyó y no se le puede desmentir sin pagarlo."""
    por_clave: dict[tuple[str, str], HechoDeCanon] = {}
    for hecho in sorted(canon, key=lambda h: h.orden_discurso):
        por_clave.setdefault((hecho.entidad, hecho.atributo), hecho)

    defectos = []
    for a in afirmaciones:
        if not (a.sujeto and a.atributo and a.valor):
            continue
        establecido = por_clave.get((a.sujeto, a.atributo))
        if establecido and establecido.valor != a.valor:
            defectos.append(
                citar(
                    texto,
                    a.cita,
                    CodigoDeDefecto.CAN_01,
                    version_texto_id,
                    hecho_canon_id=establecido.hc_id,
                    detalle=(
                        f"{a.sujeto}.{a.atributo} es '{establecido.valor}' desde la "
                        f"escena de orden {establecido.orden_discurso}, no '{a.valor}'"
                    ),
                )
            )
    return defectos


# --- RF-CAL-07: objeto no disponible (CON-02) -------------------------------

INDISPONIBLES = frozenset({"perdido", "roto", "destruido"})


def validar_objetos(
    afirmaciones: list[Afirmacion],
    estado_de_objetos: dict[str, str],
    texto: str,
    version_texto_id: str,
) -> list[Defecto]:
    """RG-05."""
    return [
        citar(
            texto,
            a.cita,
            CodigoDeDefecto.CON_02,
            version_texto_id,
            detalle=f"'{a.objeto}' esta {estado_de_objetos[a.objeto]}",
        )
        for a in afirmaciones
        if a.objeto and estado_de_objetos.get(a.objeto) in INDISPONIBLES
    ]


# --- RF-CAL-12: persona y tiempo verbal declarados (VOZ-03) -----------------

# El dialogo se excluye: un personaje puede hablar en primera dentro de una
# narracion en tercera, y medir sobre el entero daria falsos positivos en casi
# toda escena dialogada.
_DIALOGO = re.compile(r"(«[^»]*»|\"[^\"]*\"|—[^\n]*)")

_MARCAS_DE_PERSONA = {
    "primera": re.compile(r"\b(yo|me|mi|mis|conmigo)\b", re.IGNORECASE),
    "tercera": re.compile(r"\b(el|ella|le|lo|la|su|sus)\b", re.IGNORECASE),
}
_MARCAS_DE_TIEMPO = {
    "pasado": re.compile(r"\w+(?:ó|aba|ía|aron|ieron|abas)\b", re.IGNORECASE),
    "presente": re.compile(r"\w+(?:a|e|an|en)\b"),
}


def solo_narracion(texto: str) -> str:
    """Quita el diálogo. Es la mitad del valor de VOZ-03."""
    return _DIALOGO.sub(" ", texto)


def validar_discurso(
    texto: str, persona: str, tiempo_verbal: str, version_texto_id: str
) -> list[Defecto]:
    """RG-13 y axioma 13. Cierra una restricción dura que hasta ahora sostenía
    solo el prompt, pese a que `CLAUDE.md` §10 lo prohíbe."""
    narracion = solo_narracion(texto)
    defectos = []

    contraria = "primera" if persona == "tercera" else "tercera"
    patron = _MARCAS_DE_PERSONA.get(contraria)
    if patron is not None:
        encontrada = patron.search(narracion)
        if encontrada and not _MARCAS_DE_PERSONA[persona].search(narracion):
            defectos.append(
                citar(
                    texto,
                    encontrada.group(0),
                    CodigoDeDefecto.VOZ_03,
                    version_texto_id,
                    detalle=(
                        f"la narracion usa {contraria} persona y la obra declara "
                        f"{persona}"
                    ),
                )
            )

    esperado = _MARCAS_DE_TIEMPO.get(tiempo_verbal)
    if esperado is not None and narracion.strip() and not esperado.search(narracion):
        defectos.append(
            citar(
                texto,
                narracion.split()[0],
                CodigoDeDefecto.VOZ_03,
                version_texto_id,
                detalle=(
                    f"no se detecta tiempo verbal '{tiempo_verbal}' en la narracion"
                ),
            )
        )
    return defectos
