"""
DeepTrace — Case Number Generator
Generates human-readable investigation case numbers: "DT-PK-YYYY-NNNNNN"
Uses the PostgreSQL sequence defined in migrations/001_extensions.sql.
"""

from app.db.client import db


async def generate_case_number() -> str:
    """
    Generate the next unique case number by calling the PostgreSQL sequence function.

    Returns:
        str: e.g. "DT-PK-2026-000412"
    """
    result = await db.query_raw("SELECT generate_case_number() AS case_number")
    return result[0]["case_number"]
