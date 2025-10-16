from typing import List, Optional
from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.fee_service import FeeService
from ...models.tenant_specific.fee_management import PaymentStatus, FeeType, FeeFrequency

router = APIRouter(prefix="/api/v1/school_authority/fees", tags=["School Authority - Fee Management"])

# Fee Structure Management
@router.post("/structure", response_model=dict)
async async def create_fee_structure(
    fee_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new fee structure"""
    service = FeeService(db)
    
    try:
        fee_structure = service.create_fee_structure(fee_data)
        return {
            "id": str(fee_structure.id),
            "message": "Fee structure created successfully",
            "fee_name": fee_structure.fee_name,
            "fee_type": fee_structure.fee_type.value,
            "base_amount": float(fee_structure.base_amount)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/structure/{tenant_id}", response_model=dict)
async async def get_fee_structures(
    tenant_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    academic_year: Optional[str] = Query(None),
    fee_type: Optional[FeeType] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated fee structures for a tenant"""
    service = FeeService(db)
    
    try:
        filters = {"tenant_id": tenant_id}
        if academic_year:
            filters["academic_year"] = academic_year
        if fee_type:
            filters["fee_type"] = fee_type
        if is_active is not None:
            filters["is_active"] = is_active
        
        result = service.get_paginated(page=page, size=size, **filters)
        
        formatted_structures = [
            {
                "id": str(fs.id),
                "fee_name": fs.fee_name,
                "fee_type": fs.fee_type.value,
                "fee_frequency": fs.fee_frequency.value,
                "base_amount": float(fs.base_amount),
                "currency": fs.currency,
                "applicable_grades": fs.applicable_grades,
                "is_mandatory": fs.is_mandatory,
                "is_active": fs.is_active,
                "academic_year": fs.academic_year,
                "effective_from": fs.effective_from.isoformat() if fs.effective_from else None,
                "effective_until": fs.effective_until.isoformat() if fs.effective_until else None,
                "late_fee_amount": float(fs.late_fee_amount) if fs.late_fee_amount else 0,
                "late_fee_days": fs.late_fee_days,
                "description": fs.description
            }
            for fs in result["items"]
        ]
        
        return {
            "items": formatted_structures,
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "has_next": result["has_next"],
            "has_previous": result["has_previous"],
            "total_pages": result["total_pages"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Student Fee Assignment
@router.post("/assign", response_model=dict)
async async def assign_fee_to_student(
    assignment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Assign fee to a specific student"""
    service = FeeService(db)
    
    try:
        student_fee = service.assign_fee_to_student(
            student_id=UUID(assignment_data["student_id"]),
            fee_structure_id=UUID(assignment_data["fee_structure_id"]),
            due_date=date.fromisoformat(assignment_data["due_date"]),
            discount_amount=assignment_data.get("discount_amount", 0),
            scholarship_amount=assignment_data.get("scholarship_amount", 0),
            assigned_by=UUID(assignment_data["assigned_by"]) if assignment_data.get("assigned_by") else None
        )
        
        return {
            "id": str(student_fee.id),
            "message": "Fee assigned to student successfully",
            "student_id": str(student_fee.student_id),
            "final_amount": float(student_fee.final_amount),
            "due_date": student_fee.due_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/student/{student_id}", response_model=List[dict])
async async def get_student_fees(
    student_id: UUID,
    academic_year: Optional[str] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all fees for a specific student"""
    service = FeeService(db)
    
    try:
        student_fees = service.get_student_fees(
            student_id=student_id,
            academic_year=academic_year,
            payment_status=payment_status
        )
        
        return [
            {
                "id": str(sf.id),
                "fee_structure_id": str(sf.fee_structure_id),
                "fee_name": sf.fee_structure.fee_name,
                "fee_type": sf.fee_structure.fee_type.value,
                "academic_year": sf.academic_year,
                "term": sf.term,
                "base_amount": float(sf.base_amount),
                "discount_amount": float(sf.discount_amount),
                "scholarship_amount": float(sf.scholarship_amount),
                "late_fee_amount": float(sf.late_fee_amount),
                "final_amount": float(sf.final_amount),
                "paid_amount": float(sf.paid_amount),
                "pending_amount": float(sf.pending_amount),
                "payment_status": sf.payment_status.value,
                "due_date": sf.due_date.isoformat(),
                "last_payment_date": sf.last_payment_date.isoformat() if sf.last_payment_date else None,
                "discount_reason": sf.discount_reason,
                "notes": sf.notes
            }
            for sf in student_fees
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Payment Processing
@router.post("/payment", response_model=dict)
async async def process_payment(
    payment_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Process a fee payment"""
    service = FeeService(db)
    
    try:
        payment = service.process_payment(payment_data)
        return {
            "id": str(payment.id),
            "message": "Payment processed successfully",
            "payment_id": payment.payment_id,
            "receipt_number": payment.receipt_number,
            "payment_amount": float(payment.payment_amount),
            "payment_method": payment.payment_method.value,
            "payment_date": payment.payment_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/payments/student/{student_id}", response_model=List[dict])
async async def get_payment_history(
    student_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get payment history for a student"""
    service = FeeService(db)
    
    try:
        payments = service.get_payment_history(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return [
            {
                "id": str(payment.id),
                "payment_id": payment.payment_id,
                "receipt_number": payment.receipt_number,
                "payment_date": payment.payment_date.isoformat(),
                "payment_amount": float(payment.payment_amount),
                "payment_method": payment.payment_method.value,
                "payment_status": payment.payment_status.value,
                "transaction_id": payment.transaction_id,
                "reference_number": payment.reference_number,
                "is_verified": payment.is_verified,
                "payment_notes": payment.payment_notes,
                "collected_by": str(payment.collected_by) if payment.collected_by else None
            }
            for payment in payments
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Outstanding Fees
@router.get("/outstanding/{tenant_id}", response_model=List[dict])
async async def get_outstanding_fees(
    tenant_id: UUID,
    class_id: Optional[UUID] = Query(None),
    overdue_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """Get outstanding fees for a tenant"""
    service = FeeService(db)
    
    try:
        outstanding_fees = service.get_outstanding_fees(
            tenant_id=tenant_id,
            class_id=class_id,
            overdue_only=overdue_only
        )
        
        return [
            {
                "id": str(sf.id),
                "student_id": str(sf.student_id),
                "student_name": f"{sf.student.first_name} {sf.student.last_name}",
                "fee_name": sf.fee_structure.fee_name,
                "fee_type": sf.fee_structure.fee_type.value,
                "final_amount": float(sf.final_amount),
                "paid_amount": float(sf.paid_amount),
                "pending_amount": float(sf.pending_amount),
                "due_date": sf.due_date.isoformat(),
                "days_overdue": (date.today() - sf.due_date).days if sf.due_date < date.today() else 0,
                "payment_status": sf.payment_status.value,
                "class_name": sf.class_ref.class_name if sf.class_ref else None
            }
            for sf in outstanding_fees
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Fee Summary and Reports
@router.get("/summary/{tenant_id}", response_model=dict)
async async def get_fee_summary(
    tenant_id: UUID,
    academic_year: str,
    db: AsyncSession = Depends(get_db)
):
    """Get fee collection summary"""
    service = FeeService(db)
    
    try:
        summary = service.get_fee_summary(tenant_id, academic_year)
        return summary
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Late Fee Management
@router.post("/late-fees/apply/{tenant_id}", response_model=dict)
async async def apply_late_fees(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Apply late fees to overdue payments"""
    service = FeeService(db)
    
    try:
        count = service.apply_late_fees(tenant_id)
        return {
            "message": f"Late fees applied to {count} overdue payments",
            "affected_records": count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Scholarship Management
@router.post("/scholarship", response_model=dict)
async async def create_scholarship(
    scholarship_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scholarship program"""
    service = FeeService(db)
    
    try:
        scholarship = service.create_scholarship(scholarship_data)
        return {
            "id": str(scholarship.id),
            "message": "Scholarship created successfully",
            "scholarship_name": scholarship.scholarship_name,
            "scholarship_code": scholarship.scholarship_code
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/scholarship/apply", response_model=dict)
async async def apply_for_scholarship(
    application_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Apply for scholarship"""
    service = FeeService(db)
    
    try:
        application = service.apply_for_scholarship(
            student_id=UUID(application_data["student_id"]),
            scholarship_id=UUID(application_data["scholarship_id"]),
            application_data=application_data
        )
        return {
            "id": str(application.id),
            "message": "Scholarship application submitted successfully",
            "application_number": application.application_number
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
