from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.grades_service import GradesService
from ...models.tenant_specific.grades_assessment import AssessmentType, GradingSystem

router = APIRouter(prefix="/api/v1/school_authority/grades", tags=["School Authority - Grades & Assessment"])

# Subject Management
@router.post("/subjects", response_model=dict)
async async def create_subject(
    subject_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new subject"""
    service = GradesService(db)
    
    try:
        subject = service.create_subject(subject_data)
        return {
            "id": str(subject.id),
            "message": "Subject created successfully",
            "subject_code": subject.subject_code,
            "subject_name": subject.subject_name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subjects/{tenant_id}", response_model=dict)
async async def get_subjects(
    tenant_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    academic_year: Optional[str] = Query(None),
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated subjects for a tenant"""
    service = GradesService(db)
    
    try:
        filters = {"tenant_id": tenant_id, "is_active": is_active}
        if academic_year:
            filters["academic_year"] = academic_year
        
        result = service.get_paginated(page=page, size=size, **filters)
        
        formatted_subjects = [
            {
                "id": str(subject.id),
                "subject_code": subject.subject_code,
                "subject_name": subject.subject_name,
                "description": subject.description,
                "department": subject.department,
                "credit_hours": subject.credit_hours,
                "academic_year": subject.academic_year,
                "grading_system": subject.grading_system.value,
                "passing_grade": float(subject.passing_grade),
                "max_grade": float(subject.max_grade),
                "grade_components": subject.grade_components
            }
            for subject in result["items"]
        ]
        
        return {
            "items": formatted_subjects,
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "has_next": result["has_next"],
            "has_previous": result["has_previous"],
            "total_pages": result["total_pages"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Class-Subject Assignment
@router.post("/class-subjects/assign", response_model=dict)
async async def assign_subject_to_class(
    assignment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Assign subject to a class with teacher"""
    service = GradesService(db)
    
    try:
        class_subject = service.assign_subject_to_class(
            subject_id=UUID(assignment_data["subject_id"]),
            class_id=UUID(assignment_data["class_id"]),
            teacher_id=UUID(assignment_data["teacher_id"]),
            assignment_data={k: v for k, v in assignment_data.items() 
                           if k not in ["subject_id", "class_id", "teacher_id"]}
        )
        
        return {
            "id": str(class_subject.id),
            "message": "Subject assigned to class successfully",
            "class_id": str(class_subject.class_id),
            "subject_id": str(class_subject.subject_id),
            "teacher_id": str(class_subject.teacher_id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Assessment Management
@router.post("/assessments", response_model=dict)
async async def create_assessment(
    assessment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new assessment"""
    service = GradesService(db)
    
    try:
        assessment = service.create_assessment(assessment_data)
        return {
            "id": str(assessment.id),
            "message": "Assessment created successfully",
            "assessment_title": assessment.assessment_title,
            "assessment_type": assessment.assessment_type.value,
            "max_marks": float(assessment.max_marks)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/assessments/{class_id}", response_model=List[dict])
async async def get_class_assessments(
    class_id: UUID,
    subject_id: Optional[UUID] = Query(None),
    assessment_type: Optional[AssessmentType] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get assessments for a class"""
    service = GradesService(db)
    
    try:
        filters = {"class_id": class_id}
        if subject_id:
            filters["subject_id"] = subject_id
        if assessment_type:
            filters["assessment_type"] = assessment_type
        
        from ..models.tenant_specific.grades_assessment import Assessment
        assessments = service.db.query(Assessment).filter_by(**filters).all()
        
        return [
            {
                "id": str(assessment.id),
                "assessment_title": assessment.assessment_title,
                "assessment_code": assessment.assessment_code,
                "assessment_type": assessment.assessment_type.value,
                "subject_name": assessment.subject.subject_name,
                "max_marks": float(assessment.max_marks),
                "scheduled_date": assessment.scheduled_date.isoformat() if assessment.scheduled_date else None,
                "due_date": assessment.due_date.isoformat() if assessment.due_date else None,
                "status": assessment.status.value,
                "academic_year": assessment.academic_year
            }
            for assessment in assessments
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Submission Management
@router.post("/submissions", response_model=dict)
async async def submit_assessment(
    submission_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Submit an assessment"""
    service = GradesService(db)
    
    try:
        submission = service.submit_assessment(
            assessment_id=UUID(submission_data["assessment_id"]),
            student_id=UUID(submission_data["student_id"]),
            submission_data={k: v for k, v in submission_data.items() 
                           if k not in ["assessment_id", "student_id"]}
        )
        
        return {
            "id": str(submission.id),
            "message": "Assessment submitted successfully",
            "submission_date": submission.submission_date.isoformat(),
            "is_late": submission.is_late,
            "attempt_number": submission.attempt_number
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Grading
@router.post("/submissions/{submission_id}/grade", response_model=dict)
async async def grade_submission(
    submission_id: UUID,
    grading_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Grade an assessment submission"""
    service = GradesService(db)
    
    try:
        submission = service.grade_submission(
            submission_id=submission_id,
            marks_obtained=grading_data["marks_obtained"],
            graded_by=UUID(grading_data["graded_by"]),
            feedback=grading_data.get("feedback")
        )
        
        return {
            "id": str(submission.id),
            "message": "Submission graded successfully",
            "marks_obtained": float(submission.marks_obtained),
            "percentage": float(submission.percentage),
            "grade_letter": submission.grade_letter,
            "graded_date": submission.graded_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Student Grades
@router.get("/students/{student_id}", response_model=List[dict])
async async def get_student_grades(
    student_id: UUID,
    academic_year: Optional[str] = Query(None),
    term: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get grades for a specific student"""
    service = GradesService(db)
    
    try:
        grades = service.get_student_grades(
            student_id=student_id,
            academic_year=academic_year,
            term=term
        )
        
        return [
            {
                "id": str(grade.id),
                "subject_name": grade.class_subject.subject.subject_name,
                "subject_code": grade.class_subject.subject.subject_code,
                "academic_year": grade.academic_year,
                "term": grade.term,
                "component_grades": grade.component_grades,
                "percentage": float(grade.percentage) if grade.percentage else None,
                "letter_grade": grade.letter_grade,
                "gpa": float(grade.gpa) if grade.gpa else None,
                "is_final": grade.is_final,
                "is_published": grade.is_published,
                "teacher_comments": grade.teacher_comments,
                "last_updated": grade.last_updated.isoformat() if grade.last_updated else None
            }
            for grade in grades
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Report Cards
@router.post("/report-cards", response_model=dict)
async async def generate_report_card(
    report_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Generate report card for a student"""
    service = GradesService(db)
    
    try:
        report_card = service.generate_report_card(
            student_id=UUID(report_data["student_id"]),
            class_id=UUID(report_data["class_id"]),
            report_period=report_data["report_period"],
            academic_year=report_data["academic_year"]
        )
        
        return {
            "id": str(report_card.id),
            "message": "Report card generated successfully",
            "overall_percentage": float(report_card.overall_percentage),
            "overall_gpa": float(report_card.overall_gpa),
            "overall_grade": report_card.overall_grade,
            "subjects_passed": report_card.subjects_passed,
            "subjects_failed": report_card.subjects_failed
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/report-cards/{student_id}", response_model=List[dict])
async async def get_student_report_cards(
    student_id: UUID,
    academic_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get report cards for a student"""
    service = GradesService(db)
    
    try:
        from ..models.tenant_specific.grades_assessment import ReportCard
        
        query = service.db.query(ReportCard).filter(ReportCard.student_id == student_id)
        if academic_year:
            query = query.filter(ReportCard.academic_year == academic_year)
        
        report_cards = query.all()
        
        return [
            {
                "id": str(rc.id),
                "report_period": rc.report_period,
                "academic_year": rc.academic_year,
                "overall_percentage": float(rc.overall_percentage),
                "overall_gpa": float(rc.overall_gpa),
                "overall_grade": rc.overall_grade,
                "total_subjects": rc.total_subjects,
                "subjects_passed": rc.subjects_passed,
                "subjects_failed": rc.subjects_failed,
                "class_rank": rc.class_rank,
                "total_students": rc.total_students,
                "attendance_percentage": float(rc.attendance_percentage) if rc.attendance_percentage else None,
                "is_published": rc.is_published,
                "generated_date": rc.generated_date.isoformat() if rc.generated_date else None,
                "subject_grades": rc.subject_grades
            }
            for rc in report_cards
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Class Performance
@router.get("/performance/class/{class_id}/subject/{subject_id}", response_model=dict)
async async def get_class_performance(
    class_id: UUID,
    subject_id: UUID,
    academic_year: str,
    db: AsyncSession = Depends(get_db)
):
    """Get class performance summary for a subject"""
    service = GradesService(db)
    
    try:
        performance = service.get_class_performance_summary(
            class_id=class_id,
            subject_id=subject_id,
            academic_year=academic_year
        )
        return performance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
