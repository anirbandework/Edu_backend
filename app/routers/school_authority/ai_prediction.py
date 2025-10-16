# from typing import List, Optional
# from uuid import UUID
# from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
# from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

# from ...core.database import get_db
# from ...services.ai_prediction_service import AIPredictionService
# from ...models.tenant_specific.ai_prediction import PredictionModel as ModelEnum

# router = APIRouter(prefix="/api/v1/school_authority/ai-prediction", tags=["School Authority - AI Prediction"])

# @router.post("/collect-data/{student_id}", response_model=dict)
# async async def collect_student_data(
#     student_id: UUID,
#     tenant_id: UUID,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Collect and analyze student performance data"""
#     service = AIPredictionService(db)
    
#     try:
#         performance_data = service.collect_student_performance_data(
#             student_id=student_id,
#             tenant_id=tenant_id
#         )
        
#         return {
#             "message": "Student performance data collected successfully",
#             "student_id": str(student_id),
#             "data_completeness": float(performance_data.data_completeness_score or 0),
#             "subjects_analyzed": len(performance_data.subject_averages or {}),
#             "attendance_rate": float(performance_data.attendance_percentage or 0),
#             "last_updated": performance_data.last_updated.isoformat()
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/predict/{student_id}", response_model=dict)
# async async def generate_prediction(
#     student_id: UUID,
#     target_grade: str = Query("10th", description="Target grade to predict"),
#     model_type: ModelEnum = Query(ModelEnum.RANDOM_FOREST, description="ML model to use"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Generate AI-powered performance prediction for student"""
#     service = AIPredictionService(db)
    
#     try:
#         prediction = service.predict_performance(
#             student_id=student_id,
#             target_grade=target_grade,
#             model_type=model_type
#         )
        
#         return {
#             "prediction_id": prediction.prediction_id,
#             "student_id": str(student_id),
#             "message": "Prediction generated successfully",
#             "overall_predicted_percentage": float(prediction.overall_predicted_percentage),
#             "predicted_scores": prediction.predicted_scores,
#             "confidence_scores": prediction.confidence_scores,
#             "subjects_at_risk": prediction.subjects_at_risk,
#             "dropout_risk_score": float(prediction.dropout_risk_score),
#             "validation_score": float(prediction.validation_score),
#             "prediction_date": prediction.prediction_date.isoformat(),
#             "source_grade": prediction.source_grade,
#             "target_grade": prediction.target_grade
#         }
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.get("/prediction/{prediction_id}", response_model=dict)
# async async def get_prediction_details(
#     prediction_id: str,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get detailed prediction information"""
#     service = AIPredictionService(db)
    
#     prediction = service.get_prediction_by_id(prediction_id)
#     if not prediction:
#         raise HTTPException(status_code=404, detail="Prediction not found")
    
#     return {
#         "prediction_id": prediction.prediction_id,
#         "student_id": str(prediction.student_id),
#         "student_name": f"{prediction.student.first_name} {prediction.student.last_name}",
#         "prediction_date": prediction.prediction_date.isoformat(),
#         "source_grade": prediction.source_grade,
#         "target_grade": prediction.target_grade,
#         "model_used": prediction.model_used.value,
#         "overall_predicted_percentage": float(prediction.overall_predicted_percentage),
#         "predicted_scores": prediction.predicted_scores,
#         "confidence_scores": prediction.confidence_scores,
#         "prediction_ranges": prediction.prediction_ranges,
#         "dropout_risk_score": float(prediction.dropout_risk_score),
#         "subjects_at_risk": prediction.subjects_at_risk,
#         "intervention_recommendations": prediction.intervention_recommendations,
#         "influential_factors": prediction.influential_factors,
#         "explanation": prediction.explanation,
#         "key_insights": prediction.key_insights,
#         "validation_score": float(prediction.validation_score)
#     }

# @router.get("/student/{student_id}/predictions", response_model=List[dict])
# async async def get_student_predictions(
#     student_id: UUID,
#     limit: int = Query(10, le=50),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get all predictions for a specific student"""
#     service = AIPredictionService(db)
    
#     try:
#         predictions = service.get_student_predictions(student_id, limit)
        
#         return [
#             {
#                 "prediction_id": pred.prediction_id,
#                 "prediction_date": pred.prediction_date.isoformat(),
#                 "source_grade": pred.source_grade,
#                 "target_grade": pred.target_grade,
#                 "overall_predicted_percentage": float(pred.overall_predicted_percentage),
#                 "dropout_risk_score": float(pred.dropout_risk_score),
#                 "model_used": pred.model_used.value,
#                 "validation_score": float(pred.validation_score),
#                 "subjects_at_risk_count": len(pred.subjects_at_risk or [])
#             }
#             for pred in predictions
#         ]
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.get("/class/{class_id}/analysis", response_model=dict)
# async async def get_class_prediction_analysis(
#     class_id: UUID,
#     target_grade: str = Query("10th"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get prediction analysis for entire class"""
#     service = AIPredictionService(db)
    
#     try:
#         from ...models.tenant_specific.student import Student
        
#         # Get all students in the class
#         students = service.db.query(Student).filter(
#             Student.class_id == class_id,
#             Student.is_active == True
#         ).all()
        
#         if not students:
#             raise HTTPException(status_code=404, detail="No students found in class")
        
#         class_analysis = {
#             "class_id": str(class_id),
#             "total_students": len(students),
#             "target_grade": target_grade,
#             "students_analyzed": 0,
#             "average_predicted_percentage": 0,
#             "high_risk_students": 0,
#             "subjects_needing_attention": {},
#             "top_performers": [],
#             "at_risk_students": []
#         }
        
#         total_percentage = 0
#         analyzed_students = 0
        
#         for student in students:
#             # Get latest prediction for student
#             latest_prediction = service.db.query(service.model).filter(
#                 service.model.student_id == student.id,
#                 service.model.target_grade == target_grade
#             ).order_by(service.model.prediction_date.desc()).first()
            
#             if latest_prediction:
#                 analyzed_students += 1
#                 student_percentage = float(latest_prediction.overall_predicted_percentage)
#                 total_percentage += student_percentage
                
#                 # Track high risk students (< 60%)
#                 if student_percentage < 60:
#                     class_analysis["high_risk_students"] += 1
#                     class_analysis["at_risk_students"].append({
#                         "student_id": str(student.id),
#                         "name": f"{student.first_name} {student.last_name}",
#                         "predicted_percentage": student_percentage,
#                         "subjects_at_risk": latest_prediction.subjects_at_risk
#                     })
                
#                 # Track top performers (>= 85%)
#                 if student_percentage >= 85:
#                     class_analysis["top_performers"].append({
#                         "student_id": str(student.id),
#                         "name": f"{student.first_name} {student.last_name}",
#                         "predicted_percentage": student_percentage
#                     })
                
#                 # Aggregate subjects needing attention
#                 for subject in (latest_prediction.subjects_at_risk or []):
#                     class_analysis["subjects_needing_attention"][subject] = \
#                         class_analysis["subjects_needing_attention"].get(subject, 0) + 1
        
#         if analyzed_students > 0:
#             class_analysis["average_predicted_percentage"] = round(total_percentage / analyzed_students, 2)
#             class_analysis["students_analyzed"] = analyzed_students
        
#         # Sort subjects by number of at-risk students
#         class_analysis["subjects_needing_attention"] = dict(
#             sorted(class_analysis["subjects_needing_attention"].items(), 
#                   key=lambda x: x[1], reverse=True)
#         )
        
#         return class_analysis
        
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/batch-predict", response_model=dict)
# async async def batch_predict_class(
#     class_id: UUID,
#     background_tasks: BackgroundTasks,
#     target_grade: str = Query("10th"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Generate predictions for all students in a class (background task)"""
    
#     async def generate_batch_predictions():
#         service = AIPredictionService(db)
        
#         # Get all students in class
#         from ...models.tenant_specific.student import Student
#         students = service.db.query(Student).filter(
#             Student.class_id == class_id,
#             Student.is_active == True
#         ).all()
        
#         results = {"successful": 0, "failed": 0, "total": len(students)}
        
#         for student in students:
#             try:
#                 service.predict_performance(
#                     student_id=student.id,
#                     target_grade=target_grade
#                 )
#                 results["successful"] += 1
#             except Exception as e:
#                 results["failed"] += 1
#                 print(f"Failed to predict for student {student.id}: {e}")
        
#         return results
    
#     # Add to background tasks
#     background_tasks.add_task(generate_batch_predictions)
    
#     return {
#         "message": "Batch prediction started",
#         "class_id": str(class_id),
#         "target_grade": target_grade,
#         "status": "processing"
#     }

# @router.get("/models/performance", response_model=List[dict])
# async async def get_model_performance(
#     tenant_id: UUID,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get performance metrics of all AI models"""
#     service = AIPredictionService(db)
    
#     try:
#         from ...models.tenant_specific.ai_prediction import PredictionModel
        
#         models = service.db.query(PredictionModel).filter(
#             PredictionModel.tenant_id == tenant_id
#         ).all()
        
#         return [
#             {
#                 "model_name": model.model_name,
#                 "model_type": model.model_type.value,
#                 "version": model.model_version,
#                 "accuracy": float(model.accuracy or 0),
#                 "mean_absolute_error": float(model.mean_absolute_error or 0),
#                 "training_data_size": model.training_data_size or 0,
#                 "is_active": model.is_active,
#                 "usage_count": model.usage_count or 0,
#                 "last_trained": model.training_completion_date.isoformat() if model.training_completion_date else None
#             }
#             for model in models
#         ]
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/interventions/{student_id}", response_model=dict)
# async async def suggest_interventions(
#     student_id: UUID,
#     prediction_id: Optional[str] = Query(None, description="Specific prediction ID to base interventions on"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get detailed intervention suggestions for a student"""
#     service = AIPredictionService(db)
    
#     try:
#         if prediction_id:
#             prediction = service.get_prediction_by_id(prediction_id)
#         else:
#             # Get latest prediction
#             predictions = service.get_student_predictions(student_id, limit=1)
#             prediction = predictions[0] if predictions else None
        
#         if not prediction:
#             raise HTTPException(status_code=404, detail="No predictions found for student")
        
#         # Get detailed performance data
#         performance_data = service.db.query(service.StudentPerformanceData).filter(
#             service.StudentPerformanceData.student_id == student_id
#         ).order_by(service.StudentPerformanceData.last_updated.desc()).first()
        
#         # Generate comprehensive intervention plan
#         intervention_plan = {
#             "student_id": str(student_id),
#             "prediction_id": prediction.prediction_id,
#             "overall_risk_level": "high" if prediction.dropout_risk_score > 70 else "medium" if prediction.dropout_risk_score > 40 else "low",
#             "priority_interventions": prediction.intervention_recommendations or [],
#             "subject_specific_plans": {},
#             "behavioral_interventions": [],
#             "engagement_strategies": [],
#             "parent_involvement": [],
#             "timeline": "immediate" if prediction.dropout_risk_score > 70 else "within_month"
#         }
        
#         # Subject-specific interventions
#         for subject, score in (prediction.predicted_scores or {}).items():
#             if score < 70:
#                 intervention_plan["subject_specific_plans"][subject] = {
#                     "current_predicted_score": score,
#                     "target_improvement": min(15, 80 - score),
#                     "strategies": [
#                         f"Weekly tutoring sessions in {subject}",
#                         f"Practice worksheets for {subject} fundamentals",
#                         f"Peer study groups for {subject}"
#                     ],
#                     "resources_needed": [
#                         "Additional textbooks",
#                         "Online practice platforms",
#                         "Tutor assignment"
#                     ]
#                 }
        
#         # Behavioral interventions based on attendance and participation
#         if performance_data:
#             if performance_data.attendance_percentage and performance_data.attendance_percentage < 80:
#                 intervention_plan["behavioral_interventions"].append({
#                     "type": "attendance",
#                     "current_rate": float(performance_data.attendance_percentage),
#                     "target_rate": 90.0,
#                     "actions": [
#                         "Daily check-ins with counselor",
#                         "Parent communication about attendance",
#                         "Identify and address attendance barriers"
#                     ]
#                 })
            
#             if performance_data.class_participation_score and performance_data.class_participation_score < 70:
#                 intervention_plan["engagement_strategies"].append({
#                     "type": "participation",
#                     "current_score": float(performance_data.class_participation_score),
#                     "strategies": [
#                         "Encourage participation in doubt-clearing sessions",
#                         "Assign group leadership roles",
#                         "Provide positive reinforcement for participation"
#                     ]
#                 })
        
#         # Parent involvement strategies
#         intervention_plan["parent_involvement"] = [
#             "Schedule parent-teacher conference",
#             "Share prediction results and improvement plan",
#             "Establish home study schedule",
#             "Regular progress updates to parents"
#         ]
        
#         return intervention_plan
        
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.get("/dashboard/overview", response_model=dict)
# async async def get_ai_prediction_dashboard(
#     tenant_id: UUID,
#     grade_filter: Optional[str] = Query(None, description="Filter by current grade"),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get AI prediction dashboard overview"""
#     service = AIPredictionService(db)
    
#     try:
#         from ...models.tenant_specific.student import Student
        
#         # Get all students for tenant
#         student_query = service.db.query(Student).filter(
#             Student.tenant_id == tenant_id,
#             Student.is_active == True
#         )
        
#         if grade_filter:
#             student_query = student_query.filter(Student.grade_level == grade_filter)
        
#         students = student_query.all()
        
#         # Get prediction statistics
#         total_students = len(students)
#         students_with_predictions = 0
#         high_risk_count = 0
#         medium_risk_count = 0
#         low_risk_count = 0
#         average_predicted_percentage = 0
#         total_predicted_percentage = 0
        
#         subject_risk_summary = {}
#         grade_distribution = {}
        
#         for student in students:
#             latest_prediction = service.db.query(service.model).filter(
#                 service.model.student_id == student.id
#             ).order_by(service.model.prediction_date.desc()).first()
            
#             if latest_prediction:
#                 students_with_predictions += 1
#                 predicted_percentage = float(latest_prediction.overall_predicted_percentage)
#                 total_predicted_percentage += predicted_percentage
                
#                 # Risk categorization
#                 if latest_prediction.dropout_risk_score > 70:
#                     high_risk_count += 1
#                 elif latest_prediction.dropout_risk_score > 40:
#                     medium_risk_count += 1
#                 else:
#                     low_risk_count += 1
                
#                 # Grade distribution
#                 grade_category = "A" if predicted_percentage >= 85 else \
#                                "B" if predicted_percentage >= 75 else \
#                                "C" if predicted_percentage >= 60 else "D"
                
#                 grade_distribution[grade_category] = grade_distribution.get(grade_category, 0) + 1
                
#                 # Subject risk summary
#                 for subject in (latest_prediction.subjects_at_risk or []):
#                     subject_risk_summary[subject] = subject_risk_summary.get(subject, 0) + 1
        
#         if students_with_predictions > 0:
#             average_predicted_percentage = total_predicted_percentage / students_with_predictions
        
#         dashboard_data = {
#             "tenant_id": str(tenant_id),
#             "overview": {
#                 "total_students": total_students,
#                 "students_with_predictions": students_with_predictions,
#                 "prediction_coverage": round((students_with_predictions / total_students * 100), 2) if total_students > 0 else 0,
#                 "average_predicted_performance": round(average_predicted_percentage, 2)
#             },
#             "risk_distribution": {
#                 "high_risk": high_risk_count,
#                 "medium_risk": medium_risk_count,
#                 "low_risk": low_risk_count
#             },
#             "grade_distribution": grade_distribution,
#             "subjects_at_risk": dict(sorted(subject_risk_summary.items(), key=lambda x: x[1], reverse=True)),
#             "recommendations": {
#                 "immediate_attention_needed": high_risk_count,
#                 "monitoring_required": medium_risk_count,
#                 "intervention_programs_needed": len([s for s in subject_risk_summary.values() if s >= 5])
#             }
#         }
        
#         return dashboard_data
        
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))






from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.gemini_prediction_service import GeminiPredictionService

router = APIRouter(prefix="/api/v1/school_authority/ai-prediction", tags=["AI Prediction - Gemini"])

@router.post("/predict/{student_id}", response_model=Dict[str, Any])
async async def generate_prediction(
    student_id: UUID,
    tenant_id: UUID,
    target_grade: str = "10th",
    db: AsyncSession = Depends(get_db)
):
    """Generate AI prediction using Google Gemini"""
    service = GeminiPredictionService(db)
    
    try:
        result = service.predict_performance(
            student_id=student_id,
            target_grade=target_grade,
            tenant_id=tenant_id
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result)
        
        return {
            "success": True,
            "prediction": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/student-data/{student_id}")
async async def get_student_data(
    student_id: UUID,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get collected student data for analysis"""
    service = GeminiPredictionService(db)
    
    try:
        data = service.collect_student_data(student_id, tenant_id)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
