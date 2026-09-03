"""
Agents service — multi-agent swarm orchestration and interactive Q&A.
TODO: Implement LangGraph agent orchestration.
"""
from prisma import Prisma


async def run_interactive_qa(db: Prisma, investigation_id: str, user_id: str,
                              question: str) -> object:
    """
    Dispatch an interactive Q&A query to the Lead Investigator Agent.
    The agent is constrained to the verified evidence manifest for this investigation
    (zero-hallucination policy from proposal §6).
    TODO: Implement LangGraph agent invocation.
    """
    raise NotImplementedError


async def get_agent_sessions(db: Prisma, investigation_id: str) -> list:
    """List all agent sessions (swarm + Q&A) for an investigation."""
    # TODO: db.agentsession.find_many(where={"investigationId": investigation_id})
    raise NotImplementedError
