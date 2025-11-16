# app/models/__init__.py
"""Import all models here, if needed for Alembic migration."""
from .base import Base


# app/models/__init__.py
from .shared.tenant import Tenant
from .tenant_specific.school_authority import SchoolAuthority

# This ensures both models are loaded when importing models
