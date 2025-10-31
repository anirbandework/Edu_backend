# app/routers/teacher_assignment.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..schemas.teacher_assignment_schemas import TeacherAssignment, TeacherAssignmentCreate, TeacherAssignmentUpdate
from ..services.teacher_assignment_service import TeacherAssignmentService

router = APIRouter(prefix="/teacher-assignments", tags=["teacher-assignments"])

@router.post("/", response_model=TeacherAssignment, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    tenant_id: UUID,
    assignment: TeacherAssignmentCreate,
    db: AsyncSession = Depends(get_db)
):
    service = TeacherAssignmentService(db)
    return await service.create_with_tenant(tenant_id, assignment)

@router.get("/teacher/{teacher_id}", response_model=List[TeacherAssignment])
async def get_teacher_assignments(
    tenant_id: UUID,
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = TeacherAssignmentService(db)
    return await service.get_by_teacher(tenant_id, teacher_id)

@router.get("/class/{class_id}", response_model=List[TeacherAssignment])
async def get_class_assignments(
    tenant_id: UUID,
    class_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = TeacherAssignmentService(db)
    return await service.get_by_class(tenant_id, class_id)

@router.put("/{assignment_id}", response_model=TeacherAssignment)
async def update_assignment(
    assignment_id: UUID,
    assignment: TeacherAssignmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = TeacherAssignmentService(db)
    db_assignment = await service.update(assignment_id, assignment.model_dump(exclude_unset=True))
    if not db_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return db_assignment

@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = TeacherAssignmentService(db)
    success = await service.soft_delete(assignment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")