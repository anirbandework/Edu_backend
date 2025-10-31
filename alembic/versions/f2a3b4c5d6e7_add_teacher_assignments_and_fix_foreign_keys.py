"""Add teacher assignments and fix foreign keys

Revision ID: f2a3b4c5d6e7
Revises: e0fba814e11a
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e0fba814e11a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create teacher_assignments table
    op.create_table('teacher_assignments',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('teacher_id', sa.UUID(), nullable=False),
    sa.Column('class_id', sa.UUID(), nullable=False),
    sa.Column('subject_name', sa.String(length=100), nullable=False),
    sa.Column('academic_year', sa.String(length=10), nullable=False),
    sa.Column('is_primary_teacher', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
    sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('teacher_id', 'class_id', 'subject_name', 'academic_year', name='unique_teacher_class_subject')
    )
    op.create_index(op.f('ix_teacher_assignments_class_id'), 'teacher_assignments', ['class_id'], unique=False)
    op.create_index(op.f('ix_teacher_assignments_id'), 'teacher_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_teacher_assignments_teacher_id'), 'teacher_assignments', ['teacher_id'], unique=False)
    op.create_index(op.f('ix_teacher_assignments_tenant_id'), 'teacher_assignments', ['tenant_id'], unique=False)
    
    # Add foreign key constraints to existing tables
    op.create_foreign_key('fk_class_timetables_class_id', 'class_timetables', 'classes', ['class_id'], ['id'])
    op.create_foreign_key('fk_teacher_timetables_teacher_id', 'teacher_timetables', 'teachers', ['teacher_id'], ['id'])
    op.create_foreign_key('fk_attendances_class_id', 'attendances', 'classes', ['class_id'], ['id'])


def downgrade() -> None:
    # Remove foreign key constraints
    op.drop_constraint('fk_attendances_class_id', 'attendances', type_='foreignkey')
    op.drop_constraint('fk_teacher_timetables_teacher_id', 'teacher_timetables', type_='foreignkey')
    op.drop_constraint('fk_class_timetables_class_id', 'class_timetables', type_='foreignkey')
    
    # Drop teacher_assignments table
    op.drop_index(op.f('ix_teacher_assignments_tenant_id'), table_name='teacher_assignments')
    op.drop_index(op.f('ix_teacher_assignments_teacher_id'), table_name='teacher_assignments')
    op.drop_index(op.f('ix_teacher_assignments_id'), table_name='teacher_assignments')
    op.drop_index(op.f('ix_teacher_assignments_class_id'), table_name='teacher_assignments')
    op.drop_table('teacher_assignments')