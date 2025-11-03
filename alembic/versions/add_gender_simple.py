"""Add gender field to school_authorities - simple

Revision ID: add_gender_simple
Revises: 9a359cc9ef24
Create Date: 2025-11-03 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_gender_simple'
down_revision: Union[str, None] = '9a359cc9ef24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gender column to school_authorities table
    op.add_column('school_authorities', sa.Column('gender', sa.String(length=10), nullable=True))


def downgrade() -> None:
    # Remove gender column from school_authorities table
    op.drop_column('school_authorities', 'gender')