# app/services/bulk_tenant_service.py
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update
from sqlalchemy.exc import IntegrityError
import pandas as pd
from ..core.exceptions import BulkOperationError
from ..models.shared.tenant import Tenant

class BulkTenantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def bulk_update_tenants_raw_sql(
        self, 
        tenant_data: List[Dict[str, Any]], 
        operation_id: str
    ) -> Dict[str, Any]:
        """
        High-performance bulk update using individual updates in transaction
        More reliable than complex array operations with asyncpg
        """
        start_time = datetime.now()
        successful_updates = 0
        failed_updates = 0
        errors = []
        
        try:
            # Process in smaller batches to avoid memory issues
            batch_size = 100  # Smaller batches for better error handling
            
            for i in range(0, len(tenant_data), batch_size):
                batch = tenant_data[i:i + batch_size]
                batch_successful = 0
                batch_failed = 0
                
                # Start transaction for this batch
                try:
                    async with self.db.begin():
                        for j, row_data in enumerate(batch):
                            try:
                                school_code = row_data.get('school_code')
                                if not school_code:
                                    batch_failed += 1
                                    errors.append({
                                        "row": i + j + 1,
                                        "error": "Missing school_code",
                                        "data": row_data,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    continue
                                
                                # Find existing tenant
                                stmt = select(Tenant).where(
                                    Tenant.school_code == school_code,
                                    Tenant.is_active == True
                                )
                                result = await self.db.execute(stmt)
                                existing_tenant = result.scalar_one_or_none()
                                
                                if not existing_tenant:
                                    batch_failed += 1
                                    errors.append({
                                        "row": i + j + 1,
                                        "error": f"Tenant with school_code {school_code} not found",
                                        "school_code": school_code,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    continue
                                
                                # Prepare update data (only non-None values)
                                update_data = self._prepare_update_data(row_data)
                                
                                if update_data:
                                    # Add updated_at timestamp
                                    update_data['updated_at'] = datetime.now()
                                    
                                    # Perform update
                                    update_stmt = update(Tenant).where(
                                        Tenant.id == existing_tenant.id
                                    ).values(**update_data)
                                    
                                    await self.db.execute(update_stmt)
                                    batch_successful += 1
                                else:
                                    batch_failed += 1
                                    errors.append({
                                        "row": i + j + 1,
                                        "error": "No valid data to update",
                                        "school_code": school_code,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    
                            except IntegrityError as e:
                                batch_failed += 1
                                error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                                errors.append({
                                    "row": i + j + 1,
                                    "error": f"Integrity constraint violation: {error_msg}",
                                    "school_code": row_data.get('school_code', 'unknown'),
                                    "timestamp": datetime.now().isoformat()
                                })
                                
                            except Exception as e:
                                batch_failed += 1
                                errors.append({
                                    "row": i + j + 1,
                                    "error": str(e),
                                    "school_code": row_data.get('school_code', 'unknown'),
                                    "timestamp": datetime.now().isoformat()
                                })
                
                except Exception as batch_error:
                    # If the entire batch fails, mark all rows as failed
                    batch_failed = len(batch)
                    errors.append({
                        "batch_start": i,
                        "batch_end": i + len(batch),
                        "error": str(batch_error),
                        "timestamp": datetime.now().isoformat()
                    })
                
                successful_updates += batch_successful
                failed_updates += batch_failed
                
                # Update progress
                progress = int((i + len(batch)) / len(tenant_data) * 100)
                await self._update_operation_status(
                    operation_id, 
                    'processing', 
                    progress,
                    len(tenant_data),
                    successful_updates + failed_updates
                )
            
            # Final status update
            processing_time = (datetime.now() - start_time).total_seconds()
            
            final_status = 'completed' if failed_updates == 0 else 'completed_with_errors'
            
            return {
                "total_rows": len(tenant_data),
                "successful_updates": successful_updates,
                "failed_updates": failed_updates,
                "errors": errors,
                "processing_time_seconds": processing_time,
                "operation_id": operation_id,
                "status": final_status
            }
            
        except Exception as e:
            await self.db.rollback()
            raise BulkOperationError(f"Bulk update failed: {str(e)}")

    async def bulk_create_tenants(
        self, 
        tenant_data: List[Dict[str, Any]], 
        operation_id: str
    ) -> Dict[str, Any]:
        """
        Bulk create new tenants
        """
        start_time = datetime.now()
        successful_creates = 0
        failed_creates = 0
        errors = []
        
        try:
            batch_size = 100
            
            for i in range(0, len(tenant_data), batch_size):
                batch = tenant_data[i:i + batch_size]
                batch_successful = 0
                batch_failed = 0
                
                try:
                    async with self.db.begin():
                        for j, row_data in enumerate(batch):
                            try:
                                school_code = row_data.get('school_code')
                                if not school_code:
                                    batch_failed += 1
                                    errors.append({
                                        "row": i + j + 1,
                                        "error": "Missing school_code",
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    continue
                                
                                # Check if tenant already exists
                                stmt = select(Tenant).where(Tenant.school_code == school_code)
                                result = await self.db.execute(stmt)
                                existing_tenant = result.scalar_one_or_none()
                                
                                if existing_tenant:
                                    batch_failed += 1
                                    errors.append({
                                        "row": i + j + 1,
                                        "error": f"Tenant with school_code {school_code} already exists",
                                        "school_code": school_code,
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    continue
                                
                                # Create new tenant
                                create_data = self._prepare_create_data(row_data)
                                new_tenant = Tenant(**create_data)
                                self.db.add(new_tenant)
                                await self.db.flush()
                                batch_successful += 1
                                
                            except IntegrityError as e:
                                batch_failed += 1
                                error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
                                errors.append({
                                    "row": i + j + 1,
                                    "error": f"Integrity constraint violation: {error_msg}",
                                    "school_code": row_data.get('school_code', 'unknown'),
                                    "timestamp": datetime.now().isoformat()
                                })
                                
                            except Exception as e:
                                batch_failed += 1
                                errors.append({
                                    "row": i + j + 1,
                                    "error": str(e),
                                    "school_code": row_data.get('school_code', 'unknown'),
                                    "timestamp": datetime.now().isoformat()
                                })
                
                except Exception as batch_error:
                    batch_failed = len(batch)
                    errors.append({
                        "batch_start": i,
                        "batch_end": i + len(batch),
                        "error": str(batch_error),
                        "timestamp": datetime.now().isoformat()
                    })
                
                successful_creates += batch_successful
                failed_creates += batch_failed
                
                # Update progress
                progress = int((i + len(batch)) / len(tenant_data) * 100)
                await self._update_operation_status(
                    operation_id, 
                    'processing', 
                    progress,
                    len(tenant_data),
                    successful_creates + failed_creates
                )
        
            processing_time = (datetime.now() - start_time).total_seconds()
            final_status = 'completed' if failed_creates == 0 else 'completed_with_errors'
            
            return {
                "total_rows": len(tenant_data),
                "successful_creates": successful_creates,
                "failed_creates": failed_creates,
                "errors": errors,
                "processing_time_seconds": processing_time,
                "operation_id": operation_id,
                "status": final_status
            }
            
        except Exception as e:
            await self.db.rollback()
            raise BulkOperationError(f"Bulk create failed: {str(e)}")

    def _prepare_update_data(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for updating existing tenant"""
        update_data = {}
        field_mapping = {
            'school_name': 'school_name',
            'address': 'address',
            'phone': 'phone',
            'email': 'email',
            'principal_name': 'principal_name',
            'annual_tuition': 'annual_tuition',
            'registration_fee': 'registration_fee',
            'maximum_capacity': 'maximum_capacity',
            'current_enrollment': 'current_enrollment',
            'total_students': 'total_students',
            'total_teachers': 'total_teachers',
            'total_staff': 'total_staff',
            'school_type': 'school_type',
            'established_year': 'established_year',
            'accreditation': 'accreditation',
            'language_of_instruction': 'language_of_instruction'
        }
        
        for csv_field, db_field in field_mapping.items():
            if csv_field in row_data and row_data[csv_field] is not None:
                value = row_data[csv_field]
                if isinstance(value, str):
                    value = value.strip()
                if value != "":  # Don't update with empty strings
                    update_data[db_field] = value
        
        return update_data

    def _prepare_create_data(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for creating a new tenant"""
        import uuid
        from datetime import datetime
        
        # Required fields with defaults
        create_data = {
            "id": uuid.uuid4(),
            "school_code": row_data.get("school_code"),
            "school_name": row_data.get("school_name", "New School"),
            "address": row_data.get("address", "Address Not Provided"),
            "phone": row_data.get("phone", "+1-555-0000"),
            "email": row_data.get("email", f"{row_data.get('school_code', 'school')}@example.com"),
            "principal_name": row_data.get("principal_name", "Principal Name Not Provided"),
            "annual_tuition": float(row_data.get("annual_tuition", 10000.0)),
            "registration_fee": float(row_data.get("registration_fee", 500.0)),
            "maximum_capacity": int(row_data.get("maximum_capacity", 1000)),
            "current_enrollment": int(row_data.get("current_enrollment", 0)),
            "total_students": int(row_data.get("total_students", 0)),
            "total_teachers": int(row_data.get("total_teachers", 0)),
            "total_staff": int(row_data.get("total_staff", 10)),
            "school_type": row_data.get("school_type", "K-12"),
            "grade_levels": row_data.get("grade_levels", ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]),
            "language_of_instruction": row_data.get("language_of_instruction", "English"),
            "established_year": int(row_data.get("established_year", 2020)) if row_data.get("established_year") else 2020,
            "accreditation": row_data.get("accreditation", "Not Specified"),
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        return create_data
    
    async def _update_operation_status(
        self,
        operation_id: str,
        status: str,
        progress: int,
        total_rows: int = None,
        processed_rows: int = None,
        errors: List[Dict] = None
    ):
        """Update operation status - handled by the router"""
        # This is handled by the router's operation_status_store
        pass
