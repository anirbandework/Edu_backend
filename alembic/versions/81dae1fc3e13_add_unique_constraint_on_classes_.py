"""add unique constraint on classes composite key

Revision ID: 81dae1fc3e13
Revises: e0fba814e11a
Create Date: 2025-10-18 05:43:54.131849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81dae1fc3e13'
down_revision: Union[str, None] = 'e0fba814e11a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_class_identity",
        "classes",
        ["tenant_id", "class_name", "section", "academic_year"],
    )

def downgrade() -> None:
    op.drop_constraint("uq_class_identity", "classes", type_="unique")
