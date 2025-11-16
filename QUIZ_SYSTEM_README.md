# 🎯 Carpadiem Quiz Platform - Backend Setup

## Overview
Complete quiz management system for the EduAssist platform with topics, questions, quizzes, and student attempts tracking.

## 🏗️ Architecture

### Database Models
- **Topics**: Subject-based categorization (Math, Science, English, etc.)
- **Questions**: Individual quiz questions with multiple types
- **Quizzes**: Collections of questions for students
- **Quiz Attempts**: Student quiz sessions and scoring
- **Quiz Answers**: Individual question responses

### Question Types Supported
- Multiple Choice
- True/False  
- Short Answer
- Essay

### Difficulty Levels
- Easy
- Medium
- Hard

## 🚀 Setup Instructions

### 1. Database Migration
```bash
# Run the quiz system migration
cd /Users/adityachauhan/Desktop/Project/EDU_BACKEND/Edu_backend
alembic upgrade head
```

### 2. Seed Sample Data
```bash
# Run the data seeder to populate sample topics and questions
python quiz_data_seeder.py
```

### 3. Start the Server
```bash
# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 4. Test the Endpoints
```bash
# Run endpoint tests
python test_quiz_endpoints.py
```

## 📡 API Endpoints

### Topics
- `POST /quiz/topics` - Create new topic
- `GET /quiz/topics` - List all topics (filterable by subject/grade)

### Questions  
- `POST /quiz/questions` - Create new question
- `GET /quiz/topics/{topic_id}/questions` - Get questions for topic

### Quizzes
- `POST /quiz/quizzes` - Create new quiz
- `GET /quiz/quizzes/{quiz_id}/student` - Get quiz for student (no answers)

### Quiz Attempts
- `POST /quiz/attempts/start` - Start new quiz attempt
- `POST /quiz/attempts/submit` - Submit completed quiz
- `GET /quiz/students/{student_id}/results` - Get student results

## 🔧 Configuration

### Required Environment Variables
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
REDIS_URL=redis://host:port
JWT_SECRET_KEY=your-secret-key
```

### Database Connection
The system uses the existing EduAssist database configuration with multi-tenant support.

## 📊 Sample Data Structure

### Topic Example
```json
{
  "name": "Basic Mathematics",
  "description": "Fundamental math concepts",
  "subject": "Mathematics", 
  "grade_level": 5
}
```

### Question Example
```json
{
  "topic_id": "uuid",
  "question_text": "What is 15 + 27?",
  "question_type": "multiple_choice",
  "difficulty_level": "easy",
  "options": {"A": "40", "B": "42", "C": "44", "D": "46"},
  "correct_answer": "B",
  "explanation": "15 + 27 = 42",
  "points": 1
}
```

### Quiz Creation Example
```json
{
  "topic_id": "uuid",
  "title": "Math Quiz 1",
  "description": "Basic arithmetic quiz",
  "question_ids": ["uuid1", "uuid2", "uuid3"],
  "time_limit": 30,
  "allow_retakes": true,
  "show_results_immediately": true
}
```

## 🎮 Usage Flow

### For Teachers
1. Create topics for subjects
2. Add questions to topics
3. Create quizzes from questions
4. Assign quizzes to classes
5. Monitor student results

### For Students  
1. View available quizzes
2. Start quiz attempt
3. Answer questions
4. Submit quiz
5. View results (if enabled)

## 🔐 Security Features

- Multi-tenant isolation
- Soft delete functionality
- Input validation with Pydantic
- SQL injection prevention
- Authentication integration ready

## 📈 Performance Features

- Async/await throughout
- Connection pooling
- Efficient database queries
- Caching support ready
- Bulk operations support

## 🧪 Testing

### Manual Testing
1. Use `test_quiz_endpoints.py` for API testing
2. Use `quiz_data_seeder.py` for sample data
3. Check database directly with DBeaver

### Automated Testing
```bash
# Run with pytest (when implemented)
pytest tests/test_quiz_system.py
```

## 🔄 Integration Points

### Existing EduAssist Features
- **Students**: Quiz attempts linked to student records
- **Teachers**: Quiz creation and management
- **Classes**: Quiz assignment to specific classes
- **Tenants**: Multi-school support
- **Notifications**: Quiz reminders (ready for integration)

### Future Enhancements
- Real-time quiz sessions
- Advanced analytics
- Question bank sharing
- Auto-grading for essays
- Plagiarism detection
- Mobile app support

## 📁 File Structure
```
app/
├── models/tenant_specific/
│   └── quiz.py                 # Database models
├── schemas/
│   └── quiz_schemas.py         # Pydantic schemas  
├── services/
│   └── quiz_service.py         # Business logic
├── routers/
│   └── quiz.py                 # API endpoints
└── main.py                     # Updated with quiz routes

alembic/versions/
└── quiz_system_migration.py    # Database migration

Root files:
├── quiz_data_seeder.py         # Sample data seeder
├── test_quiz_endpoints.py      # API testing script
└── QUIZ_SYSTEM_README.md       # This file
```

## 🐛 Troubleshooting

### Common Issues
1. **Migration fails**: Check database connection and permissions
2. **Seeder fails**: Verify tenant_id exists in database
3. **API errors**: Check authentication and tenant_id parameters
4. **No questions**: Run the seeder script first

### Debug Commands
```bash
# Check database connection
python test_class_query.py

# Verify tables exist
psql -h host -U user -d db -c "\dt"

# Check sample data
python -c "import asyncio; from quiz_data_seeder import seed_quiz_data; asyncio.run(seed_quiz_data())"
```

## 📞 Support
For issues or questions about the quiz system, check:
1. Database logs for connection issues
2. FastAPI logs for API errors  
3. Migration logs for schema issues
4. This README for setup steps

---
**Carpadiem Quiz Platform** - Built for EduAssist Educational Management System