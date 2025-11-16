#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def make_phone_optional():
    """Make phone field optional in students table"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not found in environment")
        return
    
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Make phone optional
        await conn.execute("ALTER TABLE students ALTER COLUMN phone DROP NOT NULL;")
        
        print("Successfully made phone field optional")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(make_phone_optional())