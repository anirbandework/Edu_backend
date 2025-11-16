"""Add simplified grades and assessment system using existing tables

Revision ID: f1a2b3c4d5e6
Revises: e0fba814e11a
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = '81dae1fc3e13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip enum creation - using string columns instead
    
    # Create assessments table (uses existing subjects, classes, teachers tables)
    op.create_table('assessments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),  # References existing subjects table
        sa.Column('class_id', sa.UUID(), nullable=False),    # References existing classmodel table
        sa.Column('teacher_id', sa.UUID(), nullable=False),  # References existing teacher table
        sa.Column('assessment_title', sa.String(length=200), nullable=False),
        sa.Column('assessment_type', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('max_marks', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('allow_late_submission', sa.Boolean(), nullable=True, default=False),
        sa.Column('status', sa.String(20), nullable=True, default='draft'),
        sa.Column('academic_year', sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),  # Uses existing subjects table
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),  # Uses existing classes table
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ),   # Uses existing teacher table
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessments_id'), 'assessments', ['id'], unique=False)
    op.create_index(op.f('ix_assessments_tenant_id'), 'assessments', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_assessments_subject_id'), 'assessments', ['subject_id'], unique=False)
    op.create_index(op.f('ix_assessments_class_id'), 'assessments', ['class_id'], unique=False)
    op.create_index(op.f('ix_assessments_teacher_id'), 'assessments', ['teacher_id'], unique=False)

    # Create assessment_submissions table
    op.create_table('assessment_submissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),  # References existing student table
        sa.Column('submission_date', sa.DateTime(), nullable=True),
        sa.Column('is_late', sa.Boolean(), nullable=True, default=False),
        sa.Column('marks_obtained', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('grade_letter', sa.String(length=5), nullable=True),
        sa.Column('is_graded', sa.Boolean(), nullable=True, default=False),
        sa.Column('teacher_feedback', sa.Text(), nullable=True),
        sa.Column('graded_by', sa.UUID(), nullable=True),
        sa.Column('graded_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, default='not_submitted'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),    # Uses existing student table
        sa.ForeignKeyConstraint(['graded_by'], ['teachers.id'], ),     # Uses existing teacher table
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_submissions_id'), 'assessment_submissions', ['id'], unique=False)
    op.create_index(op.f('ix_assessment_submissions_tenant_id'), 'assessment_submissions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_assessment_submissions_assessment_id'), 'assessment_submissions', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_assessment_submissions_student_id'), 'assessment_submissions', ['student_id'], unique=False)

    # Create student_grades table (uses existing students, subjects, classes tables)
    op.create_table('student_grades',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),  # References existing student table
        sa.Column('subject_id', sa.UUID(), nullable=False),  # References existing subjects table
        sa.Column('class_id', sa.UUID(), nullable=False),    # References existing classmodel table
        sa.Column('academic_year', sa.String(length=10), nullable=False),
        sa.Column('term', sa.String(length=20), nullable=True),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('letter_grade', sa.String(length=5), nullable=True),
        sa.Column('gpa', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('is_final', sa.Boolean(), nullable=True, default=False),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('calculated_by', sa.UUID(), nullable=True),
        sa.Column('teacher_comments', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),    # Uses existing student table
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),   # Uses existing subjects table
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),   # Uses existing classes table
        sa.ForeignKeyConstraint(['calculated_by'], ['teachers.id'], ), # Uses existing teacher table
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_student_grades_id'), 'student_grades', ['id'], unique=False)
    op.create_index(op.f('ix_student_grades_tenant_id'), 'student_grades', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_student_grades_student_id'), 'student_grades', ['student_id'], unique=False)
    op.create_index(op.f('ix_student_grades_subject_id'), 'student_grades', ['subject_id'], unique=False)
    op.create_index(op.f('ix_student_grades_class_id'), 'student_grades', ['class_id'], unique=False)

    # Create grade_scales table
    op.create_table('grade_scales',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('scale_name', sa.String(length=50), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
        sa.Column('grade_ranges', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('academic_year', sa.String(length=10), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['school_authorities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_grade_scales_id'), 'grade_scales', ['id'], unique=False)
    op.create_index(op.f('ix_grade_scales_tenant_id'), 'grade_scales', ['tenant_id'], unique=False)

    # Create report_cards table (uses existing students, classes tables)
    op.create_table('report_cards',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),  # References existing student table
        sa.Column('class_id', sa.UUID(), nullable=False),    # References existing classmodel table
        sa.Column('report_period', sa.String(length=20), nullable=False),
        sa.Column('academic_year', sa.String(length=10), nullable=False),
        sa.Column('total_subjects', sa.Integer(), nullable=True),
        sa.Column('subjects_passed', sa.Integer(), nullable=True),
        sa.Column('subjects_failed', sa.Integer(), nullable=True),
        sa.Column('overall_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('overall_gpa', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('overall_grade', sa.String(length=5), nullable=True),
        sa.Column('subject_grades', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('class_teacher_comments', sa.Text(), nullable=True),
        sa.Column('principal_comments', sa.Text(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True, default=False),
        sa.Column('published_date', sa.DateTime(), nullable=True),
        sa.Column('generated_by', sa.UUID(), nullable=True),
        sa.Column('generated_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),      # Uses existing student table
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),     # Uses existing classes table
        sa.ForeignKeyConstraint(['generated_by'], ['school_authorities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_cards_id'), 'report_cards', ['id'], unique=False)
    op.create_index(op.f('ix_report_cards_tenant_id'), 'report_cards', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_report_cards_student_id'), 'report_cards', ['student_id'], unique=False)
    op.create_index(op.f('ix_report_cards_class_id'), 'report_cards', ['class_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_report_cards_class_id'), table_name='report_cards')
    op.drop_index(op.f('ix_report_cards_student_id'), table_name='report_cards')
    op.drop_index(op.f('ix_report_cards_tenant_id'), table_name='report_cards')
    op.drop_index(op.f('ix_report_cards_id'), table_name='report_cards')
    op.drop_table('report_cards')
    
    op.drop_index(op.f('ix_grade_scales_tenant_id'), table_name='grade_scales')
    op.drop_index(op.f('ix_grade_scales_id'), table_name='grade_scales')
    op.drop_table('grade_scales')
    
    op.drop_index(op.f('ix_student_grades_class_id'), table_name='student_grades')
    op.drop_index(op.f('ix_student_grades_subject_id'), table_name='student_grades')
    op.drop_index(op.f('ix_student_grades_student_id'), table_name='student_grades')
    op.drop_index(op.f('ix_student_grades_tenant_id'), table_name='student_grades')
    op.drop_index(op.f('ix_student_grades_id'), table_name='student_grades')
    op.drop_table('student_grades')
    
    op.drop_index(op.f('ix_assessment_submissions_student_id'), table_name='assessment_submissions')
    op.drop_index(op.f('ix_assessment_submissions_assessment_id'), table_name='assessment_submissions')
    op.drop_index(op.f('ix_assessment_submissions_tenant_id'), table_name='assessment_submissions')
    op.drop_index(op.f('ix_assessment_submissions_id'), table_name='assessment_submissions')
    op.drop_table('assessment_submissions')
    
    op.drop_index(op.f('ix_assessments_teacher_id'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_class_id'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_subject_id'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_tenant_id'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_id'), table_name='assessments')
    op.drop_table('assessments')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS submissionstatus")
    op.execute("DROP TYPE IF EXISTS assessmentstatus")
    op.execute("DROP TYPE IF EXISTS assessmenttype")