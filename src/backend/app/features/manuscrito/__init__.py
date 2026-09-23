"""API publica de la feature `manuscrito`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.manuscrito.repository import (
    FragmentoDeManuscrito,
    Manuscrito,
    RepositorioDeManuscrito,
)
from app.features.manuscrito.service import a_markdown, a_pdf, exportar

__all__ = [
    "FragmentoDeManuscrito",
    "Manuscrito",
    "RepositorioDeManuscrito",
    "a_markdown",
    "a_pdf",
    "exportar",
]
