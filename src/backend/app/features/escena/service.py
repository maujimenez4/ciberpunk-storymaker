"""Casos de uso de la feature `escena`."""

from app.commons.domain import ParametrosDeDiscurso, Reloj
from app.commons.llm import ClienteDeModelo
from app.features.escena.agents import invocar_planificador
from app.features.escena.schemas import FichaDeEscena


def planificar_escena(
    escena_id: str,
    parametros: ParametrosDeDiscurso,
    cliente: ClienteDeModelo,
    prompt: str,
    reloj: Reloj,
) -> FichaDeEscena:
    """RF-ESC-01 y RF-ESC-02: la ficha, con lo heredado impuesto por codigo.

    El orden importa: se valida la propuesta y **despues** se imponen los
    parametros de discurso. Al reves, una propuesta con un nivel de calor mas
    alto podria colarse si algun dia se relaja la validacion.
    """
    propuesta = invocar_planificador(cliente, prompt)
    return FichaDeEscena(
        escena_id=escena_id,
        **propuesta.model_dump(),
        persona=parametros.persona,
        tiempo_verbal=parametros.tiempo_verbal,
        nivel_de_calor=parametros.nivel_de_calor,
    )
