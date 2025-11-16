"""Add comprehensive quiz system tables

Revision ID: quiz_system_001
Revises: f1a2b3c4d5e6
Create Date: 2024-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '9a359cc9ef24'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create enum types
    difficulty_level_enum = postgresql.ENUM('easy', 'medium', 'hard', name='difficultylevel')
    difficulty_level_enum.create(op.get_bind())
    
    question_type_enum = postgresql.ENUM('multiple_choice', 'true_false', 'short_answer', 'essay', name='questiontype')
    question_type_enum.create(op.get_bind())
    
    # Create topics table
    op.create_table('topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=50), nullable=False),
        sa.Column('grade_level', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_topics_id'), 'topics', ['id'], unique=False)
    op.create_index(op.f('ix_topics_tenant_id'), 'topics', ['tenant_id'], unique=False)
    
    # Create questions table
    op.create_table('questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', question_type_enum, nullable=False),
        sa.Column('difficulty_level', difficulty_level_enum, nullable=True),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('correct_answer', sa.String(length=500), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('time_limit', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)
    op.create_index(op.f('ix_questions_tenant_id'), 'questions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_questions_topic_id'), 'questions', ['topic_id'], unique=False)
    
    # Create quizzes table
    op.create_table('quizzes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('class_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('teacher_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('total_points', sa.Integer(), nullable=False),
        sa.Column('time_limit', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('allow_retakes', sa.Boolean(), nullable=True),
        sa.Column('show_results_immediately', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_class_id'), 'quizzes', ['class_id'], unique=False)
    op.create_index(op.f('ix_quizzes_id'), 'quizzes', ['id'], unique=False)
    op.create_index(op.f('ix_quizzes_tenant_id'), 'quizzes', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_quizzes_topic_id'), 'quizzes', ['topic_id'], unique=False)
    
    # Create quiz_questions table
    op.create_table('quiz_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('quiz_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_number', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_questions_id'), 'quiz_questions', ['id'], unique=False)
    op.create_index(op.f('ix_quiz_questions_question_id'), 'quiz_questions', ['question_id'], unique=False)
    op.create_index(op.f('ix_quiz_questions_quiz_id'), 'quiz_questions', ['quiz_id'], unique=False)
    
    # Create quiz_attempts table
    op.create_table('quiz_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quiz_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('total_score', sa.Integer(), nullable=True),
        sa.Column('max_score', sa.Integer(), nullable=False),
        sa.Column('percentage', sa.Integer(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('is_submitted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_attempts_id'), 'quiz_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_quiz_attempts_quiz_id'), 'quiz_attempts', ['quiz_id'], unique=False)
    op.create_index(op.f('ix_quiz_attempts_student_id'), 'quiz_attempts', ['student_id'], unique=False)
    op.create_index(op.f('ix_quiz_attempts_tenant_id'), 'quiz_attempts', ['tenant_id'], unique=False)
    
    # Create quiz_answers table
    op.create_table('quiz_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_answer', sa.Text(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('points_earned', sa.Integer(), nullable=True),
        sa.Column('time_taken', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['attempt_id'], ['quiz_attempts.id'], ),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_answers_attempt_id'), 'quiz_answers', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_quiz_answers_id'), 'quiz_answers', ['id'], unique=False)
    op.create_index(op.f('ix_quiz_answers_question_id'), 'quiz_answers', ['question_id'], unique=False)

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('quiz_answers')
    op.drop_table('quiz_attempts')
    op.drop_table('quiz_questions')
    op.drop_table('quizzes')
    op.drop_table('questions')
    op.drop_table('topics')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS questiontype')
    op.execute('DROP TYPE IF EXISTS difficultylevel')