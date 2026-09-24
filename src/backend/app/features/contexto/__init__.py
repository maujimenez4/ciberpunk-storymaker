"""La UNICA puerta de entrada a la feature `contexto` (`CLAUDE.md` §5.1).

Lo que no esta aqui no se importa desde fuera. Hoy solo esta el presupuesto de
la llamada; el Ensamblador (T6) entra despues y por esta misma puerta.
"""

from app.features.contexto.presupuesto import (
    TECHO_POR_LLAMADA,
    TOPES,
    Capa,
    Desglose,
    LineaDeCapa,
    Pieza,
    presupuestar,
)

__all__ = [
    "TECHO_POR_LLAMADA",
    "TOPES",
    "Capa",
    "Desglose",
    "LineaDeCapa",
    "Pieza",
    "presupuestar",
]
