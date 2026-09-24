from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """De ella heredan TODAS las tablas del proyecto.

    Alembic la usa como `target_metadata`: una tabla que no herede de aqui no
    aparece en `--autogenerate` y su migracion no existe.
    """
