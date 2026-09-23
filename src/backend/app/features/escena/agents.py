"""El Planificador de escena: la frontera con el modelo, y el único sitio donde vive.

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
from app.features.escena.schemas import FichaInvalida, PropuestaDeFicha


def invocar_planificador(cliente: ClienteDeModelo, prompt: str) -> PropuestaDeFicha:
    """RF-ESC-01: el Planificador propone la ficha. Lo heredado lo impone
    después el caso de uso, nunca el agente."""
    respuesta = cliente.generar(prompt)
    try:
        return PropuestaDeFicha.model_validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise FichaInvalida(
            f"la salida del Planificador no valida contra PropuestaDeFicha: {error}"
        ) from error
