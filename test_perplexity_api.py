#!/usr/bin/env python3
"""
Test Perplexity API connection
"""

import asyncio
import os
import requests
from dotenv import load_dotenv

load_dotenv()

async def test_perplexity_api():
    """Test direct Perplexity API call"""
    
    api_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not api_key:
        print("❌ PERPLEXITY_API_KEY not found in environment")
        return
    
    print(f"🔑 API Key found: {api_key[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [
            {
                "role": "user", 
                "content": "Generate 1 simple math question for grade 10. Return only JSON: [{\"question_text\": \"...\", \"answer\": \"...\"}]"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        print("🚀 Making API request...")
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ API Response: {content[:200]}...")
        else:
            print(f"❌ Error Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_perplexity_api())