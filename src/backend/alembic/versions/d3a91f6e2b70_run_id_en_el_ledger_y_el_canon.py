"""run_id en el ledger y en el canon

Plan 5, T1 (parte de `canon` y `obra`), P-6. `evento` y `hecho_canon` no sabian
que corrida los escribio, y el guardia de idempotencia los reconocia por escena:
al regenerar un capitulo integrado, la corrida de ayer tapaba la de hoy. Nulo a
proposito: las filas anteriores no tienen corrida y no se les puede inventar.

Revision ID: d3a91f6e2b70
Revises: 5b7e0a1c9d42
Create Date: 2026-09-24 20:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3a91f6e2b70"
down_revision: str | Sequence[str] | None = "5b7e0a1c9d42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evento", sa.Column("run_id", sa.String(length=60), nullable=True))
    op.create_index("ix_evento_run_id", "evento", ["run_id"])
    op.add_column("hecho_canon", sa.Column("run_id", sa.String(length=60), nullable=True))
    op.create_index("ix_hecho_canon_run_id", "hecho_canon", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_hecho_canon_run_id", table_name="hecho_canon")
    op.drop_index("ix_evento_run_id", table_name="evento")
    # `DROP COLUMN` nativo (SQLite >= 3.35) y no el modo batch: batch recrea la
    # tabla y `evento` perderia sus disparadores de *append-only*.
    op.execute("ALTER TABLE hecho_canon DROP COLUMN run_id")
    op.execute("ALTER TABLE evento DROP COLUMN run_id")
