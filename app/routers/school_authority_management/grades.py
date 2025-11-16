from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from ...core.database import get_db
from ...services.grades_service import GradesService
from ...models.tenant_specific.grades_assessment import Assessment, AssessmentSubmission, StudentGrade, ReportCard
from ...models.tenant_specific.timetable import Subject
from ...models.tenant_specific.student import Student
from ...models.tenant_specific.class_model import ClassModel
from ...models.tenant_specific.teacher import Teacher

router = APIRouter(prefix="/api/v1/school_authority/grades", tags=["School Authority - Grades & Assessment"])

# Test endpoint
@router.get("/test", response_model=dict)
async def test_grades_system(
    db: AsyncSession = Depends(get_db)
):
    """Test grades system connectivity"""
    try:
        # Simple test query
        stmt = select(Subject).limit(1)
        result = await db.execute(stmt)
        subject = result.scalar_one_or_none()
        
        # Get sample class and teacher for the same tenant
        class_stmt = select(ClassModel).where(ClassModel.tenant_id == subject.tenant_id).limit(1)
        class_result = await db.execute(class_stmt)
        class_obj = class_result.scalar_one_or_none()
        
        teacher_stmt = select(Teacher).where(Teacher.tenant_id == subject.tenant_id).limit(1)
        teacher_result = await db.execute(teacher_stmt)
        teacher_obj = teacher_result.scalar_one_or_none()
        
        student_stmt = select(Student).where(Student.tenant_id == subject.tenant_id).limit(1)
        student_result = await db.execute(student_stmt)
        student_obj = student_result.scalar_one_or_none()
        
        return {
            "message": "Grades system is working",
            "database_connected": True,
            "sample_subject": str(subject.id) if subject else None,
            "sample_tenant": str(subject.tenant_id) if subject else None,
            "sample_class": str(class_obj.id) if class_obj else None,
            "sample_teacher": str(teacher_obj.id) if teacher_obj else None,
            "sample_student": str(student_obj.id) if student_obj else None
        }
    except Exception as e:
        return {
            "message": "Grades system test failed",
            "database_connected": False,
            "error": str(e)
        }

# Direct assessment creation without dependency injection
@router.post("/assessments-direct", response_model=dict)
async def create_assessment_direct(
    assessment_data: dict
):
    """Create assessment directly without dependency injection"""
    from ...core.database import AsyncSessionLocal
    from datetime import datetime
    
    async with AsyncSessionLocal() as db:
        try:
            # Parse datetime if it's a string
            if "due_date" in assessment_data and isinstance(assessment_data["due_date"], str):
                assessment_data["due_date"] = datetime.fromisoformat(assessment_data["due_date"])
            
            # Explicitly set status to avoid enum issues (ensure lowercase)
            assessment_data["status"] = "draft"
            
            assessment = Assessment(**assessment_data)
            db.add(assessment)
            await db.commit()
            
            return {
                "id": str(assessment.id),
                "message": "Assessment created successfully (direct)",
                "assessment_title": assessment_data.get("assessment_title", "")
            }
        except Exception as e:
            await db.rollback()
            return {
                "error": str(e),
                "message": "Failed to create assessment"
            }

# Subjects Management (for grades system)
@router.post("/subjects", response_model=dict)
async def create_subject(
    subject_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a subject for grades system"""
    try:
        subject = Subject(
            tenant_id=subject_data["tenant_id"],
            subject_name=subject_data["subject_name"],
            subject_code=subject_data["subject_code"],
            description=subject_data.get("description", ""),
            grade_levels=subject_data.get("grade_levels", []),
            subject_category=subject_data.get("subject_category", "core"),
            periods_per_week=subject_data.get("periods_per_week", 5),
            academic_year=subject_data["academic_year"]
        )
        
        db.add(subject)
        await db.commit()
        await db.refresh(subject)
        
        return {
            "id": str(subject.id),
            "message": "Subject created successfully",
            "subject_name": subject.subject_name,
            "subject_code": subject.subject_code
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subjects", response_model=List[dict])
async def get_subjects(
    tenant_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Get all subjects for a tenant"""
    try:
        stmt = select(Subject).where(Subject.tenant_id == tenant_id)
        result = await db.execute(stmt)
        subjects = result.scalars().all()
        
        return [
            {
                "id": str(subject.id),
                "subject_name": subject.subject_name,
                "subject_code": subject.subject_code,
                "description": subject.description,
                "grade_levels": subject.grade_levels,
                "subject_category": subject.subject_category,
                "periods_per_week": subject.periods_per_week,
                "academic_year": subject.academic_year
            }
            for subject in subjects
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Assessment Management
@router.post("/assessments", response_model=dict)
async def create_assessment(
    assessment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new assessment using existing subjects/classes/teachers"""
    try:
        # Store values before commit
        assessment_title = assessment_data.get("assessment_title", "")
        
        # Parse datetime if it's a string
        if "due_date" in assessment_data and isinstance(assessment_data["due_date"], str):
            assessment_data["due_date"] = datetime.fromisoformat(assessment_data["due_date"])
        
        # Ensure status is lowercase for database enum
        if "status" in assessment_data:
            assessment_data["status"] = assessment_data["status"].lower()
        
        # Ensure assessment_type is lowercase for database enum
        if "assessment_type" in assessment_data:
            assessment_data["assessment_type"] = assessment_data["assessment_type"].lower()
        
        # Create assessment
        assessment = Assessment(**assessment_data)
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)
        
        return {
            "id": str(assessment.id),
            "message": "Assessment created successfully",
            "assessment_title": assessment_title
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/assessments/{class_id}", response_model=List[dict])
async def get_class_assessments(
    class_id: UUID,
    subject_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get assessments for a class"""
    try:
        stmt = select(Assessment).where(Assessment.class_id == class_id)
        
        if subject_id:
            stmt = stmt.where(Assessment.subject_id == subject_id)
        
        result = await db.execute(stmt)
        assessments = result.scalars().all()
        
        return [
            {
                "id": str(assessment.id),
                "assessment_title": assessment.assessment_title,
                "assessment_type": assessment.assessment_type.value,
                "subject_id": str(assessment.subject_id),
                "max_marks": float(assessment.max_marks),
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
async def submit_assessment(
    submission_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Submit an assessment"""
    service = GradesService(db)
    
    try:
        submission = await service.submit_assessment(
            assessment_id=UUID(submission_data["assessment_id"]),
            student_id=UUID(submission_data["student_id"]),
            submission_data={k: v for k, v in submission_data.items() 
                           if k not in ["assessment_id", "student_id"]}
        )
        
        return {
            "id": str(submission.id),
            "message": "Assessment submitted successfully",
            "submission_date": submission.submission_date.isoformat(),
            "is_late": submission.is_late
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Grading
@router.post("/submissions/{submission_id}/grade", response_model=dict)
async def grade_submission(
    submission_id: UUID,
    grading_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Grade an assessment submission"""
    service = GradesService(db)
    
    try:
        submission = await service.grade_submission(
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
@router.get("/students/{student_id}/class/{class_id}", response_model=List[dict])
async def get_student_grades(
    student_id: UUID,
    class_id: UUID,
    academic_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get grades for a specific student in a class"""
    service = GradesService(db)
    
    try:
        grades = await service.get_student_grades(
            student_id=student_id,
            class_id=class_id,
            academic_year=academic_year
        )
        
        return [
            {
                "id": str(grade.id),
                "subject_id": str(grade.subject_id),
                "academic_year": grade.academic_year,
                "term": grade.term,
                "percentage": float(grade.percentage) if grade.percentage else None,
                "letter_grade": grade.letter_grade,
                "gpa": float(grade.gpa) if grade.gpa else None,
                "is_final": grade.is_final,
                "teacher_comments": grade.teacher_comments,
                "last_updated": grade.last_updated.isoformat() if grade.last_updated else None
            }
            for grade in grades
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Report Cards
@router.post("/report-cards", response_model=dict)
async def generate_report_card(
    report_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Generate report card for a student"""
    service = GradesService(db)
    
    try:
        report_card = await service.generate_report_card(
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
async def get_student_report_cards(
    student_id: UUID,
    academic_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get report cards for a student"""
    try:
        stmt = select(ReportCard).where(ReportCard.student_id == student_id)
        if academic_year:
            stmt = stmt.where(ReportCard.academic_year == academic_year)
        
        result = await db.execute(stmt)
        report_cards = result.scalars().all()
        
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
                "is_published": rc.is_published,
                "generated_date": rc.generated_date.isoformat() if rc.generated_date else None,
                "subject_grades": rc.subject_grades
            }
            for rc in report_cards
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Setup grade scale
@router.patch("/assessments/{assessment_id}/status", response_model=dict)
async def update_assessment_status(
    assessment_id: UUID,
    status_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update assessment status (draft/published/completed/graded)"""
    try:
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        new_status = status_data.get("status", "").lower()
        valid_statuses = ["draft", "published", "completed", "graded"]
        
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        assessment.status = new_status
        await db.commit()
        
        return {
            "message": f"Assessment status updated to {new_status}",
            "assessment_id": str(assessment_id),
            "assessment_title": assessment.assessment_title,
            "new_status": new_status
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/assessments/{assessment_id}", response_model=dict)
async def delete_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an assessment"""
    try:
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        assessment_title = assessment.assessment_title
        
        await db.delete(assessment)
        await db.commit()
        
        return {
            "message": "Assessment deleted successfully",
            "assessment_title": assessment_title,
            "assessment_id": str(assessment_id)
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Student View Endpoints
@router.get("/students/{student_id}/dashboard", response_model=dict)
async def get_student_dashboard(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get student dashboard with assignments and grades"""
    try:
        # Get student info
        stmt = select(Student).where(Student.id == student_id)
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()
        
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get student's current grades first
        grades_stmt = select(StudentGrade).where(
            StudentGrade.student_id == student_id
        )
        grades_result = await db.execute(grades_stmt)
        grades = grades_result.scalars().all()
        
        # Get student's class from their grades (more reliable)
        class_id = None
        if grades:
            class_id = grades[0].class_id
        
        assessments = []
        if class_id:
            # Get published assessments for student's class
            assessments_stmt = select(Assessment).where(
                and_(
                    Assessment.class_id == class_id,
                    Assessment.status == "published"
                )
            )
            assessments_result = await db.execute(assessments_stmt)
            assessments = assessments_result.scalars().all()
        
        return {
            "student_name": f"{student.first_name} {student.last_name}",
            "student_id": str(student_id),
            "available_assignments": len(assessments),
            "current_grades": len(grades),
            "assignments": [
                {
                    "id": str(a.id),
                    "title": a.assessment_title,
                    "type": a.assessment_type,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                    "max_marks": float(a.max_marks)
                } for a in assessments
            ],
            "grades": [
                {
                    "subject_id": str(g.subject_id),
                    "percentage": float(g.percentage) if g.percentage else None,
                    "letter_grade": g.letter_grade,
                    "gpa": float(g.gpa) if g.gpa else None
                } for g in grades
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/students/{student_id}/submissions", response_model=List[dict])
async def get_student_submission_history(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get student's submission history"""
    try:
        stmt = select(AssessmentSubmission).join(Assessment).where(
            AssessmentSubmission.student_id == student_id
        ).order_by(AssessmentSubmission.submission_date.desc())
        
        result = await db.execute(stmt)
        submissions = result.scalars().all()
        
        submission_history = []
        for submission in submissions:
            # Get assessment details
            assessment_stmt = select(Assessment).where(Assessment.id == submission.assessment_id)
            assessment_result = await db.execute(assessment_stmt)
            assessment = assessment_result.scalar_one_or_none()
            
            submission_history.append({
                "submission_id": str(submission.id),
                "assessment_title": assessment.assessment_title if assessment else "Unknown",
                "assessment_type": assessment.assessment_type if assessment else "unknown",
                "submission_date": submission.submission_date.isoformat() if submission.submission_date else None,
                "is_graded": submission.is_graded,
                "marks_obtained": float(submission.marks_obtained) if submission.marks_obtained else None,
                "percentage": float(submission.percentage) if submission.percentage else None,
                "grade_letter": submission.grade_letter,
                "teacher_feedback": submission.teacher_feedback,
                "is_late": submission.is_late
            })
        
        return submission_history
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/setup-grade-scale", response_model=dict)
async def setup_grade_scale(
    setup_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Setup default grade scale for a tenant"""
    service = GradesService(db)
    
    try:
        await service.create_default_grade_scale(
            tenant_id=UUID(setup_data["tenant_id"]),
            academic_year=setup_data["academic_year"]
        )
        
        return {
            "message": "Grade scale setup successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Analytics and Reports
@router.get("/analytics/class/{class_id}", response_model=dict)
async def get_class_performance_analytics(
    class_id: UUID,
    subject_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get class performance analytics"""
    try:
        # Get all student grades for the class
        stmt = select(StudentGrade).where(StudentGrade.class_id == class_id)
        if subject_id:
            stmt = stmt.where(StudentGrade.subject_id == subject_id)
        
        result = await db.execute(stmt)
        grades = result.scalars().all()
        
        if not grades:
            return {"message": "No grades found for this class", "analytics": {}}
        
        # Calculate analytics
        percentages = [float(g.percentage) for g in grades if g.percentage]
        
        analytics = {
            "total_students": len(grades),
            "average_percentage": sum(percentages) / len(percentages) if percentages else 0,
            "highest_percentage": max(percentages) if percentages else 0,
            "lowest_percentage": min(percentages) if percentages else 0,
            "grade_distribution": {},
            "pass_rate": len([p for p in percentages if p >= 60]) / len(percentages) * 100 if percentages else 0
        }
        
        # Grade distribution
        for grade in grades:
            letter = grade.letter_grade or "N/A"
            analytics["grade_distribution"][letter] = analytics["grade_distribution"].get(letter, 0) + 1
        
        return {"class_id": str(class_id), "analytics": analytics}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analytics/teacher/{teacher_id}", response_model=dict)
async def get_teacher_performance_report(
    teacher_id: UUID,
    academic_year: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get teacher performance report"""
    try:
        # Get assessments created by teacher
        stmt = select(Assessment).where(Assessment.teacher_id == teacher_id)
        if academic_year:
            stmt = stmt.where(Assessment.academic_year == academic_year)
        
        result = await db.execute(stmt)
        assessments = result.scalars().all()
        
        # Get submissions for teacher's assessments
        assessment_ids = [a.id for a in assessments]
        if assessment_ids:
            submissions_stmt = select(AssessmentSubmission).where(
                AssessmentSubmission.assessment_id.in_(assessment_ids)
            )
            submissions_result = await db.execute(submissions_stmt)
            submissions = submissions_result.scalars().all()
        else:
            submissions = []
        
        # Calculate teacher metrics
        graded_submissions = [s for s in submissions if s.is_graded]
        
        report = {
            "teacher_id": str(teacher_id),
            "total_assessments_created": len(assessments),
            "total_submissions_received": len(submissions),
            "submissions_graded": len(graded_submissions),
            "grading_completion_rate": len(graded_submissions) / len(submissions) * 100 if submissions else 0,
            "assessment_types": {},
            "average_marks_given": sum([float(s.marks_obtained) for s in graded_submissions if s.marks_obtained]) / len(graded_submissions) if graded_submissions else 0
        }
        
        # Assessment type distribution
        for assessment in assessments:
            atype = assessment.assessment_type
            report["assessment_types"][atype] = report["assessment_types"].get(atype, 0) + 1
        
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analytics/grade-distribution/{class_id}", response_model=dict)
async def get_grade_distribution_chart_data(
    class_id: UUID,
    subject_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get grade distribution data for charts"""
    try:
        stmt = select(StudentGrade).where(StudentGrade.class_id == class_id)
        if subject_id:
            stmt = stmt.where(StudentGrade.subject_id == subject_id)
        
        result = await db.execute(stmt)
        grades = result.scalars().all()
        
        # Prepare chart data
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        percentage_ranges = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "0-59": 0}
        
        for grade in grades:
            # Letter grade distribution
            letter = grade.letter_grade or "F"
            if letter in distribution:
                distribution[letter] += 1
            
            # Percentage range distribution
            if grade.percentage:
                pct = float(grade.percentage)
                if pct >= 90: percentage_ranges["90-100"] += 1
                elif pct >= 80: percentage_ranges["80-89"] += 1
                elif pct >= 70: percentage_ranges["70-79"] += 1
                elif pct >= 60: percentage_ranges["60-69"] += 1
                else: percentage_ranges["0-59"] += 1
        
        return {
            "class_id": str(class_id),
            "total_students": len(grades),
            "letter_grade_distribution": distribution,
            "percentage_range_distribution": percentage_ranges
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Notifications
@router.post("/notifications/new-assignment", response_model=dict)
async def notify_students_new_assignment(
    notification_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Notify students about new assignment"""
    try:
        assessment_id = UUID(notification_data["assessment_id"])
        
        # Get assessment details
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        # Get students in the class through enrollments
        from ...models.tenant_specific.enrollment import Enrollment
        students_stmt = select(Student).join(Enrollment).where(
            and_(
                Enrollment.class_id == assessment.class_id,
                Enrollment.is_deleted == False,
                Student.is_deleted == False
            )
        )
        students_result = await db.execute(students_stmt)
        students = students_result.scalars().all()
        
        # Create notification records (simplified - in real app would integrate with notification service)
        notifications_created = []
        for student in students:
            notification = {
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "message": f"New assignment: {assessment.assessment_title}",
                "due_date": assessment.due_date.isoformat() if assessment.due_date else None
            }
            notifications_created.append(notification)
        
        return {
            "message": f"Notifications sent to {len(students)} students",
            "assessment_title": assessment.assessment_title,
            "notifications": notifications_created
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/notifications/grades-published", response_model=dict)
async def notify_students_grades_published(
    notification_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Notify students when grades are published"""
    try:
        assessment_id = UUID(notification_data["assessment_id"])
        
        # Get graded submissions for this assessment
        stmt = select(AssessmentSubmission).join(Assessment).where(
            and_(
                AssessmentSubmission.assessment_id == assessment_id,
                AssessmentSubmission.is_graded == True
            )
        )
        result = await db.execute(stmt)
        submissions = result.scalars().all()
        
        # Get assessment details
        assessment_stmt = select(Assessment).where(Assessment.id == assessment_id)
        assessment_result = await db.execute(assessment_stmt)
        assessment = assessment_result.scalar_one_or_none()
        
        notifications_created = []
        for submission in submissions:
            # Get student details
            student_stmt = select(Student).where(Student.id == submission.student_id)
            student_result = await db.execute(student_stmt)
            student = student_result.scalar_one_or_none()
            
            if student:
                notification = {
                    "student_id": str(student.id),
                    "student_name": f"{student.first_name} {student.last_name}",
                    "message": f"Grade published for: {assessment.assessment_title}",
                    "grade": submission.grade_letter,
                    "percentage": float(submission.percentage) if submission.percentage else None
                }
                notifications_created.append(notification)
        
        return {
            "message": f"Grade notifications sent to {len(submissions)} students",
            "assessment_title": assessment.assessment_title if assessment else "Unknown",
            "notifications": notifications_created
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/students/{student_id}/notifications", response_model=dict)
async def get_student_notifications(
    student_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get student notifications (simulated from recent activity)"""
    try:
        # Get recent graded submissions for notifications
        stmt = select(AssessmentSubmission).join(Assessment).where(
            and_(
                AssessmentSubmission.student_id == student_id,
                AssessmentSubmission.is_graded == True
            )
        ).order_by(AssessmentSubmission.graded_date.desc()).limit(5)
        
        result = await db.execute(stmt)
        submissions = result.scalars().all()
        
        notifications = []
        for submission in submissions:
            # Get assessment details
            assessment_stmt = select(Assessment).where(Assessment.id == submission.assessment_id)
            assessment_result = await db.execute(assessment_stmt)
            assessment = assessment_result.scalar_one_or_none()
            
            if assessment:
                notifications.append({
                    "type": "grade_published",
                    "message": f"Grade published for: {assessment.assessment_title}",
                    "assessment_title": assessment.assessment_title,
                    "grade": submission.grade_letter,
                    "percentage": float(submission.percentage) if submission.percentage else None,
                    "date": submission.graded_date.isoformat() if submission.graded_date else None
                })
        
        # Get recent published assignments
        published_stmt = select(Assessment).where(
            Assessment.status == "published"
        ).order_by(Assessment.updated_at.desc()).limit(3)
        
        published_result = await db.execute(published_stmt)
        published_assessments = published_result.scalars().all()
        
        for assessment in published_assessments:
            notifications.append({
                "type": "new_assignment",
                "message": f"New assignment: {assessment.assessment_title}",
                "assessment_title": assessment.assessment_title,
                "due_date": assessment.due_date.isoformat() if assessment.due_date else None,
                "date": assessment.updated_at.isoformat() if assessment.updated_at else None
            })
        
        return {
            "student_id": str(student_id),
            "total_notifications": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))