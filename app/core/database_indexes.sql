-- Critical database indexes for 100k users
-- Run these in production database

-- Quiz Performance Indexes
CREATE INDEX CONCURRENTLY idx_quiz_attempts_student_tenant ON quiz_attempts(student_id, tenant_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_quiz_attempts_quiz_submitted ON quiz_attempts(quiz_id, is_submitted, created_at DESC);
CREATE INDEX CONCURRENTLY idx_quiz_answers_attempt_question ON quiz_answers(attempt_id, question_id);

-- Question Search Indexes
CREATE INDEX CONCURRENTLY idx_questions_topic_difficulty ON questions(topic_id, difficulty_level, is_deleted);
CREATE INDEX CONCURRENTLY idx_questions_tenant_subject ON questions(tenant_id, subject, is_deleted);

-- Assessment Performance Indexes
CREATE INDEX CONCURRENTLY idx_assessments_class_status ON assessments(class_id, status, due_date);
CREATE INDEX CONCURRENTLY idx_submissions_assessment_status ON assessment_submissions(assessment_id, status, submission_date DESC);

-- Student Performance Indexes
CREATE INDEX CONCURRENTLY idx_student_grades_student_year ON student_grades(student_id, academic_year, last_updated DESC);
CREATE INDEX CONCURRENTLY idx_student_grades_class_subject ON student_grades(class_id, subject_id, academic_year);

-- CBSE Content Indexes
CREATE INDEX CONCURRENTLY idx_book_chunks_subject_tenant ON book_chunks(subject, tenant_id, difficulty_level);
CREATE INDEX CONCURRENTLY idx_cbse_papers_subject_tenant ON cbse_sample_papers(subject, tenant_id, is_official_pattern);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY idx_quiz_performance_lookup ON quiz_attempts(student_id, tenant_id, is_submitted, created_at DESC) 
WHERE is_submitted = true;