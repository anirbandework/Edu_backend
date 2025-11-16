#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from db_config import LOCAL_DATABASE, TARGET_DATABASE

async def exact_copy():
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
        
        # Drop and recreate tables to match source exactly
        await target_conn.execute(text("DROP TABLE IF EXISTS book_chunks"))
        await target_conn.execute(text("DROP TABLE IF EXISTS quizzes"))
        
        print("✅ Cleared existing data")
        
        async with local_engine.connect() as local_conn:
            # Get CREATE TABLE statements from source
            result = await local_conn.execute(text("""
                SELECT 'CREATE TABLE book_chunks (' || string_agg(column_name || ' ' || data_type || 
                CASE WHEN character_maximum_length IS NOT NULL THEN '(' || character_maximum_length || ')' ELSE '' END, ', ') || ');'
                FROM information_schema.columns 
                WHERE table_name = 'book_chunks'
                GROUP BY table_name
            """))
            create_book_chunks = result.scalar()
            
            result = await local_conn.execute(text("""
                SELECT 'CREATE TABLE quizzes (' || string_agg(column_name || ' ' || data_type || 
                CASE WHEN character_maximum_length IS NOT NULL THEN '(' || character_maximum_length || ')' ELSE '' END, ', ') || ');'
                FROM information_schema.columns 
                WHERE table_name = 'quizzes'
                GROUP BY table_name
            """))
            create_quizzes = result.scalar()
            
            # Create tables
            if create_book_chunks:
                await target_conn.execute(text(create_book_chunks))
                print("✅ Created book_chunks table")
            
            if create_quizzes:
                await target_conn.execute(text(create_quizzes))
                print("✅ Created quizzes table")
            
            # Copy data row by row
            result = await local_conn.execute(text("SELECT * FROM book_chunks"))
            chunks = result.fetchall()
            columns = list(result.keys())
            
            for chunk in chunks:
                escaped_vals = []
                for val in chunk:
                    if val is None:
                        escaped_vals.append('NULL')
                    else:
                        escaped_val = str(val).replace("'", "''")
                        escaped_vals.append(f"'{escaped_val}'")
                values = ', '.join(escaped_vals)
                await target_conn.execute(text(f"INSERT INTO book_chunks VALUES ({values})"))
            
            print(f"✅ Copied {len(chunks)} book chunks")
            
            result = await local_conn.execute(text("SELECT * FROM quizzes"))
            quizzes = result.fetchall()
            
            for quiz in quizzes:
                escaped_vals = []
                for val in quiz:
                    if val is None:
                        escaped_vals.append('NULL')
                    else:
                        escaped_val = str(val).replace("'", "''")
                        escaped_vals.append(f"'{escaped_val}'")
                values = ', '.join(escaped_vals)
                await target_conn.execute(text(f"INSERT INTO quizzes VALUES ({values})"))
            
            print(f"✅ Copied {len(quizzes)} quizzes")
        
        print("✅ Exact copy completed!")

if __name__ == "__main__":
    asyncio.run(exact_copy())