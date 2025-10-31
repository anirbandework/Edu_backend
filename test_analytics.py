#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, and_
from app.models.shared.tenant import Tenant
from app.core.config import settings

async def test_analytics():
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Test basic count
            print("Testing basic count...")
            total_count = await db.scalar(select(func.count(Tenant.id)).where(Tenant.is_deleted == False))
            print(f"Total tenants: {total_count}")
            
            # Test aggregation
            print("Testing aggregation...")
            result = await db.execute(select(
                func.count(Tenant.id).label('total'),
                func.sum(func.case((Tenant.is_active == True, 1), else_=0)).label('active'),
                func.coalesce(func.sum(Tenant.total_students), 0).label('students')
            ).where(Tenant.is_deleted == False))
            
            stats = result.first()
            print(f"Stats: total={stats.total}, active={stats.active}, students={stats.students}")
            
            print("Analytics queries work successfully!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analytics())