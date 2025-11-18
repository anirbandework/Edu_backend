# app/services/ai_service.py

import os
import json
import logging
import httpx
from typing import Dict, List, Optional, Any
from app.schemas.assesment.quiz_validation_schemas import QuestionType, DifficultyLevel
from app.core.config_assessment import assessment_settings

logger = logging.getLogger(__name__)

class AIServiceException(Exception):
    """Custom exception for AI service errors"""
    pass

class AIService:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.error("PERPLEXITY_API_KEY not configured")
            raise AIServiceException("AI service not properly configured")
            
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, messages: List[Dict], model: str = None) -> str:
        """Make request to Perplexity API with proper error handling"""
        if model is None:
            model = assessment_settings.AI_MODEL
            
        payload = {
            "model": model,
            "messages": messages,
            "temperature": assessment_settings.AI_TEMPERATURE,
            "max_tokens": assessment_settings.AI_MAX_TOKENS
        }
        
        try:
            async with httpx.AsyncClient(timeout=assessment_settings.AI_TIMEOUT) as client:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            logger.error("AI API request timeout")
            raise AIServiceException("AI service timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"AI API HTTP error: {e.response.status_code} - {e.response.text}")
            raise AIServiceException(f"AI service error: {e.response.status_code}")
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid AI API response format: {e}")
            raise AIServiceException("Invalid AI response format")
        except Exception as e:
            logger.error(f"Unexpected AI service error: {e}")
            raise AIServiceException(f"AI service error: {str(e)}")
    
    async def generate_questions(
        self, 
        topic: str, 
        subject: str, 
        grade_level: int,
        question_type: QuestionType,
        difficulty: DifficultyLevel,
        count: int = 5,
        learning_objectives: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate questions using AI"""
        
        prompt = f"""
You are an expert educator. Generate {count} high-quality {difficulty.value} level {question_type.value} questions for grade {grade_level} students.

Subject: {subject}
Topic: {topic}
{f'Learning Objectives: {learning_objectives}' if learning_objectives else ''}

Requirements:
- Questions must be educationally sound and age-appropriate
- Ensure correct answers are accurate
- Provide clear, helpful explanations
- Points: Easy=1-2, Medium=2-3, Hard=3-5

Return ONLY a valid JSON array:
[
  {{
    "question_text": "Clear, specific question",
    "options": {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}} or null,
    "correct_answer": "A" or "exact answer",
    "explanation": "Step-by-step explanation",
    "points": 2
  }}
]
"""
        
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_request(messages)
        
        try:
            # Extract JSON from response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                questions = json.loads(json_str)
                return questions[:count]  # Ensure we don't exceed requested count
        except Exception as e:
            print(f"AI parsing error: {e}")
        
        # Fallback to sample questions if AI fails
        return self._generate_fallback_questions(count, question_type, difficulty, topic)
    
    def _generate_fallback_questions(self, count: int, question_type: QuestionType, difficulty: DifficultyLevel, topic: str) -> List[Dict[str, Any]]:
        """Generate fallback questions when AI fails"""
        questions = []
        points = 1 if difficulty == DifficultyLevel.EASY else 2 if difficulty == DifficultyLevel.MEDIUM else 3
        
        for i in range(count):
            if question_type == QuestionType.MULTIPLE_CHOICE:
                questions.append({
                    "question_text": f"Sample question {i+1} about {topic}",
                    "options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                    "correct_answer": "A",
                    "explanation": "This is a sample explanation",
                    "points": points
                })
            else:
                questions.append({
                    "question_text": f"Short answer question {i+1} about {topic}",
                    "options": None,
                    "correct_answer": "Sample answer",
                    "explanation": "This is a sample explanation",
                    "points": points
                })
        
        return questions
    
    async def suggest_quiz_assembly(
        self,
        available_questions: List[Dict],
        target_duration: Optional[int],
        difficulty_distribution: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """Suggest optimal question combination for quiz"""
        
        prompt = f"""
Analyze these available questions and suggest optimal quiz assembly:

Available Questions: {json.dumps(available_questions, indent=2)}
Target Duration: {target_duration} minutes
Difficulty Distribution: {difficulty_distribution or 'balanced'}

Provide recommendations for:
1. Question selection (by ID)
2. Optimal order
3. Time allocation
4. Difficulty balance
5. Total points

Format as JSON:
{{
  "selected_questions": ["question_id1", "question_id2"],
  "suggested_order": ["question_id1", "question_id2"],
  "time_per_question": {{"question_id1": 3, "question_id2": 5}},
  "difficulty_balance": {{"easy": 2, "medium": 2, "hard": 1}},
  "total_points": 10,
  "estimated_duration": 25,
  "recommendations": "..."
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_request(messages)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        
        return {}
    
    async def grade_subjective_answer(
        self,
        question: str,
        correct_answer: str,
        student_answer: str,
        max_points: int,
        rubric: Optional[str] = None
    ) -> Dict[str, Any]:
        """Grade subjective answers using AI"""
        
        prompt = f"""
Grade this student's answer:

Question: {question}
Model Answer: {correct_answer}
Student Answer: {student_answer}
Max Points: {max_points}
{f'Rubric: {rubric}' if rubric else ''}

Provide:
1. Points earned (0 to {max_points})
2. Detailed feedback
3. Areas for improvement
4. Strengths identified

Format as JSON:
{{
  "points_earned": 3,
  "percentage": 75,
  "feedback": "...",
  "strengths": ["..."],
  "improvements": ["..."],
  "is_correct": true/false
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_request(messages)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        
        return {"points_earned": 0, "feedback": "Unable to grade automatically"}
    
    async def analyze_class_performance(
        self,
        quiz_results: List[Dict],
        class_info: Dict
    ) -> Dict[str, Any]:
        """Analyze class performance and provide insights"""
        
        prompt = f"""
Analyze this class performance data:

Class Info: {json.dumps(class_info, indent=2)}
Quiz Results: {json.dumps(quiz_results, indent=2)}

Provide insights on:
1. Overall performance trends
2. Common mistakes/weak areas
3. Top performers
4. Students needing help
5. Teaching recommendations
6. Question difficulty analysis

Format as JSON:
{{
  "overall_stats": {{
    "average_score": 75.5,
    "pass_rate": 85,
    "difficulty_rating": "medium"
  }},
  "weak_areas": ["topic1", "topic2"],
  "strong_areas": ["topic3"],
  "at_risk_students": ["student_id1"],
  "top_performers": ["student_id2"],
  "recommendations": [
    "Review topic1 with more examples",
    "Consider additional practice for struggling students"
  ],
  "question_analysis": {{
    "easiest": "question_id1",
    "hardest": "question_id2",
    "most_missed": "question_id3"
  }}
}}
"""
        
        messages = [{"role": "user", "content": prompt}]
        response = await self._make_request(messages)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass
        
        return {}

# Legacy function for backward compatibility
async def get_gemini_reply(user_message: str) -> str:
    ai_service = AIService()
    messages = [{"role": "user", "content": user_message}]
    return await ai_service._make_request(messages)