"""El Continuista: la frontera con el modelo, y el unico sitio donde vive.

`CLAUDE.md` §9.3. Devuelve **codigos con cita**, nunca prosa corregida (§9.1), y
lo que aqui se produce no son todavia defectos: son `Afirmacion`, lo que la
prosa dice. Contrastarlas contra el canon y el estado es cosa de
`validadores.py`, y esa division es la que hace mecanica a G1a **en el
contraste** aunque la extraccion sea probabilistica (`verification.md` §6.2).

**La salida se valida antes de devolverla** (RF-ORQ-15), como en el Extractor.
Lo que no valida es fallo del paso: una salida rota convertida en lista vacia
seria un cero de defectos indistinguible del de una escena limpia.
"""

from pydantic import TypeAdapter, ValidationError

from app.commons.llm import ClienteDeModelo, RespuestaDeModelo, extraer_json
from app.features.calidad.schemas import AfirmacionesInvalidas, LecturaDelContinuista
from app.features.calidad.validadores import Afirmacion

_AFIRMACIONES = TypeAdapter(list[Afirmacion])


def invocar_continuista(cliente: ClienteDeModelo, prompt: str) -> LecturaDelContinuista:
    """RF-CAL-04 a RF-CAL-07: lo que la prosa afirma, con su pasaje.

    Como el Escritor, **solo ve un texto** (§9.1): ni repositorios ni base de
    datos. Si le falta contexto para afirmar algo, el fallo es del ensamblado y
    no suyo, y eso es lo que mantiene el defecto atribuible.
    """
    respuesta: RespuestaDeModelo = cliente.generar(prompt)
    try:
        afirmaciones = _AFIRMACIONES.validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise AfirmacionesInvalidas(
            f"la salida del Continuista no valida contra list[Afirmacion]: {error}"
        ) from error
    return LecturaDelContinuista(
        afirmaciones=afirmaciones,
        modelo=respuesta.modelo or "doble",
        parametros=respuesta.parametros,
    )
