#!/bin/bash

# Development startup script
source venv/bin/activate

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://eduassist_admin:EduAssist2024!Dev@eduassist-postgres-dev.cvks46m00t2t.eu-north-1.rds.amazonaws.com:5432/eduassist"
export REDIS_URL="redis://eduassist-valkey-dev.serverless.eun1.cache.amazonaws.com:6379"
export JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-production"
export PERPLEXITY_API_KEY="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"
export PORT=8000

# Start the application with gunicorn
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000