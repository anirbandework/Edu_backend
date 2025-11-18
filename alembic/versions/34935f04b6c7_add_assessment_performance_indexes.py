"""add_assessment_performance_indexes

Revision ID: 34935f04b6c7
Revises: assessment_models_001
Create Date: 2025-11-18 12:05:57.795215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34935f04b6c7'
down_revision: Union[str, None] = 'assessment_models_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Critical performance indexes for 100k users (without CONCURRENTLY for migration)
    op.execute("CREATE INDEX IF NOT EXISTS idx_quiz_attempts_student_tenant ON quiz_attempts(student_id, tenant_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz_submitted ON quiz_attempts(quiz_id, is_submitted, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_quiz_answers_attempt_question ON quiz_answers(attempt_id, question_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_questions_topic_difficulty ON questions(topic_id, difficulty_level, is_deleted)")
    # Skip subject index - column doesn't exist in questions table
    op.execute("CREATE INDEX IF NOT EXISTS idx_quiz_performance_lookup ON quiz_attempts(student_id, tenant_id, is_submitted, created_at DESC) WHERE is_submitted = true")

def downgrade() -> None:
    # Drop performance indexes
    op.execute("DROP INDEX IF EXISTS idx_quiz_attempts_student_tenant")
    op.execute("DROP INDEX IF EXISTS idx_quiz_attempts_quiz_submitted")
    op.execute("DROP INDEX IF EXISTS idx_quiz_answers_attempt_question")
    op.execute("DROP INDEX IF EXISTS idx_questions_topic_difficulty")
    op.execute("DROP INDEX IF EXISTS idx_questions_tenant_subject")
    op.execute("DROP INDEX IF EXISTS idx_quiz_performance_lookup")
