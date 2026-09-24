"""Casos de uso de la feature `obra`.

Hoy la entrevista y los hechos que el brief trae consigo, y a proposito nada
mas. Cerrar la entrevista —crear la obra, guardar destinatario y vetos, no crear
dos al doble clic— necesita los errores de dominio que anade la Tarea 9, que no
existen cuando se escribe esto. Adivinar esas interfaces habria sido escribir
codigo contra una firma que aun nadie ha fijado: ver Desviaciones del plan.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.obra.agents import Entrevistador, Evaluacion
from app.features.obra.modelos import HechoCanon
from app.features.obra.repository import guardar_hechos_del_brief


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
    enunciados: list[str],
) -> list[HechoCanon]:
    """Los hechos que el comprador trajo entran al canon (RF-ENT-06).

    El caso de uso **no tiene parametro `origen`**, y esa ausencia es su unico
    contenido: el repositorio lo acepta porque la Fase 2 escribira por ahi
    hechos de escena, pero por la via de la entrevista no se puede pedir otra
    cosa que `brief`. Es la frontera que el router de la Tarea 9 va a cruzar,
    y `CLAUDE.md` §6 no le deja llamar al repositorio por su cuenta.

    De donde salen los enunciados —el texto aportado, las respuestas— no es de
    aqui: cuando exista el Extractor sera el quien los produzca. Este caso de
    uso recibe la lista ya hecha.
    """
    return await guardar_hechos_del_brief(sesion, obra_id, enunciados)
