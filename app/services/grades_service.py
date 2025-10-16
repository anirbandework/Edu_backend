from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import and_, or_, func, desc
from .base_service import BaseService
from ..models.tenant_specific.grades_assessment import (
    Subject, ClassSubject, Assessment, AssessmentSubmission, StudentGrade,
    GradeScale, ReportCard, GradeAuditLog, AssessmentType, GradingSystem,
    AssessmentStatus, SubmissionStatus
)

class GradesService(BaseService[Subject]):
    async def __init__(self, db: Session):
        super().__init__(Subject, db)
    
    async def create_subject(self, subject_data: dict) -> Subject:
        """Create a new subject"""
        subject = self.create(subject_data)
        
        # Create default grade scale if not exists
        if not subject_data.get("grade_scale_id"):
            self._create_default_grade_scale(subject.tenant_id, subject.academic_year)
        
        return subject
    
    async def _create_default_grade_scale(self, tenant_id: UUID, academic_year: str):
        """Create default grade scale for the tenant"""
        existing = self.await db.execute(select(GradeScale).filter(
            GradeScale.tenant_id == tenant_id,
            GradeScale.academic_year == academic_year,
            GradeScale.is_default == True
        ).first()
        
        if not existing:
            default_scale = GradeScale(
                tenant_id=tenant_id,
                scale_name="Standard Grade Scale",
                academic_year=academic_year,
                is_default=True,
                grade_ranges=[
                    {"min": 90, "max": 100, "letter": "A", "gpa": 4.0},
                    {"min": 80, "max": 89, "letter": "B", "gpa": 3.0},
                    {"min": 70, "max": 79, "letter": "C", "gpa": 2.0},
                    {"min": 60, "max": 69, "letter": "D", "gpa": 1.0},
                    {"min": 0, "max": 59, "letter": "F", "gpa": 0.0}
                ]
            )
            self.db.add(default_scale)
            self.db.commit()
    
    async def assign_subject_to_class(
        self,
        subject_id: UUID,
        class_id: UUID,
        teacher_id: UUID,
        assignment_data: dict
    ) -> ClassSubject:
        """Assign subject to a class with a teacher"""
        class_subject = ClassSubject(
            subject_id=subject_id,
            class_id=class_id,
            teacher_id=teacher_id,
            **assignment_data
        )
        
        self.db.add(class_subject)
        self.db.commit()
        self.db.refresh(class_subject)
        
        return class_subject
    
    async def create_assessment(self, assessment_data: dict) -> Assessment:
        """Create a new assessment"""
        assessment = Assessment(**assessment_data)
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        return assessment
    
    async def submit_assessment(
        self,
        assessment_id: UUID,
        student_id: UUID,
        submission_data: dict
    ) -> AssessmentSubmission:
        """Submit an assessment"""
        
        # Check if assessment exists and is published
        assessment = self.await db.execute(select(Assessment).filter(
            Assessment.id == assessment_id,
            Assessment.status == AssessmentStatus.PUBLISHED
        ).first()
        
        if not assessment:
            raise ValueError("Assessment not found or not published")
        
        # Check for existing submission
        existing = self.await db.execute(select(AssessmentSubmission).filter(
            AssessmentSubmission.assessment_id == assessment_id,
            AssessmentSubmission.student_id == student_id
        ).first()
        
        if existing and assessment.attempts_allowed <= existing.attempt_number:
            raise ValueError("Maximum attempts exceeded")
        
        # Determine attempt number
        attempt_number = (existing.attempt_number + 1) if existing else 1
        
        # Check if late submission
        is_late = False
        if assessment.due_date and datetime.now() > assessment.due_date:
            if not assessment.allow_late_submission:
                raise ValueError("Late submission not allowed")
            is_late = True
        
        submission = AssessmentSubmission(
            tenant_id=assessment.tenant_id,
            assessment_id=assessment_id,
            student_id=student_id,
            submission_date=datetime.now(),
            is_late=is_late,
            attempt_number=attempt_number,
            status=SubmissionStatus.SUBMITTED,
            **submission_data
        )
        
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        
        return submission
    
    async def grade_submission(
        self,
        submission_id: UUID,
        marks_obtained: Decimal,
        graded_by: UUID,
        feedback: Optional[str] = None
    ) -> AssessmentSubmission:
        """Grade an assessment submission"""
        
        submission = self.await db.execute(select(AssessmentSubmission).filter(
            AssessmentSubmission.id == submission_id
        ).first()
        
        if not submission:
            raise ValueError("Submission not found")
        
        # Calculate percentage
        percentage = (marks_obtained / submission.assessment.max_marks) * 100
        
        # Apply late penalty if applicable
        if submission.is_late and submission.assessment.late_penalty_percent > 0:
            penalty = percentage * (submission.assessment.late_penalty_percent / 100)
            percentage = max(0, percentage - penalty)
            marks_obtained = (percentage / 100) * submission.assessment.max_marks
        
        # Determine letter grade
        letter_grade = self._calculate_letter_grade(
            percentage, submission.assessment.tenant_id, submission.assessment.academic_year
        )
        
        # Update submission
        submission.marks_obtained = marks_obtained
        submission.percentage = percentage
        submission.grade_letter = letter_grade
        submission.is_graded = True
        submission.teacher_feedback = feedback
        submission.graded_by = graded_by
        submission.graded_date = datetime.now()
        submission.status = SubmissionStatus.GRADED
        
        self.db.commit()
        
        # Update student's overall grade for the subject
        self._update_student_grade(submission.student_id, submission.assessment.subject_id)
        
        return submission
    
    async def _calculate_letter_grade(
        self, 
        percentage: Decimal, 
        tenant_id: UUID, 
        academic_year: str
    ) -> str:
        """Calculate letter grade based on percentage"""
        
        grade_scale = self.await db.execute(select(GradeScale).filter(
            GradeScale.tenant_id == tenant_id,
            GradeScale.academic_year == academic_year,
            GradeScale.is_default == True
        ).first()
        
        if not grade_scale:
            return "N/A"
        
        for range_data in grade_scale.grade_ranges:
            if range_data["min"] <= percentage <= range_data["max"]:
                return range_data["letter"]
        
        return "F"
    
    async def _update_student_grade(self, student_id: UUID, subject_id: UUID):
        """Update student's overall grade for a subject"""
        
        # Get class_subject_id
        class_subject = self.await db.execute(select(ClassSubject).filter(
            ClassSubject.subject_id == subject_id
        ).first()
        
        if not class_subject:
            return
        
        # Get all submissions for this student and subject
        submissions = self.await db.execute(select(AssessmentSubmission).join(Assessment).filter(
            Assessment.subject_id == subject_id,
            AssessmentSubmission.student_id == student_id,
            AssessmentSubmission.is_graded == True
        ).all()
        
        if not submissions:
            return
        
        # Group by assessment type and calculate component averages
        component_grades = {}
        component_weights = class_subject.custom_grade_components or class_subject.subject.grade_components or {}
        
        for submission in submissions:
            assessment_type = submission.assessment.assessment_type.value
            
            if assessment_type not in component_grades:
                component_grades[assessment_type] = []
            
            component_grades[assessment_type].append(float(submission.percentage))
        
        # Calculate component averages
        component_averages = {}
        for component, grades in component_grades.items():
            component_averages[component] = sum(grades) / len(grades)
        
        # Calculate weighted overall percentage
        total_weighted_score = 0
        total_weights = 0
        
        for component, weight in component_weights.items():
            if component in component_averages:
                total_weighted_score += component_averages[component] * weight
                total_weights += weight
        
        if total_weights == 0:
            return
        
        overall_percentage = total_weighted_score / total_weights
        
        # Get or create student grade record
        student_grade = self.await db.execute(select(StudentGrade).filter(
            StudentGrade.student_id == student_id,
            StudentGrade.class_subject_id == class_subject.id
        ).first()
        
        if not student_grade:
            student_grade = StudentGrade(
                tenant_id=class_subject.tenant_id,
                student_id=student_id,
                class_subject_id=class_subject.id,
                academic_year=class_subject.academic_year,
                term=class_subject.term
            )
            self.db.add(student_grade)
        
        # Update grade
        student_grade.component_grades = component_averages
        student_grade.component_weights = component_weights
        student_grade.percentage = overall_percentage
        student_grade.letter_grade = self._calculate_letter_grade(
            overall_percentage, class_subject.tenant_id, class_subject.academic_year
        )
        student_grade.gpa = self._calculate_gpa(
            overall_percentage, class_subject.tenant_id, class_subject.academic_year
        )
        student_grade.last_updated = datetime.now()
        
        self.db.commit()
    
    async def _calculate_gpa(
        self, 
        percentage: Decimal, 
        tenant_id: UUID, 
        academic_year: str
    ) -> Decimal:
        """Calculate GPA based on percentage"""
        
        grade_scale = self.await db.execute(select(GradeScale).filter(
            GradeScale.tenant_id == tenant_id,
            GradeScale.academic_year == academic_year,
            GradeScale.is_default == True
        ).first()
        
        if not grade_scale:
            return Decimal("0.00")
        
        for range_data in grade_scale.grade_ranges:
            if range_data["min"] <= percentage <= range_data["max"]:
                return Decimal(str(range_data["gpa"]))
        
        return Decimal("0.00")
    
    async def get_student_grades(
        self,
        student_id: UUID,
        academic_year: Optional[str] = None,
        term: Optional[str] = None
    ) -> List[StudentGrade]:
        """Get grades for a specific student"""
        
        query = self.await db.execute(select(StudentGrade).filter(
            StudentGrade.student_id == student_id
        )
        
        if academic_year:
            query = query.filter(StudentGrade.academic_year == academic_year)
        
        if term:
            query = query.filter(StudentGrade.term == term)
        
        return query.all()
    
    async def generate_report_card(
        self,
        student_id: UUID,
        class_id: UUID,
        report_period: str,
        academic_year: str
    ) -> ReportCard:
        """Generate report card for a student"""
        
        # Get student grades for the period
        student_grades = self.await db.execute(select(StudentGrade).join(ClassSubject).filter(
            StudentGrade.student_id == student_id,
            StudentGrade.academic_year == academic_year,
            ClassSubject.class_id == class_id
        ).all()
        
        if not student_grades:
            raise ValueError("No grades found for student")
        
        # Calculate overall statistics
        total_subjects = len(student_grades)
        subjects_passed = sum(1 for sg in student_grades if sg.percentage >= 60)
        subjects_failed = total_subjects - subjects_passed
        
        # Calculate overall percentage and GPA
        total_percentage = sum(float(sg.percentage) for sg in student_grades)
        overall_percentage = total_percentage / total_subjects if total_subjects > 0 else 0
        
        total_gpa = sum(float(sg.gpa) for sg in student_grades)
        overall_gpa = total_gpa / total_subjects if total_subjects > 0 else 0
        
        overall_grade = self._calculate_letter_grade(
            overall_percentage, student_grades[0].tenant_id, academic_year
        )
        
        # Prepare subject-wise grades
        subject_grades = []
        for sg in student_grades:
            subject_grades.append({
                "subject_name": sg.class_subject.subject.subject_name,
                "subject_code": sg.class_subject.subject.subject_code,
                "teacher_name": f"{sg.class_subject.teacher.personal_info.get('basic_details', {}).get('first_name', '')} {sg.class_subject.teacher.personal_info.get('basic_details', {}).get('last_name', '')}",
                "percentage": float(sg.percentage),
                "letter_grade": sg.letter_grade,
                "gpa": float(sg.gpa),
                "component_grades": sg.component_grades
            })
        
        # Create report card
        report_card = ReportCard(
            tenant_id=student_grades[0].tenant_id,
            student_id=student_id,
            class_id=class_id,
            report_period=report_period,
            academic_year=academic_year,
            total_subjects=total_subjects,
            subjects_passed=subjects_passed,
            subjects_failed=subjects_failed,
            overall_percentage=overall_percentage,
            overall_gpa=overall_gpa,
            overall_grade=overall_grade,
            subject_grades=subject_grades,
            generated_date=datetime.now()
        )
        
        self.db.add(report_card)
        self.db.commit()
        self.db.refresh(report_card)
        
        return report_card
    
    async def get_class_performance_summary(
        self,
        class_id: UUID,
        subject_id: UUID,
        academic_year: str
    ) -> Dict[str, Any]:
        """Get performance summary for a class in a subject"""
        
        # Get class subject
        class_subject = self.await db.execute(select(ClassSubject).filter(
            ClassSubject.class_id == class_id,
            ClassSubject.subject_id == subject_id,
            ClassSubject.academic_year == academic_year
        ).first()
        
        if not class_subject:
            raise ValueError("Class subject assignment not found")
        
        # Get all student grades for this class-subject
        student_grades = self.await db.execute(select(StudentGrade).filter(
            StudentGrade.class_subject_id == class_subject.id
        ).all()
        
        if not student_grades:
            return {"message": "No grades available"}
        
        # Calculate statistics
        percentages = [float(sg.percentage) for sg in student_grades if sg.percentage]
        
        total_students = len(student_grades)
        passed_students = sum(1 for sg in student_grades if sg.percentage >= 60)
        failed_students = total_students - passed_students
        
        average_percentage = sum(percentages) / len(percentages) if percentages else 0
        highest_percentage = max(percentages) if percentages else 0
        lowest_percentage = min(percentages) if percentages else 0
        
        # Grade distribution
        grade_distribution = {}
        for sg in student_grades:
            grade = sg.letter_grade or "N/A"
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        return {
            "class_id": str(class_id),
            "subject_name": class_subject.subject.subject_name,
            "academic_year": academic_year,
            "total_students": total_students,
            "passed_students": passed_students,
            "failed_students": failed_students,
            "pass_rate": round((passed_students / total_students * 100), 2) if total_students > 0 else 0,
            "average_percentage": round(average_percentage, 2),
            "highest_percentage": round(highest_percentage, 2),
            "lowest_percentage": round(lowest_percentage, 2),
            "grade_distribution": grade_distribution
        }
