"""merge_heads

Revision ID: 9a359cc9ef24
Revises: 8941297970e2, f2a3b4c5d6e7
Create Date: 2025-10-30 03:17:57.606540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a359cc9ef24'
down_revision: Union[str, None] = ('8941297970e2', 'f2a3b4c5d6e7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
