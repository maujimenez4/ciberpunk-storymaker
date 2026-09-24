from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

ESPERA_MS = 5000


def crear_motor(ruta: Path) -> AsyncEngine:
    """El motor de la base de la instalacion (RD-01, spec P-07).

    `ruta` es un FICHERO, no una carpeta. Hay una sola base: la obra no vive
    en un fichero aparte, porque `serie` comparte canon entre obras y un
    `comprador` encarga varias. En pruebas, la fixture `motor` le pasa una
    ruta dentro del `tmp_path` de pytest.

    `foreign_keys` y `busy_timeout` SI son por conexion y hay que ponerlos en
    cada una. `journal_mode=WAL` NO: se escribe en la cabecera del fichero y
    persiste. Se deja aqui porque es inofensivo y hace explicita la primera
    creacion, pero que nadie crea que WAL se pierde al cerrar la conexion.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    motor = create_async_engine(f"sqlite+aiosqlite:///{ruta}")

    @event.listens_for(motor.sync_engine, "connect")
    def _pragmas(dbapi_con: Any, _record: Any) -> None:
        cur = dbapi_con.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute(f"PRAGMA busy_timeout={ESPERA_MS}")
        cur.close()

    return motor
