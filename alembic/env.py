# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import asyncio
import os
import sys

# Add your app directory to sys.path so we can import properly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import your base and ALL model classes
from app.models.base import Base
from app.models.shared.tenant import Tenant
from app.models.tenant_specific.school_authority import SchoolAuthority
from app.models.tenant_specific.teacher import Teacher
from app.models.tenant_specific.student import Student
from app.models.tenant_specific.class_model import ClassModel
from app.models.tenant_specific.enrollment import Enrollment

# NEW: Import FIXED notification models (no more metadata conflict)
from app.models.tenant_specific.notification import (
    Notification,
    NotificationRecipient,
    NotificationTemplate,
    NotificationDeliveryLog,
    NotificationPreference,
    NotificationGroup,
    NotificationSchedule,
    NotificationBatch
)

from app.models.tenant_specific.attendance import (
    Attendance,
    AttendanceSummary,
    AttendancePolicy,
    AttendanceReport,
    AttendanceAlert
)

from app.models.tenant_specific.timetable import (
    MasterTimetable,
    Period,
    ClassTimetable,
    TeacherTimetable,
    Subject,
    ScheduleEntry,
    TimetableConflict,
    TimetableTemplate,
    TimetableAuditLog
)


config = context.config

# Get the database URL from env or .ini
config.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL', config.get_main_option('sqlalchemy.url')))

# Setup logging config from ini file
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url, 
        target_metadata=target_metadata, 
        literal_binds=True, 
        dialect_opts={'paramstyle': 'named'}
    )
    with context.begin_transaction():
        context.run_migrations()

def do_sync_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def do_async_migrations(connection):
    await connection.run_sync(do_sync_migrations)

def run_migrations_online():
    connectable = create_async_engine(
        config.get_main_option('sqlalchemy.url'),
        poolclass=pool.NullPool,
        future=True,
    )
    
    async def run_async():
        async with connectable.connect() as connection:
            await do_async_migrations(connection)
        await connectable.dispose()

    asyncio.run(run_async())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
