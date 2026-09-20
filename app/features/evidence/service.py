"""
Evidence service — handles queries and persistence for forensic findings and visual overlays.
"""
from typing import Any

from app.config import get_settings
from app.core.storage import storage
from app.db.client import db, set_org_context

settings = get_settings()


from app.features.evidence import schemas

def _to_response(item) -> schemas.EvidenceItemResponse:
    resp = schemas.EvidenceItemResponse.model_validate(item)
    if resp.technical_details:
        td = resp.technical_details
        if resp.pattern is None and "pattern" in td:
            resp.pattern = td["pattern"]
        if resp.multiplier is None and "multiplier" in td:
            try:
                resp.multiplier = float(td["multiplier"])
            except (ValueError, TypeError):
                pass
        if resp.rule_version is None and "rule_version" in td:
            try:
                resp.rule_version = int(td["rule_version"])
            except (ValueError, TypeError):
                pass
        if not resp.endpoints and "endpoints" in td and isinstance(td["endpoints"], list):
            valid_endpoints = []
            for ep in td["endpoints"]:
                if isinstance(ep, dict) and "role" in ep and "page" in ep and "bbox" in ep:
                    valid_endpoints.append(schemas.EvidenceEndpointResponse(**ep))
            resp.endpoints = valid_endpoints

    for art in resp.artifacts:
        if art.storage_path:
            art.storage_url = storage.get_url(settings.s3_bucket_artifacts, art.storage_path)
    return resp


async def list_evidence(
    org_id: str,
    investigation_id: str,
    severity: str | None = None,
) -> list[schemas.EvidenceItemResponse]:
    """
    List all forensic evidence items for an investigation,
    including pixel-precise bounding boxes and visual artifacts.
    """
    async with set_org_context(org_id) as tx:
        docs = await tx.document.find_many(
            where={"investigationId": investigation_id},
        )
        doc_ids = [d.id for d in docs]
        if not doc_ids:
            return []

        where_clause: dict[str, Any] = {"documentId": {"in": doc_ids}}
        if severity:
            where_clause["severity"] = severity.upper()

        items = await tx.evidenceitem.find_many(
            where=where_clause,
            include={
                "boundingBoxes": True,
                "artifacts": True,
            },
            order={"createdAt": "asc"},
        )

        return [_to_response(item) for item in items]


async def get_evidence_item(
    org_id: str,
    evidence_id: str,
) -> schemas.EvidenceItemResponse | None:
    """Retrieve a single evidence item by ID with full relations."""
    async with set_org_context(org_id) as tx:
        item = await tx.evidenceitem.find_unique(
            where={"id": evidence_id},
            include={
                "boundingBoxes": True,
                "artifacts": True,
            },
        )
        if not item:
            return None

        return _to_response(item)
