"""El Arquitecto, en su segunda intervención: la frontera con el modelo.

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
from app.features.outline.schemas import Outline, OutlineInvalido


def invocar_arquitecto(cliente: ClienteDeModelo, prompt: str) -> Outline:
    """RF-OUT-01 a RF-OUT-05: el Arquitecto produce el outline."""
    respuesta = cliente.generar(prompt)
    try:
        return Outline.model_validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise OutlineInvalido(str(error)) from error
