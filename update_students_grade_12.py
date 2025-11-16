#!/usr/bin/env python3
"""
Script to update all students to grade level 12
"""
import asyncio
import httpx
import json

# Student data from the API response
STUDENTS = [
    {"id": "65bee12c-a64d-46ff-9f51-7c1b80832a1a", "student_id": "stu-21", "name": "Riya Verma"},
    {"id": "0fab6fa1-fae4-424a-8839-41d8ae7d5f3b", "student_id": "stuvghmtbkjhg1", "name": "Aarav Sharma"},
    {"id": "1edc4ae9-e2e8-4af8-a3c8-1b51ec840f02", "student_id": "suhvfbhv", "name": "Aarav Sharma"},
    {"id": "2bd54dbb-079a-4015-a7de-5ad985380dc3", "student_id": "stu-2004", "name": "Dev Patel"},
    {"id": "a7d0ed91-7909-44fb-9070-f64962d40482", "student_id": "s", "name": "Aarav Sharma"},
    {"id": "6336762a-85d9-4a1b-8122-43be7f391fb1", "student_id": "83o786w", "name": "Aarav Sharma"},
    {"id": "0ababdf2-e541-4c0d-a2e9-e5944b2c9ae7", "student_id": "STU025", "name": "Emma Rodriguez"},
    {"id": "3f954f27-5ad6-4056-8b8c-adf0237e21d2", "student_id": "stu-2001", "name": "Riya Verma"},
    {"id": "95b76e3e-6309-4bfa-a53b-b2708a9feead", "student_id": "poinkkl", "name": "Riya Verma"}
]

TENANT_ID = "351e3b19-0c37-4e48-a06d-3ceaa7e584c2"
BASE_URL = "http://localhost:8000"  # Update this to your actual API URL

async def update_students_to_grade_12():
    """Update all students to grade level 12"""
    
    # Prepare grade updates using student UUIDs
    grade_updates = [
        {"student_uuid": student["id"], "new_grade": 12}
        for student in STUDENTS
    ]
    
    payload = {
        "tenant_id": TENANT_ID,
        "grade_updates": grade_updates
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/school_authority/students/bulk/update-grades",
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Successfully updated students to grade 12!")
                print(f"Updated students: {result.get('updated_students', 0)}")
                print(f"Total requests: {result.get('total_requests', 0)}")
                return result
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            return None

if __name__ == "__main__":
    print("Updating students to grade level 12...")
    print(f"Total students to update: {len(STUDENTS)}")
    print(f"Tenant ID: {TENANT_ID}")
    
    result = asyncio.run(update_students_to_grade_12())
    
    if result:
        print("\n🎉 Update completed successfully!")
    else:
        print("\n💥 Update failed!")