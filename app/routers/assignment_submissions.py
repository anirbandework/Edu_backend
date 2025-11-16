from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from fastapi.responses import Response

from ..core.database import get_db

router = APIRouter(prefix="/assignments", tags=["Assignment Submissions"])

@router.post("/submit/{assessment_id}")
async def submit_assignment_pdf(
    assessment_id: UUID,
    student_id: UUID,
    tenant_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Submit assignment as PDF"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    pdf_content = await file.read()
    submission_id = str(uuid4())
    
    await db.execute(text("""
        INSERT INTO assessment_submissions 
        (id, tenant_id, assessment_id, student_id, submission_date, submission_pdf, pdf_filename, pdf_size, status, is_deleted, created_at)
        VALUES (:id, :tenant_id, :assessment_id, :student_id, NOW(), :pdf_content, :filename, :size, 'submitted', false, NOW())
    """), {
        "id": submission_id,
        "tenant_id": str(tenant_id),
        "assessment_id": str(assessment_id),
        "student_id": str(student_id),
        "pdf_content": pdf_content,
        "filename": file.filename,
        "size": len(pdf_content)
    })
    
    await db.commit()
    
    return {
        "message": "Assignment submitted successfully",
        "submission_id": submission_id,
        "filename": file.filename,
        "size": len(pdf_content)
    }

@router.get("/download/{submission_id}")
async def download_submission(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download student submission PDF"""
    
    result = await db.execute(text("""
        SELECT submission_pdf, pdf_filename 
        FROM assessment_submissions 
        WHERE id = :submission_id AND submission_pdf IS NOT NULL
    """), {"submission_id": str(submission_id)})
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return Response(
        content=row[0],
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={row[1]}"}
    )

@router.get("/submissions/{assessment_id}")
async def list_submissions(
    assessment_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all submissions for an assessment"""
    
    result = await db.execute(text("""
        SELECT s.id, s.student_id, s.pdf_filename, s.pdf_size, s.submission_date, s.status,
               st.first_name, st.last_name
        FROM assessment_submissions s
        LEFT JOIN students st ON s.student_id = st.id
        WHERE s.assessment_id = :assessment_id AND s.tenant_id = :tenant_id
    """), {"assessment_id": str(assessment_id), "tenant_id": str(tenant_id)})
    
    submissions = [
        {
            "submission_id": str(row[0]),
            "student_id": str(row[1]),
            "filename": row[2],
            "size": row[3],
            "submitted_at": row[4].isoformat() if row[4] else None,
            "status": row[5],
            "student_name": f"{row[6]} {row[7]}" if row[6] and row[7] else "Unknown"
        }
        for row in result.fetchall()
    ]
    
    return {"assessment_id": str(assessment_id), "submissions": submissions}