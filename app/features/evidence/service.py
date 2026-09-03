"""Evidence service. TODO: Implement."""
from prisma import Prisma

async def list_evidence(db: Prisma, investigation_id: str, severity: str | None = None) -> list:
    """List all evidence items for an investigation, optionally filtered by severity."""
    # TODO: join through documents to get evidence for all docs in investigation
    raise NotImplementedError

async def record_evidence_item(db: Prisma, document_id: str, pipeline_stage_id: str, data: dict) -> object:
    """Helper called by pipeline tasks to persist a new evidence finding."""
    # TODO: db.evidenceitem.create(...) + db.boundingbox.create_many(...)
    raise NotImplementedError
