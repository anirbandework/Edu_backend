# 🤖 AI Features Documentation

## Overview
This document describes the AI-powered features integrated into the EduAssist Backend for enhancing quiz creation, grading, and performance analytics.

## 🚀 Features Implemented

### 1. AI Question Generation
**Endpoint:** `POST /ai-quiz/generate-questions`

Generate questions automatically based on:
- Topic and subject
- Grade level (1-12)
- Question type (multiple choice, true/false, short answer, essay)
- Difficulty level (easy, medium, hard)
- Learning objectives
- Desired quantity

**Example Request:**
```json
{
  "topic": "Photosynthesis",
  "subject": "Biology",
  "grade_level": 10,
  "question_type": "multiple_choice",
  "difficulty": "medium",
  "count": 5,
  "learning_objectives": "Understand the process and importance of photosynthesis"
}
```

### 2. Smart Quiz Assembly
**Endpoint:** `POST /ai-quiz/suggest-quiz-assembly`

AI suggests optimal question combinations considering:
- Target duration
- Difficulty distribution
- Point allocation
- Question variety
- Learning progression

**Example Request:**
```json
{
  "topic_id": "uuid-here",
  "target_duration": 30,
  "difficulty_distribution": {"easy": 2, "medium": 3, "hard": 1},
  "total_questions": 6
}
```

### 3. AI-Powered Subjective Grading
**Endpoint:** `POST /ai-quiz/grade-subjective`

Automatically grade essay and short-answer questions with:
- Point allocation
- Detailed feedback
- Strength identification
- Improvement suggestions
- Rubric-based evaluation

**Example Request:**
```json
{
  "question_text": "Explain the water cycle",
  "correct_answer": "The water cycle involves evaporation, condensation, precipitation...",
  "student_answer": "Water evaporates from oceans, forms clouds, then rains...",
  "max_points": 10,
  "rubric": "Award points for: process steps (4pts), scientific terms (3pts), examples (3pts)"
}
```

### 4. Performance Analytics
**Endpoint:** `POST /ai-quiz/analyze-performance`

AI analyzes class performance providing:
- Overall statistics
- Weak/strong topic areas
- At-risk student identification
- Top performer recognition
- Teaching recommendations
- Question difficulty analysis

### 5. Enhanced Quiz Grading
**Endpoint:** `POST /ai-quiz/enhanced-grading/{attempt_id}`

Combines traditional and AI grading:
- Objective questions: Traditional logic
- Subjective questions: AI-powered grading
- Comprehensive feedback
- Detailed scoring breakdown

## 🛠️ Technical Implementation

### AI Service Architecture
```
AIService
├── Question Generation (Perplexity API)
├── Quiz Assembly Logic
├── Subjective Grading Engine
└── Performance Analytics
```

### Key Components

1. **AIService** (`app/services/ai_service.py`)
   - Core AI functionality
   - Perplexity API integration
   - Prompt engineering
   - Response parsing

2. **AIQuizService** (`app/services/ai_quiz_service.py`)
   - Business logic layer
   - Database integration
   - Error handling
   - Fallback mechanisms

3. **AI Schemas** (`app/schemas/ai_schemas.py`)
   - Request/response models
   - Data validation
   - Type safety

4. **API Routes** (`app/routers/ai_quiz.py`)
   - RESTful endpoints
   - Authentication integration
   - Error handling

## 📊 Usage Examples

### For Teachers

#### 1. Generate Questions for a Topic
```python
# Generate 5 medium-difficulty multiple choice questions about algebra
POST /ai-quiz/generate-questions
{
  "topic": "Linear Equations",
  "subject": "Mathematics", 
  "grade_level": 9,
  "question_type": "multiple_choice",
  "difficulty": "medium",
  "count": 5
}
```

#### 2. Get Quiz Assembly Suggestions
```python
# Get AI suggestions for a 45-minute quiz
POST /ai-quiz/suggest-quiz-assembly
{
  "topic_id": "math-algebra-uuid",
  "target_duration": 45,
  "difficulty_distribution": {"easy": 3, "medium": 4, "hard": 2}
}
```

#### 3. Analyze Class Performance
```python
# Analyze how the class performed on a quiz
POST /ai-quiz/analyze-performance
{
  "quiz_id": "quiz-uuid-here",
  "class_id": "class-uuid-here"
}
```

### Batch Operations

#### Generate Multiple Question Sets
```python
POST /ai-quiz/batch-generate-questions
{
  "requests": [
    {
      "topic": "Photosynthesis",
      "subject": "Biology",
      "grade_level": 10,
      "question_type": "multiple_choice",
      "difficulty": "medium",
      "count": 3
    },
    {
      "topic": "Cell Division", 
      "subject": "Biology",
      "grade_level": 10,
      "question_type": "short_answer",
      "difficulty": "hard",
      "count": 2
    }
  ]
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
PERPLEXITY_API_KEY=your-perplexity-api-key

# Optional
AI_MODEL=llama-3.1-sonar-small-128k-online
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=2000
```

### API Rate Limits
- Question Generation: 10 requests/minute
- Subjective Grading: 50 requests/minute  
- Performance Analysis: 5 requests/minute

## 🧪 Testing

### Run AI Feature Tests
```bash
python test_ai_features.py
```

### Manual Testing Endpoints
```bash
# Health check
GET /ai-quiz/health

# Test question generation
curl -X POST "http://localhost:8050/ai-quiz/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Fractions",
    "subject": "Mathematics",
    "grade_level": 5,
    "question_type": "multiple_choice", 
    "difficulty": "easy",
    "count": 2
  }'
```

## 🚨 Error Handling

### Common Error Responses
```json
{
  "detail": "Failed to generate questions: API rate limit exceeded"
}
```

### Fallback Mechanisms
- AI service unavailable → Basic question templates
- Grading failure → Manual review required
- Analysis failure → Basic statistics only

## 🔮 Future Enhancements

### Planned Features
1. **Adaptive Learning**: AI adjusts difficulty based on student performance
2. **Content Recommendations**: Suggest study materials for weak areas
3. **Plagiarism Detection**: Check for copied answers
4. **Multi-language Support**: Generate questions in different languages
5. **Image-based Questions**: AI-generated visual questions
6. **Voice Assessment**: Audio response grading

### Integration Roadmap
1. **Phase 1**: Core AI features ✅
2. **Phase 2**: Student insights dashboard
3. **Phase 3**: Predictive analytics
4. **Phase 4**: Advanced personalization

## 📈 Benefits

### For Teachers
- ⏰ **Time Saving**: Automated question generation
- 📊 **Better Insights**: AI-powered analytics
- 🎯 **Targeted Teaching**: Identify weak areas
- 📝 **Consistent Grading**: Standardized evaluation

### For Students  
- 📚 **Personalized Learning**: Tailored recommendations
- 🔍 **Detailed Feedback**: Comprehensive analysis
- 📈 **Progress Tracking**: Performance insights
- 🎯 **Focused Study**: Weakness identification

### For Administrators
- 📊 **Data-Driven Decisions**: Performance analytics
- 🏫 **School-wide Insights**: Comparative analysis
- 📈 **Improvement Tracking**: Progress monitoring
- 💰 **Cost Efficiency**: Automated processes

## 🔒 Privacy & Security

### Data Protection
- Student responses encrypted in transit
- AI processing uses anonymized data
- No personal information sent to AI APIs
- GDPR/COPPA compliant data handling

### API Security
- Rate limiting implemented
- Request validation and sanitization
- Error messages don't expose sensitive data
- Audit logging for AI operations

---

**Note**: This is the initial implementation focusing on teacher-facing AI features. Student-facing features and advanced analytics will be added in subsequent phases.