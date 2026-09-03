"""Agents router — /api/v1/investigations/{id}/ask + sessions."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.features.auth.dependencies import get_current_user
from app.features.investigations.dependencies import get_investigation
from app.features.agents import schemas, service

router = APIRouter()

@router.post("/{investigation_id}/ask", summary="Ask the Lead Investigator Agent a forensic question")
async def ask_agent(
    body: schemas.AskRequest,
    investigation=Depends(get_investigation),
    user=Depends(get_current_user),
):
    """
    Streams SSE chunks from the Lead Investigator Agent.
    The agent has access to the complete verified evidence manifest but is
    forbidden from introducing facts outside of it (zero-hallucination policy).
    """
    # TODO: if body.stream: return StreamingResponse(service.run_interactive_qa(...), media_type="text/event-stream")
    # TODO: else: return await service.run_interactive_qa(...)
    raise NotImplementedError

@router.get("/{investigation_id}/agents", response_model=list[schemas.AgentSessionResponse],
            summary="List all agent sessions for an investigation")
async def list_agent_sessions(investigation=Depends(get_investigation)):
    # TODO: service.get_agent_sessions(...)
    raise NotImplementedError
