# app/routers/chat_ai.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import httpx
from typing import Optional

router = APIRouter()

class AIRequest(BaseModel):
    prompt: str
    context: Optional[str] = None  # For educational context

class AIResponse(BaseModel):
    response_text: str

# Perplexity API configuration
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "sonar"  # Online model with web search capabilities - replaced deprecated llama-3.1-sonar-small-128k-online

async def call_perplexity(api_key: str, prompt: str, context: Optional[str] = None) -> str:
    """Call Perplexity API for AI responses"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Build system message for educational context
    system_message = "You are an AI assistant for EduAssist, an educational management platform. Help teachers, students, and administrators with platform guidance, educational content, and academic support. Be helpful, accurate, and educational."
    
    if context:
        system_message += f" Context: {context}"
    
    body = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(PERPLEXITY_API_URL, headers=headers, json=body)
    
    if r.status_code != 200:
        raise RuntimeError(f"Perplexity API failed: {r.status_code} - {r.text}")
    
    data = r.json()
    
    # Extract response text
    if "choices" in data and data["choices"]:
        return data["choices"][0].get("message", {}).get("content", "No response generated")
    
    return "No response generated"

@router.post("/ai_chat", response_model=AIResponse)
async def ai_chat(request: AIRequest):
    """AI Chat endpoint using Perplexity API"""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Perplexity API key not configured")
    
    try:
        generated_text = await call_perplexity(api_key, request.prompt, request.context)
        return AIResponse(response_text=generated_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")

@router.post("/ai_help", response_model=AIResponse)
async def ai_help(request: AIRequest):
    """AI Help for platform guidance"""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Perplexity API key not configured")
    
    # Add platform-specific context
    platform_context = """EduAssist Platform Features:
    - Grades & Assessments: Create tests, grade submissions, generate report cards
    - Student Management: View student profiles, track performance
    - Teacher Tools: Manage classes, create assignments, analytics
    - Admin Dashboard: School-wide reports, user management
    
    Available endpoints: /grades/, /students/, /teachers/, /classes/, /analytics/
    """
    
    try:
        generated_text = await call_perplexity(api_key, request.prompt, platform_context)
        return AIResponse(response_text=generated_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI help failed: {str(e)}")

@router.get("/ai_status")
async def ai_status():
    """Check AI service status"""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    return {
        "service": "Perplexity AI",
        "model": DEFAULT_MODEL,
        "api_configured": bool(api_key),
        "endpoints": ["/ai_chat", "/ai_help"]
    }
