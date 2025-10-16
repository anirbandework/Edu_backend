# from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, Text, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.dialects.postgresql import UUID, JSON
# from sqlalchemy.orm import relationship
# from ..base import BaseModel
# import enum

# class PredictionModel(enum.Enum):
#     RANDOM_FOREST = "random_forest"
#     NAIVE_BAYES = "naive_bayes"
#     KNN = "knn"
#     GRADIENT_BOOSTING = "gradient_boosting"
#     NEURAL_NETWORK = "neural_network"
#     ENSEMBLE = "ensemble"

# class PredictionStatus(enum.Enum):
#     PENDING = "pending"
#     PROCESSING = "processing"
#     COMPLETED = "completed"
#     FAILED = "failed"

# class SubjectDifficulty(enum.Enum):
#     BASIC = "basic"
#     INTERMEDIATE = "intermediate"
#     ADVANCED = "advanced"

# class StudentPerformanceData(BaseModel):
#     __tablename__ = "student_performance_data"
    
#     # Foreign Keys
#     tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
#     student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    
#     # Academic Information
#     current_grade = Column(String(10), nullable=False)
#     academic_year = Column(String(10), nullable=False)
    
#     # Performance Metrics (Historical Data)
#     exam_scores = Column(JSON)  # {"math": [85, 78, 92], "science": [76, 80, 88]}
#     assignment_scores = Column(JSON)
#     quiz_scores = Column(JSON)
#     project_scores = Column(JSON)
    
#     # Subject-wise Performance
#     subject_averages = Column(JSON)  # {"math": 85.5, "science": 78.2, "english": 89.1}
#     subject_trends = Column(JSON)    # Improving/declining trends
#     subject_difficulties = Column(JSON)  # Subject difficulty levels
    
#     # Behavioral and Engagement Metrics
#     attendance_percentage = Column(Numeric(5, 2))
#     homework_completion_rate = Column(Numeric(5, 2))
#     class_participation_score = Column(Numeric(5, 2))
#     doubt_resolution_rate = Column(Numeric(5, 2))  # From chat system
    
#     # Learning Pattern Analysis
#     study_habits = Column(JSON)  # {"study_time_hours": 3, "preferred_time": "evening"}
#     learning_style = Column(String(50))  # visual, auditory, kinesthetic
#     response_time_patterns = Column(JSON)  # Speed of answering questions
    
#     # External Factors
#     socioeconomic_factors = Column(JSON)  # Family background, resources
#     extracurricular_activities = Column(JSON)
#     peer_interaction_score = Column(Numeric(5, 2))
    
#     # Teacher Assessments
#     teacher_feedback = Column(JSON)  # Qualitative assessments
#     behavioral_scores = Column(JSON)  # Discipline, cooperation, etc.
    
#     # Time-based Analysis
#     performance_over_time = Column(JSON)  # Monthly/quarterly trends
#     seasonal_patterns = Column(JSON)  # Performance during different seasons
    
#     # Last Update
#     last_updated = Column(DateTime, nullable=False)
#     data_completeness_score = Column(Numeric(5, 2))  # How complete the data is
    
#     # Relationships
#     tenant = relationship("Tenant")
#     student = relationship("Student")
#     predictions = relationship("PerformancePrediction", back_populates="student_data")

# class PerformancePrediction(BaseModel):
#     __tablename__ = "performance_predictions"
    
#     # Foreign Keys
#     tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
#     student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
#     student_data_id = Column(UUID(as_uuid=True), ForeignKey("student_performance_data.id"), nullable=False)
    
#     # Prediction Information
#     prediction_id = Column(String(50), unique=True, nullable=False)
#     prediction_date = Column(DateTime, nullable=False)
    
#     # Target Information
#     source_grade = Column(String(10), nullable=False)  # "8th"
#     target_grade = Column(String(10), nullable=False)  # "10th"
#     prediction_horizon_months = Column(Integer, default=24)  # 2 years ahead
    
#     # Model Information
#     model_used = Column(Enum(PredictionModel), nullable=False)
#     model_version = Column(String(20), default="1.0")
#     training_data_size = Column(Integer)
#     model_accuracy = Column(Numeric(5, 2))  # Model's accuracy on validation data
    
#     # Predictions (Subject-wise)
#     predicted_scores = Column(JSON)  # {"math": 78.5, "science": 82.1, "english": 76.8}
#     confidence_scores = Column(JSON)  # {"math": 0.85, "science": 0.78, "english": 0.92}
#     prediction_ranges = Column(JSON)  # {"math": {"min": 72, "max": 85}, ...}
    
#     # Overall Performance Prediction
#     overall_predicted_percentage = Column(Numeric(5, 2))
#     predicted_class_rank = Column(Integer)
#     predicted_grade_category = Column(String(20))  # "Excellent", "Good", "Average", etc.
    
#     # Risk Assessment
#     dropout_risk_score = Column(Numeric(5, 2))  # 0-100 scale
#     subjects_at_risk = Column(JSON)  # ["math", "physics"] - subjects likely to fail
#     intervention_recommendations = Column(JSON)  # Recommended actions
    
#     # Feature Importance
#     influential_factors = Column(JSON)  # Which factors most influence the prediction
#     improvement_areas = Column(JSON)   # Areas where student can improve
    
#     # Comparison with Peers
#     peer_comparison = Column(JSON)  # How student compares with similar students
#     percentile_prediction = Column(Numeric(5, 2))  # Predicted percentile in class
    
#     # Status and Validation
#     status = Column(Enum(PredictionStatus), default=PredictionStatus.PENDING)
#     validation_score = Column(Numeric(5, 2))  # How reliable the prediction is
    
#     # Explanation and Insights
#     explanation = Column(Text)  # Human-readable explanation of prediction
#     key_insights = Column(JSON)  # Key findings from analysis
    
#     # Monitoring and Updates
#     actual_scores = Column(JSON)  # Actual scores when available (for model validation)
#     prediction_accuracy = Column(Numeric(5, 2))  # How accurate this prediction was
    
#     # Relationships
#     tenant = relationship("Tenant")
#     student = relationship("Student")
#     student_data = relationship("StudentPerformanceData", back_populates="predictions")

# class PredictionModel(BaseModel):
#     __tablename__ = "prediction_models"
    
#     # Foreign Keys
#     tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
#     # Model Information
#     model_name = Column(String(100), nullable=False)
#     model_type = Column(Enum(PredictionModel), nullable=False)
#     model_version = Column(String(20), default="1.0")
    
#     # Training Information
#     training_start_date = Column(DateTime, nullable=False)
#     training_completion_date = Column(DateTime)
#     training_data_size = Column(Integer)
#     validation_data_size = Column(Integer)
    
#     # Performance Metrics
#     accuracy = Column(Numeric(5, 2))
#     precision = Column(Numeric(5, 2))
#     recall = Column(Numeric(5, 2))
#     f1_score = Column(Numeric(5, 2))
#     mean_absolute_error = Column(Numeric(8, 4))
    
#     # Model Configuration
#     hyperparameters = Column(JSON)  # Model-specific parameters
#     features_used = Column(JSON)    # List of features used for training
#     feature_importance = Column(JSON)  # Importance scores for features
    
#     # Subject-specific Performance
#     subject_accuracy = Column(JSON)  # Accuracy per subject
    
#     # Model Files and Artifacts
#     model_file_path = Column(String(500))  # Path to saved model
#     preprocessing_pipeline_path = Column(String(500))
#     feature_scaler_path = Column(String(500))
    
#     # Status and Metadata
#     is_active = Column(Boolean, default=False)
#     is_production = Column(Boolean, default=False)
#     usage_count = Column(Integer, default=0)
    
#     # Model Description
#     description = Column(Text)
#     training_notes = Column(Text)
    
#     # Relationships
#     tenant = relationship("Tenant")

# class ModelTrainingJob(BaseModel):
#     __tablename__ = "model_training_jobs"
    
#     # Foreign Keys
#     tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
#     # Job Information
#     job_id = Column(String(50), unique=True, nullable=False)
#     job_name = Column(String(100), nullable=False)
    
#     # Training Configuration
#     model_type = Column(Enum(PredictionModel), nullable=False)
#     target_grades = Column(JSON)  # ["9th", "10th"] - what grades to predict
#     subjects = Column(JSON)       # ["math", "science", "english"]
    
#     # Data Configuration
#     min_historical_months = Column(Integer, default=12)
#     training_data_filters = Column(JSON)  # Filters for training data
    
#     # Job Status
#     status = Column(String(20), default="pending")  # pending, running, completed, failed
#     progress_percentage = Column(Integer, default=0)
    
#     # Timing
#     scheduled_start = Column(DateTime)
#     actual_start = Column(DateTime)
#     completion_time = Column(DateTime)
    
#     # Results
#     model_performance = Column(JSON)
#     training_logs = Column(Text)
#     error_details = Column(Text)
    
#     # Output
#     generated_model_id = Column(UUID(as_uuid=True), ForeignKey("prediction_models.id"))
    
#     # Relationships
#     tenant = relationship("Tenant")
#     generated_model = relationship("PredictionModel")

# class PredictionFeedback(BaseModel):
#     __tablename__ = "prediction_feedback"
    
#     # Foreign Keys
#     tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
#     prediction_id = Column(UUID(as_uuid=True), ForeignKey("performance_predictions.id"), nullable=False)
    
#     # Feedback Information
#     feedback_date = Column(DateTime, nullable=False)
#     feedback_provider = Column(UUID(as_uuid=True))  # Teacher, student, or parent
#     feedback_provider_type = Column(String(20))  # "teacher", "student", "parent"
    
#     # Accuracy Assessment
#     predicted_vs_actual = Column(JSON)  # Comparison when actual results available
#     accuracy_rating = Column(Integer)   # 1-5 rating of prediction accuracy
    
#     # Usefulness Assessment
#     usefulness_rating = Column(Integer)  # 1-5 rating
#     intervention_effectiveness = Column(JSON)  # How well recommended actions worked
    
#     # Feedback Details
#     comments = Column(Text)
#     suggestions_for_improvement = Column(Text)
    
#     # Relationships
#     tenant = relationship("Tenant")
#     prediction = relationship("PerformancePrediction")
