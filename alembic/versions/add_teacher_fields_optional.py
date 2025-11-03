"""Add optional individual fields to teachers table

Revision ID: add_teacher_fields_optional
Revises: add_gender_teacher_student
Create Date: 2025-11-03 21:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_teacher_fields_optional'
down_revision: Union[str, None] = 'add_gender_teacher_student'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add optional individual fields to teachers table
    op.add_column('teachers', sa.Column('first_name', sa.String(length=50), nullable=True))
    op.add_column('teachers', sa.Column('last_name', sa.String(length=50), nullable=True))
    op.add_column('teachers', sa.Column('email', sa.String(length=100), nullable=True))
    op.add_column('teachers', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('teachers', sa.Column('date_of_birth', sa.DateTime(), nullable=True))
    op.add_column('teachers', sa.Column('address', sa.String(length=500), nullable=True))
    op.add_column('teachers', sa.Column('position', sa.String(length=100), nullable=True))
    op.add_column('teachers', sa.Column('joining_date', sa.DateTime(), nullable=True))
    op.add_column('teachers', sa.Column('role', sa.String(length=20), nullable=False, server_default='teacher'))
    op.add_column('teachers', sa.Column('qualification', sa.String(length=500), nullable=True))
    op.add_column('teachers', sa.Column('experience_years', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('teachers', sa.Column('teacher_details', sa.JSON(), nullable=True))
    
    # Create index on email
    op.create_index(op.f('ix_teachers_email'), 'teachers', ['email'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index(op.f('ix_teachers_email'), table_name='teachers')
    
    # Remove individual fields from teachers table
    op.drop_column('teachers', 'teacher_details')
    op.drop_column('teachers', 'experience_years')
    op.drop_column('teachers', 'qualification')
    op.drop_column('teachers', 'role')
    op.drop_column('teachers', 'joining_date')
    op.drop_column('teachers', 'position')
    op.drop_column('teachers', 'address')
    op.drop_column('teachers', 'date_of_birth')
    op.drop_column('teachers', 'phone')
    op.drop_column('teachers', 'email')
    op.drop_column('teachers', 'last_name')
    op.drop_column('teachers', 'first_name')