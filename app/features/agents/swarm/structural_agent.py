"""
Agent 1: PDF objects, metadata revisions, font descriptors, creation software fingerprints.
"""
from app.features.agents.swarm.base_agent import BaseForensicAgent


class StructuralForensicAgent(BaseForensicAgent):
    """Agent 1: PDF objects, metadata revisions, font descriptors, creation software fingerprints."""

    async def analyze(self) -> dict:
        """
        Evaluate PDF object streams, incremental revisions, producer signatures, and font typography.
        Strictly bound to verified evidence items (zero-hallucination policy).
        """
        raw_findings = (
            self.get_findings_by_rule_prefix("RULE_PDF_")
            + self.get_findings_by_rule_prefix("RULE_METADATA_")
            + self.get_findings_by_rule_prefix("RULE_FONT_")
            + self.get_findings_by_category("PDF_OBJECT_ANOMALY")
            + self.get_findings_by_category("METADATA_TIMESTAMP_MISMATCH")
            + self.get_findings_by_category("FONT_BASELINE_INCONSISTENCY")
        )
        seen_ids = set()
        structural_findings = []
        for it in raw_findings:
            it_id = it.get("id") or it.get("ruleId") or str(it)
            if it_id not in seen_ids:
                seen_ids.add(it_id)
                structural_findings.append(it)

        anomalies_count = len(structural_findings)
        citations = [it.get("ruleId") or it.get("rule_id", "") for it in structural_findings]
        citations = [c for c in citations if c]

        key_indicators = []
        has_incremental_save = any("INCREMENTAL_SAVE" in c for c in citations)
        has_producer_tamper = any("PRODUCER" in c for c in citations)
        has_timestamp_divergence = any("TIMESTAMP" in c for c in citations)
        has_font_jitter = any("FONT" in c for c in citations)

        if has_incremental_save:
            key_indicators.append("Post-creation incremental revision / trailer update detected.")
        if has_producer_tamper:
            key_indicators.append("Consumer/desktop PDF editor software signature identified.")
        if has_timestamp_divergence:
            key_indicators.append("Divergence between internal PDF metadata creation and modification dates.")
        if has_font_jitter:
            key_indicators.append("Sub-pixel font baseline offset or typography substitution detected.")

        if anomalies_count > 0:
            confidence = min(0.95, 0.60 + (anomalies_count * 0.10))
            summary = (
                f"Structural forensic analysis identified {anomalies_count} anomalous byte-level indicator(s). "
                f"Evidence indicates the document was modified post-generation using external editing tools. "
                f"Key signatures: {'; '.join(key_indicators) if key_indicators else 'Document stream irregularities.'}"
            )
        else:
            confidence = 0.90
            summary = (
                "Structural forensic analysis verified clean, authentic PDF object stream integrity. "
                "No incremental saves, producer signatures, timestamp divergences, or font baseline offsets detected."
            )

        return {
            "agent_role": "STRUCTURAL_FORENSIC",
            "anomalies_detected": anomalies_count,
            "confidence_score": confidence,
            "summary": summary,
            "key_indicators": key_indicators,
            "evidence_citations": citations,
            "findings": structural_findings,
        }
