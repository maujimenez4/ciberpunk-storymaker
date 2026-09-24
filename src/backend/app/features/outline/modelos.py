"""Las tablas de la feature `outline`: la biblia versionada y los capitulos.

Entran con las de `escena`, `escritura` y `canon` en **una sola migracion**
(Tarea 2 del plan 2, regla 2 del reparto): `alembic revision --autogenerate`
lee `Base.metadata` entera, y dos agentes generando a la vez producen dos
*heads*.

Las claves ajenas van **nombradas**. SQLite no altera tablas: cualquier
migracion que toque una de estas la recrea en modo batch, y ahi una restriccion
anonima muere con «Constraint must have a name».
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.commons.db.base import Base
from app.commons.domain.reloj import RelojDelSistema

# `definitions.md` §4.1: un capitulo mide de 1.000 a 1.500 palabras. No es un
# valor por defecto sino el rango declarado, y por eso lo sostiene la base.
EXTENSION_MINIMA = 1000
EXTENSION_MAXIMA = 1500


class VersionObra(Base):
    """El estado congelado de la biblia con el que se escribio un tramo (RF-PLA-01).

    Cambiar la biblia no edita la anterior: crea otra version. Cada `Escena`
    apunta a la que estaba vigente cuando se escribio, y eso es lo que permite
    releer un capitulo sabiendo **con que hechos** se escribio, no con cuales
    estan hoy en la biblia.

    `biblia` es JSON y no un arbol de tablas a proposito: lo que se congela es
    un documento entero, y partirlo en filas obligaria a versionar cada una.
    """

    __tablename__ = "version_obra"
    __table_args__ = (UniqueConstraint("obra_id", "numero", name="uq_version_obra_obra_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_version_obra_obra_id"))
    numero: Mapped[int]
    biblia: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    vigente_desde: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: RelojDelSistema().ahora()
    )


class Capitulo(Base):
    """Unidad de **lectura** y de ritmo; es donde el lector decide si sigue.

    Es una tabla distinta de `escena` y hoy la cardinalidad es 1:1 (decision
    **P-C** del plan 2). No se colapsan: el capitulo es unidad de lectura y la
    escena de generacion, y si la extension crece la cardinalidad vuelve a
    `1..*` sin migrar datos. Colapsarlas ahorraria una tabla hoy y costaria una
    migracion de datos despues.

    `resumen_id` no vive aqui sino al reves -- `resumen_capitulo.capitulo_id` --
    para no crear un ciclo de claves ajenas entre las dos tablas.
    """

    __tablename__ = "capitulo"
    __table_args__ = (
        CheckConstraint("length(trim(lugar)) > 0", name="ck_capitulo_lugar_no_vacio"),
        CheckConstraint("length(trim(objetivo)) > 0", name="ck_capitulo_objetivo_no_vacio"),
        CheckConstraint("length(trim(obstaculo)) > 0", name="ck_capitulo_obstaculo_no_vacio"),
        CheckConstraint(
            "length(trim(giro_de_valor_previsto)) > 0",
            name="ck_capitulo_giro_de_valor_previsto_no_vacio",
        ),
        UniqueConstraint("obra_id", "numero", name="uq_capitulo_obra_numero"),
        CheckConstraint(
            f"extension_objetivo BETWEEN {EXTENSION_MINIMA} AND {EXTENSION_MAXIMA}",
            name="ck_capitulo_extension_objetivo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    obra_id: Mapped[int] = mapped_column(ForeignKey("obra.id", name="fk_capitulo_obra_id"))
    numero: Mapped[int]
    titulo: Mapped[str | None] = mapped_column(String(200))
    pov_dominante: Mapped[str] = mapped_column(String(120))
    gancho_de_apertura: Mapped[str] = mapped_column(String(500))
    tipo_de_corte_final: Mapped[str] = mapped_column(String(60))
    extension_objetivo: Mapped[int]

    # RF-PLA-04: los cuatro que faltaban. El requisito pide POV, lugar,
    # objetivo, obstaculo y giro previsto; la tabla tenia solo el primero, asi
    # que el outline se producia, se validaba, la API lo devolvia entero y se
    # perdia al guardar. Lo destapo T3 al cerrar la ola 2 de la Fase 2.
    lugar: Mapped[str] = mapped_column(String(200))
    objetivo: Mapped[str] = mapped_column(String(500))
    obstaculo: Mapped[str] = mapped_column(String(500))
    giro_de_valor_previsto: Mapped[str] = mapped_column(String(200))
