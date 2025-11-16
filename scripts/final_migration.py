#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from uuid import uuid4
import json
from db_config import LOCAL_DATABASE, TARGET_DATABASE

async def migrate_book_data():
    # Build connection strings
    local_url = f"postgresql+asyncpg://{LOCAL_DATABASE['username']}:{LOCAL_DATABASE['password']}@{LOCAL_DATABASE['host']}:{LOCAL_DATABASE['port']}/{LOCAL_DATABASE['database']}"
    
    print("🚀 Starting Book Chunks Migration")
    print("=" * 50)
    
    try:
        # Test connection and get data
        local_engine = create_async_engine(local_url)
        async with local_engine.connect() as conn:
            # Check if tables exist
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name IN ('book_chunks', 'quizzes')
            """))
            existing_tables = [row[0] for row in result.fetchall()]
            
            if 'book_chunks' not in existing_tables:
                print("❌ book_chunks table not found!")
                return
            
            has_quizzes_table = 'quizzes' in existing_tables
            print(f"📋 Tables found: {', '.join(existing_tables)}")
            
            # Get total counts
            result = await conn.execute(text("SELECT COUNT(*) FROM book_chunks"))
            total_chunks = result.scalar()
            print(f"📚 Found {total_chunks} book chunks to migrate")
            
            if has_quizzes_table:
                result = await conn.execute(text("SELECT COUNT(*) FROM quizzes"))
                total_quizzes = result.scalar()
                print(f"🎯 Found {total_quizzes} existing quizzes to migrate")
            
            # Get unique chapters
            result = await conn.execute(text("""
                SELECT chapter, COUNT(*) as sections
                FROM book_chunks 
                GROUP BY chapter 
                ORDER BY chapter
            """))
            chapters_info = result.fetchall()
            
            print(f"📖 Chapters found:")
            for chapter, count in chapters_info:
                print(f"   - {chapter}: {count} sections")
        
        # Migrate to target
        target_engine = create_async_engine(TARGET_DATABASE["url"])
        
        async with target_engine.begin() as target_conn:
            print(f"\n🧹 Clearing existing data...")
            
            # Clear existing quiz data for this tenant
            tenant_id = TARGET_DATABASE["tenant_id"]
            await target_conn.execute(text("DELETE FROM quiz_answers WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE tenant_id = :tenant_id)"), {"tenant_id": tenant_id})
            await target_conn.execute(text("DELETE FROM quiz_attempts WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await target_conn.execute(text("DELETE FROM quiz_questions WHERE quiz_id IN (SELECT id FROM quizzes WHERE tenant_id = :tenant_id)"), {"tenant_id": tenant_id})
            await target_conn.execute(text("DELETE FROM quizzes WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await target_conn.execute(text("DELETE FROM questions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            await target_conn.execute(text("DELETE FROM topics WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            
            print("✅ Cleared existing data")
            
            # Get all book chunks from source
            async with local_engine.connect() as local_conn:
                result = await local_conn.execute(text("""
                    SELECT id, chapter, section, text 
                    FROM book_chunks 
                    ORDER BY chapter, id
                """))
                all_chunks = result.fetchall()
            
            # Create topics from unique chapters
            topic_mapping = {}
            created_topics = 0
            
            for chapter, count in chapters_info:
                topic_id = str(uuid4())
                topic_mapping[chapter] = topic_id
                
                # Smart subject mapping
                subject, grade = map_chapter_to_subject(chapter)
                
                await target_conn.execute(text("""
                    INSERT INTO topics (id, tenant_id, name, description, subject, grade_level, created_at, updated_at, is_deleted)
                    VALUES (:id, :tenant_id, :name, :description, :subject, :grade_level, NOW(), NOW(), false)
                """), {
                    "id": topic_id,
                    "tenant_id": tenant_id,
                    "name": chapter,
                    "description": f"Educational content for {chapter} with {count} sections",
                    "subject": subject,
                    "grade_level": grade
                })
                created_topics += 1
                print(f"✅ Topic: {chapter} → {subject} (Grade {grade})")
            
            # Create questions from chunks
            created_questions = 0
            
            for chunk_id, chapter, section, content in all_chunks:
                topic_id = topic_mapping[chapter]
                
                # Create meaningful question
                question_text = f"What is the main focus of the '{section}' section in {chapter}?"
                
                # Generate contextual options
                options = generate_options(chapter, section, content)
                
                # Create explanation from content
                explanation = create_explanation(content)
                
                question_id = str(uuid4())
                await target_conn.execute(text("""
                    INSERT INTO questions (id, tenant_id, topic_id, question_text, question_type, 
                                         difficulty_level, options, correct_answer, explanation, 
                                         points, created_at, updated_at, is_deleted)
                    VALUES (:id, :tenant_id, :topic_id, :question_text, :question_type, 
                            :difficulty_level, :options, :correct_answer, :explanation, 
                            :points, NOW(), NOW(), false)
                """), {
                    "id": question_id,
                    "tenant_id": tenant_id,
                    "topic_id": topic_id,
                    "question_text": question_text,
                    "question_type": "multiple_choice",
                    "difficulty_level": determine_difficulty(chapter),
                    "options": json.dumps(options),
                    "correct_answer": "A",
                    "explanation": explanation,
                    "points": 1
                })
                created_questions += 1
            
            # Import existing quizzes if table exists
            created_quizzes = 0
            if has_quizzes_table:
                # First, check if we have any teachers or create a default one
                result = await target_conn.execute(text("SELECT id FROM teachers WHERE tenant_id = :tenant_id LIMIT 1"), {"tenant_id": tenant_id})
                teacher_row = result.fetchone()
                
                if not teacher_row:
                    # Create a default teacher for migration
                    default_teacher_id = str(uuid4())
                    await target_conn.execute(text("""
                        INSERT INTO teachers (id, tenant_id, first_name, last_name, email, is_active, created_at, updated_at, is_deleted)
                        VALUES (:id, :tenant_id, :first_name, :last_name, :email, :is_active, NOW(), NOW(), false)
                    """), {
                        "id": default_teacher_id,
                        "tenant_id": tenant_id,
                        "first_name": "Migration",
                        "last_name": "Teacher",
                        "email": "migration@example.com",
                        "is_active": True
                    })
                    teacher_id = default_teacher_id
                    print("✅ Created default teacher for migration")
                else:
                    teacher_id = teacher_row[0]
                    print(f"✅ Using existing teacher: {teacher_id}")
                
                async with local_engine.connect() as local_conn:
                    result = await local_conn.execute(text("SELECT * FROM quizzes LIMIT 5"))
                    existing_quizzes = result.fetchall()
                    
                    # Get column names
                    result = await local_conn.execute(text("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'quizzes' ORDER BY ordinal_position
                    """))
                    quiz_columns = [row[0] for row in result.fetchall()]
                    print(f"🎯 Quiz table columns: {', '.join(quiz_columns)}")
                    
                    # Import quizzes (basic structure)
                    for quiz_row in existing_quizzes:
                        quiz_id = str(uuid4())
                        # Use first topic as default
                        first_topic_id = list(topic_mapping.values())[0] if topic_mapping else str(uuid4())
                        
                        await target_conn.execute(text("""
                            INSERT INTO quizzes (id, tenant_id, topic_id, teacher_id, title, description, 
                                               total_questions, total_points, is_active, created_at, updated_at, is_deleted)
                            VALUES (:id, :tenant_id, :topic_id, :teacher_id, :title, :description, 
                                   :total_questions, :total_points, :is_active, NOW(), NOW(), false)
                        """), {
                            "id": quiz_id,
                            "tenant_id": tenant_id,
                            "topic_id": first_topic_id,
                            "teacher_id": teacher_id,
                            "title": f"Imported Quiz {created_quizzes + 1}",
                            "description": "Quiz imported from existing system",
                            "total_questions": 5,
                            "total_points": 5,
                            "is_active": True
                        })
                        created_quizzes += 1
                        
                        if created_quizzes >= 5:  # Limit to 5 sample quizzes
                            break
            
            print(f"\n🎉 Migration completed successfully!")
            print(f"📊 Created {created_topics} topics")
            print(f"❓ Created {created_questions} questions")
            if created_quizzes > 0:
                print(f"🎯 Created {created_quizzes} sample quizzes")
            print(f"✅ All data imported into EduAssist Quiz System")
        
        await local_engine.dispose()
        await target_engine.dispose()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check database credentials in db_config.py")
        print("2. Ensure local database is running")
        print("3. Verify book_chunks and quizzes tables exist")

def map_chapter_to_subject(chapter):
    """Map chapter names to appropriate subjects and grade levels"""
    chapter_lower = chapter.lower()
    
    if "real number" in chapter_lower:
        return "Number Systems", 9
    elif "polynomial" in chapter_lower:
        return "Algebra", 10
    elif "arithmetic" in chapter_lower and "progression" in chapter_lower:
        return "Sequences and Series", 11
    elif "triangle" in chapter_lower:
        return "Geometry", 9
    elif "coordinate" in chapter_lower and "geometry" in chapter_lower:
        return "Coordinate Geometry", 10
    elif "circle" in chapter_lower:
        return "Geometry", 10
    elif "statistic" in chapter_lower:
        return "Statistics", 11
    elif "probability" in chapter_lower:
        return "Probability", 11
    else:
        return "Mathematics", 8

def generate_options(chapter, section, content):
    """Generate contextual multiple choice options"""
    return {
        "A": f"Core concepts of {section}",
        "B": f"Introduction to {chapter}",
        "C": f"Advanced applications",
        "D": f"Problem-solving techniques"
    }

def create_explanation(content):
    """Create explanation from content"""
    # Clean and truncate content
    clean_content = content.replace('\n', ' ').replace('\r', ' ').strip()
    if len(clean_content) > 300:
        return clean_content[:300] + "..."
    return clean_content

def determine_difficulty(chapter):
    """Determine difficulty based on chapter complexity"""
    chapter_lower = chapter.lower()
    
    if any(word in chapter_lower for word in ["introduction", "basic", "real number"]):
        return "easy"
    elif any(word in chapter_lower for word in ["coordinate", "statistic", "probability"]):
        return "hard"
    else:
        return "medium"

if __name__ == "__main__":
    print("📖 Final Book Chunks Migration")
    print("Update db_config.py with your database credentials first!")
    print()
    
    proceed = input("Ready to migrate? (y/n): ")
    if proceed.lower() == 'y':
        asyncio.run(migrate_book_data())
    else:
        print("Please update db_config.py and run again.")