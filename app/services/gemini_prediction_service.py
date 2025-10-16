import google.generativeai as genai
from typing import Dict, Any, Optional
from uuid import UUID
import json
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base_service import BaseService
from ..core.config import settings

class GeminiPredictionService(BaseService):
    async def __init__(self, db: Session):
        super().__init__(None, db)
        self.logger = logging.getLogger(__name__)
        
        # Configure Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def collect_student_data(self, student_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """Collect student performance data from database"""
        
        from ..models.tenant_specific.student import Student
        from ..models.tenant_specific.grades_assessment import StudentGrade, AssessmentSubmission
        from ..models.tenant_specific.attendance import Attendance
        
        # Get student basic info
        student = self.await db.execute(select(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError("Student not found")
        
        # Get grades
        grades = self.await db.execute(select(StudentGrade).filter(
            StudentGrade.student_id == student_id
        ).all()
        
        # Get attendance
        attendance_records = self.await db.execute(select(Attendance).filter(
            Attendance.student_id == student_id
        ).all()
        
        # Get assignments
        assignments = self.await db.execute(select(AssessmentSubmission).filter(
            AssessmentSubmission.student_id == student_id,
            AssessmentSubmission.is_graded == True
        ).all()
        
        # Process data
        subject_scores = {}
        for grade in grades:
            subject_name = grade.class_subject.subject.subject_name
            if subject_name not in subject_scores:
                subject_scores[subject_name] = []
            if grade.percentage:
                subject_scores[subject_name].append(float(grade.percentage))
        
        # Calculate averages
        subject_averages = {}
        for subject, scores in subject_scores.items():
            if scores:
                subject_averages[subject] = sum(scores) / len(scores)
        
        # Calculate attendance
        total_days = len(attendance_records)
        present_days = len([a for a in attendance_records if a.status == "present"])
        attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
        
        return {
            "student_id": str(student_id),
            "student_name": f"{student.first_name} {student.last_name}",
            "current_grade": student.grade_level,
            "subject_averages": subject_averages,
            "attendance_rate": attendance_rate,
            "total_assignments": len(assignments),
            "completed_assignments": len([a for a in assignments if a.percentage and a.percentage >= 60])
        }
    
    async def predict_performance(
        self, 
        student_id: UUID, 
        target_grade: str = "10th",
        tenant_id: UUID = None
    ) -> Dict[str, Any]:
        """Generate AI prediction using Gemini API"""
        
        try:
            # Collect student data
            student_data = self.collect_student_data(student_id, tenant_id)
            
            # Create prompt for Gemini
            prompt = self._create_prediction_prompt(student_data, target_grade)
            
            # Get prediction from Gemini
            response = self.model.generate_content(prompt)
            
            # Parse and structure the response
            prediction_result = self._parse_gemini_response(response.text, student_data)
            
            return {
                "prediction_id": f"PRED{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "student_id": str(student_id),
                "source_grade": student_data["current_grade"],
                "target_grade": target_grade,
                "prediction_date": datetime.now().isoformat(),
                **prediction_result
            }
            
        except Exception as e:
            self.logger.error(f"Prediction failed for student {student_id}: {str(e)}")
            return {
                "error": "Prediction failed",
                "message": str(e),
                "student_id": str(student_id)
            }
    
    async def _create_prediction_prompt(self, student_data: Dict[str, Any], target_grade: str) -> str:
        """Create a detailed prompt for Gemini API"""
        
        prompt = f"""
You are an expert educational AI analyst. Based on the following 8th grade student performance data, predict their likely performance in 10th grade and provide detailed analysis.

STUDENT DATA:
- Name: {student_data['student_name']}
- Current Grade: {student_data['current_grade']}
- Target Grade: {target_grade}
- Attendance Rate: {student_data['attendance_rate']:.1f}%
- Total Assignments: {student_data['total_assignments']}
- Completed Assignments: {student_data['completed_assignments']}

SUBJECT PERFORMANCE:
{self._format_subject_data(student_data['subject_averages'])}

PLEASE PROVIDE A DETAILED ANALYSIS IN THE FOLLOWING JSON FORMAT:
{{
    "overall_predicted_percentage": <number>,
    "predicted_scores": {{
        "math": <number>,
        "science": <number>,
        "english": <number>,
        "social_studies": <number>,
        "hindi": <number>
    }},
    "confidence_level": <number 0-100>,
    "risk_assessment": {{
        "dropout_risk": <number 0-100>,
        "subjects_at_risk": [<list of subjects>]
    }},
    "strengths": [<list of academic strengths>],
    "areas_for_improvement": [<list of areas needing work>],
    "intervention_recommendations": [
        {{
            "type": "<academic/behavioral/attendance>",
            "priority": "<high/medium/low>",
            "action": "<specific recommendation>",
            "expected_impact": "<expected improvement>"
        }}
    ],
    "explanation": "<detailed explanation of prediction reasoning>",
    "key_insights": [<list of important insights>]
}}

Consider factors like:
- Current performance trends
- Attendance impact on learning
- Subject-wise strengths and weaknesses
- Assignment completion rates
- Typical academic progression patterns
- Areas where intervention would be most effective

Provide realistic, actionable predictions based on educational research and patterns.
"""
        return prompt
    
    async def _format_subject_data(self, subject_averages: Dict[str, float]) -> str:
        """Format subject data for the prompt"""
        if not subject_averages:
            return "No subject data available"
        
        formatted = []
        for subject, average in subject_averages.items():
            formatted.append(f"- {subject}: {average:.1f}%")
        
        return "\n".join(formatted)
    
    async def _parse_gemini_response(self, response_text: str, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate Gemini response"""
        
        try:
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_text = response_text[json_start:json_end]
                prediction_data = json.loads(json_text)
                
                # Validate and set defaults
                return {
                    "overall_predicted_percentage": prediction_data.get("overall_predicted_percentage", 75.0),
                    "predicted_scores": prediction_data.get("predicted_scores", {}),
                    "confidence_level": prediction_data.get("confidence_level", 80.0),
                    "dropout_risk": prediction_data.get("risk_assessment", {}).get("dropout_risk", 30.0),
                    "subjects_at_risk": prediction_data.get("risk_assessment", {}).get("subjects_at_risk", []),
                    "strengths": prediction_data.get("strengths", []),
                    "areas_for_improvement": prediction_data.get("areas_for_improvement", []),
                    "intervention_recommendations": prediction_data.get("intervention_recommendations", []),
                    "explanation": prediction_data.get("explanation", "AI analysis completed successfully."),
                    "key_insights": prediction_data.get("key_insights", [])
                }
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            self.logger.warning(f"Failed to parse Gemini response: {e}")
            
            # Return fallback prediction
            return {
                "overall_predicted_percentage": 75.0,
                "predicted_scores": self._generate_fallback_scores(student_data),
                "confidence_level": 70.0,
                "dropout_risk": 40.0,
                "subjects_at_risk": [],
                "strengths": ["Consistent attendance" if student_data["attendance_rate"] > 80 else "Needs improvement"],
                "areas_for_improvement": ["Overall academic performance"],
                "intervention_recommendations": [
                    {
                        "type": "academic",
                        "priority": "medium",
                        "action": "Regular tutoring sessions",
                        "expected_impact": "5-10% improvement"
                    }
                ],
                "explanation": f"Based on current performance data, the student shows potential for moderate improvement. Raw AI response: {response_text[:200]}...",
                "key_insights": ["Student data successfully collected", "Prediction generated using fallback method"]
            }
    
    async def _generate_fallback_scores(self, student_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate fallback subject predictions"""
        
        subject_averages = student_data.get("subject_averages", {})
        fallback_scores = {}
        
        for subject in ["math", "science", "english", "social_studies", "hindi"]:
            if subject in subject_averages:
                # Project slight improvement
                fallback_scores[subject] = min(95, subject_averages[subject] + 2)
            else:
                fallback_scores[subject] = 75.0
        
        return fallback_scores
