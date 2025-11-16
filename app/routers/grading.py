from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from fastapi.responses import Response

from ..core.database import get_db

router = APIRouter(prefix="/grading", tags=["Grading System"])

@router.post("/submit-assignment/{assessment_id}")
async def submit_assignment(
    assessment_id: UUID,
    student_id: UUID,
    tenant_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Submit assignment as PDF for grading"""
    
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
        "message": "Assignment submitted for grading",
        "submission_id": submission_id,
        "filename": file.filename,
        "size": len(pdf_content),
        "status": "submitted"
    }

@router.get("/submissions/{assessment_id}")
async def get_submissions_for_grading(
    assessment_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all submissions for grading by teachers"""
    
    result = await db.execute(text("""
        SELECT s.id, s.student_id, s.pdf_filename, s.pdf_size, s.submission_date, s.status,
               s.marks_obtained, s.grade_letter, s.teacher_feedback,
               st.first_name, st.last_name
        FROM assessment_submissions s
        LEFT JOIN students st ON s.student_id = st.id
        WHERE s.assessment_id = :assessment_id AND s.tenant_id = :tenant_id
        ORDER BY s.submission_date DESC
    """), {"assessment_id": str(assessment_id), "tenant_id": str(tenant_id)})
    
    submissions = [
        {
            "submission_id": str(row[0]),
            "student_id": str(row[1]),
            "filename": row[2],
            "size": row[3],
            "submitted_at": row[4].isoformat() if row[4] else None,
            "status": row[5],
            "marks_obtained": float(row[6]) if row[6] else None,
            "grade": row[7],
            "feedback": row[8],
            "student_name": f"{row[9]} {row[10]}" if row[9] and row[10] else "Unknown"
        }
        for row in result.fetchall()
    ]
    
    return {
        "assessment_id": str(assessment_id),
        "total_submissions": len(submissions),
        "submissions": submissions
    }

@router.get("/download-submission/{submission_id}")
async def download_submission_for_grading(
    submission_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Download student submission for grading"""
    
    result = await db.execute(text("""
        SELECT submission_pdf, pdf_filename, s.student_id, st.first_name, st.last_name
        FROM assessment_submissions s
        LEFT JOIN students st ON s.student_id = st.id
        WHERE s.id = :submission_id AND s.submission_pdf IS NOT NULL
    """), {"submission_id": str(submission_id)})
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    student_name = f"{row[3]}_{row[4]}" if row[3] and row[4] else "Unknown"
    filename = f"{student_name}_{row[1]}"
    
    return Response(
        content=row[0],
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/grade-submission/{submission_id}")
async def grade_submission(
    submission_id: UUID,
    marks: float,
    grade: str,
    feedback: str,
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Grade a student submission"""
    
    await db.execute(text("""
        UPDATE assessment_submissions 
        SET marks_obtained = :marks,
            grade_letter = :grade,
            teacher_feedback = :feedback,
            graded_by = :teacher_id,
            graded_date = NOW(),
            status = 'graded',
            is_graded = true
        WHERE id = :submission_id
    """), {
        "marks": marks,
        "grade": grade,
        "feedback": feedback,
        "teacher_id": str(teacher_id),
        "submission_id": str(submission_id)
    })
    
    await db.commit()
    
    return {
        "message": "Submission graded successfully",
        "submission_id": str(submission_id),
        "marks": marks,
        "grade": grade,
        "status": "graded"
    }