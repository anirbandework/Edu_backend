#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from uuid import uuid4
import json
from db_config import LOCAL_DATABASE, TARGET_DATABASE

async def simple_copy():
    local_url = f"postgresql+asyncpg://{LOCAL_DATABASE['username']}:{LOCAL_DATABASE['password']}@{LOCAL_DATABASE['host']}:{LOCAL_DATABASE['port']}/{LOCAL_DATABASE['database']}"
    
    local_engine = create_async_engine(local_url)
    target_engine = create_async_engine(TARGET_DATABASE["url"])
    tenant_id = TARGET_DATABASE["tenant_id"]
    
    # Get teacher
    async with target_engine.connect() as conn:
        result = await conn.execute(text("SELECT id FROM teachers WHERE tenant_id = :tenant_id LIMIT 1"), {"tenant_id": tenant_id})
        teacher_id = result.scalar()
    
    # Get first 50 quizzes only
    async with local_engine.connect() as local_conn:
        result = await local_conn.execute(text("SELECT * FROM quizzes LIMIT 50"))
        quizzes = result.fetchall()
        columns = result.keys()
        
        print(f"Processing {len(quizzes)} quizzes...")
        
        async with target_engine.begin() as target_conn:
            for i, quiz in enumerate(quizzes):
                quiz_dict = dict(zip(columns, quiz))
                
                # Create topic
                topic_id = str(uuid4())
                await target_conn.execute(text("""
                    INSERT INTO topics (id, tenant_id, name, description, subject, grade_level, created_at, updated_at, is_deleted)
                    VALUES (:id, :tenant_id, :name, :description, :subject, :grade_level, NOW(), NOW(), false)
                """), {
                    "id": topic_id,
                    "tenant_id": tenant_id,
                    "name": quiz_dict.get('topic', f'Topic {i+1}'),
                    "description": f"Copied from quiz {i+1}",
                    "subject": "Mathematics",
                    "grade_level": 10
                })
                
                # Create question
                question_id = str(uuid4())
                q_type = quiz_dict.get('question_type', 'mcq')
                if q_type == 'mcq':
                    q_type = 'multiple_choice'
                elif q_type == 'short':
                    q_type = 'short_answer'
                
                options = quiz_dict.get('options', '{}')
                if isinstance(options, str) and options != '{}':
                    try:
                        options = json.loads(options)
                    except:
                        options = {}
                else:
                    options = {}
                
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
                    "question_text": quiz_dict.get('question_text', f'Question {i+1}'),
                    "question_type": q_type,
                    "difficulty_level": "medium",
                    "options": json.dumps(options),
                    "correct_answer": quiz_dict.get('correct_answer') or 'A',
                    "explanation": quiz_dict.get('rubric') or 'No explanation',
                    "points": quiz_dict.get('points', 1)
                })
                
                # Create quiz
                quiz_id = str(uuid4())
                await target_conn.execute(text("""
                    INSERT INTO quizzes (id, tenant_id, topic_id, teacher_id, title, description, 
                                       total_questions, total_points, is_active, created_at, updated_at, is_deleted)
                    VALUES (:id, :tenant_id, :topic_id, :teacher_id, :title, :description, 
                           :total_questions, :total_points, :is_active, NOW(), NOW(), false)
                """), {
                    "id": quiz_id,
                    "tenant_id": tenant_id,
                    "topic_id": topic_id,
                    "teacher_id": teacher_id,
                    "title": f"Quiz {i+1}: {quiz_dict.get('topic', 'Untitled')}",
                    "description": quiz_dict.get('question_text', 'Copied quiz')[:100],
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
                    "quiz_id": quiz_id,
                    "question_id": question_id,
                    "order_number": 1
                })
                
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1} quizzes...")
        
        print("✅ Quiz data copied successfully!")

if __name__ == "__main__":
    asyncio.run(simple_copy())