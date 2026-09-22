"""API publica de commons/errors."""

from app.commons.errors.errores import (
    ContextBudgetExceeded,
    ErrorDeDominio,
    FalloDeProveedor,
    RecursoNoEncontrado,
    ReglaDeDominioViolada,
    TiempoAgotado,
)
from app.commons.errors.manejadores import CODIGOS, registrar_manejadores

__all__ = [
    "CODIGOS",
    "ContextBudgetExceeded",
    "ErrorDeDominio",
    "FalloDeProveedor",
    "ReglaDeDominioViolada",
    "RecursoNoEncontrado",
    "TiempoAgotado",
    "registrar_manejadores",
]
