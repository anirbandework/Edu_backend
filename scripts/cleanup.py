#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from db_config import TARGET_DATABASE

async def cleanup():
    engine = create_async_engine(TARGET_DATABASE["url"])
    tenant_id = TARGET_DATABASE["tenant_id"]
    
    async with engine.begin() as conn:
        # Delete all migrated data
        await conn.execute(text("DELETE FROM quiz_answers WHERE attempt_id IN (SELECT id FROM quiz_attempts WHERE tenant_id = :tenant_id)"), {"tenant_id": tenant_id})
        await conn.execute(text("DELETE FROM quiz_attempts WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await conn.execute(text("DELETE FROM quiz_questions WHERE quiz_id IN (SELECT id FROM quizzes WHERE tenant_id = :tenant_id)"), {"tenant_id": tenant_id})
        await conn.execute(text("DELETE FROM quizzes WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await conn.execute(text("DELETE FROM questions WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        await conn.execute(text("DELETE FROM topics WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        
        print("✅ Deleted all migrated quiz data")

if __name__ == "__main__":
    asyncio.run(cleanup())