from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID, uuid4
from typing import List, Dict, Any
from datetime import datetime

from app.core.database import get_db

router = APIRouter(prefix="/cbse-quiz", tags=["CBSE Quiz Platform"])

@router.post("/create-quiz")
async def create_cbse_quiz(
    subject: str,
    title: str,
    tenant_id: UUID,
    class_id: UUID,
    teacher_id: UUID,
    time_limit: int = 60,
    db: AsyncSession = Depends(get_db)
):
    """Create CBSE subject quiz"""
    
    quiz_id = str(uuid4())
    topic_id = str(uuid4())
    
    # Create topic for subject
    await db.execute(text("""
        INSERT INTO topics (id, tenant_id, name, description, subject, grade_level, created_at, is_deleted)
        VALUES (:id, :tenant_id, :name, :description, :subject, 10, NOW(), false)
        ON CONFLICT DO NOTHING
    """), {
        "id": topic_id,
        "tenant_id": str(tenant_id),
        "name": f"{subject} Topic",
        "description": f"CBSE {subject} questions",
        "subject": subject
    })
    
    # Create quiz
    await db.execute(text("""
        INSERT INTO quizzes (id, tenant_id, topic_id, class_id, teacher_id, title, description, 
                           total_questions, total_points, time_limit, is_active, created_at, is_deleted)
        VALUES (:id, :tenant_id, :topic_id, :class_id, :teacher_id, :title, :description,
                0, 0, :time_limit, true, NOW(), false)
    """), {
        "id": quiz_id,
        "tenant_id": str(tenant_id),
        "topic_id": topic_id,
        "class_id": str(class_id),
        "teacher_id": str(teacher_id),
        "title": title,
        "description": f"CBSE {subject} Quiz",
        "time_limit": time_limit
    })
    
    await db.commit()
    
    return {
        "quiz_id": quiz_id,
        "topic_id": topic_id,
        "subject": subject,
        "title": title,
        "time_limit": time_limit,
        "status": "created"
    }

@router.post("/add-question/{quiz_id}")
async def add_question_to_quiz(
    quiz_id: UUID,
    request_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Add question to CBSE quiz"""
    
    import json
    
    question_text = request_data.get("question_text")
    question_type = request_data.get("question_type")
    correct_answer = request_data.get("correct_answer")
    points = request_data.get("points", 1)
    options = request_data.get("options")
    explanation = request_data.get("explanation")
    
    # Convert options dict to JSON string for PostgreSQL
    if options and isinstance(options, dict):
        options = json.dumps(options)
    
    if not question_text or not question_type or not correct_answer:
        raise HTTPException(status_code=400, detail="question_text, question_type, and correct_answer are required")
    
    question_id = str(uuid4())
    
    # Get topic_id from quiz
    result = await db.execute(text("SELECT topic_id, tenant_id FROM quizzes WHERE id = :quiz_id"), 
                             {"quiz_id": str(quiz_id)})
    quiz_data = result.fetchone()
    if not quiz_data:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Add question
    await db.execute(text("""
        INSERT INTO questions (id, tenant_id, topic_id, question_text, question_type, 
                             correct_answer, explanation, points, options, created_at, is_deleted)
        VALUES (:id, :tenant_id, :topic_id, :question_text, :question_type,
                :correct_answer, :explanation, :points, :options, NOW(), false)
    """), {
        "id": question_id,
        "tenant_id": quiz_data[1],
        "topic_id": quiz_data[0],
        "question_text": question_text,
        "question_type": question_type,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "points": points,
        "options": options
    })
    
    # Get current question count
    result = await db.execute(text("SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = :quiz_id"), 
                             {"quiz_id": str(quiz_id)})
    order_number = result.scalar() + 1
    
    # Link question to quiz
    await db.execute(text("""
        INSERT INTO quiz_questions (id, quiz_id, question_id, order_number, points, created_at, is_deleted)
        VALUES (:id, :quiz_id, :question_id, :order_number, :points, NOW(), false)
    """), {
        "id": str(uuid4()),
        "quiz_id": str(quiz_id),
        "question_id": question_id,
        "order_number": order_number,
        "points": points
    })
    
    # Update quiz totals
    await db.execute(text("""
        UPDATE quizzes SET 
            total_questions = (SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = :quiz_id),
            total_points = (SELECT SUM(points) FROM quiz_questions WHERE quiz_id = :quiz_id)
        WHERE id = :quiz_id
    """), {"quiz_id": str(quiz_id)})
    
    await db.commit()
    
    return {
        "question_id": question_id,
        "quiz_id": str(quiz_id),
        "order_number": order_number,
        "points": points,
        "status": "added"
    }

@router.get("/quiz/{quiz_id}")
async def get_quiz_details(
    quiz_id: UUID,
    include_answers: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get quiz details with questions"""
    
    # Get quiz info
    result = await db.execute(text("""
        SELECT q.title, q.description, q.total_questions, q.total_points, q.time_limit,
               t.subject, t.name as topic_name
        FROM quizzes q
        JOIN topics t ON q.topic_id = t.id
        WHERE q.id = :quiz_id
    """), {"quiz_id": str(quiz_id)})
    
    quiz_info = result.fetchone()
    if not quiz_info:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get questions
    questions_query = """
        SELECT qz.order_number, q.id, q.question_text, q.question_type, q.options, qz.points
    """
    if include_answers:
        questions_query += ", q.correct_answer, q.explanation"
    
    questions_query += """
        FROM quiz_questions qz
        JOIN questions q ON qz.question_id = q.id
        WHERE qz.quiz_id = :quiz_id
        ORDER BY qz.order_number
    """
    
    result = await db.execute(text(questions_query), {"quiz_id": str(quiz_id)})
    questions = []
    
    for row in result.fetchall():
        question = {
            "order": row[0],
            "question_id": str(row[1]),
            "question_text": row[2],
            "question_type": row[3],
            "options": row[4],
            "points": row[5]
        }
        if include_answers:
            question["correct_answer"] = row[6]
            question["explanation"] = row[7]
        questions.append(question)
    
    return {
        "quiz_id": str(quiz_id),
        "title": quiz_info[0],
        "description": quiz_info[1],
        "subject": quiz_info[5],
        "topic": quiz_info[6],
        "total_questions": quiz_info[2],
        "total_points": quiz_info[3],
        "time_limit": quiz_info[4],
        "questions": questions
    }

@router.post("/start-attempt/{quiz_id}")
async def start_quiz_attempt(
    quiz_id: UUID,
    request_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Start quiz attempt for student"""
    
    student_id = request_data.get("student_id")
    tenant_id = request_data.get("tenant_id")
    
    if not student_id or not tenant_id:
        raise HTTPException(status_code=400, detail="student_id and tenant_id required")
    
    attempt_id = str(uuid4())
    
    # Get quiz max score
    result = await db.execute(text("SELECT total_points FROM quizzes WHERE id = :quiz_id"), 
                             {"quiz_id": str(quiz_id)})
    max_score = result.scalar()
    
    await db.execute(text("""
        INSERT INTO quiz_attempts (id, tenant_id, quiz_id, student_id, start_time, 
                                 max_score, is_completed, is_submitted, created_at, is_deleted)
        VALUES (:id, :tenant_id, :quiz_id, :student_id, NOW(), 
                :max_score, false, false, NOW(), false)
    """), {
        "id": attempt_id,
        "tenant_id": str(tenant_id),
        "quiz_id": str(quiz_id),
        "student_id": str(student_id),
        "max_score": max_score
    })
    
    await db.commit()
    
    return {
        "attempt_id": attempt_id,
        "quiz_id": str(quiz_id),
        "student_id": str(student_id),
        "start_time": datetime.now().isoformat(),
        "max_score": max_score,
        "status": "started"
    }

@router.post("/submit-answer")
async def submit_quiz_answer(
    request_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Submit answer for quiz question"""
    
    attempt_id = request_data.get("attempt_id")
    question_id = request_data.get("question_id")
    student_answer = request_data.get("student_answer")
    time_taken = request_data.get("time_taken", 30)
    
    if not attempt_id or not question_id or not student_answer:
        raise HTTPException(status_code=400, detail="attempt_id, question_id, and student_answer required")
    
    # Get correct answer
    result = await db.execute(text("SELECT correct_answer, points FROM questions WHERE id = :question_id"), 
                             {"question_id": str(question_id)})
    question_data = result.fetchone()
    
    if not question_data:
        raise HTTPException(status_code=404, detail="Question not found")
    
    correct_answer = question_data[0].strip().upper()
    student_answer_clean = student_answer.strip().upper()
    is_correct = student_answer_clean == correct_answer
    points_earned = question_data[1] if is_correct else 0
    
    # Proper logging instead of print statements
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Question ID: {question_id}, Student: '{student_answer_clean}', Correct: '{correct_answer}', Points: {points_earned}")
    
    # Simple INSERT - each answer submission gets a new record
    await db.execute(text("""
        INSERT INTO quiz_answers (id, attempt_id, question_id, student_answer, 
                                is_correct, points_earned, time_taken, created_at, is_deleted)
        VALUES (:id, :attempt_id, :question_id, :student_answer,
                :is_correct, :points_earned, :time_taken, NOW(), false)
    """), {
        "id": str(uuid4()),
        "attempt_id": str(attempt_id),
        "question_id": str(question_id),
        "student_answer": student_answer,
        "is_correct": is_correct,
        "points_earned": points_earned,
        "time_taken": time_taken
    })
    
    await db.commit()
    
    return {
        "attempt_id": str(attempt_id),
        "question_id": str(question_id),
        "student_answer": student_answer,
        "correct_answer": question_data[0],
        "is_correct": is_correct,
        "points_earned": points_earned,
        "status": "submitted"
    }

@router.post("/complete-attempt/{attempt_id}")
async def complete_quiz_attempt(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Complete and calculate quiz attempt score"""
    
    # Calculate total score
    result = await db.execute(text("""
        SELECT SUM(points_earned), COUNT(*) 
        FROM quiz_answers 
        WHERE attempt_id = :attempt_id
    """), {"attempt_id": str(attempt_id)})
    
    score_data = result.fetchone()
    total_score = score_data[0] or 0
    answer_count = score_data[1] or 0
    
    # Get max score
    result = await db.execute(text("""
        SELECT qa.max_score FROM quiz_attempts qa WHERE qa.id = :attempt_id
    """), {"attempt_id": str(attempt_id)})
    
    max_score = result.scalar()
    percentage = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Proper logging instead of print statements
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Quiz completed - Attempt: {attempt_id}, Score: {total_score}/{max_score} ({percentage:.1f}%)")
    
    # Update attempt
    await db.execute(text("""
        UPDATE quiz_attempts SET
            end_time = NOW(),
            total_score = :total_score,
            percentage = :percentage,
            is_completed = true,
            is_submitted = true
        WHERE id = :attempt_id
    """), {
        "attempt_id": str(attempt_id),
        "total_score": total_score,
        "percentage": percentage
    })
    
    await db.commit()
    
    return {
        "attempt_id": str(attempt_id),
        "total_score": total_score,
        "max_score": max_score,
        "percentage": round(percentage, 2),
        "answer_count": answer_count,
        "status": "completed"
    }

@router.get("/results/{attempt_id}")
async def get_quiz_results(
    attempt_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed quiz results"""
    
    # Get attempt info
    result = await db.execute(text("""
        SELECT qa.total_score, qa.max_score, qa.percentage, qa.start_time, qa.end_time,
               q.title, s.first_name, s.last_name
        FROM quiz_attempts qa
        JOIN quizzes q ON qa.quiz_id = q.id
        JOIN students s ON qa.student_id = s.id
        WHERE qa.id = :attempt_id
    """), {"attempt_id": str(attempt_id)})
    
    attempt_info = result.fetchone()
    if not attempt_info:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    
    # Get answers
    result = await db.execute(text("""
        SELECT qans.question_id, qans.student_answer, qans.is_correct, qans.points_earned,
               q.question_text, q.correct_answer, q.explanation
        FROM quiz_answers qans
        JOIN questions q ON qans.question_id = q.id
        WHERE qans.attempt_id = :attempt_id
        ORDER BY q.id
    """), {"attempt_id": str(attempt_id)})
    
    answers = [
        {
            "question_id": str(row[0]),
            "question_text": row[4],
            "student_answer": row[1],
            "correct_answer": row[5],
            "is_correct": row[2],
            "points_earned": row[3],
            "explanation": row[6]
        }
        for row in result.fetchall()
    ]
    
    return {
        "attempt_id": str(attempt_id),
        "quiz_title": attempt_info[5],
        "student_name": f"{attempt_info[6]} {attempt_info[7]}",
        "score": attempt_info[0],
        "max_score": attempt_info[1],
        "percentage": attempt_info[2],
        "start_time": attempt_info[3].isoformat() if attempt_info[3] else None,
        "end_time": attempt_info[4].isoformat() if attempt_info[4] else None,
        "answers": answers
    }