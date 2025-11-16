"""make_admission_number_optional

Revision ID: make_admission_number_optional
Revises: f2a3b4c5d6e7
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'make_admission_number_optional'
down_revision = 'e0fba814e11a'
branch_labels = None
depends_on = None


def upgrade():
    # Make admission_number nullable
    op.alter_column('students', 'admission_number',
                    existing_type=sa.VARCHAR(length=20),
                    nullable=True)


def downgrade():
    # Make admission_number non-nullable again
    op.alter_column('students', 'admission_number',
                    existing_type=sa.VARCHAR(length=20),
                    nullable=False)