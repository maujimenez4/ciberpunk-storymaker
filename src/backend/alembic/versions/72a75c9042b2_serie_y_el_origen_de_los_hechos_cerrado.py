"""serie y el origen de los hechos, cerrado

Revision ID: 72a75c9042b2
Revises: 7cbf6d625fae
Create Date: 2026-09-23 22:07:52.304781

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72a75c9042b2"
down_revision: str | Sequence[str] | None = "7cbf6d625fae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "serie",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("canon_compartido", sa.Boolean(), nullable=False),
        sa.Column("orden_de_lectura", sa.JSON(), nullable=False),
        sa.Column("personajes_recurrentes", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # La clave ajena va NOMBRADA a mano. `--autogenerate` la emitio como
    # `create_foreign_key(None, ...)` y en modo batch eso muere con
    # "Constraint must have a name": SQLite no altera tablas, asi que batch la
    # recrea, y para recrear una restriccion hay que saber como se llama.
    with op.batch_alter_table("obra", schema=None) as batch_op:
        batch_op.add_column(sa.Column("serie_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_obra_serie_id_serie", "serie", ["serie_id"], ["id"])

    # Y este CheckConstraint va a mano porque `--autogenerate` NO los compara:
    # esta en el modelo desde este commit y la migracion no lo habria traido.
    # `naming_convention` es necesario aparte: al recrear `hecho_canon`, su
    # clave ajena a `obra` viene sin nombre de la migracion inicial.
    with op.batch_alter_table(
        "hecho_canon",
        schema=None,
        naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"},
    ) as batch_op:
        batch_op.create_check_constraint(
            "ck_hecho_origen_valido",
            "origen IN ('escena', 'brief', 'edicion_humana')",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "hecho_canon",
        schema=None,
        naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"},
    ) as batch_op:
        batch_op.drop_constraint("ck_hecho_origen_valido", type_="check")

    with op.batch_alter_table("obra", schema=None) as batch_op:
        batch_op.drop_constraint("fk_obra_serie_id_serie", type_="foreignkey")
        batch_op.drop_column("serie_id")

    op.drop_table("serie")
