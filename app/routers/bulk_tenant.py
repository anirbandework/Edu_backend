# app/routers/bulk_tenant.py
import uuid
from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import io

from ..core.database import get_db
from ..services.bulk_tenant_service import BulkTenantService
from ..services.csv_processor import CSVProcessor
from ..schemas.bulk_schemas import BulkUpdateResult, BulkOperationStatus

router = APIRouter(prefix="/api/v1/tenants/bulk", tags=["Bulk Tenant Operations"])

# In-memory store for operation status (use Redis in production)
operation_status_store: Dict[str, BulkOperationStatus] = {}

@router.post("/update-csv", response_model=Dict)
async def bulk_update_tenants_from_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload CSV file for bulk tenant UPDATES. Processing happens in background.
    Updates existing tenants only - use /create-csv for new tenants.
    Returns operation ID for status tracking.
    """
    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Generate operation ID
    operation_id = str(uuid.uuid4())
    
    # Initialize operation status
    operation_status_store[operation_id] = BulkOperationStatus(
        operation_id=operation_id,
        status="processing",
        progress_percentage=0,
        created_at=datetime.now()
    )
    
    # Process CSV and validate data
    try:
        valid_rows, validation_errors = await CSVProcessor.process_tenant_csv(file)
        
        if not valid_rows:
            operation_status_store[operation_id].status = "failed"
            operation_status_store[operation_id].errors = validation_errors
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "No valid rows found in CSV",
                    "validation_errors": validation_errors
                }
            )
        
        # Update status with total rows
        operation_status_store[operation_id].total_rows = len(valid_rows)
        
        # Add background task for processing
        background_tasks.add_task(
            process_bulk_update_task,
            valid_rows,
            operation_id,
            validation_errors
        )
        
        return {
            "message": "CSV uploaded successfully. Updating existing tenants in background.",
            "operation_type": "UPDATE",
            "operation_id": operation_id,
            "total_rows": len(valid_rows),
            "validation_errors_count": len(validation_errors),
            "validation_errors": validation_errors[:10] if validation_errors else []
        }
        
    except ValueError as e:
        operation_status_store[operation_id].status = "failed"
        operation_status_store[operation_id].errors = [{"error": str(e)}]
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-csv", response_model=Dict)
async def bulk_create_tenants_from_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload CSV file for bulk tenant CREATION. Processing happens in background.
    Creates new tenants only - use /upload-csv for updating existing ones.
    Returns operation ID for status tracking.
    """
    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Generate operation ID
    operation_id = str(uuid.uuid4())
    
    # Initialize operation status
    operation_status_store[operation_id] = BulkOperationStatus(
        operation_id=operation_id,
        status="processing",
        progress_percentage=0,
        created_at=datetime.now()
    )
    
    # Process CSV and validate data
    try:
        valid_rows, validation_errors = await CSVProcessor.process_tenant_csv(file)
        
        if not valid_rows:
            operation_status_store[operation_id].status = "failed"
            operation_status_store[operation_id].errors = validation_errors
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "No valid rows found in CSV",
                    "validation_errors": validation_errors
                }
            )
        
        # Update status with total rows
        operation_status_store[operation_id].total_rows = len(valid_rows)
        
        # Add background task for processing
        background_tasks.add_task(
            process_bulk_create_task,
            valid_rows,
            operation_id,
            validation_errors
        )
        
        return {
            "message": "CSV uploaded successfully. Creating new tenants in background.",
            "operation_type": "CREATE",
            "operation_id": operation_id,
            "total_rows": len(valid_rows),
            "validation_errors_count": len(validation_errors),
            "validation_errors": validation_errors[:10] if validation_errors else []
        }
        
    except ValueError as e:
        operation_status_store[operation_id].status = "failed"
        operation_status_store[operation_id].errors = [{"error": str(e)}]
        raise HTTPException(status_code=400, detail=str(e))

async def process_bulk_update_task(
    valid_rows: List[Dict],
    operation_id: str,
    validation_errors: List[Dict]
):
    """Background task for processing bulk updates"""
    try:
        # Create new database session for background task
        from ..core.database import AsyncBackgroundSessionLocal
        async with AsyncBackgroundSessionLocal() as db:
            bulk_service = BulkTenantService(db)
            
            # Perform bulk update
            result = await bulk_service.bulk_update_tenants_raw_sql(
                valid_rows, 
                operation_id
            )
            
            # Update final status
            operation_status_store[operation_id].status = result.get("status", "completed")
            operation_status_store[operation_id].progress_percentage = 100
            operation_status_store[operation_id].processed_rows = result["successful_updates"] + result["failed_updates"]
            operation_status_store[operation_id].successful_updates = result["successful_updates"]
            operation_status_store[operation_id].failed_updates = result["failed_updates"]
            operation_status_store[operation_id].processing_time_seconds = result["processing_time_seconds"]
            operation_status_store[operation_id].completed_at = datetime.now()
            operation_status_store[operation_id].errors = validation_errors + result["errors"]
            
    except Exception as e:
        operation_status_store[operation_id].status = "failed"
        operation_status_store[operation_id].errors = [{"error": f"Processing failed: {str(e)}"}]
        operation_status_store[operation_id].completed_at = datetime.now()

async def process_bulk_create_task(
    valid_rows: List[Dict],
    operation_id: str,
    validation_errors: List[Dict]
):
    """Background task for processing bulk creates"""
    try:
        # Create new database session for background task
        from ..core.database import AsyncBackgroundSessionLocal
        async with AsyncBackgroundSessionLocal() as db:
            bulk_service = BulkTenantService(db)
            
            # Perform bulk create
            result = await bulk_service.bulk_create_tenants(
                valid_rows, 
                operation_id
            )
            
            # Update final status
            operation_status_store[operation_id].status = result.get("status", "completed")
            operation_status_store[operation_id].progress_percentage = 100
            operation_status_store[operation_id].processed_rows = result["successful_creates"] + result["failed_creates"]
            operation_status_store[operation_id].successful_updates = result["successful_creates"]  # Reuse field name
            operation_status_store[operation_id].failed_updates = result["failed_creates"]
            operation_status_store[operation_id].processing_time_seconds = result["processing_time_seconds"]
            operation_status_store[operation_id].completed_at = datetime.now()
            operation_status_store[operation_id].errors = validation_errors + result["errors"]
            
    except Exception as e:
        operation_status_store[operation_id].status = "failed"
        operation_status_store[operation_id].errors = [{"error": f"Processing failed: {str(e)}"}]
        operation_status_store[operation_id].completed_at = datetime.now()

@router.get("/status/{operation_id}", response_model=BulkOperationStatus)
async def get_bulk_operation_status(operation_id: str):
    """Get status of bulk operation"""
    if operation_id not in operation_status_store:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    return operation_status_store[operation_id]

@router.get("/template/download")
async def download_csv_template():
    """Download CSV template for bulk tenant operations"""
    template_content = CSVProcessor.generate_csv_template()
    
    return StreamingResponse(
        io.StringIO(template_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tenant_bulk_template.csv"}
    )

@router.post("/validate-csv", response_model=Dict)
async def validate_csv_only(file: UploadFile = File(...)):
    """Validate CSV without processing - for preview purposes"""
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        valid_rows, validation_errors = await CSVProcessor.process_tenant_csv(file)
        
        return {
            "is_valid": len(validation_errors) == 0,
            "total_rows": len(valid_rows) + len(validation_errors),
            "valid_rows_count": len(valid_rows),
            "invalid_rows_count": len(validation_errors),
            "validation_errors": validation_errors[:20],  # First 20 errors
            "sample_valid_data": valid_rows[:5] if valid_rows else []  # First 5 valid rows
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/operations/list")
async def list_bulk_operations():
    """List all bulk operations with their status"""
    operations = []
    for operation_id, status in operation_status_store.items():
        operations.append({
            "operation_id": operation_id,
            "status": status.status,
            "created_at": status.created_at,
            "completed_at": status.completed_at,
            "total_rows": status.total_rows,
            "processed_rows": status.processed_rows
        })
    
    return {
        "operations": operations,
        "total_operations": len(operations)
    }

@router.delete("/operations/{operation_id}")
async def delete_operation_status(operation_id: str):
    """Delete operation status from memory"""
    if operation_id not in operation_status_store:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    del operation_status_store[operation_id]
    return {"message": "Operation status deleted successfully"}
