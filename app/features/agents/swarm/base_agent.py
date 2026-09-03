"""
Base Agent — shared guardrails and evidence buffer interface.
All agents in the DeepTrace swarm inherit from this base.

ZERO-HALLUCINATION POLICY: Agents may only assert facts that are present in
the verified evidence manifest passed to them at invocation time.
"""
from abc import ABC, abstractmethod


class BaseForensicAgent(ABC):
    """Abstract base for all DeepTrace forensic agents."""

    def __init__(self, evidence_manifest: dict):
        """
        Args:
            evidence_manifest: The complete structured evidence collected so far.
                               Agents are constrained to this data only.
        """
        self.evidence_manifest = evidence_manifest

    @abstractmethod
    async def analyze(self) -> dict:
        """Run the agent and return structured findings."""
        ...

    def _assert_evidence_exists(self, evidence_key: str) -> None:
        """Guardrail: Raise if the agent tries to reference non-existent evidence."""
        if evidence_key not in self.evidence_manifest:
            raise ValueError(
                f"GUARDRAIL VIOLATION: Agent attempted to reference '{evidence_key}' "
                "which is not present in the verified evidence manifest."
            )
