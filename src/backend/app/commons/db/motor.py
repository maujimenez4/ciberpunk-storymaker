"""Fabrica del motor de base de datos (RI-16).

WAL, `foreign_keys` y `busy_timeout` son PRAGMA **por conexion**: SQLite los
olvida al cerrarla. Por eso se aplican en el evento `connect` del pool y no una
sola vez al arrancar. `foreign_keys` es el que mas duele olvidar, porque SQLite
no protesta: simplemente deja de comprobar la integridad referencial.
"""

from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

BUSY_TIMEOUT_MS = 5_000


def _aplicar_pragmas(conexion: Any, _: Any) -> None:
    # Con aiosqlite la conexion es el adaptador de SQLAlchemy, no un
    # sqlite3.Connection: comprobar el tipo aqui deja los PRAGMA sin aplicar.
    cursor = conexion.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


def crear_motor(ruta: Path | str, *, echo: bool = False) -> AsyncEngine:
    """Un fichero SQLite por obra (architecture.md §2). Sin segunda base de datos."""
    motor = create_async_engine(f"sqlite+aiosqlite:///{ruta}", echo=echo)
    event.listens_for(motor.sync_engine, "connect")(_aplicar_pragmas)
    return motor
