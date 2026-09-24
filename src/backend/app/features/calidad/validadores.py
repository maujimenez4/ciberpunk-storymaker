"""Los tres validadores mecanicos del capitulo. **Ninguno llama a un modelo.**

Son los de `verification.md` §8.1 que funcionan sobre **un capitulo solo**:
`extension_de_capitulo`, `nombres_literales` y `discurso`. El Continuista
—`continuidad_y_canon`, puerta G1a— y el Critico —`juez_con_rubrica`, G1b— no
estan aqui y no es un olvido: el primero contrasta contra el grafo y un capitulo
suelto no tiene contra que chocar; el segundo **no bloquea** hasta que su
correlacion con la revision humana este medida y firmada (RF-JUZ-06). Construir
hoy un componente que por regla no puede parar nada seria peor que declararlo
pendiente. Decision **P-B** del plan de la Fase 2.

**Cada validador tiene nombre y punto de ejecucion declarado** (RF-VAL-01), y el
nombre es el de `verification.md` §8.1: la spec cita ese catalogo y no lo
duplica, asi que renombrar uno aqui rompe el enlace entre el documento y el
codigo sin que falle nada. El test `test_cada_validador_...` guarda los tres.

**Y todos producen defectos con la forma que `defectos.py` exige**: codigo de la
taxonomia, cita que es subcadena exacta en su desplazamiento. No es cortesia: un
validador propio que emitiera un defecto mal formado veria su hallazgo
descartado por la comprobacion de forma y el capitulo pasaria la puerta. Hay un
test que lo comprueba sobre los tres a la vez.
"""

import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.commons.domain.normalizacion import normalizar
from app.features.calidad.cobertura import (
    Cobertura,
    ElementoAusente,
    ElementoCubierto,
    HechoUsado,
    cobertura_de_obligatorios,
)
from app.features.calidad.schemas import (
    Defecto,
    NombreDeCanon,
    ParametrosDeDiscurso,
    Persona,
    RangoDeExtension,
    TiempoVerbal,
)

_PALABRA = re.compile(r"\w+", re.UNICODE)
_RAYAS_DE_DIALOGO = ("—", "–")  # raya y semirraya
_COMILLAS = (("«", "»"), ('"', '"'), ("“", "”"))


class PuntoDeEjecucion(StrEnum):
    """Donde corre un validador (`verification.md` §8.1). Sin esto, «cada
    validador corre en un punto concreto» es un deseo y no una afirmacion
    comprobable.

    **`PUERTA_G4` entra en la Fase 3 y no es un punto inventado:** es el que
    `verification.md` §8.1 declara para `cobertura_de_personalizacion` —«En la
    publicacion, puerta G4»—. Existe aqui antes que la publicacion porque el
    validador que lo declara **ya se puede ejecutar**: la cobertura solo es
    comprobable con la novela entera, y la novela entera existe desde T9. Lo que
    la Fase 4 anadira es la puerta que bloquea, no el punto.
    """

    HOOK_DE_CAPITULO = "hook_de_capitulo"
    HOOK_DE_POLICY = "hook_de_policy"
    PUERTA_G4 = "puerta_g4"


@dataclass(frozen=True, slots=True)
class CapituloAValidar:
    """Todo lo que los tres validadores necesitan, y nada mas.

    Es una entrada **uniforme** a proposito: sin ella el catalogo no podria
    recorrerse, cada validador tendria su propia firma y `CATALOGO` seria una
    lista de nombres que nadie puede ejecutar en bucle.
    """

    version_texto_id: str
    texto: str
    rango_de_extension: RangoDeExtension
    discurso: ParametrosDeDiscurso
    nombres_del_canon: tuple[NombreDeCanon, ...]


@dataclass(frozen=True, slots=True)
class Validador:
    """Un validador con su nombre y su punto. Lo que no se puede nombrar no se
    puede contar (RF-VAL-01)."""

    nombre: str
    punto: PuntoDeEjecucion
    comprobar: Callable[[CapituloAValidar], list[Defecto]]


# --------------------------------------------------------------------------
# Narracion y dialogo
# --------------------------------------------------------------------------

MARCAS_DE_PRIMERA_PERSONA: frozenset[str] = frozenset(
    {
        "yo",
        "me",
        "mi",
        "mis",
        "mí",
        "conmigo",
        "nosotros",
        "nosotras",
        "nos",
        "nuestro",
        "nuestra",
        "nuestros",
        "nuestras",
    }
)
"""Pronombres y posesivos de primera persona. **Solo estos discriminan**: los de
tercera no, porque «su» y «le» aparecen igual en una novela en primera persona
cuando se habla de otro. Punto ciego que se declara y no se disimula: un pasaje
en primera persona **sin un solo pronombre** se lee como tercera."""

MARCAS_DE_PASADO: frozenset[str] = frozenset(
    {
        "era", "eran", "fue", "fueron", "fui", "estaba", "estaban", "había",
        "hubo", "tenía", "tenían", "iba", "iban", "hizo", "hicieron",
        "dijo", "dijeron", "sabía", "podía", "quería", "miró",
        "sintió", "cerró", "volvió", "llegó", "pensó",
        "respondió", "pareció",
    }
)  # fmt: skip

MARCAS_DE_PRESENTE: frozenset[str] = frozenset(
    {
        "es", "son", "está", "están", "estoy", "hay", "tiene", "tienen",
        "va", "van", "hace", "hacen", "dice", "dicen", "sabe", "saben", "puede",
        "pueden", "quiere", "quieren", "mira", "siente", "cierra", "vuelve",
        "llega", "piensa", "responde", "parece",
    }
)  # fmt: skip

_MARCAS_POR_TIEMPO = {
    TiempoVerbal.PASADO: MARCAS_DE_PASADO,
    TiempoVerbal.PRESENTE: MARCAS_DE_PRESENTE,
}
"""Copulas y auxiliares de altisima frecuencia, **acentuadas**, que es lo que las
hace poco ambiguas: «esta» sin tilde es un demostrativo y «cerro» sin tilde es
una colina, asi que ninguna de las dos entra. Lo que se compara no es la
presencia de una marca sino **cual de los dos tiempos domina la narracion**: una
forma suelta no condena un capitulo, y un capitulo entero en el tiempo
equivocado no se escapa."""


def segmentos_de_narracion(texto: str) -> list[tuple[int, int]]:
    """Los tramos que **no** son dialogo, en desplazamientos del texto original.

    `verification.md` §8.1 dice que `discurso` **excluye el dialogo a
    proposito**: un personaje habla en primera persona y en presente dentro de
    una novela en tercera y en pasado, y eso no es un defecto, es una novela.

    Dos reglas, las dos de la tipografia castellana (`definitions.md` §5,
    `EstandarTipografico`): una linea que empieza por raya es dialogo entera, y
    lo encerrado en comillas latinas o rectas tambien.

    **Punto ciego declarado:** el inciso del narrador dentro de una linea de
    dialogo —«—No —dijo ella, y **cerro la puerta**»— queda excluido con el
    resto de la linea. Separarlo pide distinguir la raya que abre el inciso de
    la que lo cierra, y eso es analisis de la linea, no de un caracter. Se
    prefiere **no mirar** a mirar mal: un falso positivo aqui devuelve al
    escritor un capitulo correcto.
    """
    if not texto:
        return []

    es_dialogo = bytearray(len(texto))

    desplazamiento = 0
    for linea in texto.splitlines(keepends=True):
        if linea.lstrip().startswith(_RAYAS_DE_DIALOGO):
            es_dialogo[desplazamiento : desplazamiento + len(linea)] = b"\x01" * len(linea)
        desplazamiento += len(linea)

    for abre, cierra in _COMILLAS:
        dentro = -1
        for i, caracter in enumerate(texto):
            if dentro < 0 and caracter == abre:
                dentro = i
            elif dentro >= 0 and caracter == cierra:
                es_dialogo[dentro : i + 1] = b"\x01" * (i + 1 - dentro)
                dentro = -1

    segmentos: list[tuple[int, int]] = []
    inicio: int | None = None
    for i in range(len(texto)):
        if not es_dialogo[i] and inicio is None:
            inicio = i
        elif es_dialogo[i] and inicio is not None:
            segmentos.append((inicio, i))
            inicio = None
    if inicio is not None:
        segmentos.append((inicio, len(texto)))
    return segmentos


def _palabras_de_la_narracion(texto: str) -> Iterator[tuple[str, int, int]]:
    """Cada palabra de la narracion con su desplazamiento **en el texto
    original**. Que los desplazamientos sean absolutos y no relativos al tramo
    es lo que permite que la cita del defecto pase su propia comprobacion."""
    for inicio, fin in segmentos_de_narracion(texto):
        for encontrada in _PALABRA.finditer(texto, inicio, fin):
            yield encontrada.group(0), encontrada.start(), encontrada.end()


def _defecto(capitulo: CapituloAValidar, codigo: str, inicio: int, fin: int) -> Defecto:
    """Construye el defecto tomando la cita **del texto**, nunca de memoria."""
    return Defecto(
        codigo=codigo,
        version_texto_id=capitulo.version_texto_id,
        cita=capitulo.texto[inicio:fin],
        desplazamiento_inicio=inicio,
        desplazamiento_fin=fin,
    )


# --------------------------------------------------------------------------
# Los tres validadores
# --------------------------------------------------------------------------


def extension_de_capitulo(capitulo: CapituloAValidar) -> list[Defecto]:
    """`EST-02`: el capitulo esta fuera del rango declarado (CA-35, RF-VAL-04).

    «Dentro del rango» **incluye los extremos**: un rango es «no menos de» y «no
    mas de», y una frontera mal puesta devuelve al escritor un capitulo que
    cumple sin que nadie entienda por que.

    La cita es el capitulo entero, y es la honesta: el defecto no esta en un
    pasaje, esta en el tamano del conjunto. Lo que no detecta —`verification.md`
    §8.1— es si lo que sobra o falta es lo correcto: un capitulo en rango puede
    ser todo relleno.
    """
    palabras = len(_PALABRA.findall(capitulo.texto))
    rango = capitulo.rango_de_extension
    if rango.minimo <= palabras <= rango.maximo:
        return []
    return [_defecto(capitulo, "EST-02", 0, len(capitulo.texto))]


def nombres_literales(capitulo: CapituloAValidar) -> list[Defecto]:
    """`PER-02`: un nombre escrito de otra forma que en el canon (CA-16, RF-VAL-03).

    **La diferencia esta en el canon, declarada, no en la astucia del
    validador.** Se acepta la forma canonica y cualquier **variante declarada**;
    se senala lo que se le parece sin ser ninguna de las dos. «Maria» por
    «Maria» con tilde es defecto; «Mari» por «Maria» **no lo es** si el canon la
    declara.

    El parecido lo mide `normalizar` de `commons/`, la misma funcion con la que
    el proyecto compara las palabras vetadas: minusculas, sin acentos y sin la
    -s del plural simple. Y se compara **por palabra y no por subcadena**, para
    que «Nala» no salte dentro de «sala».

    **Lo que no detecta**, y es el punto ciego de `verification.md` §8.1: el
    nombre inventado y coherente. Si «Mari» no esta declarada, tampoco esta
    declarada como error, y el validador calla — perseguirla es exactamente lo
    que CA-16 prohibe.
    """
    defectos: list[Defecto] = []
    for nombre in capitulo.nombres_del_canon:
        formas_aceptadas = {nombre.forma_canonica, *nombre.variantes}
        parecidas = {normalizar(forma) for forma in formas_aceptadas}
        for palabra, inicio, fin in _palabras_de_la_narracion(capitulo.texto):
            if palabra in formas_aceptadas:
                continue
            if normalizar(palabra) in parecidas:
                defectos.append(_defecto(capitulo, "PER-02", inicio, fin))
    return defectos


def _defectos_de_persona(capitulo: CapituloAValidar) -> list[Defecto]:
    marcas = [
        (inicio, fin)
        for palabra, inicio, fin in _palabras_de_la_narracion(capitulo.texto)
        if palabra.lower() in MARCAS_DE_PRIMERA_PERSONA
    ]
    if capitulo.discurso.persona is Persona.PRIMERA:
        if marcas:
            return []
        # La ausencia no tiene un pasaje culpable: el defecto es del capitulo.
        return [_defecto(capitulo, "VOZ-03", 0, len(capitulo.texto))]
    if not marcas:
        return []
    inicio, fin = marcas[0]
    return [_defecto(capitulo, "VOZ-03", inicio, fin)]


def _defectos_de_tiempo_verbal(capitulo: CapituloAValidar) -> list[Defecto]:
    declarado = capitulo.discurso.tiempo_verbal
    otro = TiempoVerbal.PRESENTE if declarado is TiempoVerbal.PASADO else TiempoVerbal.PASADO
    del_declarado: list[tuple[int, int]] = []
    del_otro: list[tuple[int, int]] = []
    for palabra, inicio, fin in _palabras_de_la_narracion(capitulo.texto):
        minuscula = palabra.lower()
        if minuscula in _MARCAS_POR_TIEMPO[declarado]:
            del_declarado.append((inicio, fin))
        elif minuscula in _MARCAS_POR_TIEMPO[otro]:
            del_otro.append((inicio, fin))
    if not del_otro or len(del_otro) <= len(del_declarado):
        return []
    inicio, fin = del_otro[0]
    return [_defecto(capitulo, "VOZ-03", inicio, fin)]


def discurso(capitulo: CapituloAValidar) -> list[Defecto]:
    """`VOZ-03`: la prosa no usa la `persona` o el `tiempo_verbal` declarados.

    **Regla de dominio 10, axioma 13 de `definitions.md` §11**, y el motivo de
    que exista esta funcion esta en la propia v1.3 del documento: las dos
    restricciones se fijaban en la obra, se heredaban a la ficha y se repetian
    al principio y al final del prompt —**y ningun validador las comprobaba en
    el texto**—. Un prompt no es un mecanismo: pedir no es comprobar.

    Mira **solo la narracion** (ver `segmentos_de_narracion`). Lo que no detecta
    es la deriva de voz: que el capitulo 8 no suene como el 2 respetando las dos.
    Eso es juicio, y vive en G1b.
    """
    return [*_defectos_de_persona(capitulo), *_defectos_de_tiempo_verbal(capitulo)]


CATALOGO: tuple[Validador, ...] = (
    Validador("extension_de_capitulo", PuntoDeEjecucion.HOOK_DE_CAPITULO, extension_de_capitulo),
    Validador("nombres_literales", PuntoDeEjecucion.HOOK_DE_CAPITULO, nombres_literales),
    Validador("discurso", PuntoDeEjecucion.HOOK_DE_CAPITULO, discurso),
)
"""El catalogo, en el orden de `verification.md` §8.1. Es lo que recorre la
puerta, y es tambien lo que se puede contar: un validador que no esta aqui no
corre, y uno que corre fuera de aqui no aparece en el resultado."""


def nombres_del_catalogo(catalogo: Sequence[Validador] = CATALOGO) -> tuple[str, ...]:
    """Los nombres, para que la puerta declare que ejecuto sin saber como."""
    return tuple(validador.nombre for validador in catalogo)


# --------------------------------------------------------------------------
# El manuscrito entero, puerta G4
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ManuscritoAValidar:
    """Lo que mira un validador que **no puede mirar un capitulo solo**.

    No lleva prosa, y esa ausencia es el requisito: RF-VAL-05 se comprueba
    «contra la tabla de hechos» y no con un `in` sobre el texto, asi que lo que
    entra son los hechos con los capitulos que se apoyan en ellos.
    """

    elementos_obligatorios: tuple[str, ...]
    hechos: tuple[HechoUsado, ...]


@dataclass(frozen=True, slots=True)
class ValidadorDeManuscrito:
    """Un validador de la novela entera, con su nombre y su punto (RF-VAL-01).

    Es un tipo distinto de `Validador` y no una generalizacion suya porque lo
    que cambia no es el detalle: **miran cosas distintas y producen cosas
    distintas**. Uno recibe un capitulo y devuelve defectos con cita; este
    recibe el manuscrito y devuelve cobertura, que senala una **ausencia** y por
    tanto no tiene pasaje que citar (`cobertura.ElementoAusente`). Fundirlos
    obligaria a fabricar una cita vacia, que es justo lo que `defectos.py`
    existe para descartar.
    """

    nombre: str
    punto: PuntoDeEjecucion
    comprobar: Callable[[ManuscritoAValidar], Cobertura]


@dataclass(frozen=True, slots=True)
class CierreDelManuscrito:
    """Lo que devuelve la puerta G4 de hoy, y **dice quien corrio**.

    Por lo mismo que `ResultadoDePuerta`: un resultado que no nombra a los
    validadores ejecutados no distingue «ninguno encontro nada» de «ninguno
    corrio», y esa distincion es exactamente la que esta feature dejo abierta
    cuando la cobertura vivia fuera de todo catalogo.
    """

    cobertura: Cobertura
    validadores_ejecutados: tuple[str, ...]
    validadores_rotos: tuple[str, ...] = ()
    """Los que lanzaron. Mismo criterio que en `ResultadoDePuerta`: un validador
    roto no es una cobertura completa, es una cobertura que nadie comprobo."""


def _cobertura_de_personalizacion(manuscrito: ManuscritoAValidar) -> Cobertura:
    """La entrada del catalogo: el nombre es el de `verification.md` §8.1."""
    return cobertura_de_obligatorios(manuscrito.elementos_obligatorios, manuscrito.hechos)


CATALOGO_DE_MANUSCRITO: tuple[ValidadorDeManuscrito, ...] = (
    ValidadorDeManuscrito(
        "cobertura_de_personalizacion", PuntoDeEjecucion.PUERTA_G4, _cobertura_de_personalizacion
    ),
)
"""El segundo catalogo, y nace porque faltaba: la cobertura estaba escrita y
probada desde T7 y **no la ejecutaba nadie**, que es lo que la frase de arriba
—«un validador que no esta aqui no corre»— declaraba sin que nadie lo notara.

Es de uno solo a proposito. Crecera en la Fase 4, cuando G4 tenga las suyas
(`dedicatoria_fuera`, `spec_lean`); lo que no se hace es adelantarlas."""


def cerrar_manuscrito(
    manuscrito: ManuscritoAValidar,
    catalogo: Sequence[ValidadorDeManuscrito] = CATALOGO_DE_MANUSCRITO,
) -> CierreDelManuscrito:
    """Corre el catalogo de G4 sobre la novela entera y declara a quien ejecuto.

    Las coberturas de varios validadores se **suman por montones**: un elemento
    esta cubierto si alguno lo da por cubierto, y ausente si ninguno lo hace.
    Con un solo validador es la identidad, y se escribe asi de todas formas
    porque la alternativa —devolver la del ultimo— seria correcta hoy y falsa el
    dia que entre el segundo, sin que ningun test cayera.
    """
    cubiertos: dict[str, ElementoCubierto] = {}
    ausentes: dict[str, ElementoAusente] = {}
    ejecutados: list[str] = []

    rotos: list[str] = []
    for validador in catalogo:
        try:
            cobertura = validador.comprobar(manuscrito)
        except Exception:  # noqa: BLE001 - fallo del validador, no del manuscrito
            rotos.append(validador.nombre)
            continue
        ejecutados.append(validador.nombre)
        for cubierto in cobertura.cubiertos:
            cubiertos[cubierto.elemento] = cubierto
        for ausente in cobertura.ausentes:
            ausentes.setdefault(ausente.elemento, ausente)

    # El orden de salida es el del brief, en los dos montones: es el orden en
    # que el comprador los pidio, y el unico que le dice algo a quien lea el
    # informe. Un `dict` conserva el de insercion, que es el del catalogo, no el
    # del brief.
    orden = list(manuscrito.elementos_obligatorios)
    return CierreDelManuscrito(
        cobertura=Cobertura(
            cubiertos=tuple(cubiertos[e] for e in orden if e in cubiertos),
            ausentes=tuple(ausentes[e] for e in orden if e in ausentes and e not in cubiertos),
        ),
        validadores_ejecutados=tuple(ejecutados),
        validadores_rotos=tuple(rotos),
    )
