"""Add assigned_teachers column to classes table

Revision ID: add_assigned_teachers
Revises: 81dae1fc3e13
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_assigned_teachers'
down_revision: Union[str, None] = ('add_teacher_fields_optional', 'add_teacher_individual_fields', 'make_admission_number_optional')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add assigned_teachers column as JSON
    op.add_column('classes', sa.Column('assigned_teachers', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove assigned_teachers column
    op.drop_column('classes', 'assigned_teachers')