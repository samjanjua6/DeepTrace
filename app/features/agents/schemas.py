"""Agents schemas."""
from datetime import datetime
from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    stream: bool = True  # If True, response is SSE stream


class AskResponse(BaseModel):
    answer: str
    agent_session_id: str
    evidence_references: list[str] = []  # EvidenceItem IDs cited in the answer
    tokens_used: int


class AgentSessionResponse(BaseModel):
    id: str
    agent_role: str
    model_provider: str | None
    model_name: str | None
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    status: str
    started_at: datetime
    completed_at: datetime | None
