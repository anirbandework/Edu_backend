#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import uuid

load_dotenv()

# Map PDF files to subjects
PDF_SUBJECT_MAP = {
    "HindiCourseA-SQP.pdf": "hindi_a_002",
    "HindiCourseB-SQP.pdf": "hindi_b_085", 
    "MathsStandard-SQP.pdf": "math_standard_041",
    "EnglishL-SQP.pdf": "english_184",
    "SocialScience-SQP.pdf": "social_science_087",
    "Science-SQP.pdf": "science_086"
}

async def upload_all_pdfs():
    """Upload all PDF sample papers from sample_papers folder"""
    
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    tenant_id = "351e3b19-0c37-4e48-a06d-3ceaa7e584c2"
    
    async with engine.connect() as conn:
        print("🚀 Uploading CBSE Sample Papers...")
        
        for filename, subject in PDF_SUBJECT_MAP.items():
            pdf_path = f"sample_papers/{filename}"
            
            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                
                paper_id = str(uuid.uuid4())
                
                await conn.execute(text("""
                    INSERT INTO cbse_sample_papers 
                    (id, tenant_id, subject, paper_title, paper_code, pdf_content, pdf_filename, pdf_size, created_at, is_deleted)
                    VALUES (:id, :tenant_id, :subject, :title, :code, :pdf_content, :filename, :size, NOW(), false)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": paper_id,
                    "tenant_id": tenant_id,
                    "subject": subject,
                    "title": f"{subject.replace('_', ' ').title()} Sample Paper",
                    "code": subject.split('_')[-1],
                    "pdf_content": pdf_content,
                    "filename": filename,
                    "size": len(pdf_content)
                })
                
                print(f"✅ Uploaded {filename} -> {subject} ({len(pdf_content)} bytes)")
            else:
                print(f"❌ File not found: {pdf_path}")
        
        await conn.commit()
        print("🎉 All PDF uploads complete!")

if __name__ == "__main__":
    asyncio.run(upload_all_pdfs())