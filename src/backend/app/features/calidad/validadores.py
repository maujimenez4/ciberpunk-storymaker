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
import unicodedata

from pydantic import BaseModel, ConfigDict

from app.commons.errors import EntradaFueraDeDominio
from app.features.calidad.defectos import (
    CodigoDeDefecto,
    Defecto,
    citar,
    citar_del_modelo,
)


class Afirmacion(BaseModel):
    """Lo que el Continuista dice que la prosa afirma, con su pasaje."""

    model_config = ConfigDict(frozen=True)

    cita: str
    sujeto: str = ""
    # `objeto` es una cosa fisica y solo alimenta CON-02. `informacion` es lo
    # que un personaje sabe o usa, y solo alimenta CON-03. Eran el mismo campo,
    # y por eso una carpeta se contrastaba contra la lista de lo que alguien
    # sabe y nunca estaba ahi (RF-CAL-16).
    objeto: str = ""
    informacion: str = ""
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
    # RF-CAL-14: total sobre `texto`. Con prosa vacia -un modo de fallo
    # corriente del modelo- `texto[:40].strip() or texto` daba cadena vacia y
    # `Defecto` reventaba con un `ValidationError` de Pydantic, que el
    # orquestador no distingue de un fallo tecnico. El defecto de la ficha
    # existe igual, pero sin texto no hay pasaje que citar y el axioma 11 exige
    # que la cita ancle: se dice en voz alta.
    if not texto.strip():
        raise EntradaFueraDeDominio(
            "texto", texto, "prosa no vacia: sin texto la cita no puede anclar"
        )
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
        # RF-CAL-13. Devolver `()` aqui era devolver «nada prohibido»: una
        # errata en el `nivel_de_calor` de la obra apagaba el guardarrail de la
        # regla 5 de §8 **en silencio**, que es la peor forma de fallar de un
        # validador de seguridad.
        raise EntradaFueraDeDominio("nivel_declarado", nivel, f"uno de {_ESCALA}")
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

    for sujeto in sorted(por_sujeto):
        apariciones = por_sujeto[sujeto]
        # RF-CAL-15: con dos afirmaciones en el mismo `momento`, ordenar solo
        # por `momento` dejaba el par en el orden en que el Continuista las
        # listo, y el `detalle` -que viaja al prompt de reparacion- decia
        # «taller y puerto» o «puerto y taller» segun el dia.
        apariciones.sort(key=lambda a: (a.momento, a.lugar, a.cita))
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
            defecto = citar_del_modelo(
                texto,
                siguiente.cita,
                CodigoDeDefecto.CON_01,
                version_texto_id,
                detalle=detalle,
            )
            if defecto is not None:
                defectos.append(defecto)
    return defectos


# --- RF-CAL-05: conocimiento sin `sabe_desde` anterior (CON-03) -------------


def _sin_tildes(texto: str) -> list[str]:
    """Palabras en minuscula y sin tildes: es lo que se compara."""
    plano = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in plano if unicodedata.category(c) != "Mn").split()


def _ya_lo_sabia(informacion: str, conocidas: list[str]) -> bool:
    """RF-CAL-16. Inclusion normalizada, no igualdad exacta.

    Lo que hay a cada lado lo escriben **dos llamadas independientes** al
    modelo: `conocidas` sale de `evento.descripcion`, que redacto el Extractor,
    y `informacion` la redacta el Continuista. Exigir que coincidan palabra por
    palabra convertia en CON-03 cualquier sinonimo, y CON-03 bloqueaba: cada
    falso positivo era una escena escalada por una contradiccion inexistente.

    Sigue siendo mecanico y determinista -no entiende el texto, mira si una
    frase esta contenida en la otra-, asi que no elimina el falso positivo, lo
    baja. Lo que lo cerraria es que el contraste dejara de ser lexico, y esa
    decision necesita la tasa medida sobre una corrida real.
    """
    buscada = _sin_tildes(informacion)
    if not buscada:
        return True
    for conocida in conocidas:
        sabida = _sin_tildes(conocida)
        if _contiene(sabida, buscada) or _contiene(buscada, sabida):
            return True
    return False


def _contiene(largo: list[str], corto: list[str]) -> bool:
    if not corto or len(corto) > len(largo):
        return False
    return any(
        largo[i : i + len(corto)] == corto for i in range(len(largo) - len(corto) + 1)
    )


def validar_conocimiento(
    afirmaciones: list[Afirmacion],
    conocimientos: dict[str, list[str]],
    texto: str,
    version_texto_id: str,
) -> list[Defecto]:
    """RG-01. `conocimientos` viene del estado en T, derivado de `testigos[]`
    (RF-CAN-11): estar en una escena no es haberse enterado.

    Contrasta `informacion`, **no** `objeto` (RF-CAL-16): una carpeta es una
    cosa que se usa, no algo que se sepa, y contrastarla contra la lista de lo
    que un personaje sabe daba CON-03 en toda escena con un objeto dentro.
    """
    defectos = [
        citar_del_modelo(
            texto,
            a.cita,
            CodigoDeDefecto.CON_03,
            version_texto_id,
            detalle=f"{a.sujeto} usa '{a.informacion}' sin sabe_desde anterior",
        )
        for a in afirmaciones
        if a.sujeto
        and a.informacion
        and not _ya_lo_sabia(a.informacion, conocimientos.get(a.sujeto, []))
    ]
    return [d for d in defectos if d is not None]


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
    # RF-CAL-15. `sorted` es estable, asi que con dos hechos del mismo
    # `orden_discurso` ganaba el que viniera antes en la lista y el
    # `hecho_canon_id` del defecto cambiaba con el orden de entrada. Es
    # justo el campo que el axioma 12 exige, y CLAUDE.md §3 punto 6 pide que
    # una ejecucion se pueda reproducir: el `hc_id` desempata.
    for hecho in sorted(canon, key=lambda h: (h.orden_discurso, h.hc_id, h.valor)):
        por_clave.setdefault((hecho.entidad, hecho.atributo), hecho)

    defectos = []
    for a in afirmaciones:
        if not (a.sujeto and a.atributo and a.valor):
            continue
        establecido = por_clave.get((a.sujeto, a.atributo))
        if establecido and establecido.valor != a.valor:
            defecto = citar_del_modelo(
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
            if defecto is not None:
                defectos.append(defecto)
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
    defectos = [
        citar_del_modelo(
            texto,
            a.cita,
            CodigoDeDefecto.CON_02,
            version_texto_id,
            detalle=f"'{a.objeto}' esta {estado_de_objetos[a.objeto]}",
        )
        for a in afirmaciones
        if a.objeto and estado_de_objetos.get(a.objeto) in INDISPONIBLES
    ]
    return [d for d in defectos if d is not None]


# --- RF-CAL-12: persona y tiempo verbal declarados (VOZ-03) -----------------

# El dialogo se excluye: un personaje puede hablar en primera dentro de una
# narracion en tercera, y medir sobre el entero daria falsos positivos en casi
# toda escena dialogada.
_ENTRECOMILLADO = re.compile(r"(«[^»]*»|\"[^\"]*\")")

# Las marcas tienen que ser **inequivocas**. «el», «lo» y «la» son articulos
# antes que marca de tercera persona: con ellas dentro, cualquier narracion en
# primera quedaba tapada por un «la puerta».
_MARCAS_DE_PERSONA = {
    "primera": re.compile(
        r"\b(yo|me|mi|mis|conmigo|nosotros|nuestro|nuestra)\b", re.IGNORECASE
    ),
    "tercera": re.compile(
        r"\b(él|ella|ellos|ellas|su|sus|consigo|le|les)\b", re.IGNORECASE
    ),
}
_MARCAS_DE_TIEMPO = {
    "pasado": re.compile(r"\w+(?:ó|aba|ía|aron|ieron|abas)\b", re.IGNORECASE),
    "presente": re.compile(r"\w+(?:a|e|an|en)\b"),
}


def solo_narracion(texto: str) -> str:
    """Quita el diálogo. Es la mitad del valor de VOZ-03.

    **En español la raya no encierra el diálogo: lo abre, y el inciso del
    narrador vuelve a abrirlo.** El patrón anterior se comía desde la primera
    raya hasta el fin de línea, así que en

        —Yo no fui —dijo ella. Yo caminé hasta la puerta.

    la narración que quedaba era `' '`. VOZ-03 llevaba ciego desde que existe, y
    en romance el diálogo es casi toda la escena: la regla 10 de §8 la sostenía
    solo el prompt, que es justo lo que `CLAUDE.md` §10 prohíbe.

    Los segmentos **alternan**: lo que va tras la primera raya es réplica, tras
    la segunda es inciso del narrador —y por tanto narración—, tras la tercera
    vuelve a ser réplica.
    """
    narracion = []
    for linea in _ENTRECOMILLADO.sub(" ", texto).splitlines():
        # El índice par es narración: 0 es lo anterior a la primera raya.
        narracion += linea.split("—")[::2]
    return " ".join(narracion)


def validar_discurso(
    texto: str, persona: str, tiempo_verbal: str, version_texto_id: str
) -> list[Defecto]:
    """RG-13 y axioma 13. Cierra una restricción dura que hasta ahora sostenía
    solo el prompt, pese a que `CLAUDE.md` §10 lo prohíbe."""
    # RF-CAL-13, H-7. Las dos comprobaciones se saltaban en silencio ante una
    # `persona` o un `tiempo_verbal` que no conocian: `.get()` devolvia `None`,
    # la rama no entraba y la puerta leia `[]` como «limpio». Una errata de
    # mayusculas en la obra -«PASADO»- apagaba media regla 10 de §8 sin ruido,
    # y `_MARCAS_DE_PERSONA[persona]` subia un `KeyError` pelado. Es el mismo
    # fallo en abierto de `validar_nivel_de_calor`, en la funcion de al lado:
    # lo que se comprueba es cada validador, no la lista de los que ya se
    # miraron.
    if persona not in _MARCAS_DE_PERSONA:
        raise EntradaFueraDeDominio(
            "persona", persona, f"uno de {tuple(_MARCAS_DE_PERSONA)}"
        )
    if tiempo_verbal not in _MARCAS_DE_TIEMPO:
        raise EntradaFueraDeDominio(
            "tiempo_verbal", tiempo_verbal, f"uno de {tuple(_MARCAS_DE_TIEMPO)}"
        )

    narracion = solo_narracion(texto)
    defectos = []

    contraria = "primera" if persona == "tercera" else "tercera"
    patron = _MARCAS_DE_PERSONA.get(contraria)
    if patron is not None:
        encontrada = patron.search(narracion)
        # Domina la contraria, no «aparece la contraria y no aparece la
        # declarada»: con la condicion vieja bastaba un «ella» suelto en el
        # inciso para tapar una narracion entera en primera persona.
        propias = len(_MARCAS_DE_PERSONA[persona].findall(narracion))
        contrarias = len(patron.findall(narracion))
        if encontrada and contrarias > propias:
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
