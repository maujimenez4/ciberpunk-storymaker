from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.db.base import Base
from app.commons.db.motor import crear_motor
from app.features.obra.modelos import Obra


@pytest.fixture
async def motor(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """Una base por test, en el tmp_path de pytest. Nunca la del desarrollador."""
    motor = crear_motor(tmp_path / "prueba.db")
    async with motor.begin() as con:
        await con.run_sync(Base.metadata.create_all)
    yield motor
    await motor.dispose()


@pytest.fixture
async def sesion(motor: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Por test y con reversion al terminar: ningun test hereda escrituras."""
    async with AsyncSession(motor, expire_on_commit=False) as sesion:
        yield sesion
        await sesion.rollback()


@pytest.fixture
async def obra(sesion: AsyncSession) -> Obra:
    """La obra minima de la que cuelgan vetos y hechos. La usan T8, T9 y T10.

    Sin destinatario: la relacion es 0..1, y las tablas que la consumen solo
    necesitan un `obra_id` que exista de verdad, porque `foreign_keys=ON`.
    """
    obra = Obra(titulo="De prueba", genero="romance", tono="calido", nivel_de_calor=2)
    sesion.add(obra)
    await sesion.flush()
    return obra
