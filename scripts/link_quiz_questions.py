#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from uuid import uuid4
from db_config import TARGET_DATABASE

async def link_quiz_questions():
    engine = create_async_engine(TARGET_DATABASE["url"])
    tenant_id = TARGET_DATABASE["tenant_id"]
    
    async with engine.begin() as conn:
        # Get all quizzes
        result = await conn.execute(text("SELECT id, topic_id FROM quizzes WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        quizzes = result.fetchall()
        
        print(f"Found {len(quizzes)} quizzes")
        
        for quiz_id, topic_id in quizzes:
            # Get 5 questions for this topic
            result = await conn.execute(text("""
                SELECT id FROM questions 
                WHERE tenant_id = :tenant_id AND topic_id = :topic_id 
                LIMIT 5
            """), {"tenant_id": tenant_id, "topic_id": topic_id})
            questions = result.fetchall()
            
            print(f"Linking {len(questions)} questions to quiz {quiz_id}")
            
            # Link questions to quiz
            for i, (question_id,) in enumerate(questions):
                await conn.execute(text("""
                    INSERT INTO quiz_questions (id, quiz_id, question_id, order_number, created_at, updated_at, is_deleted)
                    VALUES (:id, :quiz_id, :question_id, :order_number, NOW(), NOW(), false)
                """), {
                    "id": str(uuid4()),
                    "quiz_id": quiz_id,
                    "question_id": question_id,
                    "order_number": i + 1
                })
        
        print("✅ Quiz questions linked successfully!")

if __name__ == "__main__":
    asyncio.run(link_quiz_questions())