"""API publica de la feature `escena`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.escena.repository import (
    EscenaPersistida,
    RepositorioDeEscenas,
    VersionDeTexto,
)
from app.features.escena.router import HistorialDeEscena, VersionEnRespuesta, router
from app.features.escena.schemas import (
    FichaDeEscena,
    FichaInvalida,
    FichaPersistida,
    PropuestaDeFicha,
)
from app.features.escena.service import planificar_escena

__all__ = [
    "EscenaPersistida",
    "HistorialDeEscena",
    "VersionEnRespuesta",
    "router",
    "FichaDeEscena",
    "FichaPersistida",
    "FichaInvalida",
    "PropuestaDeFicha",
    "RepositorioDeEscenas",
    "VersionDeTexto",
    "planificar_escena",
]
