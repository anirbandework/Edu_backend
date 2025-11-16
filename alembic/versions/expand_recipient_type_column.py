"""expand recipient_type column

Revision ID: expand_recipient_type
Revises: 
Create Date: 2025-11-14 10:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'expand_recipient_type'
down_revision = None  # Set this to your latest migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Expand recipient_type column in notifications table
    op.alter_column('notifications', 'recipient_type',
                    existing_type=sa.VARCHAR(length=12),
                    type_=sa.VARCHAR(length=20),
                    existing_nullable=False)

def downgrade():
    # Revert recipient_type column back to original size
    op.alter_column('notifications', 'recipient_type',
                    existing_type=sa.VARCHAR(length=20),
                    type_=sa.VARCHAR(length=12),
                    existing_nullable=False)