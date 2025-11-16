#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from uuid import uuid4
import json
from db_config import LOCAL_DATABASE, TARGET_DATABASE

async def copy_exact_data():
    local_url = f"postgresql+asyncpg://{LOCAL_DATABASE['username']}:{LOCAL_DATABASE['password']}@{LOCAL_DATABASE['host']}:{LOCAL_DATABASE['port']}/{LOCAL_DATABASE['database']}"
    
    local_engine = create_async_engine(local_url)
    target_engine = create_async_engine(TARGET_DATABASE["url"])
    tenant_id = TARGET_DATABASE["tenant_id"]
    
    async with target_engine.begin() as target_conn:
        # Clear existing data
        await target_conn.execute(text("DELETE FROM quiz_questions WHERE quiz_id IN (SELECT id FROM quizzes WHERE tenant_id = :tenant_id)"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM quizzes WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM questions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM topics WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        
        # Get existing teacher
        result = await target_conn.execute(text("SELECT id FROM teachers WHERE tenant_id = :tenant_id LIMIT 1"), {"tenant_id": tenant_id})
        teacher_id = result.scalar()
        
        async with local_engine.connect() as local_conn:
            # Copy quizzes directly
            result = await local_conn.execute(text("SELECT * FROM quizzes"))
            quizzes = result.fetchall()
            columns = result.keys()
            
            print(f"Copying {len(quizzes)} quizzes...")
            
            for quiz in quizzes:
                quiz_dict = dict(zip(columns, quiz))
                
                # Create topic for this quiz
                topic_id = str(uuid4())
                await target_conn.execute(text("""
                    INSERT INTO topics (id, tenant_id, name, description, subject, grade_level, created_at, updated_at, is_deleted)
                    VALUES (:id, :tenant_id, :name, :description, :subject, :grade_level, NOW(), NOW(), false)
                """), {
                    "id": topic_id,
                    "tenant_id": tenant_id,
                    "name": quiz_dict.get('topic', 'Quiz Topic'),
                    "description": f"Topic for {quiz_dict.get('topic', 'Quiz')}",
                    "subject": "Mathematics",
                    "grade_level": 10
                })
                
                # Create question from quiz data
                question_id = str(uuid4())
                options = quiz_dict.get('options', '{}')
                if isinstance(options, str):
                    try:
                        options = json.loads(options)
                    except:
                        options = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
                
                # Map question types
                q_type = quiz_dict.get('question_type', 'mcq')
                if q_type == 'mcq':
                    q_type = 'multiple_choice'
                elif q_type == 'short':
                    q_type = 'short_answer'
                
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
                    "question_text": quiz_dict.get('question_text', 'Sample Question'),
                    "question_type": q_type,
                    "difficulty_level": "medium",
                    "options": json.dumps(options),
                    "correct_answer": quiz_dict.get('correct_answer') or 'A',
                    "explanation": quiz_dict.get('rubric') or 'No explanation provided',
                    "points": quiz_dict.get('points', 1)
                })
                
                # Create quiz
                new_quiz_id = str(uuid4())
                await target_conn.execute(text("""
                    INSERT INTO quizzes (id, tenant_id, topic_id, teacher_id, title, description, 
                                       total_questions, total_points, is_active, created_at, updated_at, is_deleted)
                    VALUES (:id, :tenant_id, :topic_id, :teacher_id, :title, :description, 
                           :total_questions, :total_points, :is_active, NOW(), NOW(), false)
                """), {
                    "id": new_quiz_id,
                    "tenant_id": tenant_id,
                    "topic_id": topic_id,
                    "teacher_id": teacher_id,
                    "title": f"Quiz: {quiz_dict.get('topic', 'Untitled')}",
                    "description": f"Quiz on {quiz_dict.get('topic', 'General Topic')}",
                    "total_questions": 1,
                    "total_points": quiz_dict.get('points', 1),
                    "is_active": True
                })
                
                # Link question to quiz
                await target_conn.execute(text("""
                    INSERT INTO quiz_questions (id, quiz_id, question_id, order_number, created_at, updated_at, is_deleted)
                    VALUES (:id, :quiz_id, :question_id, :order_number, NOW(), NOW(), false)
                """), {
                    "id": str(uuid4()),
                    "quiz_id": new_quiz_id,
                    "question_id": question_id,
                    "order_number": 1
                })
        
        print("✅ Exact quiz data copied successfully!")

if __name__ == "__main__":
    asyncio.run(copy_exact_data())