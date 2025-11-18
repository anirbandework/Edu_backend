"""merge_heads_for_chat

Revision ID: ea90afc69273
Revises: add_assigned_teachers, add_simplified_timetable, chat_001, expand_recipient_type
Create Date: 2025-11-17 02:27:54.616628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea90afc69273'
down_revision: Union[str, None] = ('add_assigned_teachers', 'add_simplified_timetable', 'chat_001', 'expand_recipient_type')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
