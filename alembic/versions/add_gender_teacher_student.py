"""Add gender field to teachers and students

Revision ID: add_gender_teacher_student
Revises: add_gender_simple
Create Date: 2025-11-03 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_gender_teacher_student'
down_revision: Union[str, None] = 'add_gender_simple'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gender column to teachers table
    op.add_column('teachers', sa.Column('gender', sa.String(length=10), nullable=True))
    
    # Add gender column to students table
    op.add_column('students', sa.Column('gender', sa.String(length=10), nullable=True))


def downgrade() -> None:
    # Remove gender column from teachers table
    op.drop_column('teachers', 'gender')
    
    # Remove gender column from students table
    op.drop_column('students', 'gender')