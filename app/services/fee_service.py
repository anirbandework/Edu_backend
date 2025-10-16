from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import and_, or_, func
from .base_service import BaseService
from ..models.tenant_specific.fee_management import (
    FeeStructure, StudentFee, Payment, Scholarship, ScholarshipApplication, 
    FeeTransaction, FeeType, FeeFrequency, PaymentStatus, PaymentMethod
)

class FeeService(BaseService[FeeStructure]):
    async def __init__(self, db: Session):
        super().__init__(FeeStructure, db)
    
    async def create_fee_structure(self, fee_data: dict) -> FeeStructure:
        """Create a new fee structure"""
        fee_structure = self.create(fee_data)
        
        # Auto-assign to applicable students if specified
        if fee_data.get("auto_assign_to_students", False):
            self._auto_assign_to_students(fee_structure)
        
        return fee_structure
    
    async def _auto_assign_to_students(self, fee_structure: FeeStructure):
        """Auto-assign fee structure to applicable students"""
        from ..models.tenant_specific.student import Student
        
        # Get students based on applicable grades and class
        query = self.await db.execute(select(Student).filter(
            Student.tenant_id == fee_structure.tenant_id,
            Student.is_deleted == False,
            Student.status == "active"
        )
        
        if fee_structure.applicable_grades:
            query = query.filter(Student.grade_level.in_(fee_structure.applicable_grades))
        
        if fee_structure.class_id:
            query = query.filter(Student.class_id == fee_structure.class_id)
        
        students = query.all()
        
        for student in students:
            self.assign_fee_to_student(
                student_id=student.id,
                fee_structure_id=fee_structure.id,
                due_date=fee_structure.effective_from + timedelta(days=30)
            )
    
    async def assign_fee_to_student(
        self, 
        student_id: UUID, 
        fee_structure_id: UUID,
        due_date: date,
        discount_amount: Decimal = 0,
        scholarship_amount: Decimal = 0,
        assigned_by: Optional[UUID] = None
    ) -> StudentFee:
        """Assign a fee structure to a specific student"""
        
        fee_structure = self.get(fee_structure_id)
        if not fee_structure:
            raise ValueError("Fee structure not found")
        
        # Calculate final amount
        final_amount = fee_structure.base_amount - discount_amount - scholarship_amount
        
        student_fee = StudentFee(
            tenant_id=fee_structure.tenant_id,
            student_id=student_id,
            fee_structure_id=fee_structure_id,
            academic_year=fee_structure.academic_year,
            base_amount=fee_structure.base_amount,
            discount_amount=discount_amount,
            scholarship_amount=scholarship_amount,
            final_amount=final_amount,
            pending_amount=final_amount,
            due_date=due_date,
            assigned_by=assigned_by
        )
        
        self.db.add(student_fee)
        self.db.commit()
        self.db.refresh(student_fee)
        
        return student_fee
    
    async def process_payment(self, payment_data: dict) -> Payment:
        """Process a fee payment"""
        
        # Get student fee record
        student_fee = self.await db.execute(select(StudentFee).filter(
            StudentFee.id == payment_data["student_fee_id"]
        ).first()
        
        if not student_fee:
            raise ValueError("Student fee record not found")
        
        # Generate payment ID if not provided
        if not payment_data.get("payment_id"):
            payment_data["payment_id"] = self._generate_payment_id()
        
        # Generate receipt number if not provided
        if not payment_data.get("receipt_number"):
            payment_data["receipt_number"] = self._generate_receipt_number()
        
        # Create payment record
        payment = Payment(**payment_data)
        self.db.add(payment)
        
        # Update student fee record
        student_fee.paid_amount += payment.payment_amount
        student_fee.pending_amount = student_fee.final_amount - student_fee.paid_amount
        student_fee.last_payment_date = payment.payment_date.date()
        
        # Update payment status
        if student_fee.pending_amount <= 0:
            student_fee.payment_status = PaymentStatus.PAID
        elif student_fee.paid_amount > 0:
            student_fee.payment_status = PaymentStatus.PARTIAL
        
        # Create transaction record
        transaction = FeeTransaction(
            tenant_id=student_fee.tenant_id,
            student_id=student_fee.student_id,
            transaction_number=self._generate_transaction_number(),
            transaction_date=payment.payment_date,
            transaction_type="payment",
            amount=payment.payment_amount,
            reference_type="payment",
            reference_id=payment.id,
            description=f"Fee payment - {payment.payment_method.value}",
            processed_by=payment.collected_by
        )
        self.db.add(transaction)
        
        self.db.commit()
        self.db.refresh(payment)
        
        return payment
    
    async def _generate_payment_id(self) -> str:
        """Generate unique payment ID"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"PAY{timestamp}"
    
    async def _generate_receipt_number(self) -> str:
        """Generate unique receipt number"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"RCP{timestamp}"
    
    async def _generate_transaction_number(self) -> str:
        """Generate unique transaction number"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"TXN{timestamp}"
    
    async def get_student_fees(
        self, 
        student_id: UUID, 
        academic_year: Optional[str] = None,
        payment_status: Optional[PaymentStatus] = None
    ) -> List[StudentFee]:
        """Get all fees for a student"""
        query = self.await db.execute(select(StudentFee).filter(
            StudentFee.student_id == student_id,
            StudentFee.is_deleted == False
        )
        
        if academic_year:
            query = query.filter(StudentFee.academic_year == academic_year)
        
        if payment_status:
            query = query.filter(StudentFee.payment_status == payment_status)
        
        return query.all()
    
    async def get_outstanding_fees(
        self, 
        tenant_id: UUID,
        class_id: Optional[UUID] = None,
        overdue_only: bool = False
    ) -> List[StudentFee]:
        """Get outstanding fees for a tenant"""
        query = self.await db.execute(select(StudentFee).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.pending_amount > 0,
            StudentFee.is_deleted == False
        )
        
        if class_id:
            query = query.filter(StudentFee.class_id == class_id)
        
        if overdue_only:
            query = query.filter(StudentFee.due_date < date.today())
        
        return query.all()
    
    async def get_fee_summary(self, tenant_id: UUID, academic_year: str) -> Dict[str, Any]:
        """Get fee collection summary for a tenant"""
        
        total_fees = self.await db.execute(select(func.sum(StudentFee.final_amount)).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.academic_year == academic_year,
            StudentFee.is_deleted == False
        ).scalar() or 0
        
        total_collected = self.await db.execute(select(func.sum(StudentFee.paid_amount)).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.academic_year == academic_year,
            StudentFee.is_deleted == False
        ).scalar() or 0
        
        total_pending = self.await db.execute(select(func.sum(StudentFee.pending_amount)).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.academic_year == academic_year,
            StudentFee.is_deleted == False
        ).scalar() or 0
        
        overdue_amount = self.await db.execute(select(func.sum(StudentFee.pending_amount)).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.academic_year == academic_year,
            StudentFee.due_date < date.today(),
            StudentFee.pending_amount > 0,
            StudentFee.is_deleted == False
        ).scalar() or 0
        
        total_students = self.await db.execute(select(func.count(func.distinct(StudentFee.student_id))).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.academic_year == academic_year,
            StudentFee.is_deleted == False
        ).scalar() or 0
        
        students_paid = self.await db.execute(select(func.count(func.distinct(StudentFee.student_id))).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.academic_year == academic_year,
            StudentFee.payment_status == PaymentStatus.PAID,
            StudentFee.is_deleted == False
        ).scalar() or 0
        
        return {
            "academic_year": academic_year,
            "total_fees": float(total_fees),
            "total_collected": float(total_collected),
            "total_pending": float(total_pending),
            "overdue_amount": float(overdue_amount),
            "collection_percentage": round((total_collected / total_fees * 100), 2) if total_fees > 0 else 0,
            "total_students": total_students,
            "students_paid": students_paid,
            "students_pending": total_students - students_paid
        }
    
    async def apply_late_fees(self, tenant_id: UUID) -> int:
        """Apply late fees to overdue payments"""
        
        overdue_fees = self.await db.execute(select(StudentFee).join(FeeStructure).filter(
            StudentFee.tenant_id == tenant_id,
            StudentFee.due_date < date.today(),
            StudentFee.pending_amount > 0,
            StudentFee.late_fee_amount == 0,  # Not already applied
            FeeStructure.late_fee_amount > 0,
            StudentFee.is_deleted == False
        ).all()
        
        count = 0
        for student_fee in overdue_fees:
            days_overdue = (date.today() - student_fee.due_date).days
            
            if days_overdue >= student_fee.fee_structure.late_fee_days:
                student_fee.late_fee_amount = student_fee.fee_structure.late_fee_amount
                student_fee.final_amount += student_fee.late_fee_amount
                student_fee.pending_amount += student_fee.late_fee_amount
                count += 1
                
                # Create transaction record
                transaction = FeeTransaction(
                    tenant_id=student_fee.tenant_id,
                    student_id=student_fee.student_id,
                    transaction_number=self._generate_transaction_number(),
                    transaction_date=datetime.now(),
                    transaction_type="late_fee",
                    amount=student_fee.late_fee_amount,
                    reference_type="student_fee",
                    reference_id=student_fee.id,
                    description=f"Late fee applied - {days_overdue} days overdue"
                )
                self.db.add(transaction)
        
        self.db.commit()
        return count
    
    async def get_payment_history(
        self, 
        student_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Payment]:
        """Get payment history for a student"""
        query = self.await db.execute(select(Payment).filter(
            Payment.student_id == student_id,
            Payment.is_deleted == False
        )
        
        if start_date:
            query = query.filter(func.date(Payment.payment_date) >= start_date)
        
        if end_date:
            query = query.filter(func.date(Payment.payment_date) <= end_date)
        
        return query.order_by(Payment.payment_date.desc()).all()
    
    async def create_scholarship(self, scholarship_data: dict) -> Scholarship:
        """Create a new scholarship program"""
        scholarship = Scholarship(**scholarship_data)
        scholarship.available_slots = scholarship.total_slots
        
        self.db.add(scholarship)
        self.db.commit()
        self.db.refresh(scholarship)
        
        return scholarship
    
    async def apply_for_scholarship(
        self, 
        student_id: UUID, 
        scholarship_id: UUID,
        application_data: dict
    ) -> ScholarshipApplication:
        """Submit scholarship application"""
        
        # Check if student already applied
        existing = self.await db.execute(select(ScholarshipApplication).filter(
            ScholarshipApplication.student_id == student_id,
            ScholarshipApplication.scholarship_id == scholarship_id,
            ScholarshipApplication.is_deleted == False
        ).first()
        
        if existing:
            raise ValueError("Student has already applied for this scholarship")
        
        # Generate application number
        application_number = self._generate_application_number()
        
        application = ScholarshipApplication(
            student_id=student_id,
            scholarship_id=scholarship_id,
            application_number=application_number,
            application_date=datetime.now(),
            **application_data
        )
        
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        
        return application
    
    async def _generate_application_number(self) -> str:
        """Generate unique application number"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"APP{timestamp}"
