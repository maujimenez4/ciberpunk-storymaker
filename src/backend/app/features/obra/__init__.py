"""API publica de la feature `obra`.

Lo unico importable desde fuera (§5.2 regla 1).
"""

from app.features.obra.biblia import (
    Biblia,
    DistanciaDeBiblia,
    LugarDeBiblia,
    PersonajeDeBiblia,
    ReglaDeMundoDeBiblia,
    SalidaDeAgenteInvalida,
    VersionDeBiblia,
)
from app.features.obra.repository import RepositorioDeObras
from app.features.obra.schemas import Brief, ObraCreada
from app.features.obra.service import crear_obra, generar_biblia

__all__ = [
    "Biblia",
    "DistanciaDeBiblia",
    "LugarDeBiblia",
    "PersonajeDeBiblia",
    "ReglaDeMundoDeBiblia",
    "Brief",
    "ObraCreada",
    "RepositorioDeObras",
    "SalidaDeAgenteInvalida",
    "VersionDeBiblia",
    "crear_obra",
    "generar_biblia",
]
