#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from uuid import uuid4
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_config import TARGET_DATABASE

async def generate_questions():
    engine = create_async_engine(TARGET_DATABASE["url"])
    tenant_id = TARGET_DATABASE["tenant_id"]
    
    async with engine.begin() as conn:
        # Get teacher
        result = await conn.execute(text("SELECT id FROM teachers WHERE tenant_id = :tenant_id LIMIT 1"), {"tenant_id": tenant_id})
        teacher_id = result.scalar()
        
        # Get raw data
        result = await conn.execute(text("SELECT * FROM raw_book_chunks"))
        chunks = result.fetchall()
        
        result = await conn.execute(text("SELECT * FROM raw_quizzes"))
        quizzes = result.fetchall()
        
        print(f"Processing {len(chunks)} book chunks and {len(quizzes)} quizzes...")
        
        # Create topics from unique chapters
        chapters = set(chunk[1] for chunk in chunks)
        topic_mapping = {}
        
        for chapter in chapters:
            topic_id = str(uuid4())
            topic_mapping[chapter] = topic_id
            
            await conn.execute(text("""
                INSERT INTO topics (id, tenant_id, name, description, subject, grade_level, created_at, updated_at, is_deleted)
                VALUES (:id, :tenant_id, :name, :description, :subject, :grade_level, NOW(), NOW(), false)
            """), {
                "id": topic_id,
                "tenant_id": tenant_id,
                "name": chapter,
                "description": f"Content for {chapter}",
                "subject": "Mathematics",
                "grade_level": 10
            })
        
        print(f"✅ Created {len(chapters)} topics")
        
        # Create questions from book chunks
        for chunk in chunks:
            question_id = str(uuid4())
            topic_id = topic_mapping[chunk[1]]
            
            await conn.execute(text("""
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
                "question_text": f"What is discussed in section '{chunk[2]}' of {chunk[1]}?",
                "question_type": "multiple_choice",
                "difficulty_level": "medium",
                "options": json.dumps({"A": "Basic concepts", "B": "Advanced topics", "C": "Problem solving", "D": "Applications"}),
                "correct_answer": "A",
                "explanation": chunk[3][:200] + "..." if len(chunk[3]) > 200 else chunk[3],
                "points": 1
            })
        
        print(f"✅ Created {len(chunks)} questions from book chunks")
        
        # Create questions from raw quizzes
        for quiz in quizzes:
            question_id = str(uuid4())
            # Use first topic as default
            topic_id = list(topic_mapping.values())[0]
            
            q_type = quiz[3] if quiz[3] in ['multiple_choice', 'short_answer'] else 'multiple_choice'
            if quiz[3] == 'mcq':
                q_type = 'multiple_choice'
            elif quiz[3] == 'short':
                q_type = 'short_answer'
            
            options = quiz[4] if quiz[4] else "{}"
            if isinstance(options, str) and options.startswith('['):
                try:
                    options_list = eval(options)
                    options = json.dumps({"A": options_list[0], "B": options_list[1], "C": options_list[2], "D": options_list[3]})
                except:
                    options = json.dumps({"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"})
            
            await conn.execute(text("""
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
                "question_text": quiz[2],
                "question_type": q_type,
                "difficulty_level": "medium",
                "options": options,
                "correct_answer": quiz[5] or "A",
                "explanation": quiz[6] or "No explanation provided",
                "points": quiz[7] or 1
            })
        
        print(f"✅ Created {len(quizzes)} questions from raw quizzes")
        
        # Create sample quizzes
        for i, (chapter, topic_id) in enumerate(list(topic_mapping.items())[:10]):
            quiz_id = str(uuid4())
            
            await conn.execute(text("""
                INSERT INTO quizzes (id, tenant_id, topic_id, teacher_id, title, description, 
                                   total_questions, total_points, is_active, created_at, updated_at, is_deleted)
                VALUES (:id, :tenant_id, :topic_id, :teacher_id, :title, :description, 
                       :total_questions, :total_points, :is_active, NOW(), NOW(), false)
            """), {
                "id": quiz_id,
                "tenant_id": tenant_id,
                "topic_id": topic_id,
                "teacher_id": teacher_id,
                "title": f"Quiz: {chapter}",
                "description": f"Quiz on {chapter} concepts",
                "total_questions": 5,
                "total_points": 5,
                "is_active": True
            })
            
            # Link 5 questions to each quiz
            result = await conn.execute(text("""
                SELECT id FROM questions WHERE topic_id = :topic_id LIMIT 5
            """), {"topic_id": topic_id})
            questions = result.fetchall()
            
            for j, (question_id,) in enumerate(questions):
                await conn.execute(text("""
                    INSERT INTO quiz_questions (id, quiz_id, question_id, order_number, created_at, updated_at, is_deleted)
                    VALUES (:id, :quiz_id, :question_id, :order_number, NOW(), NOW(), false)
                """), {
                    "id": str(uuid4()),
                    "quiz_id": quiz_id,
                    "question_id": question_id,
                    "order_number": j + 1
                })
        
        print(f"✅ Created 10 sample quizzes with linked questions")
        print("✅ Question generation completed!")

if __name__ == "__main__":
    asyncio.run(generate_questions())