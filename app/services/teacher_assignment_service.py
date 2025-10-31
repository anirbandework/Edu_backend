# app/services/teacher_assignment_service.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.tenant_specific.teacher_assignment import TeacherAssignment
from ..schemas.teacher_assignment_schemas import TeacherAssignmentCreate, TeacherAssignmentUpdate
from .base_service import BaseService

class TeacherAssignmentService(BaseService[TeacherAssignment]):
    def __init__(self, db: AsyncSession):
        super().__init__(TeacherAssignment, db)

    async def get_by_teacher(self, tenant_id: UUID, teacher_id: UUID) -> List[TeacherAssignment]:
        query = select(self.model).where(
            self.model.tenant_id == tenant_id,
            self.model.teacher_id == teacher_id,
            self.model.is_deleted == False
        ).options(selectinload(self.model.class_ref))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_class(self, tenant_id: UUID, class_id: UUID) -> List[TeacherAssignment]:
        query = select(self.model).where(
            self.model.tenant_id == tenant_id,
            self.model.class_id == class_id,
            self.model.is_deleted == False
        ).options(selectinload(self.model.teacher))
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_with_tenant(self, tenant_id: UUID, obj_in: TeacherAssignmentCreate) -> TeacherAssignment:
        obj_data = obj_in.model_dump()
        obj_data['tenant_id'] = tenant_id
        return await self.create(obj_data)