"""Change id column from varchar to uuid

Revision ID: 38ed6337feaf
Revises: ac2deefa9a92
Create Date: 2025-10-03 12:34:12.154135

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '38ed6337feaf'
down_revision: Union[str, None] = 'ac2deefa9a92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add a new UUID column
    op.add_column('tenants', sa.Column('id_new', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Generate UUIDs for existing rows (if any)
    op.execute("UPDATE tenants SET id_new = gen_random_uuid()")
    
    # Drop the old primary key constraint
    op.drop_constraint('tenants_pkey', 'tenants', type_='primary')
    
    # Drop the old id column
    op.drop_column('tenants', 'id')
    
    # Rename the new column to id
    op.alter_column('tenants', 'id_new', new_column_name='id')
    
    # Add the new primary key constraint
    op.create_primary_key('tenants_pkey', 'tenants', ['id'])

def downgrade() -> None:
    # Reverse the process
    op.drop_constraint('tenants_pkey', 'tenants', type_='primary')
    op.alter_column('tenants', 'id', new_column_name='id_new')
    op.add_column('tenants', sa.Column('id', sa.String(), nullable=True))
    op.execute("UPDATE tenants SET id = id_new::varchar")
    op.drop_column('tenants', 'id_new')
    op.create_primary_key('tenants_pkey', 'tenants', ['id'])