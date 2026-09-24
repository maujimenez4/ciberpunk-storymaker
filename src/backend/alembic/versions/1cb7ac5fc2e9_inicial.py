"""inicial

Revision ID: 1cb7ac5fc2e9
Revises:
Create Date: 2026-09-23 21:38:50.050436

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "1cb7ac5fc2e9"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
