"""API publica de la feature `outline`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.outline.repository import RepositorioDeOutline
from app.features.outline.router import router
from app.features.outline.schemas import (
    BEATS_OBLIGATORIOS,
    BeatDeGenero,
    CapituloDeOutline,
    EscenaDeOutline,
    Outline,
    OutlineInvalido,
    ParteDeOutline,
    Ubicacion,
)
from app.features.outline.service import generar_outline

__all__ = [
    "BEATS_OBLIGATORIOS",
    "BeatDeGenero",
    "CapituloDeOutline",
    "EscenaDeOutline",
    "Outline",
    "OutlineInvalido",
    "ParteDeOutline",
    "RepositorioDeOutline",
    "router",
    "Ubicacion",
    "generar_outline",
]
