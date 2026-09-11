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
        self.evidence_manifest = evidence_manifest or {}
        self.evidence_items: list[dict] = self.evidence_manifest.get("evidence_items", [])
        self.risk_assessment: dict = self.evidence_manifest.get("risk_assessment", {})
        self.documents: list[dict] = self.evidence_manifest.get("documents", [])
        self.investigation: dict = self.evidence_manifest.get("investigation", {})

        # Build lookup indices
        self._by_rule_id: dict[str, list[dict]] = {}
        self._by_id: dict[str, dict] = {}
        self._by_category: dict[str, list[dict]] = {}
        for it in self.evidence_items:
            rid = it.get("ruleId") or it.get("rule_id", "")
            item_id = it.get("id", "")
            cat = it.get("category", "")
            if rid:
                self._by_rule_id.setdefault(rid, []).append(it)
            if item_id:
                self._by_id[item_id] = it
            if cat:
                self._by_category.setdefault(cat, []).append(it)

    @abstractmethod
    async def analyze(self) -> dict:
        """Run the agent and return structured findings."""
        ...

    def get_findings_by_rule_prefix(self, prefix: str) -> list[dict]:
        """Find all evidence items whose rule ID starts with a prefix."""
        res = []
        for rid, items in self._by_rule_id.items():
            if rid.startswith(prefix):
                res.extend(items)
        return res

    def get_findings_by_category(self, category: str) -> list[dict]:
        """Find all evidence items belonging to a category."""
        return self._by_category.get(category, [])

    def _assert_evidence_exists(self, evidence_key: str) -> None:
        """Guardrail: Raise if the agent tries to reference non-existent evidence."""
        if (
            evidence_key not in self.evidence_manifest
            and evidence_key not in self._by_rule_id
            and evidence_key not in self._by_id
        ):
            raise ValueError(
                f"GUARDRAIL VIOLATION: Agent attempted to reference '{evidence_key}' "
                "which is not present in the verified evidence manifest."
            )
