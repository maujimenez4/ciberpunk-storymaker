"""El paso `EXTRAYENDO`: consolidar una escena aprobada en la memoria larga.

RF-CAN-01 a RF-CAN-03, RF-CAN-08, RF-CAN-10, RD-13.

Dos reglas mandan aqui y las dos son de las que se incumplen sin ruido:

**Solo el Extractor escribe memoria de largo plazo, y solo desde este paso**
(RF-CAN-01). Ningun otro agente deja rastro permanente.

**O entra todo, o no entra nada** (RF-CAN-03). Una escena rechazada no puede
dejar hechos en canon: el canon quedaria contaminado con afirmaciones de texto
que nunca llego al manuscrito, y el sintoma apareceria capitulos despues como
una contradiccion que nadie sabe explicar. Por eso la escritura va en **una
transaccion**, y la validacion entera ocurre **antes** de abrirla.
"""

from app.commons.domain import Reloj
from app.commons.llm import ClienteDeModelo
from app.features.canon.agents import invocar_extractor
from app.features.canon.repository import RepositorioDeCanon
from app.features.canon.schemas import ResultadoDeExtraccion

# §4.4 fija este orden. No es estetico: los hilos citan escenas y los fragmentos
# citan versiones de texto, asi que invertirlo dejaria referencias colgando
# dentro de la propia transaccion.
ORDEN_DE_ESCRITURA = ("canon", "ledger", "resumen", "hilos", "fragmentos")


def extraer_de_escena(
    serie_id: str,
    escena_id: str,
    version_texto_id: str,
    cliente: ClienteDeModelo,
    prompt: str,
    repositorio: RepositorioDeCanon,
    reloj: Reloj,
) -> ResultadoDeExtraccion:
    """RF-CAN-01 a RF-CAN-03: el unico camino por el que crece la memoria."""
    extraccion = invocar_extractor(cliente, prompt)
    repositorio.consolidar(
        serie_id=serie_id,
        escena_id=escena_id,
        version_texto_id=version_texto_id,
        extraccion=extraccion,
        reloj=reloj,
    )
    return ResultadoDeExtraccion(
        escena_id=escena_id,
        orden_de_escritura=list(ORDEN_DE_ESCRITURA),
        hechos_escritos=len(extraccion.hechos),
        eventos_escritos=len(extraccion.eventos),
    )
