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
from app.features.canon.schemas import (
    Extraccion,
    ExtraccionInvalida,
    ResultadoDeExtraccion,
)
from app.features.canon.service import extraer_de_escena

__all__ = [
    "EstadoEnT",
    "Extraccion",
    "ExtraccionInvalida",
    "Evento",
    "HechoCanon",
    "RepositorioDeCanon",
    "ResultadoDeExtraccion",
    "derivar_estado_en_t",
    "extraer_de_escena",
]
