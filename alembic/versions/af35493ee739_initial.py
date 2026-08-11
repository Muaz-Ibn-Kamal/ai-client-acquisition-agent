"""initial

Revision ID: af35493ee739
Revises:
Create Date: 2026-08-11 09:59:21.135117

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "af35493ee739"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
