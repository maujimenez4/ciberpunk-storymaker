import asyncio
from logging.config import fileConfig

from alembic import context
from app.commons.config.ajustes import Ajustes
from app.commons.db.base import Base
from app.commons.db.motor import crear_motor
from sqlalchemy.engine import Connection

# Importar aqui los modulos de tablas segun entren: `--autogenerate` solo ve
# lo que este registrado en `Base.metadata` en el momento de correr, y una
# tabla que nadie importo no produce migracion, sin avisar.

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# De `Base` heredan todas las tablas del proyecto (`commons/db/base.py`).
target_metadata = Base.metadata


def _url() -> str:
    """La ruta sale de `Ajustes`, no de `alembic.ini`.

    Una sola base (spec P-07) y un solo sitio que dice donde esta: si la URL
    viviera tambien en el `.ini`, migrar y arrancar apuntarian a ficheros
    distintos en cuanto uno de los dos cambiara.
    """
    return f"sqlite+aiosqlite:///{Ajustes.desde_entorno().ruta_db}"


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse a nada."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # `render_as_batch`: SQLite no sabe hacer casi ningun ALTER TABLE, asi que
    # Alembic recrea la tabla y copia. Sin esto, la primera migracion que
    # quite una columna o anada una restriccion falla al aplicarse.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Reusa `crear_motor`, con lo que las migraciones corren con los mismos
    pragmas que la aplicacion: `foreign_keys=ON` importa al migrar tanto como
    al escribir."""
    conectable = crear_motor(Ajustes.desde_entorno().ruta_db)

    async with conectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await conectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
