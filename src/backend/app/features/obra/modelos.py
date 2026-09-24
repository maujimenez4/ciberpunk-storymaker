"""Las cuatro tablas de la Fase 1, y solo ellas.

Entran juntas y en una sola migracion porque la spec lo pide en Impacto
tecnico —«Esquema: toda la base de datos. Es la migracion inicial»— y porque
`alembic revision --autogenerate` lee `Base.metadata` **entera**: dos agentes
generando a la vez producen dos *heads* y la cadena deja de ser lineal.
"""

from datetime import date

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.commons.db.base import Base

AMBITOS_DE_VETO = ("global", "obra", "brief")


class Destinatario(Base):
    """De quien es el regalo (`definitions.md` §9.1).

    **No es un `Personaje`** y no se le aplican las reglas de canon narrativo:
    es una persona real, y sus datos entran por el comprador.
    """

    __tablename__ = "destinatario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    edad: Mapped[int]
    rasgos: Mapped[list[str]] = mapped_column(JSON, default=list)
    recuerdos: Mapped[list[str]] = mapped_column(JSON, default=list)
    fecha_de_nacimiento: Mapped[date | None]


class Obra(Base):
    """La novela individual, raiz de casi todo el grafo.

    `destinatario_id` es 0..1 a proposito: una obra sin destinatario es
    legitima; una obra **personalizada** sin el, no.
    """

    __tablename__ = "obra"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    genero: Mapped[str] = mapped_column(String(60))
    tono: Mapped[str] = mapped_column(String(60))
    nivel_de_calor: Mapped[int]
    destinatario_id: Mapped[int | None] = mapped_column(ForeignKey("destinatario.id"))


class PalabraProhibida(Base):
    """Un veto, en uno de los tres ambitos de RF-GUA-01.

    El `CheckConstraint` sobre `ambito` vive aqui y no solo en el servicio por
    el mismo motivo que el de `hecho_canon`: un cuarto ambito escrito por otra
    ruta no tendria quien lo parase.

    `obra_id` es nulo para el ambito `global`, que no pertenece a ninguna obra.
    """

    __tablename__ = "palabra_prohibida"
    __table_args__ = (
        CheckConstraint(
            "ambito IN ('global', 'obra', 'brief')",
            name="ck_palabra_prohibida_ambito",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ambito: Mapped[str] = mapped_column(String(10))
    termino: Mapped[str] = mapped_column(String(200))
    obra_id: Mapped[int | None] = mapped_column(ForeignKey("obra.id"))
    motivo: Mapped[str | None] = mapped_column(String(500))


class HechoCanon(Base):
    """Una afirmacion declarada verdadera.

    `escena_de_origen` es texto y **no** una clave ajena: la tabla `escena` es
    de la Fase 2, y una clave ajena a una tabla que no existe rompe el
    `upgrade head` con `foreign_keys=ON`.

    Nace incompleta a proposito: el `usado_en` por capitulos (RF-MEM-02) entra
    cuando haya capitulos que lo usen.
    """

    __tablename__ = "hecho_canon"
    __table_args__ = (
        CheckConstraint(
            "(origen = 'escena' AND escena_de_origen IS NOT NULL) OR "
            "(origen <> 'escena' AND escena_de_origen IS NULL)",
            name="ck_hecho_origen_coherente",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id"))
    enunciado: Mapped[str] = mapped_column(Text)
    origen: Mapped[str] = mapped_column(String(20))
    escena_de_origen: Mapped[str | None] = mapped_column(String(60))
