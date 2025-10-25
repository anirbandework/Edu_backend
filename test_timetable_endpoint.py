#!/usr/bin/env python3
"""Test script for timetable endpoint"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.services.timetable_service import TimetableService
from uuid import UUID

async def test_timetable_endpoint():
    """Test the timetable endpoint functionality"""
    try:
        # Get database session
        async for db in get_db():
            service = TimetableService(db)
            
            # Test the get_multi method with filters
            tenant_id = UUID("351e3b19-0c37-4e48-a06d-3ceaa7e584c2")
            academic_year = "2024-25"
            
            print(f"Testing timetable service with tenant_id: {tenant_id}, academic_year: {academic_year}")
            
            # This should match what the router is doing
            filters = {"tenant_id": tenant_id, "is_deleted": False}
            if academic_year:
                filters["academic_year"] = academic_year
            
            timetables = await service.get_multi(**filters)
            
            print(f"Found {len(timetables)} timetables")
            for tt in timetables:
                print(f"- {tt.timetable_name} ({tt.academic_year})")
            
            return True
            
    except Exception as e:
        print(f"Error testing timetable endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_timetable_endpoint())
    if result:
        print("Test completed successfully")
    else:
        print("Test failed")