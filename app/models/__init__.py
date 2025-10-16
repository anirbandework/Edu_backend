from .base import Base, BaseModel
from .shared.tenant import Tenant
from .tenant_specific.school_authority import SchoolAuthority
from .tenant_specific.student import Student
from .tenant_specific.teacher import Teacher
from .tenant_specific.class_model import ClassModel
from .tenant_specific.enrollment import Enrollment
from .tenant_specific.grade import Grade
from .tenant_specific.teacher_assignment import TeacherAssignment
from .tenant_specific.attendance import Attendance, AttendanceSummary, AttendancePolicy
from .tenant_specific.timetable import MasterTimetable, Period, ClassTimetable, TeacherTimetable, ScheduleEntry, TimetableConflict
from .tenant_specific.fee_management import FeeStructure, StudentFee, Payment, Scholarship, ScholarshipApplication, FeeTransaction
from .tenant_specific.grades_assessment import (
    Subject, ClassSubject, Assessment, AssessmentSubmission, 
    StudentGrade, GradeScale, ReportCard, GradeAuditLog
)
# from .tenant_specific.parent_portal import (
#     Parent, StudentParent, ParentMessage, ParentNotification,
#     ParentPortalSession, ParentFeedback, ParentEvent, ParentEventRegistration
# )
from .tenant_specific.doubt_chat import (
    ChatRoom, ChatParticipant, ChatMessage, MessageReaction,
    ChatSession, DoubtCategory, ChatAnalytics, TeacherAvailability
)

__all__ = [
    "Base", "BaseModel", "Tenant", "SchoolAuthority", "Student", 
    "Teacher", "ClassModel", "Enrollment", "Grade", "TeacherAssignment",
    "Attendance", "AttendanceSummary", "AttendancePolicy", 
    "MasterTimetable", "Period", "ClassTimetable", "TeacherTimetable", "ScheduleEntry", "TimetableConflict",
    "FeeStructure", "StudentFee", "Payment", "Scholarship", "ScholarshipApplication", "FeeTransaction",
    "Subject", "ClassSubject", "Assessment", "AssessmentSubmission", 
    "StudentGrade", "GradeScale", "ReportCard", "GradeAuditLog",
    # "Parent", "StudentParent", "ParentMessage", "ParentNotification",
    # "ParentPortalSession", "ParentFeedback", "ParentEvent", "ParentEventRegistration"
    "ChatRoom", "ChatParticipant", "ChatMessage", "MessageReaction",
    "ChatSession", "DoubtCategory", "ChatAnalytics", "TeacherAvailability"
]
