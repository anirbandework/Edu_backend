"""
Test script to verify Aurora PostgreSQL connection
Location: EDU_BACKEND/test_aurora.py
"""
import asyncio
import asyncpg
import os
import sys
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_direct_aurora_connection():
    """Test direct asyncpg connection to Aurora"""
    try:
        logger.info("🔍 Testing direct Aurora PostgreSQL connection...")
        
        # Get DATABASE_URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL not found in environment variables")
            return False
            
        logger.info(f"📍 Database URL: {database_url[:50]}...")
        
        # Parse connection details from DATABASE_URL
        import re
        pattern = r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
        match = re.match(pattern, database_url)
        
        if not match:
            logger.error("❌ Invalid DATABASE_URL format")
            logger.info("Expected format: postgresql+asyncpg://user:pass@host:port/db")
            return False
            
        user, password, host, port, database = match.groups()
        
        logger.info(f"🔗 Connection details:")
        logger.info(f"   Host: {host}")
        logger.info(f"   Port: {port}")
        logger.info(f"   Database: {database}")
        logger.info(f"   User: {user}")
        
        # Test direct asyncpg connection with timeout
        logger.info("🔄 Attempting connection...")
        
        conn = await asyncio.wait_for(
            asyncpg.connect(
                user=user,
                password=password,
                database=database,
                host=host,
                port=int(port),
                timeout=30  # Connection timeout
            ),
            timeout=35  # Overall operation timeout
        )
        
        # Test basic query
        logger.info("✅ Connected! Testing basic query...")
        result = await conn.fetchval('SELECT 1')
        logger.info(f"🎯 Test query result: {result}")
        
        # Test more detailed query
        row = await conn.fetchrow('SELECT version(), NOW(), current_database()')
        logger.info(f"📊 Database info:")
        logger.info(f"   Version: {row['version'][:100]}...")
        logger.info(f"   Timestamp: {row['now']}")
        logger.info(f"   Current DB: {row['current_database']}")
        
        await conn.close()
        logger.info("✅ Connection test successful!")
        return True
        
    except asyncio.TimeoutError:
        logger.error("❌ Connection timeout - check network connectivity and AWS security groups")
        return False
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        logger.error(f"   Error type: {type(e).__name__}")
        return False

async def test_sqlalchemy_connection():
    """Test SQLAlchemy async connection"""
    try:
        logger.info("🔍 Testing SQLAlchemy async connection...")
        
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        database_url = os.getenv('DATABASE_URL')
        
        # Create engine with same config as app
        engine = create_async_engine(
            database_url,
            connect_args={
                "command_timeout": 30,
                "server_settings": {
                    "jit": "off",
                    "application_name": "test_connection"
                }
            }
        )
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            logger.info(f"✅ SQLAlchemy test successful: {row.test}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ SQLAlchemy test failed: {e}")
        return False

async def main():
    """Run all connection tests"""
    logger.info("🚀 Starting Aurora PostgreSQL connection tests...")
    logger.info("=" * 60)
    
    # Test 1: Direct asyncpg connection
    test1_success = await test_direct_aurora_connection()
    
    logger.info("=" * 60)
    
    # Test 2: SQLAlchemy connection
    test2_success = await test_sqlalchemy_connection()
    
    logger.info("=" * 60)
    
    # Summary
    if test1_success and test2_success:
        logger.info("🎉 All tests passed! Your Aurora connection is working.")
    elif test1_success:
        logger.info("⚠️  Direct connection works, but SQLAlchemy has issues.")
    else:
        logger.error("❌ Connection tests failed. Check your AWS configuration:")
        logger.error("   1. Aurora instance is running")
        logger.error("   2. Security group allows inbound port 5432")
        logger.error("   3. Aurora is publicly accessible")
        logger.error("   4. DATABASE_URL is correct")
        
    return test1_success and test2_success

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
