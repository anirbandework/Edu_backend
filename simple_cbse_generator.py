#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import uuid

load_dotenv()

async def create_sample_cbse_content():
    """Simple CBSE content creation without complex models"""
    
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    tenant_id = "351e3b19-0c37-4e48-a06d-3ceaa7e584c2"
    
    async with async_session() as session:
        print("🚀 Creating CBSE Sample Papers...")
        
        # Math Standard Sample Paper
        paper_id = str(uuid.uuid4())
        await session.execute(text("""
            INSERT INTO cbse_sample_papers 
            (id, tenant_id, subject, paper_title, paper_code, theory_marks, internal_marks, created_at, is_deleted)
            VALUES (:id, :tenant_id, 'math_standard_041', 'Mathematics Standard Sample Paper', '041', 80, 20, NOW(), false)
        """), {"id": paper_id, "tenant_id": tenant_id})
        
        # English Sample Paper  
        paper_id2 = str(uuid.uuid4())
        await session.execute(text("""
            INSERT INTO cbse_sample_papers 
            (id, tenant_id, subject, paper_title, paper_code, theory_marks, internal_marks, created_at, is_deleted)
            VALUES (:id, :tenant_id, 'english_184', 'English Language & Literature Sample Paper', '184', 80, 20, NOW(), false)
        """), {"id": paper_id2, "tenant_id": tenant_id})
        
        # Book Chunks
        chunk_id = str(uuid.uuid4())
        await session.execute(text("""
            INSERT INTO book_chunks 
            (id, tenant_id, subject, chapter_name, chunk_title, chunk_number, content, key_concepts, created_at, is_deleted)
            VALUES (:id, :tenant_id, 'math_standard_041', 'Quadratic Equations', 'Introduction to Quadratic Equations', 1, 
            'A quadratic equation is a polynomial equation of degree 2. The general form is ax² + bx + c = 0 where a ≠ 0.', 
            '["Standard form", "Degree 2", "Coefficients"]', NOW(), false)
        """), {"id": chunk_id, "tenant_id": tenant_id})
        
        await session.commit()
        print("✅ Created Math Standard sample paper")
        print("✅ Created English sample paper") 
        print("✅ Created sample book chunk")
        print("🎉 CBSE Content Creation Complete!")

if __name__ == "__main__":
    asyncio.run(create_sample_cbse_content())