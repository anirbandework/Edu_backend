# app/services/quiz_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from ..models.tenant_specific.quiz import Topic, Question, Quiz, QuizQuestion, QuizAttempt, QuizAnswer
from ..schemas.quiz_schemas import (
    TopicCreate, QuestionCreate, QuizCreate, QuizAttemptStart, 
    QuizAnswerSubmit, QuizAttemptSubmit
)
from .base_service import BaseService

class QuizService:
    
    # Topic methods
    async def create_topic(self, db: AsyncSession, topic_data: TopicCreate, tenant_id: UUID) -> Topic:
        topic = Topic(
            tenant_id=tenant_id,
            **topic_data.model_dump()
        )
        db.add(topic)
        await db.commit()
        await db.refresh(topic)
        return topic
    
    async def get_topics(self, db: AsyncSession, tenant_id: UUID, subject: Optional[str] = None, grade_level: Optional[int] = None) -> List[Topic]:
        query = select(Topic).where(
            and_(Topic.tenant_id == tenant_id, Topic.is_deleted == False)
        )
        
        if subject:
            query = query.where(Topic.subject == subject)
        if grade_level:
            query = query.where(Topic.grade_level == grade_level)
            
        result = await db.execute(query)
        return result.scalars().all()
    
    # Question methods
    async def create_question(self, db: AsyncSession, question_data: QuestionCreate, tenant_id: UUID) -> Question:
        question = Question(
            tenant_id=tenant_id,
            **question_data.model_dump()
        )
        db.add(question)
        await db.commit()
        await db.refresh(question)
        return question
    
    async def get_questions_by_topic(self, db: AsyncSession, tenant_id: UUID, topic_id: UUID) -> List[Question]:
        query = select(Question).where(
            and_(
                Question.tenant_id == tenant_id,
                Question.topic_id == topic_id,
                Question.is_deleted == False
            )
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    # Quiz methods
    async def create_quiz(self, db: AsyncSession, quiz_data: QuizCreate, teacher_id: UUID, tenant_id: UUID) -> Quiz:
        # Calculate total points
        questions_query = select(Question).where(Question.id.in_(quiz_data.question_ids))
        questions_result = await db.execute(questions_query)
        questions = questions_result.scalars().all()
        
        total_points = sum(q.points for q in questions)
        
        quiz = Quiz(
            tenant_id=tenant_id,
            teacher_id=teacher_id,
            topic_id=quiz_data.topic_id,
            class_id=quiz_data.class_id,
            title=quiz_data.title,
            description=quiz_data.description,
            instructions=quiz_data.instructions,
            total_questions=len(quiz_data.question_ids),
            total_points=total_points,
            time_limit=quiz_data.time_limit,
            start_time=quiz_data.start_time,
            end_time=quiz_data.end_time,
            allow_retakes=quiz_data.allow_retakes,
            show_results_immediately=quiz_data.show_results_immediately
        )
        
        db.add(quiz)
        await db.flush()
        
        # Add quiz questions
        for i, question_id in enumerate(quiz_data.question_ids):
            question = next(q for q in questions if q.id == question_id)
            quiz_question = QuizQuestion(
                quiz_id=quiz.id,
                question_id=question_id,
                order_number=i + 1,
                points=question.points
            )
            db.add(quiz_question)
        
        await db.commit()
        await db.refresh(quiz)
        return quiz
    
    async def get_quiz_for_student(self, db: AsyncSession, quiz_id: UUID, tenant_id: UUID):
        query = select(Quiz).options(
            selectinload(Quiz.quiz_questions).selectinload(QuizQuestion.question)
        ).where(
            and_(Quiz.id == quiz_id, Quiz.tenant_id == tenant_id, Quiz.is_deleted == False)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    # Quiz Attempt methods
    async def start_quiz_attempt(self, db: AsyncSession, student_id: UUID, quiz_id: UUID, tenant_id: UUID) -> QuizAttempt:
        # Check if student already has attempts
        existing_attempts = await db.execute(
            select(func.count(QuizAttempt.id)).where(
                and_(
                    QuizAttempt.student_id == student_id,
                    QuizAttempt.quiz_id == quiz_id,
                    QuizAttempt.tenant_id == tenant_id
                )
            )
        )
        attempt_count = existing_attempts.scalar() or 0
        
        # Get quiz to check max score
        quiz = await db.get(Quiz, quiz_id)
        
        attempt = QuizAttempt(
            tenant_id=tenant_id,
            quiz_id=quiz_id,
            student_id=student_id,
            attempt_number=attempt_count + 1,
            start_time=datetime.utcnow(),
            max_score=quiz.total_points
        )
        
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)
        return attempt
    
    async def submit_quiz_attempt(self, db: AsyncSession, attempt_data: QuizAttemptSubmit, tenant_id: UUID) -> QuizAttempt:
        attempt = await db.get(QuizAttempt, attempt_data.attempt_id)
        if not attempt:
            raise ValueError("Quiz attempt not found")
        
        total_score = 0
        
        # Process each answer
        for answer_data in attempt_data.answers:
            question = await db.get(Question, answer_data.question_id)
            is_correct = self._check_answer(question, answer_data.student_answer)
            points_earned = question.points if is_correct else 0
            total_score += points_earned
            
            quiz_answer = QuizAnswer(
                attempt_id=attempt.id,
                question_id=answer_data.question_id,
                student_answer=answer_data.student_answer,
                is_correct=is_correct,
                points_earned=points_earned
            )
            db.add(quiz_answer)
        
        # Update attempt
        attempt.end_time = datetime.utcnow()
        attempt.total_score = total_score
        attempt.percentage = int((total_score / attempt.max_score) * 100) if attempt.max_score > 0 else 0
        attempt.is_completed = True
        attempt.is_submitted = True
        
        await db.commit()
        await db.refresh(attempt)
        return attempt
    
    def _check_answer(self, question: Question, student_answer: str) -> bool:
        if question.question_type.value == "multiple_choice":
            return student_answer.strip().upper() == question.correct_answer.strip().upper()
        elif question.question_type.value == "true_false":
            return student_answer.strip().lower() == question.correct_answer.strip().lower()
        else:
            # For short answer and essay, simple string comparison (can be enhanced)
            return student_answer.strip().lower() == question.correct_answer.strip().lower()
    
    async def get_student_quiz_results(self, db: AsyncSession, student_id: UUID, tenant_id: UUID) -> List[QuizAttempt]:
        query = select(QuizAttempt).options(
            selectinload(QuizAttempt.quiz).selectinload(Quiz.topic)
        ).where(
            and_(
                QuizAttempt.student_id == student_id,
                QuizAttempt.tenant_id == tenant_id,
                QuizAttempt.is_submitted == True
            )
        ).order_by(QuizAttempt.created_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()