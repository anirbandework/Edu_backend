#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from db_config import LOCAL_DATABASE, TARGET_DATABASE

async def direct_copy():
    local_url = f"postgresql+asyncpg://{LOCAL_DATABASE['username']}:{LOCAL_DATABASE['password']}@{LOCAL_DATABASE['host']}:{LOCAL_DATABASE['port']}/{LOCAL_DATABASE['database']}"
    target_engine = create_async_engine(TARGET_DATABASE["url"])
    local_engine = create_async_engine(local_url)
    tenant_id = TARGET_DATABASE["tenant_id"]
    
    async with target_engine.begin() as target_conn:
        # Clear existing data
        await target_conn.execute(text("DELETE FROM quiz_answers WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE tenant_id = :tenant_id)"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM quiz_attempts WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM quiz_questions WHERE quiz_id IN (SELECT id FROM quizzes WHERE tenant_id = :tenant_id)"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM quizzes WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM questions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await target_conn.execute(text("DELETE FROM topics WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        
        print("✅ Cleared existing data")
        
        async with local_engine.connect() as local_conn:
            # Copy book_chunks table exactly
            result = await local_conn.execute(text("SELECT * FROM book_chunks"))
            chunks = result.fetchall()
            columns = list(result.keys())
            
            if chunks:
                # Create book_chunks table if it doesn't exist
                await target_conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS book_chunks (
                        {', '.join([f'{col} TEXT' for col in columns])}
                    )
                """))
                
                # Insert all book_chunks
                placeholders = ', '.join([f':{col}' for col in columns])
                await target_conn.execute(text(f"""
                    INSERT INTO book_chunks ({', '.join(columns)}) 
                    VALUES ({placeholders})
                """), [dict(zip(columns, chunk)) for chunk in chunks])
                
                print(f"✅ Copied {len(chunks)} book chunks")
            
            # Copy quizzes table exactly  
            result = await local_conn.execute(text("SELECT * FROM quizzes"))
            quizzes = result.fetchall()
            columns = list(result.keys())
            
            if quizzes:
                # Create quizzes table if it doesn't exist
                await target_conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS quizzes (
                        {', '.join([f'{col} TEXT' for col in columns])}
                    )
                """))
                
                # Insert all quizzes
                placeholders = ', '.join([f':{col}' for col in columns])
                await target_conn.execute(text(f"""
                    INSERT INTO quizzes ({', '.join(columns)}) 
                    VALUES ({placeholders})
                """), [dict(zip(columns, quiz)) for quiz in quizzes])
                
                print(f"✅ Copied {len(quizzes)} quizzes")
        
        print("✅ Direct copy completed!")

if __name__ == "__main__":
    asyncio.run(direct_copy())