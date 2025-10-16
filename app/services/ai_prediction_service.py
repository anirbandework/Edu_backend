# from typing import List, Optional, Dict, Any, Tuple
# from uuid import UUID
# import uuid
# import json
# import numpy as np
# import pandas as pd
# from datetime import datetime, timedelta
# from decimal import Decimal
# from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
# from sqlalchemy import and_, or_, func
# import logging

# # ML Imports (install with: pip install scikit-learn pandas numpy)
# from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# from sklearn.naive_bayes import GaussianNB
# from sklearn.neighbors import KNeighborsRegressor
# from sklearn.model_selection import train_test_split, cross_val_score
# from sklearn.preprocessing import StandardScaler, LabelEncoder
# from sklearn.metrics import mean_absolute_error, r2_score
# import pickle
# import joblib

# from .base_service import BaseService
# from ..models.tenant_specific.ai_prediction import (
#     StudentPerformanceData, PerformancePrediction, PredictionModel,
#     ModelTrainingJob, PredictionFeedback, PredictionModel as ModelEnum,
#     PredictionStatus, SubjectDifficulty
# )

# class AIPredictionService(BaseService[PerformancePrediction]):
#     async def __init__(self, db: Session):
#         super().__init__(PerformancePrediction, db)
#         self.logger = logging.getLogger(__name__)
    
#     async def collect_student_performance_data(
#         self,
#         student_id: UUID,
#         tenant_id: UUID
#     ) -> StudentPerformanceData:
#         """Collect and aggregate all available performance data for a student"""
        
#         # Get student's basic info
#         from ..models.tenant_specific.student import Student
#         from ..models.tenant_specific.grades_assessment import StudentGrade, AssessmentSubmission
#         from ..models.tenant_specific.attendance import Attendance
#         from ..models.tenant_specific.doubt_chat import ChatRoom
        
#         student = self.await db.execute(select(Student).filter(Student.id == student_id).first()
#         if not student:
#             raise ValueError("Student not found")
        
#         # Collect exam scores from StudentGrade
#         student_grades = self.await db.execute(select(StudentGrade).filter(
#             StudentGrade.student_id == student_id
#         ).all()
        
#         exam_scores = {}
#         subject_averages = {}
#         for grade in student_grades:
#             subject_name = grade.class_subject.subject.subject_name.lower()
#             if subject_name not in exam_scores:
#                 exam_scores[subject_name] = []
            
#             if grade.percentage:
#                 exam_scores[subject_name].append(float(grade.percentage))
        
#         # Calculate subject averages
#         for subject, scores in exam_scores.items():
#             subject_averages[subject] = sum(scores) / len(scores) if scores else 0
        
#         # Collect assessment submissions
#         assessment_data = self.await db.execute(select(AssessmentSubmission).join(
#             AssessmentSubmission.assessment
#         ).filter(
#             AssessmentSubmission.student_id == student_id,
#             AssessmentSubmission.is_graded == True
#         ).all()
        
#         assignment_scores = {}
#         quiz_scores = {}
#         project_scores = {}
        
#         for submission in assessment_data:
#             subject = submission.assessment.subject.subject_name.lower()
#             assessment_type = submission.assessment.assessment_type.value
#             score = float(submission.percentage) if submission.percentage else 0
            
#             if assessment_type in ["assignment", "homework"]:
#                 if subject not in assignment_scores:
#                     assignment_scores[subject] = []
#                 assignment_scores[subject].append(score)
#             elif assessment_type == "quiz":
#                 if subject not in quiz_scores:
#                     quiz_scores[subject] = []
#                 quiz_scores[subject].append(score)
#             elif assessment_type == "project":
#                 if subject not in project_scores:
#                     project_scores[subject] = []
#                 project_scores[subject].append(score)
        
#         # Calculate attendance percentage
#         attendance_records = self.await db.execute(select(Attendance).filter(
#             Attendance.student_id == student_id
#         ).all()
        
#         total_days = len(attendance_records)
#         present_days = len([a for a in attendance_records if a.status == "present"])
#         attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
#         # Calculate doubt resolution rate from chat system
#         chat_rooms = self.await db.execute(select(ChatRoom).filter(
#             ChatRoom.student_id == student_id
#         ).all()
        
#         total_chats = len(chat_rooms)
#         resolved_chats = len([c for c in chat_rooms if c.is_resolved])
#         doubt_resolution_rate = (resolved_chats / total_chats * 100) if total_chats > 0 else 0
        
#         # Calculate trends and patterns
#         subject_trends = self._calculate_subject_trends(exam_scores)
#         performance_over_time = self._calculate_performance_trends(student_grades)
        
#         # Create or update performance data record
#         performance_data = self.await db.execute(select(StudentPerformanceData).filter(
#             StudentPerformanceData.student_id == student_id,
#             StudentPerformanceData.current_grade == student.grade_level,
#             StudentPerformanceData.academic_year == "2025-2026"  # Current academic year
#         ).first()
        
#         if not performance_data:
#             performance_data = StudentPerformanceData(
#                 tenant_id=tenant_id,
#                 student_id=student_id,
#                 current_grade=student.grade_level,
#                 academic_year="2025-2026"
#             )
#             self.db.add(performance_data)
        
#         # Update with collected data
#         performance_data.exam_scores = exam_scores
#         performance_data.assignment_scores = assignment_scores
#         performance_data.quiz_scores = quiz_scores
#         performance_data.project_scores = project_scores
#         performance_data.subject_averages = subject_averages
#         performance_data.subject_trends = subject_trends
#         performance_data.attendance_percentage = attendance_percentage
#         performance_data.doubt_resolution_rate = doubt_resolution_rate
#         performance_data.performance_over_time = performance_over_time
#         performance_data.last_updated = datetime.now()
#         performance_data.data_completeness_score = self._calculate_completeness_score(performance_data)
        
#         # Calculate homework completion and participation (mock data for now)
#         performance_data.homework_completion_rate = self._estimate_homework_completion(assignment_scores)
#         performance_data.class_participation_score = self._estimate_participation_score(
#             doubt_resolution_rate, attendance_percentage
#         )
        
#         self.db.commit()
#         self.db.refresh(performance_data)
        
#         return performance_data
    
#     async def _calculate_subject_trends(self, exam_scores: Dict[str, List[float]]) -> Dict[str, str]:
#         """Calculate whether each subject is improving, declining, or stable"""
#         trends = {}
        
#         for subject, scores in exam_scores.items():
#             if len(scores) < 2:
#                 trends[subject] = "insufficient_data"
#                 continue
            
#             # Simple linear trend analysis
#             recent_avg = sum(scores[-3:]) / len(scores[-3:])  # Last 3 scores
#             earlier_avg = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else sum(scores[:2]) / 2
            
#             if recent_avg > earlier_avg + 5:
#                 trends[subject] = "improving"
#             elif recent_avg < earlier_avg - 5:
#                 trends[subject] = "declining"
#             else:
#                 trends[subject] = "stable"
        
#         return trends
    
#     async def _calculate_performance_trends(self, grades) -> Dict[str, Any]:
#         """Calculate month-wise performance trends"""
#         monthly_performance = {}
        
#         for grade in grades:
#             if grade.last_updated:
#                 month_key = grade.last_updated.strftime("%Y-%m")
#                 if month_key not in monthly_performance:
#                     monthly_performance[month_key] = []
                
#                 if grade.percentage:
#                     monthly_performance[month_key].append(float(grade.percentage))
        
#         # Calculate monthly averages
#         monthly_averages = {}
#         for month, scores in monthly_performance.items():
#             monthly_averages[month] = sum(scores) / len(scores) if scores else 0
        
#         return monthly_averages
    
#     async def _calculate_completeness_score(self, performance_data: StudentPerformanceData) -> float:
#         """Calculate how complete the performance data is (0-100)"""
#         factors = [
#             performance_data.exam_scores,
#             performance_data.assignment_scores,
#             performance_data.attendance_percentage,
#             performance_data.subject_averages,
#             performance_data.performance_over_time
#         ]
        
#         completed_factors = sum(1 for factor in factors if factor)
#         return (completed_factors / len(factors)) * 100
    
#     async def _estimate_homework_completion(self, assignment_scores: Dict[str, List[float]]) -> float:
#         """Estimate homework completion rate based on assignment submissions"""
#         if not assignment_scores:
#             return 50.0  # Default assumption
        
#         total_assignments = sum(len(scores) for scores in assignment_scores.values())
#         # Assume each subject should have at least 10 assignments per term
#         expected_assignments = len(assignment_scores) * 10
        
#         return min(100.0, (total_assignments / expected_assignments) * 100) if expected_assignments > 0 else 50.0
    
#     async def _estimate_participation_score(
#         self, 
#         doubt_resolution_rate: float, 
#         attendance_percentage: float
#     ) -> float:
#         """Estimate class participation based on available metrics"""
#         # Weighted combination of attendance and doubt resolution
#         participation = (attendance_percentage * 0.7) + (doubt_resolution_rate * 0.3)
#         return min(100.0, participation)
    
#     async def predict_performance(
#         self,
#         student_id: UUID,
#         target_grade: str = "10th",
#         model_type: ModelEnum = ModelEnum.RANDOM_FOREST
#     ) -> PerformancePrediction:
#         """Generate performance prediction for a student"""
        
#         # Get student performance data
#         performance_data = self.await db.execute(select(StudentPerformanceData).filter(
#             StudentPerformanceData.student_id == student_id
#         ).order_by(StudentPerformanceData.last_updated.desc()).first()
        
#         if not performance_data:
#             # Collect data first
#             performance_data = self.collect_student_performance_data(
#                 student_id, 
#                 self.await db.execute(select(self.get_student_tenant_id(student_id)).first()
#             )
        
#         # Prepare features for prediction
#         features = self._prepare_features(performance_data)
        
#         # Load or train model
#         model = self._get_or_create_model(model_type, performance_data.tenant_id)
        
#         # Generate predictions
#         predictions = self._generate_predictions(model, features)
        
#         # Create prediction record
#         prediction_id = f"PRED{uuid.uuid4().hex[:8].upper()}"
        
#         prediction = PerformancePrediction(
#             tenant_id=performance_data.tenant_id,
#             student_id=student_id,
#             student_data_id=performance_data.id,
#             prediction_id=prediction_id,
#             prediction_date=datetime.now(),
#             source_grade=performance_data.current_grade,
#             target_grade=target_grade,
#             model_used=model_type,
#             model_version="1.0",
#             status=PredictionStatus.COMPLETED,
#             predicted_scores=predictions["subject_scores"],
#             confidence_scores=predictions["confidence_scores"],
#             prediction_ranges=predictions["prediction_ranges"],
#             overall_predicted_percentage=predictions["overall_percentage"],
#             dropout_risk_score=predictions["dropout_risk"],
#             subjects_at_risk=predictions["subjects_at_risk"],
#             intervention_recommendations=predictions["interventions"],
#             influential_factors=predictions["influential_factors"],
#             explanation=predictions["explanation"],
#             key_insights=predictions["key_insights"],
#             validation_score=predictions["confidence_scores"].get("overall", 0.8) * 100
#         )
        
#         self.db.add(prediction)
#         self.db.commit()
#         self.db.refresh(prediction)
        
#         return prediction
    
#     async def _prepare_features(self, performance_data: StudentPerformanceData) -> np.ndarray:
#         """Prepare features for ML model"""
        
#         features = []
        
#         # Subject averages
#         subject_averages = performance_data.subject_averages or {}
#         for subject in ["math", "science", "english", "social_studies", "hindi"]:
#             features.append(subject_averages.get(subject, 50.0))
        
#         # Attendance and engagement
#         features.append(float(performance_data.attendance_percentage or 75.0))
#         features.append(float(performance_data.homework_completion_rate or 70.0))
#         features.append(float(performance_data.class_participation_score or 65.0))
#         features.append(float(performance_data.doubt_resolution_rate or 60.0))
        
#         # Trend analysis
#         subject_trends = performance_data.subject_trends or {}
#         trend_score = 0
#         for trend in subject_trends.values():
#             if trend == "improving":
#                 trend_score += 1
#             elif trend == "declining":
#                 trend_score -= 1
#         features.append(trend_score)
        
#         # Performance consistency (standard deviation of scores)
#         exam_scores = performance_data.exam_scores or {}
#         consistency_scores = []
#         for scores in exam_scores.values():
#             if len(scores) > 1:
#                 consistency_scores.append(np.std(scores))
        
#         avg_consistency = np.mean(consistency_scores) if consistency_scores else 10.0
#         features.append(avg_consistency)
        
#         # Data completeness
#         features.append(float(performance_data.data_completeness_score or 50.0))
        
#         return np.array(features).reshape(1, -1)
    
#     async def _get_or_create_model(self, model_type: ModelEnum, tenant_id: UUID):
#         """Get existing model or create a new one"""
        
#         # Try to get existing trained model
#         existing_model = self.await db.execute(select(PredictionModel).filter(
#             PredictionModel.tenant_id == tenant_id,
#             PredictionModel.model_type == model_type,
#             PredictionModel.is_active == True
#         ).first()
        
#         if existing_model and existing_model.model_file_path:
#             try:
#                 # Load the saved model
#                 model = joblib.load(existing_model.model_file_path)
#                 return model
#             except Exception as e:
#                 self.logger.warning(f"Could not load saved model: {e}")
        
#         # Create and train a new model
#         return self._train_new_model(model_type, tenant_id)
    
#     async def _train_new_model(self, model_type: ModelEnum, tenant_id: UUID):
#         """Train a new prediction model"""
        
#         # Get training data (historical student data)
#         training_data = self._prepare_training_data(tenant_id)
        
#         if len(training_data) < 10:
#             # Not enough data, use a pre-trained generic model
#             return self._create_generic_model(model_type)
        
#         X, y = training_data["features"], training_data["targets"]
        
#         # Split data
#         X_train, X_test, y_train, y_test = train_test_split(
#             X, y, test_size=0.2, random_state=42
#         )
        
#         # Create model based on type
#         if model_type == ModelEnum.RANDOM_FOREST:
#             model = RandomForestRegressor(n_estimators=100, random_state=42)
#         elif model_type == ModelEnum.GRADIENT_BOOSTING:
#             model = GradientBoostingRegressor(random_state=42)
#         elif model_type == ModelEnum.KNN:
#             model = KNeighborsRegressor(n_neighbors=5)
#         else:
#             model = RandomForestRegressor(n_estimators=100, random_state=42)
        
#         # Train model
#         model.fit(X_train, y_train)
        
#         # Evaluate model
#         y_pred = model.predict(X_test)
#         accuracy = r2_score(y_test, y_pred)
#         mae = mean_absolute_error(y_test, y_pred)
        
#         # Save model record
#         model_record = PredictionModel(
#             tenant_id=tenant_id,
#             model_name=f"{model_type.value}_predictor",
#             model_type=model_type,
#             training_completion_date=datetime.now(),
#             training_data_size=len(X_train),
#             validation_data_size=len(X_test),
#             accuracy=accuracy * 100,
#             mean_absolute_error=mae,
#             is_active=True
#         )
        
#         self.db.add(model_record)
#         self.db.commit()
        
#         return model
    
#     async def _prepare_training_data(self, tenant_id: UUID) -> Dict[str, np.ndarray]:
#         """Prepare training data from historical student records"""
        
#         # Get all student performance data for the tenant
#         performance_records = self.await db.execute(select(StudentPerformanceData).filter(
#             StudentPerformanceData.tenant_id == tenant_id
#         ).all()
        
#         features = []
#         targets = []
        
#         for record in performance_records:
#             # Prepare features
#             feature_vector = self._prepare_features(record).flatten()
#             features.append(feature_vector)
            
#             # Use current overall performance as target (for now)
#             subject_averages = record.subject_averages or {}
#             overall_avg = sum(subject_averages.values()) / len(subject_averages) if subject_averages else 70.0
#             targets.append(overall_avg)
        
#         return {
#             "features": np.array(features),
#             "targets": np.array(targets)
#         }
    
#     async def _create_generic_model(self, model_type: ModelEnum):
#         """Create a generic model with reasonable assumptions"""
#         # This would be a pre-trained model or rule-based system
#         # For now, return a simple model that can make basic predictions
#         return RandomForestRegressor(n_estimators=50, random_state=42)
    
#     async def _generate_predictions(self, model, features: np.ndarray) -> Dict[str, Any]:
#         """Generate comprehensive predictions using the model"""
        
#         # Mock prediction logic (replace with actual model predictions)
#         base_prediction = 75.0  # Base predicted percentage
        
#         # Subject-wise predictions (with some variation)
#         subjects = ["math", "science", "english", "social_studies", "hindi"]
#         subject_scores = {}
#         confidence_scores = {}
#         prediction_ranges = {}
        
#         for i, subject in enumerate(subjects):
#             # Use feature values to adjust predictions
#             subject_feature = features[0][i] if len(features[0]) > i else base_prediction
            
#             # Add some variation and logic
#             if subject == "math":
#                 predicted = subject_feature * 0.9 + 5  # Math tends to be challenging
#             elif subject == "english":
#                 predicted = subject_feature * 1.1 - 3  # English might be easier
#             else:
#                 predicted = subject_feature * 1.0
            
#             # Ensure reasonable range
#             predicted = max(30, min(95, predicted))
            
#             subject_scores[subject] = round(predicted, 1)
#             confidence_scores[subject] = 0.75 + (predicted / 200)  # Higher scores = higher confidence
#             prediction_ranges[subject] = {
#                 "min": max(0, predicted - 8),
#                 "max": min(100, predicted + 8)
#             }
        
#         overall_percentage = sum(subject_scores.values()) / len(subject_scores)
#         confidence_scores["overall"] = sum(confidence_scores.values()) / len(confidence_scores)
        
#         # Risk assessment
#         dropout_risk = max(0, 100 - overall_percentage)
#         subjects_at_risk = [subject for subject, score in subject_scores.items() if score < 60]
        
#         # Generate recommendations
#         interventions = self._generate_interventions(subject_scores, features[0])
        
#         # Influential factors
#         influential_factors = self._identify_influential_factors(features[0])
        
#         # Generate explanation
#         explanation = self._generate_explanation(subject_scores, overall_percentage, subjects_at_risk)
        
#         # Key insights
#         key_insights = self._generate_key_insights(subject_scores, features[0])
        
#         return {
#             "subject_scores": subject_scores,
#             "confidence_scores": confidence_scores,
#             "prediction_ranges": prediction_ranges,
#             "overall_percentage": round(overall_percentage, 1),
#             "dropout_risk": round(dropout_risk, 1),
#             "subjects_at_risk": subjects_at_risk,
#             "interventions": interventions,
#             "influential_factors": influential_factors,
#             "explanation": explanation,
#             "key_insights": key_insights
#         }
    
#     async def _generate_interventions(
#         self, 
#         subject_scores: Dict[str, float], 
#         features: np.ndarray
#     ) -> List[Dict[str, str]]:
#         """Generate intervention recommendations"""
        
#         interventions = []
#         attendance = features[5] if len(features) > 5 else 75
#         participation = features[7] if len(features) > 7 else 65
        
#         # Attendance-based interventions
#         if attendance < 75:
#             interventions.append({
#                 "type": "attendance",
#                 "priority": "high",
#                 "recommendation": "Improve attendance - current rate is below 75%. Consider counseling to identify barriers.",
#                 "expected_impact": "5-10 point improvement in overall performance"
#             })
        
#         # Subject-specific interventions
#         for subject, score in subject_scores.items():
#             if score < 60:
#                 interventions.append({
#                     "type": "academic",
#                     "priority": "high",
#                     "recommendation": f"Provide additional tutoring in {subject}. Current predicted score is {score}%.",
#                     "expected_impact": f"8-15 point improvement in {subject}"
#                 })
#             elif score < 75:
#                 interventions.append({
#                     "type": "academic",
#                     "priority": "medium",
#                     "recommendation": f"Strengthen fundamentals in {subject} through practice exercises.",
#                     "expected_impact": f"5-10 point improvement in {subject}"
#                 })
        
#         # Participation-based interventions
#         if participation < 70:
#             interventions.append({
#                 "type": "engagement",
#                 "priority": "medium",
#                 "recommendation": "Encourage more active participation in class discussions and doubt-clearing sessions.",
#                 "expected_impact": "3-7 point improvement in overall engagement"
#             })
        
#         return interventions
    
#     async def _identify_influential_factors(self, features: np.ndarray) -> List[Dict[str, Any]]:
#         """Identify factors that most influence the prediction"""
        
#         factor_names = [
#             "Math Performance", "Science Performance", "English Performance", 
#             "Social Studies Performance", "Hindi Performance", "Attendance Rate",
#             "Homework Completion", "Class Participation", "Doubt Resolution",
#             "Improvement Trend", "Performance Consistency", "Data Completeness"
#         ]
        
#         # Mock feature importance (in real implementation, use model.feature_importances_)
#         importance_scores = [0.15, 0.12, 0.10, 0.08, 0.07, 0.18, 0.12, 0.08, 0.05, 0.03, 0.02]
        
#         influential_factors = []
#         for i, (name, importance) in enumerate(zip(factor_names, importance_scores)):
#             if i < len(features):
#                 influential_factors.append({
#                     "factor": name,
#                     "importance": round(importance, 3),
#                     "current_value": round(features[i], 2) if i < len(features) else "N/A",
#                     "impact": "high" if importance > 0.1 else "medium" if importance > 0.05 else "low"
#                 })
        
#         # Sort by importance
#         influential_factors.sort(key=lambda x: x["importance"], reverse=True)
        
#         return influential_factors[:8]  # Top 8 factors
    
#     async def _generate_explanation(
#         self, 
#         subject_scores: Dict[str, float], 
#         overall_percentage: float,
#         subjects_at_risk: List[str]
#     ) -> str:
#         """Generate human-readable explanation"""
        
#         explanation = f"Based on the student's current 8th-grade performance, our AI model predicts an overall 10th-grade performance of {overall_percentage:.1f}%.\n\n"
        
#         # Performance category
#         if overall_percentage >= 85:
#             performance_category = "excellent"
#         elif overall_percentage >= 75:
#             performance_category = "good"
#         elif overall_percentage >= 60:
#             performance_category = "average"
#         else:
#             performance_category = "below average"
        
#         explanation += f"This indicates {performance_category} predicted performance in 10th grade.\n\n"
        
#         # Subject-wise breakdown
#         explanation += "Subject-wise predictions:\n"
#         for subject, score in subject_scores.items():
#             explanation += f"• {subject.title()}: {score:.1f}%\n"
        
#         # Risk factors
#         if subjects_at_risk:
#             explanation += f"\nSubjects requiring attention: {', '.join(subjects_at_risk)}\n"
        
#         explanation += "\nThis prediction is based on historical performance patterns, attendance, participation, and learning trends."
        
#         return explanation
    
#     async def _generate_key_insights(
#         self, 
#         subject_scores: Dict[str, float], 
#         features: np.ndarray
#     ) -> List[str]:
#         """Generate key insights from the analysis"""
        
#         insights = []
        
#         # Performance insights
#         best_subject = max(subject_scores, key=subject_scores.get)
#         worst_subject = min(subject_scores, key=subject_scores.get)
        
#         insights.append(f"Strongest predicted subject: {best_subject.title()} ({subject_scores[best_subject]:.1f}%)")
#         insights.append(f"Subject needing most attention: {worst_subject.title()} ({subject_scores[worst_subject]:.1f}%)")
        
#         # Attendance insight
#         if len(features) > 5:
#             attendance = features[5]
#             if attendance > 90:
#                 insights.append("Excellent attendance record positively impacts predicted performance")
#             elif attendance < 75:
#                 insights.append("Low attendance is a major risk factor for academic performance")
        
#         # Trend insights
#         if len(features) > 9:
#             trend_score = features[9]
#             if trend_score > 0:
#                 insights.append("Positive learning trend indicates potential for improvement")
#             elif trend_score < 0:
#                 insights.append("Declining trend suggests need for immediate intervention")
        
#         # Overall recommendation
#         overall_avg = sum(subject_scores.values()) / len(subject_scores)
#         if overall_avg >= 80:
#             insights.append("Student shows strong potential for academic success")
#         elif overall_avg < 60:
#             insights.append("Comprehensive academic support recommended")
        
#         return insights
    
#     async def get_prediction_by_id(self, prediction_id: str) -> Optional[PerformancePrediction]:
#         """Get prediction by prediction ID"""
#         return self.await db.execute(select(PerformancePrediction).filter(
#             PerformancePrediction.prediction_id == prediction_id
#         ).first()
    
#     async def get_student_predictions(
#         self,
#         student_id: UUID,
#         limit: int = 10
#     ) -> List[PerformancePrediction]:
#         """Get all predictions for a student"""
#         return self.await db.execute(select(PerformancePrediction).filter(
#             PerformancePrediction.student_id == student_id
#         ).order_by(PerformancePrediction.prediction_date.desc()).limit(limit).all()
