"""Contratos de la feature `canon` (architecture.md §5.1).

Los modelos del Extractor viven aquí y no en `service.py` por dos razones. La de
forma: §5.1 dice que `schemas.py` es el segmento de los contratos. La que de
verdad obliga: `agents.py` necesita el esquema para validar la salida del
modelo, y si el esquema viviera en `service.py` —que importa a `agents.py`—
tendríamos un ciclo.
"""

from pydantic import BaseModel, ConfigDict, Field


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
