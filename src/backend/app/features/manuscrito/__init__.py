"""API publica de la feature `manuscrito`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.manuscrito.repository import (
    FragmentoDeManuscrito,
    Manuscrito,
    RepositorioDeManuscrito,
)

__all__ = ["FragmentoDeManuscrito", "Manuscrito", "RepositorioDeManuscrito"]
