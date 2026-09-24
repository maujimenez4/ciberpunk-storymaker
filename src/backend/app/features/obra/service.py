"""Casos de uso de la feature `obra`.

Hoy solo el de la entrevista, y a proposito nada mas. Cerrar la entrevista
—crear la obra, guardar destinatario y vetos, no crear dos al doble clic— necesita
el esquema de la Tarea 4 y los errores de dominio que anade la Tarea 9, que no
existen cuando se escribe esto. Adivinar esas interfaces habria sido escribir
codigo contra una firma que aun nadie ha fijado: ver Desviaciones del plan.
"""

from app.features.obra.agents import Entrevistador, Evaluacion


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
