"""add assessment system models

Revision ID: assessment_models_001
Revises: ea90afc69273
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'assessment_models_001'
down_revision = 'ea90afc69273'
branch_labels = None
depends_on = None

def upgrade():
    # Create assessment system tables
    
    # Topics table
    op.create_table('topics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=50), nullable=False),
        sa.Column('grade_level', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_topics_tenant_id'), 'topics', ['tenant_id'], unique=False)
    
    # Categories table
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True, default='#007bff'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_tenant_id'), 'categories', ['tenant_id'], unique=False)
    
    # Questions table
    op.create_table('questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.Enum('MULTIPLE_CHOICE', 'TRUE_FALSE', 'SHORT_ANSWER', 'ESSAY', name='questiontype'), nullable=False),
        sa.Column('difficulty_level', sa.Enum('EASY', 'MEDIUM', 'HARD', name='difficultylevel'), nullable=True, default='MEDIUM'),
        sa.Column('options', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('correct_answer', sa.String(length=500), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True, default=1),
        sa.Column('time_limit', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True, default=1),
        sa.Column('original_source', sa.String(length=100), nullable=True),
        sa.Column('import_batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_tenant_id'), 'questions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_questions_topic_id'), 'questions', ['topic_id'], unique=False)
    
    # Question categories association table
    op.create_table('question_categories',
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('question_id', 'category_id')
    )
    
    # Quizzes table
    op.create_table('quizzes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('allow_retakes', sa.Boolean(), nullable=True, default=False),
        sa.Column('show_results_immediately', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_class_id'), 'quizzes', ['class_id'], unique=False)
    op.create_index(op.f('ix_quizzes_teacher_id'), 'quizzes', ['teacher_id'], unique=False)
    op.create_index(op.f('ix_quizzes_tenant_id'), 'quizzes', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_quizzes_topic_id'), 'quizzes', ['topic_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_quizzes_topic_id'), table_name='quizzes')
    op.drop_index(op.f('ix_quizzes_tenant_id'), table_name='quizzes')
    op.drop_index(op.f('ix_quizzes_teacher_id'), table_name='quizzes')
    op.drop_index(op.f('ix_quizzes_class_id'), table_name='quizzes')
    op.drop_table('quizzes')
    op.drop_table('question_categories')
    op.drop_index(op.f('ix_questions_topic_id'), table_name='questions')
    op.drop_index(op.f('ix_questions_tenant_id'), table_name='questions')
    op.drop_table('questions')
    op.drop_index(op.f('ix_categories_tenant_id'), table_name='categories')
    op.drop_table('categories')
    op.drop_index(op.f('ix_topics_tenant_id'), table_name='topics')
    op.drop_table('topics')