from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.config.ajustes import Ajustes
from app.commons.db.motor import crear_motor


@lru_cache(maxsize=1)
def obtener_motor() -> AsyncEngine:
    """Un solo motor por proceso, sobre una sola base (spec P-07).

    Se cachea porque cada `create_async_engine` abre su propio pool: uno por
    peticion agotaria los descriptores y dejaria conexiones sin cerrar.
    """
    return crear_motor(Ajustes.desde_entorno().ruta_db)


async def obtener_sesion() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI: una sesion por peticion, cerrada al terminar.

    No hace `commit`: quien decide que una unidad de trabajo termino bien es
    el servicio, no el transporte. Lo que no se confirmo se revierte al salir.
    """
    async with AsyncSession(obtener_motor(), expire_on_commit=False) as sesion:
        yield sesion
