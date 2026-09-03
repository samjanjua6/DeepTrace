"""
DeepTrace — Prisma Client Singleton
Async context-managed Prisma client for use with FastAPI lifespan.

Usage in FastAPI:
    from app.db.client import db

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await db.connect()
        yield
        await db.disconnect()

    app = FastAPI(lifespan=lifespan)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from prisma import Prisma

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton Prisma client
# ---------------------------------------------------------------------------

db = Prisma()


async def connect() -> None:
    """Connect the Prisma client to the database.

    Call this once during FastAPI lifespan startup.
    """
    if not db.is_connected():
        logger.info("Connecting Prisma client to PostgreSQL...")
        await db.connect()
        logger.info("Prisma client connected.")


async def disconnect() -> None:
    """Disconnect the Prisma client.

    Call this once during FastAPI lifespan shutdown.
    """
    if db.is_connected():
        logger.info("Disconnecting Prisma client...")
        await db.disconnect()
        logger.info("Prisma client disconnected.")


@asynccontextmanager
async def get_db() -> AsyncGenerator[Prisma, None]:
    """Async context manager for route-level dependency injection.

    Can also be used as a FastAPI dependency via Depends().

    Example:
        async def my_route(db: Prisma = Depends(get_db_dep)):
            investigations = await db.investigation.find_many()
    """
    if not db.is_connected():
        await connect()
    yield db


async def get_db_dep() -> AsyncGenerator[Prisma, None]:
    """FastAPI dependency — yields the connected Prisma singleton."""
    async with get_db() as client:
        yield client


import re

# Strict validation pattern for CUID, UUID, or alphanumeric tenant IDs
_ORG_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


@asynccontextmanager
async def set_org_context(org_id: str) -> AsyncGenerator[Prisma, None]:
    """Set the PostgreSQL session variable used by Row-Level Security policies.

    Every tenant-scoped query should be wrapped in this context manager to
    activate RLS isolation:

        async with set_org_context(current_user.organization_id) as tx:
            results = await tx.investigation.find_many()

    The variable `app.current_org_id` is read by all RLS policies on
    tenant-scoped tables (see migrations/001_extensions.sql).

    Security:
        - Validates org_id against a strict alphanumeric regex to prevent injection
        - Uses parameterized set_config() to prevent SQL injection attacks
    """
    if not isinstance(org_id, str) or not _ORG_ID_REGEX.match(org_id):
        raise ValueError(f"Invalid organization ID format for RLS context: {org_id!r}")

    async with db.tx() as tx:
        await tx.execute_raw(
            "SELECT set_config('app.current_org_id', $1, true);",
            org_id,
        )
        yield tx


__all__ = ["db", "connect", "disconnect", "get_db", "get_db_dep", "set_org_context"]
