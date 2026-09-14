"""Agents router — /api/v1/investigations/{id}/ask + sessions."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import Annotated
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.agents import schemas, service

router = APIRouter()

@router.post("/{investigation_id}/ask", summary="Ask the Lead Investigator Agent a forensic question")
async def ask_agent(
    body: schemas.AskRequest,
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """
    Streams SSE chunks from the Lead Investigator Agent (or returns JSON).
    The agent has access to the complete verified evidence manifest but is
    forbidden from introducing facts outside of it (zero-hallucination policy).
    """
    if db is None:
        from app.db.client import db as global_db
        db = global_db

    if body.stream:
        stream_gen = await service.run_interactive_qa(
            db, investigation.id, user.id, body.question, stream=True
        )
        return StreamingResponse(stream_gen, media_type="text/event-stream")
    else:
        return await service.run_interactive_qa(
            db, investigation.id, user.id, body.question, stream=False
        )

@router.get("/{investigation_id}/ask/history", response_model=schemas.AskHistoryResponse,
            summary="Get conversation history for interactive Q&A agent session")
async def get_interactive_qa_history(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    return await service.get_interactive_qa_history(db, investigation.id)

@router.get("/{investigation_id}/agents", response_model=list[schemas.AgentSessionResponse],
            summary="List all agent sessions for an investigation")
async def list_agent_sessions(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    return await service.get_agent_sessions(db, investigation.id)


@router.get(
    "/{investigation_id}/analysis",
    response_model=schemas.LeadInvestigatorAnalysisResponse,
    summary="Get Lead Investigator forensic analysis including bilingual English and Urdu credit briefings",
)
async def get_investigation_analysis(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    if db is None:
        from app.db.client import db as global_db
        db = global_db
    return await service.run_lead_investigator_analysis(db, investigation.id)

