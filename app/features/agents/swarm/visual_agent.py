"""
Agent 2: ELA heatmaps, JPEG compression ghosting, copy-move clone boundaries, resolution variations.
"""
from app.features.agents.swarm.base_agent import BaseForensicAgent


class VisualForensicAgent(BaseForensicAgent):
    """Agent 2: ELA heatmaps, JPEG compression ghosting, copy-move clone boundaries, resolution variations."""

    async def analyze(self) -> dict:
        """
        TODO: Implement LangGraph node logic.
        - Access only evidence from self.evidence_manifest
        - Return structured findings dict
        - Do NOT hallucinate facts outside the manifest
        """
        raise NotImplementedError
