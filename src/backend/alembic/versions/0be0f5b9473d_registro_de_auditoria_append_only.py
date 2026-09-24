"""registro de auditoria append-only

Revision ID: 0be0f5b9473d
Revises: 72a75c9042b2
Create Date: 2026-09-23 22:16:04.180330

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0be0f5b9473d"
down_revision: str | Sequence[str] | None = "72a75c9042b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # El `CheckConstraint` SI aparece aqui, y conviene decir por que, porque la
    # Tarea 4 dejo anotado lo contrario y las dos cosas son ciertas:
    # `--autogenerate` no **compara** restricciones de comprobacion, asi que una
    # anadida a una tabla que ya existe no sale sola —eso es lo que le paso a
    # `hecho_canon`—; pero una tabla NUEVA se emite con su `__table_args__`
    # entero. Se ha verificado leyendo el esquema de la base migrada, no fiandose
    # de esta linea.
    #
    # La clave ajena va NOMBRADA a mano. `--autogenerate` la emitio sin nombre, y
    # SQLite no altera tablas: la primera migracion que toque esta la recreara en
    # modo batch y ahi una restriccion anonima muere con "Constraint must have a
    # name". A `hecho_canon` le costo un `naming_convention`; nombrarla al
    # crearla cuesta una linea.
    op.create_table(
        "registro_auditoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("obra_id", sa.Integer(), nullable=False),
        sa.Column("momento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(length=10), nullable=False),
        sa.Column("motivo", sa.String(length=500), nullable=False),
        sa.Column("evidencia", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('permitido', 'bloqueado')", name="ck_registro_auditoria_decision"
        ),
        sa.ForeignKeyConstraint(["obra_id"], ["obra.id"], name="fk_registro_auditoria_obra_id"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("registro_auditoria")
