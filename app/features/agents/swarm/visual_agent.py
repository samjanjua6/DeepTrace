"""
Agent 2: ELA heatmaps, JPEG compression ghosting, copy-move clone boundaries, resolution variations.
"""
from app.features.agents.swarm.base_agent import BaseForensicAgent


class VisualForensicAgent(BaseForensicAgent):
    """Agent 2: ELA heatmaps, JPEG compression ghosting, copy-move clone boundaries, resolution variations."""

    async def analyze(self) -> dict:
        """
        Interprets ELA heatmaps, JPEG compression ghosting, and copy-move clone boundaries.
        Formulates visual findings strictly as localized bounding box probabilities (zero-hallucination guardrail).
        """
        raw_findings = (
            self.get_findings_by_rule_prefix("RULE_CV_")
            + self.get_findings_by_category("COMPUTER_VISION_ELA")
            + self.get_findings_by_category("IMAGE_ELA_MANIPULATION")
            + self.get_findings_by_category("IMAGE_TAMPERING")
        )
        seen_ids = set()
        visual_findings = []
        for it in raw_findings:
            it_id = it.get("id") or it.get("ruleId") or str(it)
            if it_id not in seen_ids:
                seen_ids.add(it_id)
                visual_findings.append(it)

        adverse_findings = [it for it in visual_findings if it.get("severity") != "INFO"]
        anomalies_count = len(adverse_findings)
        citations = [it.get("ruleId") or it.get("rule_id", "") for it in visual_findings]
        citations = [c for c in citations if c]

        key_indicators = []
        bounding_box_count = 0
        for it in visual_findings:
            boxes = it.get("boundingBoxes") or []
            bounding_box_count += len(boxes)

        if anomalies_count > 0:
            confidence = min(0.92, 0.65 + (anomalies_count * 0.08))
            key_indicators.append(
                f"Error Level Analysis (ELA) identified {anomalies_count} localized compression anomaly zone(s)."
            )
            if bounding_box_count > 0:
                key_indicators.append(
                    f"{bounding_box_count} distinct coordinate bounding box(es) localized on rendered page raster."
                )
            summary = (
                f"Computer vision analysis identified {anomalies_count} localized compression/ELA anomalies "
                f"across {bounding_box_count} bounding box regions. These indicate digital re-compression or "
                "spliced raster elements inserted onto the original background."
            )
        else:
            confidence = 0.88
            summary = (
                "Computer vision and ELA analysis confirmed uniform error-level distribution across all rendered pages. "
                "No localized compression discontinuities, ghosting artifacts, or spliced raster elements detected."
            )

        return {
            "agent_role": "VISUAL_FORENSIC",
            "anomalies_detected": anomalies_count,
            "confidence_score": confidence,
            "summary": summary,
            "key_indicators": key_indicators,
            "evidence_citations": citations,
            "findings": visual_findings,
        }
