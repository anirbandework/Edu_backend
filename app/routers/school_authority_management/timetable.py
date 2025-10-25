# app/routers/school_authority/timetable.py
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from ...core.database import get_db
from ...services.timetable_service import TimetableService
from ...models.tenant_specific.timetable import DayOfWeek, TimetableStatus, PeriodType

# Pydantic Models
class MasterTimetableCreate(BaseModel):
    tenant_id: UUID
    created_by: UUID
    timetable_name: str
    description: Optional[str] = None
    academic_year: str
    term: Optional[str] = None
    effective_from: date
    effective_until: Optional[date] = None
    total_periods_per_day: int = 8
    school_start_time: str  # "09:00:00"
    school_end_time: str    # "16:00:00"
    period_duration: int = 45
    break_duration: int = 15
    lunch_duration: int = 60
    working_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    auto_generate_periods: bool = True

class ClassTimetableCreate(BaseModel):
    tenant_id: UUID
    class_id: UUID
    master_timetable_id: UUID
    academic_year: str
    term: Optional[str] = None
    class_name: Optional[str] = None
    grade_level: Optional[str] = None
    created_by: UUID

class TeacherTimetableCreate(BaseModel):
    tenant_id: UUID
    teacher_id: UUID
    master_timetable_id: UUID
    academic_year: str
    term: Optional[str] = None
    teacher_name: Optional[str] = None
    max_periods_per_day: int = 8
    min_periods_per_day: int = 1
    preferred_periods: Optional[List[int]] = None
    preferred_days: Optional[List[str]] = None
    subjects: Optional[List[str]] = None

class BulkScheduleCreate(BaseModel):
    tenant_id: UUID
    schedule_entries: List[dict]

class BulkScheduleUpdate(BaseModel):
    updates: List[dict]

# ROUTER CONFIGURATION
router = APIRouter(
    prefix="/api/v1/school_authority/timetable", 
    tags=["School Authority - Timetable Management"]
)

# MASTER TIMETABLE ENDPOINTS (School Authority Only)

@router.post("/master", response_model=dict)
async def create_master_timetable(
    timetable_data: MasterTimetableCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new master timetable with auto-generated periods"""
    service = TimetableService(db)
    
    try:
        master_timetable = await service.create_master_timetable(
            timetable_data.model_dump()
        )
        
        return {
            "id": str(master_timetable.id),
            "message": "Master timetable created successfully",
            "timetable_name": master_timetable.timetable_name,
            "academic_year": master_timetable.academic_year,
            "total_periods": master_timetable.total_periods_per_day,
            "effective_from": master_timetable.effective_from.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/master/{tenant_id}", response_model=List[dict])
async def get_master_timetables(
    tenant_id: UUID,
    academic_year: Optional[str] = Query(None),
    status: Optional[TimetableStatus] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all master timetables for a tenant"""
    service = TimetableService(db)
    
    try:
        filters = {"tenant_id": tenant_id, "is_deleted": False}
        if academic_year:
            filters["academic_year"] = academic_year
        if status:
            filters["status"] = status
        
        timetables = await service.get_multi(**filters)
        
        # Ensure we always return a list, even if empty
        if not timetables:
            return []
        
        return [
            {
                "id": str(tt.id),
                "timetable_name": tt.timetable_name,
                "description": tt.description,
                "academic_year": tt.academic_year,
                "term": tt.term,
                "effective_from": tt.effective_from.isoformat() if tt.effective_from else None,
                "effective_until": tt.effective_until.isoformat() if tt.effective_until else None,
                "school_start_time": tt.school_start_time.isoformat() if tt.school_start_time else None,
                "school_end_time": tt.school_end_time.isoformat() if tt.school_end_time else None,
                "total_periods_per_day": tt.total_periods_per_day,
                "status": tt.status.value if tt.status else "draft",
                "is_default": tt.is_default,
                "working_days": tt.working_days,
                "total_classes": tt.total_classes,
                "total_teachers": tt.total_teachers,
                "total_schedule_entries": tt.total_schedule_entries,
                "created_at": tt.created_at.isoformat()
            }
            for tt in timetables
        ]
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_master_timetables: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# CLASS TIMETABLE ENDPOINTS

@router.post("/class", response_model=dict)
async def create_class_timetable(
    class_timetable_data: ClassTimetableCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create timetable for a class (School Authority Only)"""
    service = TimetableService(db)
    
    try:
        class_timetable = await service.create_class_timetable(
            class_timetable_data.model_dump()
        )
        
        return {
            "id": str(class_timetable.id),
            "message": "Class timetable created successfully",
            "class_id": str(class_timetable.class_id),
            "class_name": class_timetable.class_name,
            "academic_year": class_timetable.academic_year
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/class/{class_id}/schedule")
async def get_class_schedule(
    class_id: UUID,
    academic_year: str,
    requester_type: str = Query("school_authority", regex="^(school_authority|teacher|student)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get weekly schedule for a class (Accessible by School Authority, Teachers, Students)"""
    service = TimetableService(db)
    
    try:
        weekly_schedule = await service.get_class_weekly_schedule(class_id, academic_year)
        
        return {
            "class_id": str(class_id),
            "academic_year": academic_year,
            "weekly_schedule": weekly_schedule,
            "total_periods": sum(len(day_schedule) for day_schedule in weekly_schedule.values()),
            "working_days": [day for day, schedule in weekly_schedule.items() if schedule],
            "access_type": "read_only" if requester_type in ["teacher", "student"] else "full_access"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# TEACHER TIMETABLE ENDPOINTS

@router.post("/teacher", response_model=dict)
async def create_teacher_timetable(
    teacher_timetable_data: TeacherTimetableCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create timetable for a teacher (School Authority Only)"""
    service = TimetableService(db)
    
    try:
        teacher_timetable = await service.create_teacher_timetable(
            teacher_timetable_data.model_dump()
        )
        
        return {
            "id": str(teacher_timetable.id),
            "message": "Teacher timetable created successfully",
            "teacher_id": str(teacher_timetable.teacher_id),
            "teacher_name": teacher_timetable.teacher_name,
            "academic_year": teacher_timetable.academic_year
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/teacher/{teacher_id}/schedule")
async def get_teacher_schedule(
    teacher_id: UUID,
    academic_year: str,
    requester_type: str = Query("school_authority", regex="^(school_authority|teacher)$"),
    requester_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get weekly schedule for a teacher (Accessible by School Authority and the teacher themselves)"""
    service = TimetableService(db)
    
    # Permission check: teachers can only view their own schedule
    if requester_type == "teacher" and requester_id != teacher_id:
        raise HTTPException(status_code=403, detail="Teachers can only view their own timetable")
    
    try:
        weekly_schedule = await service.get_teacher_weekly_schedule(teacher_id, academic_year)
        
        return {
            "teacher_id": str(teacher_id),
            "academic_year": academic_year,
            "weekly_schedule": weekly_schedule,
            "total_periods": sum(len(day_schedule) for day_schedule in weekly_schedule.values()),
            "working_days": [day for day, schedule in weekly_schedule.items() if schedule],
            "access_type": "read_only" if requester_type == "teacher" else "full_access"
        }
    except Exception as e:
        print(f"Error in get_teacher_schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# BULK OPERATIONS (School Authority Only)

@router.post("/bulk/schedule", response_model=dict)
async def bulk_create_schedule_entries(
    import_data: BulkScheduleCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Bulk create schedule entries (School Authority Only)"""
    service = TimetableService(db)
    
    result = await service.bulk_create_schedule_entries(
        schedule_entries=import_data.schedule_entries,
        tenant_id=import_data.tenant_id
    )
    
    return {
        "message": f"Bulk schedule creation completed. {result['successful_records']} entries created successfully",
        **result
    }

@router.put("/bulk/schedule", response_model=dict)
async def bulk_update_schedule_entries(
    update_data: BulkScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update schedule entries (School Authority Only)"""
    service = TimetableService(db)
    
    result = await service.bulk_update_schedule_entries(update_data.updates)
    
    return {
        "message": f"Bulk update completed. {result['updated_records']} entries updated successfully",
        **result
    }

@router.delete("/bulk/schedule", response_model=dict)
async def bulk_delete_schedule_entries(
    entry_ids: List[UUID],
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Bulk delete schedule entries (School Authority Only)"""
    service = TimetableService(db)
    
    result = await service.bulk_delete_schedule_entries(entry_ids, hard_delete)
    
    return {
        "message": f"Bulk delete completed. {result['deleted_records']} entries {result['delete_type']} deleted",
        **result
    }

# ANALYTICS AND REPORTING

@router.get("/analytics/{tenant_id}")
async def get_timetable_analytics(
    tenant_id: UUID,
    academic_year: str,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive timetable analytics (School Authority Only)"""
    service = TimetableService(db)
    
    try:
        analytics = await service.get_timetable_analytics(tenant_id, academic_year)
        
        return {
            "message": "Timetable analytics retrieved successfully",
            **analytics
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# CONFLICT MANAGEMENT (School Authority Only)

@router.get("/conflicts/{tenant_id}", response_model=List[dict])
async def get_timetable_conflicts(
    tenant_id: UUID,
    unresolved_only: bool = Query(True),
    severity: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get timetable conflicts (School Authority Only)"""
    service = TimetableService(db)
    
    try:
        # Use raw SQL for better performance
        conflicts_sql = text("""
            SELECT 
                tc.id,
                tc.conflict_type,
                tc.severity,
                tc.title,
                tc.description,
                tc.day_of_week,
                tc.period_number,
                tc.room_number,
                tc.is_resolved,
                tc.resolution_notes,
                tc.created_at,
                tc.resolved_date
            FROM timetable_conflicts tc
            WHERE tc.tenant_id = :tenant_id
            AND tc.is_deleted = false
            {}
            {}
            ORDER BY tc.severity DESC, tc.created_at DESC
        """.format(
            "AND tc.is_resolved = false" if unresolved_only else "",
            f"AND tc.severity = '{severity}'" if severity else ""
        ))
        
        result = await db.execute(conflicts_sql, {"tenant_id": tenant_id})
        conflicts = result.fetchall()
        
        return [
            {
                "id": str(conflict[0]),
                "conflict_type": conflict[1],
                "severity": conflict[2],
                "title": conflict[3],
                "description": conflict[4],
                "day_of_week": conflict[5],
                "period_number": conflict[6],
                "room_number": conflict[7],
                "is_resolved": conflict[8],
                "resolution_notes": conflict[9],
                "created_at": conflict[10].isoformat(),
                "resolved_date": conflict[11].isoformat() if conflict[11] else None
            }
            for conflict in conflicts
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# TEMPLATE SYSTEM (Future Enhancement)

@router.get("/templates/{tenant_id}")
async def get_timetable_templates(
    tenant_id: UUID,
    template_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get available timetable templates (School Authority Only)"""
    # Implementation for timetable templates
    return {
        "message": "Timetable templates feature coming soon",
        "available_types": ["class", "teacher", "grade_level"],
        "tenant_id": str(tenant_id)
    }

# READ-ONLY ENDPOINTS (For Teachers and Students)

@router.get("/readonly/class/{class_id}/today")
async def get_class_today_schedule(
    class_id: UUID,
    academic_year: str,
    today: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get today's schedule for a class (Read-only for Teachers and Students)"""
    service = TimetableService(db)
    
    if not today:
        today = date.today()
    
    day_of_week = DayOfWeek(today.strftime("%A").lower())
    
    try:
        weekly_schedule = await service.get_class_weekly_schedule(class_id, academic_year)
        today_schedule = weekly_schedule.get(day_of_week.value, [])
        
        return {
            "class_id": str(class_id),
            "date": today.isoformat(),
            "day_of_week": day_of_week.value,
            "schedule": today_schedule,
            "total_periods": len(today_schedule)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/readonly/teacher/{teacher_id}/today")
async def get_teacher_today_schedule(
    teacher_id: UUID,
    academic_year: str,
    today: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get today's schedule for a teacher (Read-only)"""
    service = TimetableService(db)
    
    if not today:
        today = date.today()
    
    day_of_week = DayOfWeek(today.strftime("%A").lower())
    
    try:
        weekly_schedule = await service.get_teacher_weekly_schedule(teacher_id, academic_year)
        today_schedule = weekly_schedule.get(day_of_week.value, [])
        
        return {
            "teacher_id": str(teacher_id),
            "date": today.isoformat(),
            "day_of_week": day_of_week.value,
            "schedule": today_schedule,
            "total_periods": len(today_schedule)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
