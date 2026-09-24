from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.db.base import Base
from app.commons.db.motor import crear_motor


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
