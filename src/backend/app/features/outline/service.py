"""Casos de uso de la feature `outline`."""

from pydantic import ValidationError

from app.commons.domain import Reloj
from app.commons.llm import ClienteDeModelo, extraer_json
from app.features.outline.repository import RepositorioDeOutline
from app.features.outline.schemas import Outline, OutlineInvalido


def generar_outline(
    obra_id: str,
    cliente: ClienteDeModelo,
    prompt: str,
    repositorio: RepositorioDeOutline,
    reloj: Reloj,
) -> Outline:
    """CU-02, RF-OUT-01 a RF-OUT-05.

    El contrato de genero se comprueba **antes** de guardar. Es la unica fase
    en la que arreglarlo es barato: mover una escena en el outline cuesta una
    linea, y en el manuscrito cuesta reescribir un capitulo.
    """
    respuesta = cliente.generar(prompt)
    try:
        outline = Outline.model_validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise OutlineInvalido(str(error)) from error
    repositorio.guardar(obra_id, outline)
    return outline
