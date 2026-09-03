"""
Investigations service — core forensic case lifecycle.
"""
from prisma import Prisma

from app.core.case_number import generate_case_number
from app.db.client import set_org_context


async def create_investigation(db: Prisma, org_id: str, user_id: str, data: dict) -> object:
    """Create a new investigation with auto-generated case number within tenant RLS context."""
    case_number = await generate_case_number()
    async with set_org_context(org_id) as tx:
        inv = await tx.investigation.create(
            data={
                "organizationId": org_id,
                "userId": user_id,
                "caseNumber": case_number,
                "title": data.get("title"),
                "description": data.get("description"),
                "clientReference": data.get("client_reference"),
                "priority": data.get("priority", 0),
            }
        )
        return inv


async def list_investigations(db: Prisma, org_id: str, filters: dict, page: int = 1, page_size: int = 20) -> list:
    """Return paginated list of investigations for an org within tenant RLS context."""
    async with set_org_context(org_id) as tx:
        where_clause: dict = {"organizationId": org_id, "deletedAt": None}
        if filters.get("status"):
            where_clause["status"] = filters["status"]
        if filters.get("priority") is not None:
            where_clause["priority"] = filters["priority"]

        items = await tx.investigation.find_many(
            where=where_clause,
            skip=(page - 1) * page_size,
            take=page_size,
            order={"createdAt": "desc"},
        )
        return items


async def update_investigation(db: Prisma, org_id: str, investigation_id: str, data: dict) -> object:
    """Update mutable fields on an investigation within tenant RLS context."""
    update_data = {}
    if data.get("title") is not None:
        update_data["title"] = data["title"]
    if data.get("description") is not None:
        update_data["description"] = data["description"]
    if data.get("priority") is not None:
        update_data["priority"] = data["priority"]
    if data.get("assigned_analyst_id") is not None:
        update_data["assignedAnalystId"] = data["assigned_analyst_id"]

    async with set_org_context(org_id) as tx:
        return await tx.investigation.update(
            where={"id": investigation_id},
            data=update_data,
        )


async def close_investigation(db: Prisma, org_id: str, investigation_id: str, notes: str | None = None) -> object:
    """Transition investigation to CLOSED status within tenant RLS context."""
    from datetime import datetime, timezone
    async with set_org_context(org_id) as tx:
        return await tx.investigation.update(
            where={"id": investigation_id},
            data={
                "status": "CLOSED",
                "closedAt": datetime.now(timezone.utc),
                "reviewNotes": notes,
            },
        )
