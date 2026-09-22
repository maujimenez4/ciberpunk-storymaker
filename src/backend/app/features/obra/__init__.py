"""API publica de la feature `obra`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.obra.repository import RepositorioDeObras
from app.features.obra.schemas import Brief, ObraCreada
from app.features.obra.service import crear_obra

__all__ = ["Brief", "ObraCreada", "RepositorioDeObras", "crear_obra"]
