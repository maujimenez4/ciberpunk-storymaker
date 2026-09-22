"""Entorno de Alembic.

Sincrono a proposito: las migraciones no compiten con nada y el driver async
solo anade ceremonia. La URL llega por `-x url=...` o por STORYMAKER_RUTA_BASE_DATOS.
"""

import os

from alembic import context
from sqlalchemy import create_engine, event

config = context.config
argumentos = context.get_x_argument(as_dictionary=True)
URL = argumentos.get("url") or "sqlite:///" + os.environ.get(
    "STORYMAKER_RUTA_BASE_DATOS", "obra.db"
)


def _claves_ajenas(conexion, _):  # type: ignore[no-untyped-def]
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def run_migrations_online() -> None:
    motor = create_engine(URL)
    event.listens_for(motor, "connect")(_claves_ajenas)
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
