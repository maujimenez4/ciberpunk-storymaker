from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.db.base import Base
from app.commons.db.motor import crear_motor
from app.commons.db.sesion import obtener_sesion
from app.commons.llm.cliente import obtener_cliente_modelo
from app.commons.llm.doble import DobleDeterminista
from app.features.obra.modelos import Obra
from app.main import crear_app


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


@pytest.fixture
def respuestas_del_modelo() -> dict[str, str]:
    """Lo que el doble devuelve, por subcadena del prompt. Vacio por defecto.

    Se sobrescribe en el modulo de tests que lo necesite. Vacio, el doble lanza
    `RespuestaNoPreparada`: un test que llama al modelo sin haberlo preparado
    esta mal escrito, y es mejor que falle a que reciba algo inventado.
    """
    return {}


@pytest.fixture
def cliente(sesion: AsyncSession, respuestas_del_modelo: dict[str, str]) -> Iterator[TestClient]:
    """La aplicacion entera, sobre **la misma sesion** que el test.

    No es un detalle: los tests de los endpoints llaman y despues cuentan filas.
    Si la aplicacion abriera su propio motor, contaria sobre otra base y
    `cuenta_obras` devolveria 0 con la obra recien creada.

    El cliente de modelo se sustituye por el doble por RNF-FIA-01 y CA-4: la
    suite corre sin red y sin credenciales. Sin esta sobrescritura,
    `obtener_cliente_modelo` levanta `NotImplementedError` — en esta fase no hay
    proveedor real, y eso es deliberado (ver Desviaciones).
    """
    app = crear_app()
    app.dependency_overrides[obtener_sesion] = lambda: sesion
    app.dependency_overrides[obtener_cliente_modelo] = lambda: DobleDeterminista(
        respuestas_del_modelo
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
