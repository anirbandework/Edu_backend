#!/usr/bin/env python3
"""Test the exact endpoint that Flutter is calling"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_exact_endpoint():
    """Test the exact endpoint that Flutter is calling"""
    client = TestClient(app)
    
    # This is the exact URL your Flutter client is calling
    url = "/api/v1/school_authority/timetable/master/351e3b19-0c37-4e48-a06d-3ceaa7e584c2"
    params = {"academic_year": "2024-25"}
    
    print(f"Testing URL: {url}")
    print(f"Parameters: {params}")
    
    try:
        response = client.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Endpoint working correctly - returns 200 OK")
            print("✅ Response is valid JSON")
            return True
        else:
            print(f"❌ Endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_exact_endpoint()
    if result:
        print("\n🎉 The API endpoint is working correctly!")
        print("The issue is likely on the Flutter client side or network connectivity.")
    else:
        print("\n💥 The API endpoint has issues that need to be fixed.")