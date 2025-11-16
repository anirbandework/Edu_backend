#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def run_manual_migration():
    DATABASE_URL = "postgresql+asyncpg://eduassist_admin:EduAssist2024!Dev@eduassist-postgres-dev.cvks46m00t2t.eu-north-1.rds.amazonaws.com:5432/eduassist"
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("🔧 Running manual quiz system migration...")
        
        try:
            # Create enum types
            await conn.execute(text("CREATE TYPE difficultylevel AS ENUM ('easy', 'medium', 'hard')"))
            print("✅ Created difficultylevel enum")
        except Exception as e:
            print(f"⚠️  difficultylevel enum might already exist: {e}")
        
        try:
            await conn.execute(text("CREATE TYPE questiontype AS ENUM ('multiple_choice', 'true_false', 'short_answer', 'essay')"))
            print("✅ Created questiontype enum")
        except Exception as e:
            print(f"⚠️  questiontype enum might already exist: {e}")
        
        # Create topics table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS topics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                name VARCHAR(100) NOT NULL,
                description TEXT,
                subject VARCHAR(50) NOT NULL,
                grade_level INTEGER NOT NULL
            )
        """))
        print("✅ Created topics table")
        
        # Create questions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS questions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                topic_id UUID NOT NULL REFERENCES topics(id),
                question_text TEXT NOT NULL,
                question_type questiontype NOT NULL,
                difficulty_level difficultylevel DEFAULT 'medium',
                options JSON,
                correct_answer VARCHAR(500) NOT NULL,
                explanation TEXT,
                points INTEGER DEFAULT 1,
                time_limit INTEGER
            )
        """))
        print("✅ Created questions table")
        
        # Create quizzes table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                topic_id UUID NOT NULL REFERENCES topics(id),
                class_id UUID REFERENCES classes(id),
                teacher_id UUID NOT NULL REFERENCES teachers(id),
                title VARCHAR(200) NOT NULL,
                description TEXT,
                instructions TEXT,
                total_questions INTEGER NOT NULL,
                total_points INTEGER NOT NULL,
                time_limit INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                allow_retakes BOOLEAN DEFAULT FALSE,
                show_results_immediately BOOLEAN DEFAULT TRUE
            )
        """))
        print("✅ Created quizzes table")
        
        # Create quiz_questions table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                quiz_id UUID NOT NULL REFERENCES quizzes(id),
                question_id UUID NOT NULL REFERENCES questions(id),
                order_number INTEGER NOT NULL,
                points INTEGER DEFAULT 1
            )
        """))
        print("✅ Created quiz_questions table")
        
        # Create quiz_attempts table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                quiz_id UUID NOT NULL REFERENCES quizzes(id),
                student_id UUID NOT NULL REFERENCES students(id),
                attempt_number INTEGER DEFAULT 1,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                total_score INTEGER DEFAULT 0,
                max_score INTEGER NOT NULL,
                percentage INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                is_submitted BOOLEAN DEFAULT FALSE
            )
        """))
        print("✅ Created quiz_attempts table")
        
        # Create quiz_answers table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quiz_answers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                attempt_id UUID NOT NULL REFERENCES quiz_attempts(id),
                question_id UUID NOT NULL REFERENCES questions(id),
                student_answer TEXT,
                is_correct BOOLEAN DEFAULT FALSE,
                points_earned INTEGER DEFAULT 0,
                time_taken INTEGER
            )
        """))
        print("✅ Created quiz_answers table")
        
        # Create indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_topics_tenant_id ON topics(tenant_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_tenant_id ON questions(tenant_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_topic_id ON questions(topic_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_quizzes_tenant_id ON quizzes(tenant_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_quizzes_topic_id ON quizzes(topic_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_quiz_attempts_tenant_id ON quiz_attempts(tenant_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_quiz_attempts_student_id ON quiz_attempts(student_id)"))
        print("✅ Created indexes")
        
        print("\n🎉 Manual migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_manual_migration())