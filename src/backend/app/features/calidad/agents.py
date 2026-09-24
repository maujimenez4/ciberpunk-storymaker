"""El Continuista: el rol que contrasta el capitulo **contra el grafo de canon**.

Es el primer `agents.py` de esta feature, y la Fase 2 la construyo entera sin
ninguno **a proposito**. La decision **P-B** de aquel plan lo dejo fuera con este
motivo exacto: «contrasta contra el grafo, y un capitulo solo no tiene contra
que chocar». Con diez capitulos, si: el problema real del producto es que el
siete contradiga al cuatro, y este fichero es quien lo mira.

**Contrastar no es opinar** (RF-VAL-06), y aqui esa diferencia es mecanica y no
una promesa del prompt:

1. **El grafo entra en el prompt con sus identificadores.** Lo que no esta en la
   lista no existe para el Continuista. Un prompt sin grafo pide una opinion.
2. **Lo que vuelve se valida con esquema antes de creerselo** (RF-ORQ-09), con
   `extra="forbid"`: un `BaseModel` por defecto acepta una clave que no conoce,
   la tira y sigue, y eso **pierde datos en silencio**. La Fase 1 lo descubrio
   en el Entrevistador y la Fase 2 lo heredo en el Extractor.
3. **La forma la comprueba la puerta de la Fase 2, no este fichero.**
   `clasificar` de `defectos.py` es quien decide si un `CAN-01` nombra un hecho
   que existe (regla de dominio 9) y si la cita es subcadena exacta en su
   desplazamiento (regla de dominio 8). Aqui se **usa**; reescribirla habria
   dado dos comprobaciones que divergen.

**El Continuista no repara** (`CLAUDE.md` §9.1). Devuelve codigos con cita y
nada mas: en `DefectoDelContinuista` no hay ningun campo donde quepa una
reescritura, y el esquema rechaza el que lo intente. La reparacion vuelve al
Escritor con el defecto concreto, y eso ya existe desde la Fase 2
(`features/escritura/agents.py`). Que sean dos roles separados es lo que hace
**atribuible** un defecto: si el que juzga arreglase, nadie sabria si el fallo
vino de quien escribio o de quien juzgo.

**Lo que este fichero NO hace, y conviene no ampliarlo al leerlo:** no puntua
—eso es del Critico, que no bloquea hasta que su correlacion con la revision
humana este medida (RF-JUZ-06)—, no persiste, no cuenta reintentos y no decide
si el capitulo pasa. Devuelve una revision; quien cruza la puerta es
`cruzar_g1a`, y quien cuenta los intentos es el orquestador.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from app.commons.llm.cliente import ClienteModelo
from app.features.calidad.defectos import DefectoMalFormado, clasificar
from app.features.calidad.schemas import Defecto

PLANTILLA_V1 = (Path(__file__).parent / "prompts" / "continuista.v1.md").read_text(encoding="utf-8")

PROMPT_ID = "continuista"
PROMPT_VERSION = "v1"
HASH_DE_PLANTILLA_V1 = sha256(PLANTILLA_V1.encode("utf-8")).hexdigest()
"""Lo que ata la fila de `ejecucion` al fichero sin duplicarlo en cada llamada
(regla de dominio 7). La plantilla **no se edita en sitio**: una version nueva
es `continuista.v2.md` con su propio hash (`CLAUDE.md` §10)."""

MARCA_CAPITULO = "capitulo"
"""La etiqueta con la que el capitulo entra **como dato** (`CLAUDE.md` §11).
Cinco de los diez roles reciben prosa, y ninguno la recibe como instruccion."""

HUECO_DEL_CAPITULO = "{{CAPITULO}}"
HUECO_DEL_CANON = "{{CANON}}"

SIN_GRAFO = (
    "No hay ningún hecho de canon. **No puede haber ninguna contradicción de canon**: "
    "no se devuelve ningún `CAN-01`."
)
"""Con el grafo vacio no hay contra que contrastar, y decirlo es mas honesto que
dejar la seccion en blanco: un hueco vacio invita a rellenarlo de memoria."""

TextoNoVacio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
"""Se repite desde `features/canon/schemas.py`. `CLAUDE.md` §5.1 regla 4 lo
manda a `commons/` al tercer uso real y este es el cuarto, pero `commons/` es de
otra tarea de esta ola: queda anotado en Desviaciones."""


class SalidaMalFormada(Exception):
    """Un agente que devuelve algo fuera de su esquema es un fallo (RF-ORQ-09).

    Se repite desde `features/canon/agents.py` por el mismo motivo que
    `TextoNoVacio`, y con la misma anotacion en Desviaciones.
    """


class OrigenDeHecho(StrEnum):
    """De donde salio un hecho (`definitions.md` §4.5). Los mismos tres valores
    que el `CheckConstraint` de la tabla, para que la proyeccion no pueda
    representar un hecho que la base no admitiria."""

    ESCENA = "escena"
    BRIEF = "brief"
    EDICION_HUMANA = "edicion_humana"


class HechoDeCanon(BaseModel):
    """Un hecho del grafo, **tal y como el Continuista lo ve**.

    Es una proyeccion, no la tabla: `HechoCanon` vive en `features/obra` y una
    feature solo entra a otra por su `__init__.py` (`CLAUDE.md` §5.1). La misma
    decision que ya tomo `puerta.py`, y por el mismo motivo: asi esta feature se
    prueba sin base de datos.

    Lleva `entidad`, `atributo` y `valor` **separados** y no una frase, porque
    eso es lo que hace comparable un hecho con otro: la regla de arbitraje de
    `definitions.md` §4.5 —si dos hechos sobre el mismo atributo difieren,
    prevalece el de menor `orden_discurso` y el otro es un `CAN-01`— no se puede
    aplicar sobre una cadena libre.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    hecho_canon_id: TextoNoVacio
    entidad: TextoNoVacio
    atributo: TextoNoVacio
    valor: TextoNoVacio
    origen: OrigenDeHecho = OrigenDeHecho.ESCENA
    escena_de_origen: str | None = None

    @model_validator(mode="after")
    def el_origen_es_coherente(self) -> "HechoDeCanon":
        """Regla de dominio 4, axioma 14 de `definitions.md` §11, **entera**.

        Las dos mitades, porque la segunda es la que se olvida: un hecho de
        escena declara la suya —sin ella R-1 puede decir que hay contradiccion
        pero no donde se establecio lo que choca— y **un hecho del brief no la
        inventa**, porque existia antes de que se escribiera una linea.
        """
        de_escena = self.origen is OrigenDeHecho.ESCENA
        if de_escena and not (self.escena_de_origen or "").strip():
            raise ValueError("un hecho de origen `escena` declara su `escena_de_origen`")
        if not de_escena and self.escena_de_origen is not None:
            raise ValueError("un hecho que no viene de una escena no inventa `escena_de_origen`")
        return self

    def como_linea(self) -> str:
        """La linea que ve el modelo. El identificador va **primero** porque es
        lo que tiene que copiar literal en el `CAN-01`."""
        procedencia = self.escena_de_origen or f"origen: {self.origen.value}"
        campos = (self.hecho_canon_id, self.entidad, self.atributo, self.valor, procedencia)
        return "- " + " · ".join(_en_una_linea(campo) for campo in campos)


class DefectoDelContinuista(BaseModel):
    """Lo que el modelo puede decir de un pasaje, y **nada mas**.

    No hay `version_texto_id`: lo pone el codigo, que sabe que version se juzga.
    Si lo pusiera el modelo seria un dato inventado con aspecto de
    trazabilidad, que es el mismo criterio con el que el Extractor tiene
    prohibido escribir la escena de origen de un hecho.

    Y no hay **ningun** campo donde quepa una reescritura. Con `extra="forbid"`,
    un modelo que devuelva `texto_corregido` no ve su sugerencia ignorada: ve su
    salida rechazada entera. `CLAUDE.md` §9.1, en el esquema y no en el prompt.

    `codigo` es `str` sin restringir por la misma razon que en `Defecto`: si el
    esquema rechazara un codigo fuera de la taxonomia, el defecto mal formado no
    llegaria a existir y no habria nada que contar aparte (CA-17).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    codigo: str
    cita: str
    desplazamiento_inicio: int
    desplazamiento_fin: int
    hecho_canon_id: str | None = None


class InformeDeContinuidad(BaseModel):
    """La salida entera del agente: una clave y ninguna mas."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    defectos: list[DefectoDelContinuista] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CapituloAContrastar:
    """El capitulo y aquello contra lo que se contrasta, juntos.

    `grafo` no es un parametro opcional de conveniencia: sin el no hay contraste
    y lo que salga es una opinion. Va en la misma estructura que el texto para
    que no se pueda llamar al Continuista «solo con la prosa» por descuido.
    """

    version_texto_id: str
    texto: str
    grafo: tuple[HechoDeCanon, ...]

    @property
    def ids_del_grafo(self) -> frozenset[str]:
        """Los identificadores que **existen**: la proyeccion que
        `comprobar_forma` necesita para la regla de dominio 9."""
        return frozenset(hecho.hecho_canon_id for hecho in self.grafo)


@dataclass(frozen=True, slots=True)
class RevisionDeContinuidad:
    """Los dos montones, y los dos presentes.

    Que los mal formados vengan en el mismo resultado es lo que hace
    comprobable «se cuenta aparte» (CA-17, RF-VAL-07), y aqui importa mas que en
    ningun otro sitio: el Continuista es **el emisor** para el que se escribio
    esa comprobacion. Los validadores mecanicos citan del texto y no pueden
    equivocarse de cita; un modelo si. La tasa de mal formados es hoy la unica
    senal directa de que quien los emite esta afirmando cosas que no estan.
    """

    defectos: tuple[Defecto, ...]
    mal_formados: tuple[DefectoMalFormado, ...]


def _en_una_linea(texto: str) -> str:
    """Un hecho ocupa una linea. Un valor con saltos partiria la lista y el
    siguiente hecho se leeria como continuacion del anterior."""
    return " ".join(sin_etiquetas(texto, MARCA_CAPITULO).split())


def sin_etiquetas(texto: str, marca: str) -> str:
    """Quita la etiqueta hasta que quitarla ya no cambie nada.

    Una pasada sola no basta: al borrar el cierre de `</cap</capitulo>itulo>` se
    unen los dos trozos que lo rodeaban y la etiqueta se vuelve a formar. Se
    repite hasta punto fijo, y termina siempre porque cada vuelta que cambia
    algo acorta la cadena.

    Se repite desde `features/canon/agents.py` —tercera copia en el
    repositorio— porque esa es interna a otra feature y §5.1 prohibe entrar por
    ella. Anotado en Desviaciones.
    """
    sano = texto
    while True:
        podado = sano.replace(f"</{marca}>", "").replace(f"<{marca}>", "")
        if podado == sano:
            return sano
        sano = podado


def render_grafo(grafo: Sequence[HechoDeCanon]) -> str:
    """El grafo, en lineas con su identificador. Es lo que convierte la revision
    en un contraste (RF-VAL-06)."""
    if not grafo:
        return SIN_GRAFO
    return "\n".join(hecho.como_linea() for hecho in grafo)


def render_continuista(plantilla: str, texto: str, grafo: Sequence[HechoDeCanon]) -> str:
    """El capitulo entra SIEMPRE marcado como dato (`CLAUDE.md` §11).

    Dos propiedades, y la segunda es la que importa: que el capitulo no pueda
    cerrar su etiqueta, y que **lo que rodea a la etiqueta no dependa del
    capitulo**. La segunda es la que hace que un ataque no cambie el prompt, y
    por tanto que un capitulo no pueda desactivar al que lo revisa.
    """
    con_canon = plantilla.replace(HUECO_DEL_CANON, render_grafo(grafo))
    if not texto.strip():
        return con_canon.replace(HUECO_DEL_CAPITULO, "")
    bloque = f"<{MARCA_CAPITULO}>\n{sin_etiquetas(texto, MARCA_CAPITULO)}\n</{MARCA_CAPITULO}>"
    return con_canon.replace(HUECO_DEL_CAPITULO, bloque)


class Continuista:
    """El rol, con su cliente inyectado (`CLAUDE.md` §6).

    No toca la base de datos y no recibe sesion: recibe el grafo ya proyectado.
    Es la misma frontera que `puerta.py` declaro en la Fase 2, y la que permite
    probar el contraste sin levantar SQLite.
    """

    def __init__(self, cliente: ClienteModelo, semilla: int = 0) -> None:
        self._cliente = cliente
        self._semilla = semilla

    async def revisar(self, capitulo: CapituloAContrastar) -> RevisionDeContinuidad:
        """Contrasta el capitulo contra el grafo y devuelve codigos con cita.

        Un capitulo en blanco **no llama al modelo**: no hay texto del que citar,
        asi que cualquier defecto sobre el seria por fuerza una cita inventada.
        Es el mismo criterio con el que el Extractor no paga por un
        `TextoAportado` vacio.
        """
        if not capitulo.texto.strip():
            return RevisionDeContinuidad(defectos=(), mal_formados=())

        crudo = await self._cliente.completar(
            render_continuista(PLANTILLA_V1, capitulo.texto, capitulo.grafo),
            semilla=self._semilla,
        )
        informe = _validar(crudo)
        clasificados = clasificar(
            (
                Defecto(
                    codigo=defecto.codigo,
                    version_texto_id=capitulo.version_texto_id,
                    cita=defecto.cita,
                    desplazamiento_inicio=defecto.desplazamiento_inicio,
                    desplazamiento_fin=defecto.desplazamiento_fin,
                    hecho_canon_id=defecto.hecho_canon_id,
                )
                for defecto in informe.defectos
            ),
            capitulo.texto,
            capitulo.ids_del_grafo,
        )
        return RevisionDeContinuidad(
            defectos=clasificados.bien_formados,
            mal_formados=clasificados.mal_formados,
        )


def _validar(crudo: str) -> InformeDeContinuidad:
    """JSON mal formado y esquema incumplido se cuentan igual: fallo del agente.

    Los dos significan lo mismo para quien llama —no hay revision utilizable— y
    distinguirlos obligaria a manejar dos excepciones para tomar la misma
    decision.
    """
    try:
        return InformeDeContinuidad.model_validate(json.loads(crudo))
    except (json.JSONDecodeError, ValidationError) as error:
        raise SalidaMalFormada(crudo[:200]) from error
