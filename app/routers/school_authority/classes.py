from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...models.tenant_specific.class_model import ClassModel
from ...services.class_service import ClassService

router = APIRouter(prefix="/api/v1/school_authority/classes", tags=["School Authority - Class Management"])

@router.get("/", response_model=dict)
async async def get_classes(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[UUID] = Query(None),
    grade_level: Optional[int] = Query(None),
    section: Optional[str] = Query(None),
    academic_year: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated classes with filtering options"""
    service = ClassService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    if grade_level:
        filters["grade_level"] = grade_level
    if section:
        filters["section"] = section
    if academic_year:
        filters["academic_year"] = academic_year
    if is_active is not None:
        filters["is_active"] = is_active
    
    result = service.get_classes_paginated(
        page=page,
        size=size,
        tenant_id=tenant_id,
        grade_level=grade_level,
        section=section,
        academic_year=academic_year,
        active_only=is_active or False
    )
    
    formatted_classes = [
        {
            "id": str(class_obj.id),
            "tenant_id": str(class_obj.tenant_id),
            "class_name": class_obj.class_name,
            "grade_level": class_obj.grade_level,
            "section": class_obj.section,
            "academic_year": class_obj.academic_year,
            "maximum_students": class_obj.maximum_students,
            "current_students": class_obj.current_students,
            "available_spots": class_obj.maximum_students - class_obj.current_students,
            "classroom": class_obj.classroom,
            "is_active": class_obj.is_active,
            "occupancy_rate": round((class_obj.current_students / class_obj.maximum_students * 100), 2) if class_obj.maximum_students > 0 else 0,
            "created_at": class_obj.created_at.isoformat(),
            "updated_at": class_obj.updated_at.isoformat()
        }
        for class_obj in result["items"]
    ]
    
    return {
        "items": formatted_classes,
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
        "has_next": result["has_next"],
        "has_previous": result["has_previous"],
        "total_pages": result["total_pages"]
    }

@router.post("/", response_model=dict)
async async def create_class(
    class_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create new class"""
    service = ClassService(db)
    
    try:
        class_obj = service.create(class_data)
        return {
            "id": str(class_obj.id),
            "message": "Class created successfully",
            "class_name": class_obj.class_name,
            "grade_level": class_obj.grade_level,
            "section": class_obj.section
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{class_id}", response_model=dict)
async async def get_class(
    class_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific class with complete details"""
    service = ClassService(db)
    class_obj = service.get(class_id)
    
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return {
        "id": str(class_obj.id),
        "tenant_id": str(class_obj.tenant_id),
        "class_name": class_obj.class_name,
        "grade_level": class_obj.grade_level,
        "section": class_obj.section,
        "academic_year": class_obj.academic_year,
        "maximum_students": class_obj.maximum_students,
        "current_students": class_obj.current_students,
        "available_spots": class_obj.maximum_students - class_obj.current_students,
        "classroom": class_obj.classroom,
        "is_active": class_obj.is_active,
        "occupancy_rate": round((class_obj.current_students / class_obj.maximum_students * 100), 2) if class_obj.maximum_students > 0 else 0,
        "created_at": class_obj.created_at.isoformat(),
        "updated_at": class_obj.updated_at.isoformat()
    }

@router.put("/{class_id}", response_model=dict)
async async def update_class(
    class_id: UUID,
    class_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update class information"""
    service = ClassService(db)
    class_obj = service.update(class_id, class_data)
    
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return {
        "id": str(class_obj.id),
        "message": "Class updated successfully",
        "class_name": class_obj.class_name
    }

@router.delete("/{class_id}")
async async def delete_class(
    class_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete class"""
    service = ClassService(db)
    success = service.soft_delete(class_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return {"message": "Class deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async async def get_classes_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all classes for a specific school/tenant"""
    service = ClassService(db)
    classes = service.get_classes_by_tenant_cached(tenant_id)
    
    return [
        {
            "id": str(class_obj.id),
            "class_name": class_obj.class_name,
            "grade_level": class_obj.grade_level,
            "section": class_obj.section,
            "current_students": class_obj.current_students,
            "maximum_students": class_obj.maximum_students,
            "classroom": class_obj.classroom,
            "is_active": class_obj.is_active,
            "academic_year": class_obj.academic_year
        }
        for class_obj in classes
    ]

@router.get("/grade/{grade_level}")
async async def get_classes_by_grade(
    grade_level: int,
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get classes by grade level"""
    service = ClassService(db)
    classes = service.get_classes_by_grade_cached(grade_level, tenant_id)
    
    return [
        {
            "id": str(class_obj.id),
            "class_name": class_obj.class_name,
            "section": class_obj.section,
            "current_students": class_obj.current_students,
            "maximum_students": class_obj.maximum_students,
            "classroom": class_obj.classroom,
            "academic_year": class_obj.academic_year,
            "is_active": class_obj.is_active
        }
        for class_obj in classes
    ]

@router.get("/availability/open")
async async def get_classes_with_availability(
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get classes that have available spots for new students"""
    service = ClassService(db)
    classes = service.get_classes_with_availability_cached(tenant_id)
    
    return [
        {
            "id": str(class_obj.id),
            "class_name": class_obj.class_name,
            "grade_level": class_obj.grade_level,
            "section": class_obj.section,
            "available_spots": class_obj.maximum_students - class_obj.current_students,
            "maximum_students": class_obj.maximum_students,
            "current_students": class_obj.current_students,
            "classroom": class_obj.classroom
        }
        for class_obj in classes
    ]

@router.get("/{class_id}/statistics")
async async def get_class_statistics(
    class_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed statistics for a specific class"""
    service = ClassService(db)
    stats = service.get_class_statistics(class_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return stats

@router.patch("/{class_id}/student-count")
async async def update_student_count(
    class_id: UUID,
    student_count_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update the current student count for a class"""
    service = ClassService(db)
    
    try:
        new_count = student_count_data.get("current_students")
        if new_count is None:
            raise HTTPException(status_code=400, detail="current_students field is required")
        
        class_obj = service.update_student_count(class_id, new_count)
        if not class_obj:
            raise HTTPException(status_code=404, detail="Class not found")
        
        return {
            "id": str(class_obj.id),
            "message": "Student count updated successfully",
            "class_name": class_obj.class_name,
            "current_students": class_obj.current_students,
            "maximum_students": class_obj.maximum_students,
            "available_spots": class_obj.maximum_students - class_obj.current_students
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/academic-year/{academic_year}")
async async def get_classes_by_academic_year(
    academic_year: str,
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all classes for a specific academic year"""
    service = ClassService(db)
    classes = service.get_by_academic_year(academic_year, tenant_id)
    
    return [
        {
            "id": str(class_obj.id),
            "class_name": class_obj.class_name,
            "grade_level": class_obj.grade_level,
            "section": class_obj.section,
            "current_students": class_obj.current_students,
            "maximum_students": class_obj.maximum_students,
            "classroom": class_obj.classroom,
            "is_active": class_obj.is_active
        }
        for class_obj in classes
    ]
