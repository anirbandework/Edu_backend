#!/usr/bin/env python3
"""
Quick test for AI question generation
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import AIService
from app.schemas.quiz_schemas import QuestionType, DifficultyLevel

async def test_ai_generation():
    """Test AI question generation"""
    
    print("🧪 Testing AI Question Generation...")
    
    ai_service = AIService()
    
    # Test parameters
    topic = "Linear equations"
    subject = "Mathematics"
    grade_level = 10
    question_type = QuestionType.MULTIPLE_CHOICE
    difficulty = DifficultyLevel.EASY
    count = 2
    learning_objectives = "To solve simple linear equations where you have to find one variable value only"
    
    try:
        questions = await ai_service.generate_questions(
            topic=topic,
            subject=subject,
            grade_level=grade_level,
            question_type=question_type,
            difficulty=difficulty,
            count=count,
            learning_objectives=learning_objectives
        )
        
        print(f"✅ Generated {len(questions)} questions")
        print(f"📚 Topic: {topic}")
        print(f"🎓 Subject: {subject}")
        print(f"📊 Difficulty: {difficulty.value}")
        
        for i, q in enumerate(questions, 1):
            print(f"\n📝 Question {i}:")
            print(f"   Text: {q['question_text']}")
            if q.get('options'):
                for key, value in q['options'].items():
                    marker = "✓" if key == q['correct_answer'] else " "
                    print(f"   {marker} {key}: {value}")
            print(f"   💡 Answer: {q['correct_answer']}")
            print(f"   📖 Explanation: {q['explanation']}")
            print(f"   🎯 Points: {q['points']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_generation())