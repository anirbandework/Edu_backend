#!/usr/bin/env python3

import asyncio
import requests
import json

API_BASE = "http://127.0.0.1:8001"
TENANT_ID = "351e3b19-0c37-4e48-a06d-3ceaa7e584c2"
CLASS_ID = "15a9829e-1ce6-431a-801c-0a83959f8497"
TEACHER_ID = "378557f4-ebb1-498c-a0ea-1f236f1f16f3"

# Math Standard Questions
MATH_QUESTIONS = [
    {
        "question_text": "What is the discriminant of the quadratic equation ax² + bx + c = 0?",
        "question_type": "multiple_choice",
        "correct_answer": "B",
        "points": 2,
        "options": {"A": "b² + 4ac", "B": "b² - 4ac", "C": "b² × 4ac", "D": "4ac - b²"},
        "explanation": "The discriminant formula is b² - 4ac"
    },
    {
        "question_text": "If the discriminant is zero, the quadratic equation has:",
        "question_type": "multiple_choice",
        "correct_answer": "C",
        "points": 2,
        "options": {"A": "No real roots", "B": "Two distinct real roots", "C": "Two equal real roots", "D": "Infinite roots"},
        "explanation": "When discriminant = 0, the equation has two equal real roots"
    },
    {
        "question_text": "The sum of first n natural numbers is:",
        "question_type": "multiple_choice",
        "correct_answer": "A",
        "points": 2,
        "options": {"A": "n(n+1)/2", "B": "n(n-1)/2", "C": "n²/2", "D": "2n+1"},
        "explanation": "Formula for sum of first n natural numbers is n(n+1)/2"
    },
    {
        "question_text": "In an arithmetic progression, if a = 5 and d = 3, what is the 10th term?",
        "question_type": "multiple_choice",
        "correct_answer": "D",
        "points": 2,
        "options": {"A": "30", "B": "32", "C": "35", "D": "32"},
        "explanation": "10th term = a + (n-1)d = 5 + (10-1)×3 = 5 + 27 = 32"
    },
    {
        "question_text": "The area of a circle with radius r is:",
        "question_type": "multiple_choice",
        "correct_answer": "B",
        "points": 1,
        "options": {"A": "2πr", "B": "πr²", "C": "πr", "D": "2πr²"},
        "explanation": "Area of circle = πr²"
    },
    {
        "question_text": "If sin θ = 3/5, what is cos θ? (θ is acute)",
        "question_type": "multiple_choice",
        "correct_answer": "A",
        "points": 3,
        "options": {"A": "4/5", "B": "3/4", "C": "5/4", "D": "5/3"},
        "explanation": "Using Pythagoras: cos θ = √(1 - sin²θ) = √(1 - 9/25) = √(16/25) = 4/5"
    },
    {
        "question_text": "The probability of getting a head when tossing a fair coin is:",
        "question_type": "multiple_choice",
        "correct_answer": "C",
        "points": 1,
        "options": {"A": "0", "B": "1/4", "C": "1/2", "D": "1"},
        "explanation": "Fair coin has equal probability for head and tail = 1/2"
    },
    {
        "question_text": "The median of the data set {2, 5, 3, 8, 1} is:",
        "question_type": "multiple_choice",
        "correct_answer": "B",
        "points": 2,
        "options": {"A": "2", "B": "3", "C": "5", "D": "8"},
        "explanation": "Arranged in order: {1, 2, 3, 5, 8}. Median is the middle value = 3"
    },
    {
        "question_text": "What is the value of log₁₀(100)?",
        "question_type": "short_answer",
        "correct_answer": "2",
        "points": 2,
        "explanation": "log₁₀(100) = log₁₀(10²) = 2"
    },
    {
        "question_text": "If x² - 5x + 6 = 0, find the sum of roots:",
        "question_type": "short_answer",
        "correct_answer": "5",
        "points": 3,
        "explanation": "For ax² + bx + c = 0, sum of roots = -b/a = -(-5)/1 = 5"
    }
]

async def create_math_quiz():
    """Create Math Standard quiz with 10 questions"""
    
    print("🎯 Creating CBSE Math Standard Quiz...")
    
    # 1. Create Quiz
    params = {
        "subject": "math_standard_041",
        "title": "CBSE Math Standard - Sample Quiz",
        "tenant_id": TENANT_ID,
        "class_id": CLASS_ID,
        "teacher_id": TEACHER_ID,
        "time_limit": 45
    }
    
    response = requests.post(f"{API_BASE}/cbse-quiz/create-quiz", params=params)
    if response.status_code != 200:
        print(f"❌ Failed to create quiz: {response.text}")
        return
    
    quiz_result = response.json()
    quiz_id = quiz_result["quiz_id"]
    print(f"✅ Quiz created! ID: {quiz_id}")
    
    # 2. Add Questions
    for i, question in enumerate(MATH_QUESTIONS, 1):
        response = requests.post(f"{API_BASE}/cbse-quiz/add-question/{quiz_id}", json=question)
        if response.status_code == 200:
            print(f"✅ Question {i} added")
        else:
            print(f"❌ Failed to add question {i}: {response.text}")
    
    print(f"\n🎉 Math Quiz Complete!")
    print(f"📝 Quiz ID: {quiz_id}")
    print(f"📚 Subject: Math Standard (041)")
    print(f"❓ Questions: 10")
    print(f"⏱️ Time Limit: 45 minutes")
    print(f"🎯 Total Points: {sum(q['points'] for q in MATH_QUESTIONS)}")
    
    # 3. Display quiz info
    response = requests.get(f"{API_BASE}/cbse-quiz/quiz/{quiz_id}?include_answers=true")
    if response.status_code == 200:
        quiz_info = response.json()
        print(f"\n📋 Quiz Details:")
        print(f"   Title: {quiz_info['title']}")
        print(f"   Questions: {quiz_info['total_questions']}")
        print(f"   Points: {quiz_info['total_points']}")
        
        print(f"\n🔗 Test URLs:")
        print(f"   Frontend: http://localhost:3000/quiz.html")
        print(f"   Use Quiz ID: {quiz_id}")
        print(f"   Student ID: 0ababdf2-e541-4c0d-a2e9-e5944b2c9ae7")
    
    return quiz_id

if __name__ == "__main__":
    asyncio.run(create_math_quiz())