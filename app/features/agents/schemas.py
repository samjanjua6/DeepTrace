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


class AgentMessageItem(BaseModel):
    id: str
    role: str  # USER or ASSISTANT
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    sequence_order: int
    created_at: datetime


class AskHistoryResponse(BaseModel):
    session_id: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    status: str = "active"
    messages: list[AgentMessageItem] = []



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


class CreditBriefingItem(BaseModel):
    page_number: int | None = None
    row_number: int | None = None
    title: str
    transaction_label: str | None = None
    expected_value: str | None = None
    actual_value: str | None = None
    discrepancy: str | None = None
    font_detected: str | None = None
    expected_font: str | None = None
    visual_cue: str | None = None
    summary_en: str
    summary_ur: str
    severity: str = "MEDIUM"
    rule_id: str | None = None
    evidence_id: str | None = None


class LeadInvestigatorAnalysisResponse(BaseModel):
    investigation_id: str
    overall_score: int
    risk_tier: str
    action_directive: str
    confidence_score: float
    anomalies_detected: int
    model_provider: str
    model_name: str
    english_summary: str
    urdu_summary: str
    narrative: str
    cross_signal_correlations: list[str] = []
    credit_briefing_items: list[CreditBriefingItem] = []
    evidence_citations: list[str] = []
    specialist_reports: dict = {}

