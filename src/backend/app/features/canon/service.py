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

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.commons.domain import Reloj
from app.commons.llm import ClienteDeModelo, extraer_json
from app.features.canon.repository import RepositorioDeCanon

# §4.4 fija este orden. No es estetico: los hilos citan escenas y los fragmentos
# citan versiones de texto, asi que invertirlo dejaria referencias colgando
# dentro de la propia transaccion.
ORDEN_DE_ESCRITURA = ("canon", "ledger", "resumen", "hilos", "fragmentos")


class ExtraccionInvalida(ValueError):
    """La salida del Extractor no valida contra su esquema (RF-ORQ-15)."""


class HechoExtraido(BaseModel):
    model_config = ConfigDict(frozen=True)

    entidad: str = Field(min_length=1)
    atributo: str = Field(min_length=1)
    valor: str = Field(min_length=1)


class EventoExtraido(BaseModel):
    model_config = ConfigDict(frozen=True)

    descripcion: str = Field(min_length=1)
    # `testigos` es lo que alimenta RF-CAL-05. Un evento sin testigos es legitimo
    # -algo que no vio nadie-, asi que no se exige.
    testigos: list[str] = Field(default_factory=list)
    participantes: list[str] = Field(default_factory=list)


class HiloExtraido(BaseModel):
    model_config = ConfigDict(frozen=True)

    pregunta: str = Field(min_length=1)
    estado: str = Field(min_length=1)


class PlantadoExtraido(BaseModel):
    model_config = ConfigDict(frozen=True)

    importancia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)


class Extraccion(BaseModel):
    """Contrato de salida del Extractor."""

    model_config = ConfigDict(frozen=True)

    hechos: list[HechoExtraido] = Field(default_factory=list)
    eventos: list[EventoExtraido] = Field(default_factory=list)
    resumen: str = Field(min_length=1)
    hilos: list[HiloExtraido] = Field(default_factory=list)
    plantados: list[PlantadoExtraido] = Field(default_factory=list)
    ngramas_gastados: list[str] = Field(default_factory=list)


class ResultadoDeExtraccion(BaseModel):
    model_config = ConfigDict(frozen=True)

    escena_id: str
    orden_de_escritura: list[str]
    hechos_escritos: int
    eventos_escritos: int


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
    respuesta = cliente.generar(prompt)
    try:
        extraccion = Extraccion.model_validate_json(extraer_json(respuesta.texto))
    except ValidationError as error:
        raise ExtraccionInvalida(
            f"la salida del Extractor no valida contra Extraccion: {error}"
        ) from error

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
