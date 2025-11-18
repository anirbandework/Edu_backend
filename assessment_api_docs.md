# Assessment System API Documentation

## Overview
Complete assessment system with AI-powered features for quiz management, student analytics, and CBSE curriculum integration.

## Base URL
`http://localhost:8000`

## Authentication
All endpoints require `tenant_id`, `student_id`, or `teacher_id` parameters for access control.

---

## 1. Quiz Management APIs (`/quiz`)

### Topics
- `POST /quiz/topics` - Create new topic
- `GET /quiz/topics` - Get topics (filtered by subject/grade)

### Questions  
- `POST /quiz/questions` - Create question
- `GET /quiz/topics/{topic_id}/questions` - Get questions by topic

### Quizzes
- `POST /quiz/quizzes` - Create quiz
- `GET /quiz/quizzes/{quiz_id}/student` - Get quiz for student (no answers)

### Quiz Attempts
- `POST /quiz/attempts/start` - Start quiz attempt
- `POST /quiz/attempts/submit` - Submit completed quiz
- `GET /quiz/students/{student_id}/results` - Get student results

---

## 2. AI Quiz Generation (`/ai-quiz`)

### Question Generation
- `POST /ai-quiz/generate-questions` - Generate questions using AI
- `POST /ai-quiz/batch-generate-questions` - Batch generate multiple sets

### Quiz Assembly
- `POST /ai-quiz/suggest-quiz-assembly` - AI suggestions for optimal quiz

### Grading
- `POST /ai-quiz/grade-subjective` - Grade subjective answers with AI
- `POST /ai-quiz/enhanced-grading/{attempt_id}` - Enhanced AI grading

### Performance Analysis
- `POST /ai-quiz/analyze-performance` - Analyze quiz performance

---

## 3. AI Student Analytics (`/ai-learning`)

### Student Insights
- `POST /ai-learning/student-insights` - Analyze student performance
- `POST /ai-learning/study-recommendations` - Generate study recommendations
- `POST /ai-learning/weakness-analysis` - Identify knowledge gaps

### Exam Preparation
- `POST /ai-learning/exam-preparation` - Generate exam prep plan
- `POST /ai-learning/performance-prediction` - Predict student performance

### Reports
- `POST /ai-learning/generate-report` - Generate AI-enhanced reports
- `POST /ai-learning/intervention-analysis` - Identify intervention needs

### Batch Operations
- `POST /ai-learning/batch-student-analysis` - Analyze multiple students

---

## 4. CBSE Quiz Platform (`/cbse-quiz`)

### Quiz Management
- `POST /cbse-quiz/create-quiz` - Create CBSE subject quiz
- `POST /cbse-quiz/add-question/{quiz_id}` - Add question to quiz
- `GET /cbse-quiz/quiz/{quiz_id}` - Get quiz details

### Quiz Taking
- `POST /cbse-quiz/start-attempt/{quiz_id}` - Start quiz attempt
- `POST /cbse-quiz/submit-answer` - Submit answer for question
- `POST /cbse-quiz/complete-attempt/{attempt_id}` - Complete quiz

### Results
- `GET /cbse-quiz/results/{attempt_id}` - Get detailed quiz results

---

## 5. AI Chat Integration

### Chat Endpoints
- `POST /ai_chat` - AI chat with Perplexity
- `POST /ai_help` - Platform-specific AI help
- `GET /ai_status` - Check AI service status

---

## Common Request Examples

### Create Quiz
```json
POST /quiz/quizzes
{
  "title": "Math Quiz",
  "description": "Basic algebra",
  "topic_id": "uuid",
  "class_id": "uuid",
  "time_limit": 60,
  "total_points": 100
}
```

### Generate AI Questions
```json
POST /ai-quiz/generate-questions
{
  "subject": "Mathematics",
  "topic": "Algebra",
  "difficulty": "medium",
  "count": 10,
  "question_types": ["mcq", "short_answer"]
}
```

### Start Quiz Attempt
```json
POST /quiz/attempts/start
{
  "quiz_id": "uuid",
  "student_id": "uuid"
}
```

---

## Response Formats

### Success Response
```json
{
  "status": "success",
  "data": {...},
  "message": "Operation completed"
}
```

### Error Response
```json
{
  "status": "error",
  "detail": "Error description",
  "code": 400
}
```

---

## Rate Limits
- Quiz topics: 5 requests/minute
- AI endpoints: 10 requests/minute
- Standard endpoints: 60 requests/minute

---

## Features

### AI-Powered
- Automatic question generation
- Intelligent grading
- Performance analytics
- Study recommendations
- Weakness identification

### CBSE Integration
- Curriculum-aligned content
- Official pattern quizzes
- Subject-specific assessments

### Analytics
- Real-time performance tracking
- Predictive analytics
- Intervention recommendations
- Comprehensive reporting

### Scalability
- Handles 100k+ users
- Redis caching
- Background processing
- Database optimization

---

## Support
For technical support or API questions, contact the development team.