"""
DeepTrace — Global FastAPI Dependencies
Shared across multiple features. Feature-specific dependencies live in
each feature`s own dependencies.py.
"""

from typing import Annotated

from fastapi import Depends
from prisma import Prisma

from app.config import Settings, get_settings
from app.db.client import get_db_dep

# Convenience type aliases for Depends injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Prisma, Depends(get_db_dep)]
