"""version_publicada.vigente y peticion_de_cambio

Plan 5, T1 (parte de `manuscrito`). La vigente es una columna y no una
deduccion por `MAX(ordinal)`: revertir (RF-PET-08) conserva la revertida, que
sigue teniendo el mayor ordinal. Relleno de datos: la ultima de cada obra pasa
a vigente, para que una obra ya publicada no se quede sin version que leer.

Revision ID: 5b7e0a1c9d42
Revises: c24bf74a966c
Create Date: 2026-09-24 20:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5b7e0a1c9d42"
down_revision: str | Sequence[str] | None = "c24bf74a966c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "version_publicada",
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.execute(
        "UPDATE version_publicada SET vigente = 1 WHERE id IN ("
        "  SELECT id FROM version_publicada AS v"
        "  WHERE v.ordinal = (SELECT MAX(w.ordinal) FROM version_publicada AS w"
        "                     WHERE w.obra_id = v.obra_id)"
        ")"
    )
    op.create_index(
        "uq_version_publicada_vigente",
        "version_publicada",
        ["obra_id"],
        unique=True,
        sqlite_where=sa.text("vigente = 1"),
    )
    op.create_table(
        "peticion_de_cambio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("obra_id", sa.Integer(), nullable=False),
        sa.Column("version_publicada_id", sa.Integer(), nullable=False),
        sa.Column("hecho_canon_id", sa.Integer(), nullable=False),
        sa.Column("texto_pedido", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=12), nullable=False, server_default="registrada"),
        sa.Column("hecho_nuevo_id", sa.Integer(), nullable=True),
        sa.Column("version_producida_id", sa.Integer(), nullable=True),
        sa.Column("resultado", sa.String(length=500), nullable=True),
        sa.Column("run_id", sa.String(length=60), nullable=True),
        sa.ForeignKeyConstraint(["obra_id"], ["obra.id"], name="fk_peticion_obra_id"),
        sa.ForeignKeyConstraint(
            ["version_publicada_id"],
            ["version_publicada.id"],
            name="fk_peticion_version_publicada_id",
        ),
        sa.ForeignKeyConstraint(
            ["hecho_canon_id"], ["hecho_canon.id"], name="fk_peticion_hecho_canon_id"
        ),
        sa.ForeignKeyConstraint(
            ["hecho_nuevo_id"], ["hecho_canon.id"], name="fk_peticion_hecho_nuevo_id"
        ),
        sa.ForeignKeyConstraint(
            ["version_producida_id"],
            ["version_publicada.id"],
            name="fk_peticion_version_producida_id",
        ),
        sa.CheckConstraint(
            "estado IN ('registrada', 'regenerando', 'atendida', 'descartada')",
            name="ck_peticion_estado",
        ),
        sa.CheckConstraint("trim(texto_pedido) <> ''", name="ck_peticion_texto_no_vacio"),
        sa.CheckConstraint(
            "estado NOT IN ('atendida', 'descartada') OR resultado IS NOT NULL",
            name="ck_peticion_terminada_con_resultado",
        ),
    )
    op.create_index("ix_peticion_de_cambio_run_id", "peticion_de_cambio", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_peticion_de_cambio_run_id", table_name="peticion_de_cambio")
    op.drop_table("peticion_de_cambio")
    op.drop_index("uq_version_publicada_vigente", table_name="version_publicada")
    with op.batch_alter_table("version_publicada") as batch:
        batch.drop_column("vigente")
