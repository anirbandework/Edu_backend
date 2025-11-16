"""Add simplified timetable columns

Revision ID: add_simplified_timetable
Revises: e0fba814e11a
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_simplified_timetable'
down_revision = '9a359cc9ef24'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to schedule_entries table
    op.add_column('schedule_entries', sa.Column('period_number', sa.Integer(), nullable=True))
    op.add_column('schedule_entries', sa.Column('start_time', sa.Time(), nullable=True))
    op.add_column('schedule_entries', sa.Column('end_time', sa.Time(), nullable=True))
    op.add_column('schedule_entries', sa.Column('teacher_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Make period_id nullable
    op.alter_column('schedule_entries', 'period_id', nullable=True)
    
    # Add index for teacher_id
    op.create_index('ix_schedule_entries_teacher_id', 'schedule_entries', ['teacher_id'])

def downgrade():
    # Remove the added columns
    op.drop_index('ix_schedule_entries_teacher_id', 'schedule_entries')
    op.drop_column('schedule_entries', 'teacher_id')
    op.drop_column('schedule_entries', 'end_time')
    op.drop_column('schedule_entries', 'start_time')
    op.drop_column('schedule_entries', 'period_number')
    
    # Make period_id non-nullable again
    op.alter_column('schedule_entries', 'period_id', nullable=False)