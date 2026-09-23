"""El Extractor: la frontera con el modelo, y el único sitio donde vive.

`CLAUDE.md` §9.3: el código de cada agente narrativo vive en el `agents.py` de
la feature que lo orquesta. Separarlo de `service.py` no es orden por el orden:
deja el caso de uso legible sin el ruido de la invocación, y —sobre todo— hace
que «quién habla con el modelo» sea una pregunta que se responde mirando los
nombres de los ficheros en vez de leyendo cuerpos de función.

**La salida se valida antes de devolverla** (RF-ORQ-15). Lo que no valida es
fallo del paso, no texto que se arrastre al siguiente y reviente más tarde en un
sitio que no tiene la culpa.
"""

from pydantic import ValidationError

from app.commons.llm import ClienteDeModelo, extraer_json
from app.features.canon.schemas import Extraccion, ExtraccionInvalida


def invocar_extractor(cliente: ClienteDeModelo, prompt: str) -> Extraccion:
    """RF-CAN-01: el Extractor lee la prosa aprobada y devuelve lo que hay
    que consolidar."""
    respuesta = cliente.generar(prompt)
    try:
        return Extraccion.model_validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise ExtraccionInvalida(
            f"la salida del Extractor no valida contra Extraccion: {error}"
        ) from error
