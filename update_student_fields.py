#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def update_student_fields():
    """Update student table to make minimal required fields"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not found in environment")
        return
    
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Make fields optional
        await conn.execute("ALTER TABLE students ALTER COLUMN first_name DROP NOT NULL;")
        await conn.execute("ALTER TABLE students ALTER COLUMN last_name DROP NOT NULL;")
        await conn.execute("ALTER TABLE students ALTER COLUMN date_of_birth DROP NOT NULL;")
        await conn.execute("ALTER TABLE students ALTER COLUMN address DROP NOT NULL;")
        await conn.execute("ALTER TABLE students ALTER COLUMN grade_level DROP NOT NULL;")
        await conn.execute("ALTER TABLE students ALTER COLUMN academic_year DROP NOT NULL;")
        
        # Update existing null phone values with placeholder
        await conn.execute("UPDATE students SET phone = CONCAT('PH', SUBSTRING(id::text, 1, 10)) WHERE phone IS NULL;")
        
        # Make phone required and add unique constraint
        await conn.execute("ALTER TABLE students ALTER COLUMN phone SET NOT NULL;")
        
        # Add unique constraints
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_tenant_student_id ON students(tenant_id, student_id);")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_phone ON students(phone) WHERE is_deleted = false;")
        
        print("Successfully updated student table structure")
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(update_student_fields())