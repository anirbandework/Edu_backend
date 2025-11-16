#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from db_config import LOCAL_DATABASE, TARGET_DATABASE

async def raw_copy():
    local_url = f"postgresql+asyncpg://{LOCAL_DATABASE['username']}:{LOCAL_DATABASE['password']}@{LOCAL_DATABASE['host']}:{LOCAL_DATABASE['port']}/{LOCAL_DATABASE['database']}"
    target_engine = create_async_engine(TARGET_DATABASE["url"])
    local_engine = create_async_engine(local_url)
    
    async with target_engine.begin() as target_conn:
        # Create raw tables
        await target_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw_book_chunks (
                id INTEGER,
                chapter TEXT,
                section TEXT,
                text TEXT
            )
        """))
        
        await target_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw_quizzes (
                id INTEGER,
                topic TEXT,
                question_text TEXT,
                question_type TEXT,
                options TEXT,
                correct_answer TEXT,
                rubric TEXT,
                points REAL
            )
        """))
        
        # Clear existing data
        await target_conn.execute(text("TRUNCATE raw_book_chunks"))
        await target_conn.execute(text("TRUNCATE raw_quizzes"))
        
        async with local_engine.connect() as local_conn:
            # Copy book_chunks
            result = await local_conn.execute(text("SELECT * FROM book_chunks"))
            chunks = result.fetchall()
            
            for chunk in chunks:
                await target_conn.execute(text("""
                    INSERT INTO raw_book_chunks (id, chapter, section, text)
                    VALUES (:id, :chapter, :section, :text)
                """), {
                    "id": chunk[0],
                    "chapter": chunk[1],
                    "section": chunk[2], 
                    "text": chunk[3]
                })
            
            print(f"✅ Copied {len(chunks)} book chunks")
            
            # Copy quizzes
            result = await local_conn.execute(text("SELECT * FROM quizzes"))
            quizzes = result.fetchall()
            
            for quiz in quizzes:
                await target_conn.execute(text("""
                    INSERT INTO raw_quizzes (id, topic, question_text, question_type, options, correct_answer, rubric, points)
                    VALUES (:id, :topic, :question_text, :question_type, :options, :correct_answer, :rubric, :points)
                """), {
                    "id": quiz[0],
                    "topic": quiz[1],
                    "question_text": quiz[2],
                    "question_type": quiz[3],
                    "options": str(quiz[4]) if quiz[4] is not None else None,
                    "correct_answer": quiz[5],
                    "rubric": quiz[6],
                    "points": quiz[7]
                })
            
            print(f"✅ Copied {len(quizzes)} quizzes")
        
        print("✅ Raw data copied to raw_book_chunks and raw_quizzes tables!")

if __name__ == "__main__":
    asyncio.run(raw_copy())