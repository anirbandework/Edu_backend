"""Add question bank management features

Revision ID: question_bank_mgmt
Revises: quiz_system_migration
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'question_bank_mgmt'
down_revision = 'quiz_system_migration'
branch_labels = None
depends_on = None

def upgrade():
    # Create categories table
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_tenant_id'), 'categories', ['tenant_id'], unique=False)

    # Create question_templates table
    op.create_table('question_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', sa.Enum('MULTIPLE_CHOICE', 'TRUE_FALSE', 'SHORT_ANSWER', 'ESSAY', name='templatetype'), nullable=False),
        sa.Column('template_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_templates_tenant_id'), 'question_templates', ['tenant_id'], unique=False)

    # Create question_versions table
    op.create_table('question_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('correct_answer', sa.String(length=500), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_versions_question_id'), 'question_versions', ['question_id'], unique=False)

    # Create question_categories association table
    op.create_table('question_categories',
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.PrimaryKeyConstraint('question_id', 'category_id')
    )

    # Add new columns to questions table
    op.add_column('questions', sa.Column('version', sa.Integer(), nullable=True))
    op.add_column('questions', sa.Column('original_source', sa.String(length=100), nullable=True))
    op.add_column('questions', sa.Column('import_batch_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Set default version for existing questions
    op.execute("UPDATE questions SET version = 1 WHERE version IS NULL")

def downgrade():
    # Remove new columns from questions table
    op.drop_column('questions', 'import_batch_id')
    op.drop_column('questions', 'original_source')
    op.drop_column('questions', 'version')
    
    # Drop tables
    op.drop_table('question_categories')
    op.drop_index(op.f('ix_question_versions_question_id'), table_name='question_versions')
    op.drop_table('question_versions')
    op.drop_index(op.f('ix_question_templates_tenant_id'), table_name='question_templates')
    op.drop_table('question_templates')
    op.drop_index(op.f('ix_categories_tenant_id'), table_name='categories')
    op.drop_table('categories')