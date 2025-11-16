#!/usr/bin/env python3
"""
Test script for AI Quiz features
Run this to test the AI integration
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import AIService
from app.schemas.quiz_schemas import QuestionType, DifficultyLevel

async def test_ai_service():
    """Test the AI service functionality"""
    print("🤖 Testing AI Service...")
    
    ai_service = AIService()
    
    # Test 1: Question Generation
    print("\n📝 Testing Question Generation...")
    try:
        questions = await ai_service.generate_questions(
            topic="Photosynthesis",
            subject="Biology",
            grade_level=10,
            question_type=QuestionType.MULTIPLE_CHOICE,
            difficulty=DifficultyLevel.MEDIUM,
            count=2,
            learning_objectives="Understand the process of photosynthesis and its importance"
        )
        
        if questions:
            print(f"✅ Generated {len(questions)} questions successfully!")
            for i, q in enumerate(questions[:1], 1):  # Show first question
                print(f"\nQuestion {i}:")
                print(f"Text: {q.get('question_text', 'N/A')}")
                print(f"Options: {q.get('options', 'N/A')}")
                print(f"Answer: {q.get('correct_answer', 'N/A')}")
        else:
            print("❌ No questions generated")
    except Exception as e:
        print(f"❌ Question generation failed: {e}")
    
    # Test 2: Subjective Grading
    print("\n📊 Testing Subjective Grading...")
    try:
        grading = await ai_service.grade_subjective_answer(
            question="Explain the process of photosynthesis.",
            correct_answer="Photosynthesis is the process by which plants convert light energy into chemical energy using chlorophyll, carbon dioxide, and water to produce glucose and oxygen.",
            student_answer="Plants use sunlight and chlorophyll to make food from CO2 and water, releasing oxygen.",
            max_points=5
        )
        
        if grading:
            print("✅ Subjective grading completed!")
            print(f"Points: {grading.get('points_earned', 0)}/{5}")
            print(f"Feedback: {grading.get('feedback', 'N/A')[:100]}...")
        else:
            print("❌ Grading failed")
    except Exception as e:
        print(f"❌ Subjective grading failed: {e}")
    
    # Test 3: Quiz Assembly
    print("\n🧩 Testing Quiz Assembly...")
    try:
        sample_questions = [
            {"id": "1", "question_text": "What is photosynthesis?", "difficulty": "easy", "points": 2, "estimated_time": 2},
            {"id": "2", "question_text": "Explain chlorophyll function", "difficulty": "medium", "points": 3, "estimated_time": 4},
            {"id": "3", "question_text": "Compare C3 and C4 plants", "difficulty": "hard", "points": 5, "estimated_time": 6}
        ]
        
        assembly = await ai_service.suggest_quiz_assembly(
            available_questions=sample_questions,
            target_duration=15,
            difficulty_distribution={"easy": 1, "medium": 1, "hard": 1}
        )
        
        if assembly:
            print("✅ Quiz assembly suggestions generated!")
            print(f"Selected questions: {assembly.get('selected_questions', [])}")
            print(f"Total points: {assembly.get('total_points', 0)}")
            print(f"Estimated duration: {assembly.get('estimated_duration', 0)} minutes")
        else:
            print("❌ Quiz assembly failed")
    except Exception as e:
        print(f"❌ Quiz assembly failed: {e}")
    
    print("\n🎉 AI Service testing completed!")

if __name__ == "__main__":
    print("🚀 Starting AI Features Test...")
    asyncio.run(test_ai_service())