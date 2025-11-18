# app/routers/ai_learning.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.services.assesment.ai_student_analytics_service import AILearningService
from app.services.assesment.ai_report_generation_service import AIReportService
from app.schemas.assesment.ai_analytics_schemas import (
    StudentInsightsRequest, StudentInsightsResponse,
    StudyRecommendationRequest, StudyRecommendationResponse,
    WeaknessAnalysisRequest, WeaknessAnalysisResponse,
    ExamPrepRequest, ExamPrepResponse,
    PerformancePredictionRequest, PerformancePredictionResponse,
    ReportGenerationRequest, ReportGenerationResponse,
    InterventionRequest, InterventionResponse
)

router = APIRouter(prefix="/ai-learning", tags=["AI Learning Analytics"])

# Student Insights Endpoints
@router.post("/student-insights", response_model=StudentInsightsResponse)
async def analyze_student_insights(
    request: StudentInsightsRequest,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Analyze student performance and provide personalized insights"""
    try:
        ai_learning_service = AILearningService()
        return await ai_learning_service.analyze_student_insights(
            db=db,
            request=request,
            tenant_id=tenant_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze student insights: {str(e)}"
        )

@router.post("/study-recommendations", response_model=StudyRecommendationResponse)
async def generate_study_recommendations(
    request: StudyRecommendationRequest,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate personalized study recommendations for student"""
    try:
        ai_learning_service = AILearningService()
        return await ai_learning_service.generate_study_recommendations(
            db=db,
            request=request,
            tenant_id=tenant_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate study recommendations: {str(e)}"
        )

@router.post("/weakness-analysis", response_model=WeaknessAnalysisResponse)
async def identify_knowledge_gaps(
    request: WeaknessAnalysisRequest,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Identify specific knowledge gaps and learning weaknesses"""
    try:
        ai_learning_service = AILearningService()
        return await ai_learning_service.identify_knowledge_gaps(
            db=db,
            request=request,
            tenant_id=tenant_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze weaknesses: {str(e)}"
        )

@router.post("/exam-preparation", response_model=ExamPrepResponse)
async def generate_exam_prep_plan(
    request: ExamPrepRequest,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered exam preparation plan"""
    try:
        ai_learning_service = AILearningService()
        return await ai_learning_service.generate_exam_prep_plan(
            db=db,
            request=request,
            tenant_id=tenant_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate exam preparation plan: {str(e)}"
        )

@router.post("/performance-prediction", response_model=PerformancePredictionResponse)
async def predict_student_performance(
    request: PerformancePredictionRequest,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Predict student performance for upcoming assessments"""
    try:
        ai_learning_service = AILearningService()
        return await ai_learning_service.predict_performance(
            db=db,
            request=request,
            tenant_id=tenant_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to predict performance: {str(e)}"
        )

# Report Generation Endpoints
@router.post("/generate-report", response_model=ReportGenerationResponse)
async def generate_intelligent_report(
    request: ReportGenerationRequest,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-enhanced reports (student progress, class summary, parent reports)"""
    try:
        ai_report_service = AIReportService()
        
        if request.report_type == "student_progress":
            return await ai_report_service.generate_student_progress_report(
                db=db, request=request, tenant_id=tenant_id
            )
        elif request.report_type == "class_summary":
            return await ai_report_service.generate_class_summary_report(
                db=db, request=request, tenant_id=tenant_id
            )
        elif request.report_type == "parent_report":
            return await ai_report_service.generate_parent_report(
                db=db, request=request, tenant_id=tenant_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported report type: {request.report_type}"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Report generation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )

@router.post("/intervention-analysis", response_model=InterventionResponse)
async def analyze_intervention_needs(
    request: InterventionRequest,
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Identify students needing intervention and suggest strategies"""
    try:
        ai_report_service = AIReportService()
        return await ai_report_service.identify_intervention_needs(
            db=db,
            request=request,
            tenant_id=tenant_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze intervention needs: {str(e)}"
        )

# Batch Analysis Endpoints
@router.post("/batch-student-analysis")
async def batch_analyze_students(
    student_ids: List[UUID],
    tenant_id: UUID,
    analysis_types: List[str] = ["insights", "recommendations", "weaknesses"],
    db: AsyncSession = Depends(get_db)
):
    """Perform batch analysis for multiple students"""
    try:
        ai_learning_service = AILearningService()
        results = {}
        
        for student_id in student_ids:
            student_results = {}
            
            if "insights" in analysis_types:
                insights_request = StudentInsightsRequest(student_id=student_id)
                student_results["insights"] = await ai_learning_service.analyze_student_insights(
                    db=db, request=insights_request, tenant_id=tenant_id
                )
            
            if "recommendations" in analysis_types:
                rec_request = StudyRecommendationRequest(student_id=student_id)
                student_results["recommendations"] = await ai_learning_service.generate_study_recommendations(
                    db=db, request=rec_request, tenant_id=tenant_id
                )
            
            if "weaknesses" in analysis_types:
                weakness_request = WeaknessAnalysisRequest(student_id=student_id)
                student_results["weaknesses"] = await ai_learning_service.identify_knowledge_gaps(
                    db=db, request=weakness_request, tenant_id=tenant_id
                )
            
            results[str(student_id)] = student_results
        
        return {
            "batch_analysis_results": results,
            "total_students_analyzed": len(student_ids),
            "analysis_types": analysis_types
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform batch analysis: {str(e)}"
        )

@router.get("/health")
async def ai_learning_health():
    """Health check for AI learning services"""
    return {
        "status": "healthy", 
        "services": ["AI Learning Analytics", "AI Report Generation"],
        "features": [
            "Student Insights",
            "Study Recommendations", 
            "Weakness Analysis",
            "Exam Preparation",
            "Performance Prediction",
            "Intelligent Reports",
            "Intervention Analysis"
        ]
    }