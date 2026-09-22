"""Casos de uso de la feature `obra`."""

from app.commons.domain import Reloj
from app.features.obra.repository import RepositorioDeObras
from app.features.obra.schemas import Brief, ObraCreada


def crear_obra(
    brief: Brief, repositorio: RepositorioDeObras, reloj: Reloj
) -> ObraCreada:
    """CU-01, RF-OBR-01: arrancar una obra desde un brief.

    El reloj entra por parametro y no se llama a `datetime.now()` aqui: es lo
    que hace reproducible cualquier test sobre fechas (RI-13).
    """
    return repositorio.crear(brief, reloj.ahora())
