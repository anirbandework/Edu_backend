#!/usr/bin/env python3
"""Emergency script to block quiz topics spam"""

import asyncio
import aiohttp
import time

async def block_endpoint():
    """Block the spamming endpoint temporarily"""
    print("🚨 BLOCKING QUIZ TOPICS ENDPOINT DUE TO SPAM")
    
    # This will trigger rate limiting
    async with aiohttp.ClientSession() as session:
        for i in range(10):
            try:
                async with session.get('http://localhost:8000/quiz/topics') as resp:
                    print(f"Request {i+1}: {resp.status}")
                    if resp.status == 429:
                        print("✅ Rate limiting activated!")
                        break
            except Exception as e:
                print(f"Error: {e}")
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(block_endpoint())