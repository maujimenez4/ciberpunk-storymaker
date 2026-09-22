"""Casos de uso de la feature `escena`."""

from pydantic import ValidationError

from app.commons.domain import ParametrosDeDiscurso, Reloj
from app.commons.llm import ClienteDeModelo, extraer_json
from app.features.escena.schemas import (
    FichaDeEscena,
    FichaInvalida,
    PropuestaDeFicha,
)


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
    respuesta = cliente.generar(prompt)
    try:
        propuesta = PropuestaDeFicha.model_validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise FichaInvalida(
            f"la salida del Planificador no valida contra PropuestaDeFicha: {error}"
        ) from error

    return FichaDeEscena(
        escena_id=escena_id,
        **propuesta.model_dump(),
        persona=parametros.persona,
        tiempo_verbal=parametros.tiempo_verbal,
        nivel_de_calor=parametros.nivel_de_calor,
    )
