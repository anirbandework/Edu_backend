from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.services.assesment.cbse_curriculum_service import CBSEContentService
# Removed enum import

router = APIRouter(prefix="/cbse", tags=["CBSE Content"])

@router.post("/generate-chunks/{subject}")
async def generate_book_chunks(
    subject: str,
    chapter_content: str,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered book chunks for a subject"""
    service = CBSEContentService(db)
    
    try:
        chunks = await service.generate_book_chunks(subject, chapter_content, tenant_id)
        return {
            "message": f"Generated {len(chunks)} chunks for {subject.value}",
            "chunks": [{"id": str(c.id), "title": c.chunk_title} for c in chunks]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-sample-paper/{subject}")
async def generate_sample_paper(
    subject: str,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate CBSE pattern sample paper"""
    service = CBSEContentService(db)
    
    try:
        paper = await service.generate_sample_paper(subject, tenant_id)
        return {
            "message": f"Generated sample paper for {subject.value}",
            "paper": {
                "id": str(paper.id),
                "title": paper.paper_title,
                "code": paper.paper_code,
                "marks": paper.theory_marks
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content/{subject}")
async def get_subject_content(
    subject: str,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get all content for a subject"""
    service = CBSEContentService(db)
    
    try:
        content = await service.get_subject_content(subject, tenant_id)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-generate")
async def bulk_generate_content(
    tenant_id: UUID,
    subjects: List[str],
    db: AsyncSession = Depends(get_db)
):
    """Generate sample papers for multiple subjects"""
    service = CBSEContentService(db)
    results = []
    
    for subject in subjects:
        try:
            paper = await service.generate_sample_paper(subject, tenant_id)
            results.append({
                "subject": subject.value,
                "status": "success",
                "paper_id": str(paper.id)
            })
        except Exception as e:
            results.append({
                "subject": subject.value,
                "status": "error",
                "error": str(e)
            })
    
    return {"results": results}