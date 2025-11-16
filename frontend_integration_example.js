// Frontend Integration Example for AI Features
// This shows how to integrate the AI backend with your frontend

const API_BASE_URL = 'http://localhost:8000';
const TENANT_ID = '123e4567-e89b-12d3-a456-426614174000';

class AIEducationService {
    constructor(baseUrl = API_BASE_URL, tenantId = TENANT_ID) {
        this.baseUrl = baseUrl;
        this.tenantId = tenantId;
    }

    // Helper method for API calls
    async apiCall(endpoint, method = 'GET', data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }

    // AI Quiz Features
    async generateQuestions(questionData) {
        return await this.apiCall(
            `/ai-quiz/generate-questions?tenant_id=${this.tenantId}&auto_save=false`,
            'POST',
            questionData
        );
    }

    async suggestQuizAssembly(assemblyData) {
        return await this.apiCall(
            `/ai-quiz/suggest-quiz-assembly?tenant_id=${this.tenantId}`,
            'POST',
            assemblyData
        );
    }

    async gradeSubjectiveAnswer(gradingData) {
        return await this.apiCall(
            '/ai-quiz/grade-subjective',
            'POST',
            gradingData
        );
    }

    async analyzeQuizPerformance(performanceData) {
        return await this.apiCall(
            `/ai-quiz/analyze-performance?tenant_id=${this.tenantId}`,
            'POST',
            performanceData
        );
    }

    // AI Learning Analytics
    async getStudentInsights(studentId, subject = null, timePeriod = null) {
        const data = { student_id: studentId };
        if (subject) data.subject = subject;
        if (timePeriod) data.time_period = timePeriod;

        return await this.apiCall(
            `/ai-learning/student-insights?tenant_id=${this.tenantId}`,
            'POST',
            data
        );
    }

    async getStudyRecommendations(studentId, subject = null, studyGoals = null, availableHours = null) {
        const data = { student_id: studentId };
        if (subject) data.subject = subject;
        if (studyGoals) data.study_goals = studyGoals;
        if (availableHours) data.available_time_hours = availableHours;

        return await this.apiCall(
            `/ai-learning/study-recommendations?tenant_id=${this.tenantId}`,
            'POST',
            data
        );
    }

    async analyzeWeaknesses(studentId, subject = null, depth = 'detailed') {
        const data = {
            student_id: studentId,
            analysis_depth: depth
        };
        if (subject) data.subject = subject;

        return await this.apiCall(
            `/ai-learning/weakness-analysis?tenant_id=${this.tenantId}`,
            'POST',
            data
        );
    }

    async generateExamPrepPlan(studentId, examDate, subjects = null, examType = null, dailyHours = null) {
        const data = {
            student_id: studentId,
            exam_date: examDate
        };
        if (subjects) data.exam_subjects = subjects;
        if (examType) data.exam_type = examType;
        if (dailyHours) data.daily_study_hours = dailyHours;

        return await this.apiCall(
            `/ai-learning/exam-preparation?tenant_id=${this.tenantId}`,
            'POST',
            data
        );
    }

    async predictPerformance(studentId, assessmentSubject = null, assessmentType = null, assessmentDate = null) {
        const data = { student_id: studentId };
        if (assessmentSubject) data.assessment_subject = assessmentSubject;
        if (assessmentType) data.assessment_type = assessmentType;
        if (assessmentDate) data.assessment_date = assessmentDate;

        return await this.apiCall(
            `/ai-learning/performance-prediction?tenant_id=${this.tenantId}`,
            'POST',
            data
        );
    }

    // Report Generation
    async generateReport(reportType, studentId = null, classId = null, timePeriod = null) {
        const data = {
            report_type: reportType,
            include_recommendations: true
        };
        if (studentId) data.student_id = studentId;
        if (classId) data.class_id = classId;
        if (timePeriod) data.time_period = timePeriod;

        return await this.apiCall(
            `/ai-learning/generate-report?tenant_id=${this.tenantId}`,
            'POST',
            data
        );
    }

    async analyzeInterventionNeeds(studentIds, riskThreshold = 0.6, interventionType = 'academic') {
        const data = {
            student_ids: studentIds,
            risk_threshold: riskThreshold,
            intervention_type: interventionType
        };

        return await this.apiCall(
            `/ai-learning/intervention-analysis?tenant_id=${this.tenantId}`,
            'POST',
            data
        );
    }

    // Batch Operations
    async batchAnalyzeStudents(studentIds, analysisTypes = ['insights', 'recommendations', 'weaknesses']) {
        return await this.apiCall(
            `/ai-learning/batch-student-analysis?tenant_id=${this.tenantId}`,
            'POST',
            null,
            {
                student_ids: studentIds,
                analysis_types: analysisTypes
            }
        );
    }
}

// Usage Examples
class AIFeatureExamples {
    constructor() {
        this.aiService = new AIEducationService();
    }

    // Example: Generate questions for a quiz
    async exampleGenerateQuestions() {
        try {
            const questionData = {
                topic: "Linear Equations",
                subject: "Mathematics",
                grade_level: 10,
                question_type: "multiple_choice",
                difficulty: "medium",
                count: 5,
                learning_objectives: "Students should be able to solve linear equations"
            };

            const result = await this.aiService.generateQuestions(questionData);
            console.log('Generated Questions:', result);
            return result;
        } catch (error) {
            console.error('Failed to generate questions:', error);
        }
    }

    // Example: Get student insights
    async exampleStudentInsights(studentId) {
        try {
            const insights = await this.aiService.getStudentInsights(
                studentId,
                'Mathematics',
                'last_month'
            );
            console.log('Student Insights:', insights);
            return insights;
        } catch (error) {
            console.error('Failed to get student insights:', error);
        }
    }

    // Example: Generate study recommendations
    async exampleStudyRecommendations(studentId) {
        try {
            const recommendations = await this.aiService.getStudyRecommendations(
                studentId,
                'Mathematics',
                'Improve algebra skills for upcoming test',
                10 // 10 hours per week
            );
            console.log('Study Recommendations:', recommendations);
            return recommendations;
        } catch (error) {
            console.error('Failed to get study recommendations:', error);
        }
    }

    // Example: Generate student progress report
    async exampleStudentReport(studentId) {
        try {
            const report = await this.aiService.generateReport(
                'student_progress',
                studentId,
                null,
                'last_quarter'
            );
            console.log('Student Report:', report);
            return report;
        } catch (error) {
            console.error('Failed to generate student report:', error);
        }
    }

    // Example: Analyze intervention needs
    async exampleInterventionAnalysis(studentIds) {
        try {
            const analysis = await this.aiService.analyzeInterventionNeeds(
                studentIds,
                0.6, // 60% threshold
                'academic'
            );
            console.log('Intervention Analysis:', analysis);
            return analysis;
        } catch (error) {
            console.error('Failed to analyze intervention needs:', error);
        }
    }
}

// React Component Examples
const AIQuestionGenerator = () => {
    const [questions, setQuestions] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const aiService = new AIEducationService();

    const generateQuestions = async (formData) => {
        setLoading(true);
        try {
            const result = await aiService.generateQuestions(formData);
            setQuestions(result.questions);
        } catch (error) {
            console.error('Error generating questions:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="ai-question-generator">
            <h2>🤖 AI Question Generator</h2>
            {/* Form components would go here */}
            {loading && <div>Generating questions...</div>}
            {questions.map((question, index) => (
                <div key={index} className="question-card">
                    <h4>{question.question_text}</h4>
                    {question.options && (
                        <ul>
                            {Object.entries(question.options).map(([key, value]) => (
                                <li key={key}>{key}: {value}</li>
                            ))}
                        </ul>
                    )}
                    <p><strong>Answer:</strong> {question.correct_answer}</p>
                    <p><strong>Explanation:</strong> {question.explanation}</p>
                    <p><strong>Points:</strong> {question.points}</p>
                </div>
            ))}
        </div>
    );
};

const StudentInsightsDashboard = ({ studentId }) => {
    const [insights, setInsights] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    const aiService = new AIEducationService();

    React.useEffect(() => {
        const fetchInsights = async () => {
            setLoading(true);
            try {
                const result = await aiService.getStudentInsights(studentId);
                setInsights(result);
            } catch (error) {
                console.error('Error fetching insights:', error);
            } finally {
                setLoading(false);
            }
        };

        if (studentId) {
            fetchInsights();
        }
    }, [studentId]);

    if (loading) return <div>Loading insights...</div>;
    if (!insights) return <div>No insights available</div>;

    return (
        <div className="student-insights-dashboard">
            <h2>📊 Student Learning Insights</h2>
            
            <div className="performance-overview">
                <h3>Performance Overview</h3>
                <p>Progress Score: {insights.progress_score}/10</p>
                {/* Display other performance metrics */}
            </div>

            <div className="strengths-weaknesses">
                <div className="strengths">
                    <h3>💪 Strengths</h3>
                    <ul>
                        {insights.strengths.map((strength, index) => (
                            <li key={index}>{strength}</li>
                        ))}
                    </ul>
                </div>

                <div className="weaknesses">
                    <h3>🎯 Areas for Improvement</h3>
                    <ul>
                        {insights.weaknesses.map((weakness, index) => (
                            <li key={index}>{weakness}</li>
                        ))}
                    </ul>
                </div>
            </div>

            <div className="recommendations">
                <h3>📝 Recommendations</h3>
                <ul>
                    {insights.recommendations.map((rec, index) => (
                        <li key={index}>{rec}</li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

// Export for use in your application
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AIEducationService,
        AIFeatureExamples,
        AIQuestionGenerator,
        StudentInsightsDashboard
    };
}

// Usage instructions
console.log(`
🎓 AI Education Service Integration Guide

1. Initialize the service:
   const aiService = new AIEducationService();

2. Generate questions:
   const questions = await aiService.generateQuestions({
     topic: "Algebra",
     subject: "Mathematics",
     grade_level: 10,
     question_type: "multiple_choice",
     difficulty: "medium",
     count: 5
   });

3. Get student insights:
   const insights = await aiService.getStudentInsights(studentId, "Mathematics");

4. Generate reports:
   const report = await aiService.generateReport("student_progress", studentId);

5. Analyze intervention needs:
   const analysis = await aiService.analyzeInterventionNeeds([studentId1, studentId2]);

For more examples, check the AIFeatureExamples class above.
`);