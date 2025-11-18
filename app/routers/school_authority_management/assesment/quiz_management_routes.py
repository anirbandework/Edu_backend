# app/routers/quiz.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.services.assesment.quiz_management_service import QuizService
from app.core.rate_limiter import rate_limiter
from app.schemas.assesment.quiz_validation_schemas import (
    TopicCreate, TopicResponse, QuestionCreate, QuestionResponse,
    QuizCreate, QuizResponse, QuizForStudent, QuizAttemptStart,
    QuizAttemptSubmit, QuizAttemptResponse, QuizResultResponse
)

router = APIRouter(prefix="/quiz", tags=["Quiz Management"])
quiz_service = QuizService()

# Topic endpoints
@router.post("/topics", response_model=TopicResponse)
async def create_topic(
    topic_data: TopicCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = None  # This should come from authentication
):
    """Create a new topic for quizzes."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    topic = await quiz_service.create_topic(db, topic_data, tenant_id)
    return topic

@router.get("/topics", response_model=List[TopicResponse])
async def get_topics(
    subject: Optional[str] = None,
    grade_level: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = None,
    _: None = Depends(lambda req: rate_limiter.check_rate_limit(req, max_requests=5, window=60))
):
    """Get all topics, optionally filtered by subject and grade level."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    # Cache key for topics
    from app.core.cache import cache_manager
    cache_key = f"topics:{tenant_id}:{subject}:{grade_level}"
    
    # Try cache first
    cached_topics = await cache_manager.get(cache_key)
    if cached_topics:
        return cached_topics
    
    topics = await quiz_service.get_topics(db, tenant_id, subject, grade_level)
    
    # Cache for 5 minutes
    await cache_manager.set(cache_key, topics, expire=300)
    return topics

# Question endpoints
@router.post("/questions", response_model=QuestionResponse)
async def create_question(
    question_data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = None
):
    """Create a new question for a topic."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    question = await quiz_service.create_question(db, question_data, tenant_id)
    return question

@router.get("/topics/{topic_id}/questions", response_model=List[QuestionResponse])
async def get_questions_by_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = None
):
    """Get all questions for a specific topic."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    questions = await quiz_service.get_questions_by_topic(db, tenant_id, topic_id)
    return questions

# Quiz endpoints
@router.post("/quizzes", response_model=QuizResponse)
async def create_quiz(
    quiz_data: QuizCreate,
    db: AsyncSession = Depends(get_db),
    teacher_id: UUID = None,  # This should come from authentication
    tenant_id: UUID = None
):
    """Create a new quiz."""
    if not tenant_id or not teacher_id:
        raise HTTPException(status_code=400, detail="Tenant ID and Teacher ID required")
    
    quiz = await quiz_service.create_quiz(db, quiz_data, teacher_id, tenant_id)
    return quiz

@router.get("/quizzes/{quiz_id}/student", response_model=QuizForStudent)
async def get_quiz_for_student(
    quiz_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = None
):
    """Get quiz details for student (without correct answers)."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    quiz = await quiz_service.get_quiz_for_student(db, quiz_id, tenant_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Format for student view (remove correct answers)
    questions = []
    for quiz_question in sorted(quiz.quiz_questions, key=lambda x: x.order_number):
        question = quiz_question.question
        questions.append({
            "id": question.id,
            "question_text": question.question_text,
            "question_type": question.question_type,
            "options": question.options,
            "points": quiz_question.points,
            "time_limit": question.time_limit
        })
    
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "instructions": quiz.instructions,
        "total_questions": quiz.total_questions,
        "total_points": quiz.total_points,
        "time_limit": quiz.time_limit,
        "questions": questions
    }

# Quiz Attempt endpoints
@router.post("/attempts/start", response_model=QuizAttemptResponse)
async def start_quiz_attempt(
    attempt_data: QuizAttemptStart,
    db: AsyncSession = Depends(get_db),
    student_id: UUID = None,  # This should come from authentication
    tenant_id: UUID = None
):
    """Start a new quiz attempt for a student."""
    if not tenant_id or not student_id:
        raise HTTPException(status_code=400, detail="Tenant ID and Student ID required")
    
    attempt = await quiz_service.start_quiz_attempt(db, student_id, attempt_data.quiz_id, tenant_id)
    return attempt

@router.post("/attempts/submit", response_model=QuizAttemptResponse)
async def submit_quiz_attempt(
    attempt_data: QuizAttemptSubmit,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = None
):
    """Submit a completed quiz attempt."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    try:
        attempt = await quiz_service.submit_quiz_attempt(db, attempt_data, tenant_id)
        return attempt
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/students/{student_id}/results", response_model=List[QuizAttemptResponse])
async def get_student_quiz_results(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = None
):
    """Get all quiz results for a student."""
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")
    
    results = await quiz_service.get_student_quiz_results(db, student_id, tenant_id)
    return results