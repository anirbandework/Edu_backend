from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.timetable_service import TimetableService
from ...models.tenant_specific.timetable import DayOfWeek, TimetableStatus

router = APIRouter(prefix="/api/v1/school_authority/timetable", tags=["School Authority - Timetable Management"])

# Master Timetable Management
@router.post("/master", response_model=dict)
async async def create_master_timetable(
    timetable_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new master timetable"""
    service = TimetableService(db)
    
    try:
        master_timetable = service.create_master_timetable(timetable_data)
        return {
            "id": str(master_timetable.id),
            "message": "Master timetable created successfully",
            "timetable_name": master_timetable.timetable_name,
            "academic_year": master_timetable.academic_year
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/master/{tenant_id}", response_model=List[dict])
async async def get_master_timetables(
    tenant_id: UUID,
    academic_year: Optional[str] = Query(None),
    status: Optional[TimetableStatus] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all master timetables for a tenant"""
    service = TimetableService(db)
    
    try:
        filters = {"tenant_id": tenant_id}
        if academic_year:
            filters["academic_year"] = academic_year
        if status:
            filters["status"] = status
        
        timetables = service.get_multi(**filters)
        
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
                "status": tt.status.value,
                "is_default": tt.is_default,
                "working_days": tt.working_days
            }
            for tt in timetables
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Class Timetable Management
@router.post("/class", response_model=dict)
async async def create_class_timetable(
    class_timetable_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create timetable for a class"""
    service = TimetableService(db)
    
    try:
        class_timetable = service.create_class_timetable(class_timetable_data)
        return {
            "id": str(class_timetable.id),
            "message": "Class timetable created successfully",
            "class_id": str(class_timetable.class_id),
            "academic_year": class_timetable.academic_year
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/class/{class_id}", response_model=dict)
async async def get_class_timetable(
    class_id: UUID,
    academic_year: str,
    db: AsyncSession = Depends(get_db)
):
    """Get timetable for a specific class"""
    service = TimetableService(db)
    
    try:
        class_timetable = service.get_class_timetable(class_id, academic_year)
        
        if not class_timetable:
            raise HTTPException(status_code=404, detail="Class timetable not found")
        
        return {
            "id": str(class_timetable.id),
            "tenant_id": str(class_timetable.tenant_id),
            "class_id": str(class_timetable.class_id),
            "master_timetable_id": str(class_timetable.master_timetable_id),
            "academic_year": class_timetable.academic_year,
            "term": class_timetable.term,
            "is_active": class_timetable.is_active,
            "created_at": class_timetable.created_at.isoformat(),
            "updated_at": class_timetable.updated_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Teacher Timetable Management
@router.post("/teacher", response_model=dict)
async async def create_teacher_timetable(
    teacher_timetable_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create timetable for a teacher"""
    service = TimetableService(db)
    
    try:
        teacher_timetable = service.create_teacher_timetable(teacher_timetable_data)
        return {
            "id": str(teacher_timetable.id),
            "message": "Teacher timetable created successfully",
            "teacher_id": str(teacher_timetable.teacher_id),
            "academic_year": teacher_timetable.academic_year
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/teacher/{teacher_id}", response_model=dict)
async async def get_teacher_timetable(
    teacher_id: UUID,
    academic_year: str,
    db: AsyncSession = Depends(get_db)
):
    """Get timetable for a specific teacher"""
    service = TimetableService(db)
    
    try:
        teacher_timetable = service.get_teacher_timetable(teacher_id, academic_year)
        
        if not teacher_timetable:
            raise HTTPException(status_code=404, detail="Teacher timetable not found")
        
        return {
            "id": str(teacher_timetable.id),
            "tenant_id": str(teacher_timetable.tenant_id),
            "teacher_id": str(teacher_timetable.teacher_id),
            "master_timetable_id": str(teacher_timetable.master_timetable_id),
            "academic_year": teacher_timetable.academic_year,
            "term": teacher_timetable.term,
            "total_periods_per_week": teacher_timetable.total_periods_per_week,
            "max_periods_per_day": teacher_timetable.max_periods_per_day,
            "preferred_periods": teacher_timetable.preferred_periods,
            "is_active": teacher_timetable.is_active
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Schedule Entry Management
@router.post("/schedule", response_model=dict)
async async def add_schedule_entry(
    schedule_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Add a new schedule entry"""
    service = TimetableService(db)
    
    try:
        schedule_entry = service.add_schedule_entry(schedule_data)
        return {
            "id": str(schedule_entry.id),
            "message": "Schedule entry added successfully",
            "subject_name": schedule_entry.subject_name,
            "day_of_week": schedule_entry.day_of_week.value,
            "room_number": schedule_entry.room_number
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schedule/class/{class_timetable_id}/daily", response_model=List[dict])
async async def get_daily_schedule(
    class_timetable_id: UUID,
    day_of_week: DayOfWeek,
    db: AsyncSession = Depends(get_db)
):
    """Get daily schedule for a class"""
    service = TimetableService(db)
    
    try:
        schedule_entries = service.get_daily_schedule(class_timetable_id, day_of_week)
        
        return [
            {
                "id": str(entry.id),
                "period_number": entry.period.period_number,
                "period_name": entry.period.period_name,
                "start_time": entry.period.start_time.isoformat() if entry.period.start_time else None,
                "end_time": entry.period.end_time.isoformat() if entry.period.end_time else None,
                "subject_name": entry.subject_name,
                "subject_code": entry.subject_code,
                "room_number": entry.room_number,
                "building": entry.building,
                "notes": entry.notes,
                "is_substitution": entry.is_substitution
            }
            for entry in schedule_entries
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schedule/class/{class_timetable_id}/weekly", response_model=Dict[str, List[dict]])
async async def get_weekly_schedule(
    class_timetable_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get weekly schedule for a class"""
    service = TimetableService(db)
    
    try:
        weekly_schedule = service.get_weekly_schedule(class_timetable_id)
        
        formatted_schedule = {}
        for day, entries in weekly_schedule.items():
            formatted_schedule[day] = [
                {
                    "id": str(entry.id),
                    "period_number": entry.period.period_number,
                    "period_name": entry.period.period_name,
                    "start_time": entry.period.start_time.isoformat() if entry.period.start_time else None,
                    "end_time": entry.period.end_time.isoformat() if entry.period.end_time else None,
                    "subject_name": entry.subject_name,
                    "subject_code": entry.subject_code,
                    "room_number": entry.room_number,
                    "building": entry.building
                }
                for entry in entries
            ]
        
        return formatted_schedule
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schedule/teacher/{teacher_timetable_id}/daily", response_model=List[dict])
async async def get_teacher_daily_schedule(
    teacher_timetable_id: UUID,
    day_of_week: DayOfWeek,
    db: AsyncSession = Depends(get_db)
):
    """Get daily schedule for a teacher"""
    service = TimetableService(db)
    
    try:
        schedule_entries = service.get_teacher_daily_schedule(teacher_timetable_id, day_of_week)
        
        return [
            {
                "id": str(entry.id),
                "period_number": entry.period.period_number,
                "period_name": entry.period.period_name,
                "start_time": entry.period.start_time.isoformat() if entry.period.start_time else None,
                "end_time": entry.period.end_time.isoformat() if entry.period.end_time else None,
                "subject_name": entry.subject_name,
                "subject_code": entry.subject_code,
                "room_number": entry.room_number,
                "class_timetable_id": str(entry.class_timetable_id),
                "notes": entry.notes
            }
            for entry in schedule_entries
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Conflicts Management
@router.get("/conflicts/{tenant_id}", response_model=List[dict])
async async def get_timetable_conflicts(
    tenant_id: UUID,
    unresolved_only: bool = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get timetable conflicts"""
    service = TimetableService(db)
    
    try:
        conflicts = service.get_conflicts(tenant_id, unresolved_only)
        
        return [
            {
                "id": str(conflict.id),
                "conflict_type": conflict.conflict_type,
                "severity": conflict.severity,
                "description": conflict.description,
                "is_resolved": conflict.is_resolved,
                "created_at": conflict.created_at.isoformat(),
                "resolved_date": conflict.resolved_date.isoformat() if conflict.resolved_date else None,
                "resolution_notes": conflict.resolution_notes
            }
            for conflict in conflicts
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/conflicts/{conflict_id}/resolve", response_model=dict)
async async def resolve_conflict(
    conflict_id: UUID,
    resolution_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Resolve a timetable conflict"""
    service = TimetableService(db)
    
    try:
        conflict = service.resolve_conflict(
            conflict_id=conflict_id,
            resolved_by=resolution_data.get("resolved_by"),
            resolution_notes=resolution_data.get("resolution_notes", "")
        )
        
        if not conflict:
            raise HTTPException(status_code=404, detail="Conflict not found")
        
        return {
            "id": str(conflict.id),
            "message": "Conflict resolved successfully",
            "is_resolved": conflict.is_resolved,
            "resolved_date": conflict.resolved_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Analytics and Reports
@router.get("/analytics/room-utilization", response_model=dict)
async async def get_room_utilization(
    tenant_id: UUID,
    room_number: str,
    academic_year: str,
    db: AsyncSession = Depends(get_db)
):
    """Get room utilization statistics"""
    service = TimetableService(db)
    
    try:
        utilization = service.get_room_utilization(tenant_id, room_number, academic_year)
        return utilization
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analytics/teacher-workload", response_model=dict)
async async def get_teacher_workload(
    teacher_id: UUID,
    academic_year: str,
    db: AsyncSession = Depends(get_db)
):
    """Get teacher workload statistics"""
    service = TimetableService(db)
    
    try:
        workload = service.get_teacher_workload(teacher_id, academic_year)
        return workload
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
