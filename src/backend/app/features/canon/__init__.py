"""API publica de la feature `canon`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.canon.repository import (
    EstadoEnT,
    Evento,
    HechoCanon,
    RepositorioDeCanon,
    derivar_estado_en_t,
)
from app.features.canon.router import CanonDeObra, HechoEnRespuesta, router
from app.features.canon.schemas import (
    EventoExtraido,
    Extraccion,
    ExtraccionInvalida,
    HechoExtraido,
    HiloExtraido,
    PlantadoExtraido,
    ResultadoDeExtraccion,
)
from app.features.canon.service import extraer_de_escena

__all__ = [
    "CanonDeObra",
    "EstadoEnT",
    "HechoEnRespuesta",
    "router",
    "Extraccion",
    "ExtraccionInvalida",
    "Evento",
    "EventoExtraido",
    "HechoCanon",
    "HechoExtraido",
    "HiloExtraido",
    "PlantadoExtraido",
    "RepositorioDeCanon",
    "ResultadoDeExtraccion",
    "derivar_estado_en_t",
    "extraer_de_escena",
]
