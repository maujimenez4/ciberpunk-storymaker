"""Casos de uso de la feature `obra`.

La entrevista de principio a fin: abrirla, ir recogiendo respuestas y cerrarla
creando la obra. Aqui vive la decision que CA-2 pide en codigo —no en la prosa
del modelo— y R-5, que hace que cerrar dos veces no cree dos obras.

**Ningun `HTTPException` entra en este fichero** (`CLAUDE.md` §6): lo que sale
de aqui son excepciones de `commons/domain/errores.py`, y el manejador central
de `commons/errors/` decide con que codigo se cuentan.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.domain.errores import (
    BriefContradictorio,
    BriefIncompleto,
    EntrevistaDesconocida,
)
from app.features.obra.agents import Entrevistador, Evaluacion
from app.features.obra.modelos import Entrevista, HechoCanon
from app.features.obra.repository import (
    abrir_entrevista as abrir_entrevista_en_bd,
)
from app.features.obra.repository import (
    crear_obra_desde_brief,
    guardar_hechos_del_brief,
    guardar_respuestas,
    guardar_texto_aportado,
    leer_textos_aportados,
    obtener_entrevista,
)
from app.features.obra.schemas import BriefEntrada, HechoDelBrief

_CAMPOS_DEL_DESTINATARIO = (
    "nombre",
    "edad",
    "rasgos",
    "recuerdos_aportados",
    "fecha_de_nacimiento",
)
_CAMPOS_DE_LA_OBRA = ("genero", "tono", "nivel_de_calor", "vetos", "elementos_obligatorios")


@dataclass(frozen=True)
class CierreDeEntrevista:
    """Que obra quedo, y si la creo **esta** llamada.

    `creada` existe solo para que el router sepa si responder 201 o 200: la
    segunda vez que se cierra no se ha creado nada, y decir «Created» seria
    mentir sobre lo unico que R-5 garantiza.
    """

    obra_id: int
    creada: bool


async def evaluar_entrevista(
    entrevistador: Entrevistador,
    respuestas: dict[str, object],
    texto_aportado: str = "",
) -> Evaluacion:
    """Pregunta que falta y que se contradice (RF-ENT-03, RF-ENT-04).

    El agente informa; no decide. Se lo dice su propia plantilla —«No decidas tu
    si la obra se crea»— y CA-2 pone esa decision en codigo: quien la tome lee
    `Evaluacion.completa`, no la prosa del modelo.

    `texto_aportado` es opcional porque el comprador puede no pegar nada, y un
    texto en blanco no debe generar seccion en el prompt (R-2).
    """
    return await entrevistador.evaluar(respuestas, texto_aportado)


async def registrar_hechos_del_brief(
    sesion: AsyncSession,
    obra_id: int,
    hechos: list[HechoDelBrief],
) -> list[HechoCanon]:
    """Los hechos que el comprador trajo entran al canon (RF-ENT-06).

    El caso de uso **no tiene parametro `origen`**, y esa ausencia es su unico
    contenido: el repositorio lo acepta porque la Fase 2 escribira por ahi
    hechos de escena, pero por la via de la entrevista no se puede pedir otra
    cosa que `brief`.

    De donde salen los hechos —el texto aportado, las respuestas— no es de
    aqui: cuando exista el Extractor sera el quien los produzca. Este caso de
    uso recibe la lista ya hecha.
    """
    return await guardar_hechos_del_brief(sesion, obra_id, hechos)


def _brief_desde_respuestas(respuestas: dict[str, Any]) -> BriefEntrada:
    """De lo que el comprador fue respondiendo a un `BriefEntrada` (RF-ENT-07).

    Las respuestas llegan planas —`nombre`, `edad`, `genero`…— porque asi las
    escribe quien rellena un formulario; el brief las quiere con el
    destinatario anidado. Se acepta tambien la forma ya anidada por si quien
    llama la manda hecha.

    **Solo se copian las claves presentes.** Pasar `None` por una que falta
    convertiria un error `missing` en uno de tipo, y entonces un dato que falta
    dejaria de contarse como faltante y pasaria por contradiccion.
    """
    destinatario = respuestas.get(
        "destinatario",
        {clave: respuestas[clave] for clave in _CAMPOS_DEL_DESTINATARIO if clave in respuestas},
    )
    crudo: dict[str, Any] = {
        clave: respuestas[clave] for clave in _CAMPOS_DE_LA_OBRA if clave in respuestas
    }
    crudo["destinatario"] = destinatario
    return BriefEntrada.model_validate(crudo)


def _campo(loc: tuple[int | str, ...]) -> str:
    """`('destinatario', 'edad')` -> `destinatario.edad`, como lo nombra el agente."""
    return ".".join(str(parte) for parte in loc)


def _brief_validado(respuestas: dict[str, Any]) -> BriefEntrada:
    """El esquema, traducido a las dos excepciones que el dominio sabe nombrar.

    Un `ValidationError` trae dos cosas distintas mezcladas y no se pueden
    contar igual: lo que **falta** (`missing`) es RF-ENT-03, y lo que **no
    puede ser cierto a la vez** —la regla de dominio 6, la edad contra la fecha
    de nacimiento (R-7), el veto que choca con el nombre (R-8)— es RF-ENT-04.
    Meterlo todo en un `detail` dejaria al comprador sin saber si tiene que
    aportar un dato o corregir otro.
    """
    try:
        return _brief_desde_respuestas(respuestas)
    except ValidationError as error:
        faltantes = [_campo(e["loc"]) for e in error.errors() if e["type"] == "missing"]
        if faltantes:
            raise BriefIncompleto(faltantes) from error
        raise BriefContradictorio(
            [{"campos": [_campo(e["loc"])], "explicacion": e["msg"]} for e in error.errors()]
        ) from error


async def abrir_entrevista(sesion: AsyncSession) -> Entrevista:
    """RI-01. Nada mas: la entrevista nace vacia y se rellena a trozos."""
    entrevista = await abrir_entrevista_en_bd(sesion)
    await sesion.commit()
    return entrevista


async def _entrevista_o_error(sesion: AsyncSession, entrevista_id: int) -> Entrevista:
    entrevista = await obtener_entrevista(sesion, entrevista_id)
    if entrevista is None:
        raise EntrevistaDesconocida(entrevista_id)
    return entrevista


async def _texto_de_la_entrevista(sesion: AsyncSession, entrevista_id: int) -> str:
    """Todo lo que el comprador pego, en orden de llegada.

    Se junta para evaluar, y solo para eso: lo guardado sigue siendo una fila
    por texto, con su procedencia.
    """
    textos = await leer_textos_aportados(sesion, entrevista_id)
    return "\n\n".join(texto.contenido for texto in textos)


async def responder_entrevista(
    sesion: AsyncSession,
    entrevistador: Entrevistador,
    entrevista_id: int,
    respuestas: dict[str, Any],
    texto_aportado: str = "",
) -> Evaluacion:
    """RI-02: se acumula lo respondido y se devuelve que falta y que choca.

    El texto libre se guarda como `TextoAportado` (RF-ENT-05) **antes** de
    evaluar, y se evalua junto con lo que ya hubiera: el comprador puede pegar
    la carta en una llamada y responder el resto en otra, y el Entrevistador
    tiene que ver las dos cosas a la vez para poder decir que falta.

    No decide nada: devuelve la evaluacion tal cual. La decision de crear o no
    la obra es de `cerrar_entrevista`, y esta en codigo y no en la prosa del
    modelo (CA-2).
    """
    entrevista = await _entrevista_o_error(sesion, entrevista_id)
    await guardar_respuestas(sesion, entrevista, respuestas)
    await guardar_texto_aportado(sesion, entrevista.id, texto_aportado)
    evaluacion = await evaluar_entrevista(
        entrevistador,
        entrevista.respuestas,
        await _texto_de_la_entrevista(sesion, entrevista.id),
    )
    await sesion.commit()
    return evaluacion


async def cerrar_entrevista(
    sesion: AsyncSession,
    entrevistador: Entrevistador,
    entrevista_id: int,
) -> CierreDeEntrevista:
    """RI-03 y CU-01 entero: se valida el brief y se crea la obra.

    El orden lo fija el caso de uso de la spec: primero lo que el Entrevistador
    ve —lo que falta y lo que se contradice—, y solo si no hay nada de eso se
    valida el brief con esquema y se escribe. Nada se escribe antes: la
    excepcion de CU-01 dice «se vuelve a preguntar; **no se escribe nada**».

    Las contradicciones se miran antes que los faltantes porque una
    contradiccion no se arregla aportando el dato que falta: hay que corregir
    uno de los dos que chocan, y decir primero «te falta la edad» manda al
    comprador a rellenar un hueco que no es el problema.
    """
    entrevista = await _entrevista_o_error(sesion, entrevista_id)

    # R-5. El comprador da doble clic y nadie prometio que no lo hiciera. La
    # idempotencia se apoya en la fila y no en la memoria del proceso porque el
    # segundo clic puede llegar a otro trabajador.
    if entrevista.obra_id is not None:
        return CierreDeEntrevista(obra_id=entrevista.obra_id, creada=False)

    evaluacion = await evaluar_entrevista(
        entrevistador,
        entrevista.respuestas,
        await _texto_de_la_entrevista(sesion, entrevista.id),
    )
    if evaluacion.contradicciones:
        raise BriefContradictorio([c.model_dump() for c in evaluacion.contradicciones])
    if evaluacion.faltantes:
        raise BriefIncompleto(evaluacion.faltantes)

    brief = _brief_validado(entrevista.respuestas)
    obra = await crear_obra_desde_brief(sesion, brief)
    entrevista.obra_id = obra.id
    await sesion.commit()
    return CierreDeEntrevista(obra_id=obra.id, creada=True)
