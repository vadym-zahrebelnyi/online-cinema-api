"""add refund_requested status

Revision ID: 29c209a0327b
Revises: 5b4f14b545e1
Create Date: 2026-02-07 22:29:52.632117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29c209a0327b'
down_revision: Union[str, Sequence[str], None] = '5b4f14b545e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE paymentstatusenum ADD VALUE 'REFUND_REQUESTED'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
