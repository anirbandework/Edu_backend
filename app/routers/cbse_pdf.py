from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from fastapi.responses import Response

from ..core.database import get_db

router = APIRouter(prefix="/cbse-pdf", tags=["CBSE PDF"])

@router.post("/upload-paper/{subject}")
async def upload_sample_paper(
    subject: str,
    tenant_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload PDF sample paper"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    pdf_content = await file.read()
    paper_id = str(uuid4())
    
    await db.execute(text("""
        INSERT INTO cbse_sample_papers 
        (id, tenant_id, subject, paper_title, paper_code, pdf_content, pdf_filename, pdf_size, created_at, is_deleted)
        VALUES (:id, :tenant_id, :subject, :title, :code, :pdf_content, :filename, :size, NOW(), false)
    """), {
        "id": paper_id,
        "tenant_id": str(tenant_id),
        "subject": subject,
        "title": f"{subject.replace('_', ' ').title()} Sample Paper",
        "code": subject.split('_')[-1],
        "pdf_content": pdf_content,
        "filename": file.filename,
        "size": len(pdf_content)
    })
    
    await db.commit()
    
    return {
        "message": "PDF uploaded successfully",
        "paper_id": paper_id,
        "filename": file.filename,
        "size": len(pdf_content)
    }

@router.get("/download-paper/{paper_id}")
async def download_sample_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download PDF sample paper"""
    
    result = await db.execute(text("""
        SELECT pdf_content, pdf_filename 
        FROM cbse_sample_papers 
        WHERE id = :paper_id AND pdf_content IS NOT NULL
    """), {"paper_id": str(paper_id)})
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    return Response(
        content=row[0],
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={row[1]}"}
    )

@router.get("/papers/{subject}")
async def list_pdf_papers(
    subject: str,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List PDF papers for a subject"""
    
    result = await db.execute(text("""
        SELECT id, paper_title, pdf_filename, pdf_size, created_at
        FROM cbse_sample_papers 
        WHERE subject = :subject AND tenant_id = :tenant_id AND pdf_content IS NOT NULL
    """), {"subject": subject, "tenant_id": str(tenant_id)})
    
    papers = [
        {
            "id": str(row[0]),
            "title": row[1],
            "filename": row[2],
            "size": row[3],
            "uploaded_at": row[4].isoformat() if row[4] else None
        }
        for row in result.fetchall()
    ]
    
    return {"subject": subject, "papers": papers}