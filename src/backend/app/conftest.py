from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.commons.db.base import Base
from app.commons.db.motor import crear_motor
from app.commons.db.sesion import obtener_sesion
from app.commons.llm.cliente import obtener_cliente_modelo
from app.commons.llm.doble import DobleDeterminista
from app.features.canon.modelos import Evento  # noqa: F401  (registra las tablas de `canon`)
from app.features.escena.modelos import Escena
from app.features.escritura.modelos import VersionTexto  # noqa: F401  (registra `escritura`)
from app.features.obra.modelos import HechoCanon, Obra
from app.features.outline.modelos import Capitulo, VersionObra
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


@dataclass(frozen=True)
class ObraConOutline:
    """Lo que devuelve la fixture `obra_con_outline`, con nombre.

    Es un `dataclass` y no una tupla porque la usan cinco tareas de la Fase 2 y
    una tupla de cinco elementos se desempaqueta mal en cuanto entra un sexto.
    """

    obra: Obra
    version_obra: VersionObra
    capitulos: list[Capitulo]
    escena: Escena
    hecho_canon: HechoCanon


@pytest.fixture
async def obra_con_outline(sesion: AsyncSession, obra: Obra) -> ObraConOutline:
    """Una obra planificada: biblia versionada, diez capitulos y la escena del primero.

    Es el punto de partida de casi todo lo de esta fase, y por eso vive aqui y
    no en una feature: la usan `escena`, `escritura`, `canon` y `contexto`, y
    ninguna de las cuatro puede importar de las otras (`CLAUDE.md` §5.1).

    **Diez capitulos y una sola escena.** Los diez son RF-PLA-02; la escena es
    una porque la cardinalidad de hoy es 1:1 (P-C) y porque lo que las tareas
    siguientes necesitan es *una escena que exista de verdad*, con su capitulo
    y su version de biblia detras, no diez iguales.

    Hace `flush` y no `commit`, como el resto de fixtures: la sesion revierte al
    terminar el test y ninguno hereda escrituras del anterior.
    """
    version_obra = VersionObra(obra_id=obra.id, numero=1, biblia={"protagonista": "Nadia"})
    sesion.add(version_obra)
    await sesion.flush()

    capitulos = [
        Capitulo(
            obra_id=obra.id,
            numero=n,
            titulo=f"Capitulo {n}",
            pov_dominante="Nadia",
            gancho_de_apertura="La puerta estaba abierta",
            tipo_de_corte_final="pregunta",
            extension_objetivo=1200,
        )
        for n in range(1, 11)
    ]
    sesion.add_all(capitulos)
    await sesion.flush()

    escena = Escena(
        capitulo_id=capitulos[0].id,
        version_obra_id=version_obra.id,
        orden_discurso=1,
        tiempo_historia="dia 1, manana",
        pov="Nadia",
        lugar="El invernadero",
        presentes=["Nadia", "Teo"],
        objetivo_del_pov="Que Teo confiese",
        obstaculo="Teo no habla de su madre",
        resultado="si-pero",
        valor_entrada="confianza",
        valor_salida="sospecha",
        extension_objetivo=1200,
        densidad_de_dialogo_objetivo=0.4,
        distancia_psiquica=3,
    )
    hecho_canon = HechoCanon(
        obra_id=obra.id,
        entidad="perro",
        atributo="nombre",
        valor="Luna",
        origen="brief",
    )
    sesion.add_all([escena, hecho_canon])
    await sesion.flush()

    return ObraConOutline(
        obra=obra,
        version_obra=version_obra,
        capitulos=capitulos,
        escena=escena,
        hecho_canon=hecho_canon,
    )


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
