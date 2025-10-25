#!/usr/bin/env python3
"""Test the actual API endpoint"""

import asyncio
import httpx
import uvicorn
import threading
import time
from app.main import app

def start_server():
    """Start the server in a separate thread"""
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

async def test_endpoint():
    """Test the timetable endpoint"""
    try:
        # Wait for server to start
        await asyncio.sleep(2)
        
        async with httpx.AsyncClient() as client:
            # Test the endpoint that's failing
            url = "http://127.0.0.1:8001/api/v1/school_authority/timetable/master/351e3b19-0c37-4e48-a06d-3ceaa7e584c2"
            params = {"academic_year": "2024-25"}
            
            print(f"Testing: {url}")
            print(f"Params: {params}")
            
            response = await client.get(url, params=params)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ Endpoint working correctly")
                return True
            else:
                print("❌ Endpoint returned error")
                return False
                
    except Exception as e:
        print(f"Error testing endpoint: {e}")
        return False

async def main():
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Test the endpoint
    result = await test_endpoint()
    
    if result:
        print("API endpoint test passed")
    else:
        print("API endpoint test failed")

if __name__ == "__main__":
    asyncio.run(main())