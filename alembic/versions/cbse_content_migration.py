"""Add CBSE content management tables

Revision ID: cbse_content_001
Revises: f1a2b3c4d5e6
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'cbse_content_001'
down_revision = '9a359cc9ef24'
branch_labels = None
depends_on = None

def upgrade():
    # Create ENUM types
    cbse_subject_enum = postgresql.ENUM(
        'hindi_a_002', 'hindi_b_085', 'math_standard_041', 
        'math_basic_241', 'english_184', 'computer_165', 'social_science_087',
        name='cbsesubject'
    )
    cbse_subject_enum.create(op.get_bind())
    
    content_type_enum = postgresql.ENUM(
        'book_chunk', 'sample_paper', 'practice_set',
        name='contenttype'
    )
    content_type_enum.create(op.get_bind())
    
    section_type_enum = postgresql.ENUM(
        'section_a', 'section_b', 'section_c', 'section_d', 'section_e',
        name='sectiontype'
    )
    section_type_enum.create(op.get_bind())
    
    # Create book_chunks table
    op.create_table('book_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', cbse_subject_enum, nullable=False),
        sa.Column('chapter_name', sa.String(length=200), nullable=False),
        sa.Column('chunk_title', sa.String(length=200), nullable=False),
        sa.Column('chunk_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text()),
        sa.Column('key_concepts', postgresql.JSON()),
        sa.Column('difficulty_level', sa.String(length=20)),
        sa.Column('estimated_time', sa.Integer()),
        sa.Column('learning_objectives', postgresql.JSON()),
        sa.Column('prerequisite_concepts', postgresql.JSON()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_book_chunks_tenant_id', 'book_chunks', ['tenant_id'])
    
    # Create cbse_sample_papers table
    op.create_table('cbse_sample_papers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', cbse_subject_enum, nullable=False),
        sa.Column('paper_title', sa.String(length=200), nullable=False),
        sa.Column('paper_code', sa.String(length=10), nullable=False),
        sa.Column('duration_hours', sa.Integer()),
        sa.Column('theory_marks', sa.Integer()),
        sa.Column('internal_marks', sa.Integer()),
        sa.Column('instructions', sa.Text()),
        sa.Column('sections', postgresql.JSON()),
        sa.Column('is_official_pattern', sa.Boolean()),
        sa.Column('academic_year', sa.String(length=10)),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cbse_sample_papers_tenant_id', 'cbse_sample_papers', ['tenant_id'])
    
    # Create paper_sections table
    op.create_table('paper_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_type', section_type_enum, nullable=False),
        sa.Column('section_name', sa.String(length=100), nullable=False),
        sa.Column('total_marks', sa.Integer(), nullable=False),
        sa.Column('question_count', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('question_pattern', postgresql.JSON()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['cbse_sample_papers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create section_questions table
    op.create_table('section_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_number', sa.String(length=10), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=20), nullable=False),
        sa.Column('marks', sa.Integer(), nullable=False),
        sa.Column('options', postgresql.JSON()),
        sa.Column('correct_answer', sa.Text()),
        sa.Column('marking_scheme', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['section_id'], ['paper_sections.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('section_questions')
    op.drop_table('paper_sections')
    op.drop_index('ix_cbse_sample_papers_tenant_id', 'cbse_sample_papers')
    op.drop_table('cbse_sample_papers')
    op.drop_index('ix_book_chunks_tenant_id', 'book_chunks')
    op.drop_table('book_chunks')
    
    # Drop ENUM types
    op.execute('DROP TYPE sectiontype')
    op.execute('DROP TYPE contenttype')
    op.execute('DROP TYPE cbsesubject')