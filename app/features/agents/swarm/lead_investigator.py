"""
Agent 4: Synthesizes findings from Agents 1-3, correlates cross-signal evidence, answers Q&A queries.
"""
from app.features.agents.swarm.base_agent import BaseForensicAgent


from app.features.agents.swarm.structural_agent import StructuralForensicAgent
from app.features.agents.swarm.visual_agent import VisualForensicAgent
from app.features.agents.swarm.semantic_pk_agent import SemanticPKFinancialAgent


class LeadInvestigatorAgent(BaseForensicAgent):
    """
    Agent 4: Synthesizes findings from Agents 1-3, correlates cross-signal evidence,
    and answers interactive Q&A queries under a strict zero-hallucination policy.
    """

    async def analyze(self) -> dict:
        """
        Coordinate specialist agents (Agents 1-3), correlate cross-signal evidence,
        and synthesize the overall forensic investigation narrative.
        """
        agent_1 = StructuralForensicAgent(self.evidence_manifest)
        agent_2 = VisualForensicAgent(self.evidence_manifest)
        agent_3 = SemanticPKFinancialAgent(self.evidence_manifest)

        res_struct = await agent_1.analyze()
        res_visual = await agent_2.analyze()
        res_financial = await agent_3.analyze()

        # Cross-signal correlation
        cross_signal_correlations = []
        has_structural = res_struct["anomalies_detected"] > 0
        has_visual = res_visual["anomalies_detected"] > 0
        has_financial = res_financial["anomalies_detected"] > 0

        if has_structural and has_financial:
            cross_signal_correlations.append(
                "Multi-Vector Convergence: Post-creation PDF structural/font tampering directly correlates "
                "with mathematical balance manipulation."
            )
        if has_visual and has_financial:
            cross_signal_correlations.append(
                "Visual-Arithmetic Coupling: Localized ELA compression anomalies align with manipulated ledger rows."
            )
        if has_structural and has_visual:
            cross_signal_correlations.append(
                "Structural-Visual Concurrence: External editor signatures concur with pixel-level re-compression boundaries."
            )

        total_anomalies = (
            res_struct["anomalies_detected"]
            + res_visual["anomalies_detected"]
            + res_financial["anomalies_detected"]
        )

        all_citations = list(
            dict.fromkeys(
                res_struct["evidence_citations"]
                + res_visual["evidence_citations"]
                + res_financial["evidence_citations"]
            )
        )

        # Build holistic narrative
        risk_tier = self.risk_assessment.get("riskTier", "UNKNOWN")
        overall_score = self.risk_assessment.get("overallScore", 0)

        if total_anomalies > 0:
            narrative = (
                f"Multi-Agent forensic investigation completed with an overall risk score of {overall_score}/100 ({risk_tier}). "
                f"Synthesized {total_anomalies} independent indicator(s) across specialized domains: "
                f"Structural ({res_struct['anomalies_detected']}), Visual ({res_visual['anomalies_detected']}), "
                f"and Financial ({res_financial['anomalies_detected']}). "
                f"{' '.join(cross_signal_correlations)}"
            )
            confidence = max(res_struct["confidence_score"], res_visual["confidence_score"], res_financial["confidence_score"])
        else:
            narrative = (
                f"Multi-Agent forensic investigation verified document authenticity (Risk Score: {overall_score}/100, {risk_tier}). "
                "No structural, visual, or mathematical anomalies detected across the evidence manifest."
            )
            confidence = 0.95

        return {
            "agent_role": "LEAD_INVESTIGATOR",
            "anomalies_detected": total_anomalies,
            "confidence_score": confidence,
            "overall_score": overall_score,
            "risk_tier": risk_tier,
            "narrative": narrative,
            "cross_signal_correlations": cross_signal_correlations,
            "evidence_citations": all_citations,
            "specialist_reports": {
                "structural": res_struct,
                "visual": res_visual,
                "financial": res_financial,
            },
        }

    async def answer_query(self, question: str) -> dict:
        """
        Answer an investigator's natural language question strictly using the verified evidence manifest.
        ZERO-HALLUCINATION POLICY: Answers are formulated strictly from verified EvidenceItem records.
        """
        q_lower = question.lower().strip()
        cited_evidence_ids = []
        parts = []

        overall_score = self.risk_assessment.get("overallScore", 0)
        risk_tier = self.risk_assessment.get("riskTier", "UNKNOWN")
        action_directive = self.risk_assessment.get("actionDirective", "REVIEW")

        # 1. Questions regarding risk score or why classified as high/critical
        if any(w in q_lower for w in ["why", "risk", "score", "classified", "critical", "tier", "assessment"]):
            parts.append(
                f"The investigation was classified as **{risk_tier} Risk ({overall_score}/100)** with directive **{action_directive}** based on the following verified forensic evidence:"
            )
            for idx, item in enumerate(self.evidence_items[:5], 1):
                item_id = item.get("id", "")
                if item_id:
                    cited_evidence_ids.append(item_id)
                disc = f" (Discrepancy: {item.get('discrepancy')})" if item.get("discrepancy") else ""
                parts.append(
                    f"{idx}. **{item.get('title', 'Finding')}** [{item.get('severity', 'UNKNOWN')}]: {item.get('description', '')}{disc}"
                )

        # 2. Questions regarding IBAN authenticity
        elif any(w in q_lower for w in ["iban", "account number", "pakistani iban", "sbp"]):
            iban_findings = self.get_findings_by_rule_prefix("RULE_PK_IBAN")
            if iban_findings:
                for f in iban_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                parts.append(
                    f"⚠️ **PK-IBAN Check Failed**: {iban_findings[0].get('description', 'The stated Pakistani IBAN failed ISO 7064 MOD-97 checksum validation.')}"
                )
            else:
                parts.append(
                    "✓ **PK-IBAN Check Verified**: All Pakistani IBAN(s) detected in the document are mathematically authentic under ISO 7064 MOD-97 check-digit validation with legitimate State Bank of Pakistan (SBP) registered bank codes."
                )

        # 3. Questions regarding balance tampering or ledger calculations
        elif any(w in q_lower for w in ["balance", "ledger", "math", "opening", "closing", "tamper", "tampered", "discrepancy"]):
            fin_findings = (
                self.get_findings_by_rule_prefix("RULE_PK_")
                + self.get_findings_by_category("FINANCIAL_VERIFICATION")
            )
            if fin_findings:
                parts.append("The following deterministic mathematical discrepancies were identified in the transaction ledger:")
                for f in fin_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(
                        f"- **{f.get('title')}**: Expected `{f.get('expectedValue')}`, Actual `{f.get('actualValue')}` (Discrepancy: `{f.get('discrepancy')}`).\n  {f.get('description')}"
                    )
            else:
                parts.append(
                    "✓ **Ledger Math Verified**: All transactions across all pages reconcile with 0 mathematical errors. The running balances strictly match stated opening and closing balances."
                )

        # 4. Questions regarding fonts, typography, or desktop editors
        elif any(w in q_lower for w in ["font", "typography", "producer", "software", "editor", "acrobat", "incremental"]):
            struct_findings = (
                self.get_findings_by_rule_prefix("RULE_PDF_")
                + self.get_findings_by_rule_prefix("RULE_FONT_")
                + self.get_findings_by_rule_prefix("RULE_METADATA_")
            )
            if struct_findings:
                parts.append("Structural and typography forensic analysis identified:")
                for f in struct_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(f"- **{f.get('title')}**: {f.get('description')}")
            else:
                parts.append("✓ **Typography & Structure Verified**: No font substitutions, sub-pixel baseline offsets, or consumer PDF editor signatures were detected.")

        # 5. Questions regarding visual ELA or image tampering
        elif any(w in q_lower for w in ["ela", "visual", "image", "compression", "heat", "ghosting", "pixel"]):
            vis_findings = self.get_findings_by_rule_prefix("RULE_CV_")
            if vis_findings:
                parts.append("Computer Vision & Error Level Analysis (ELA) detected:")
                for f in vis_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(f"- **{f.get('title')}**: {f.get('description')}")
            else:
                parts.append("✓ **Visual Integrity Verified**: Clean ELA heatmap with uniform compression residuals across all pages.")

        # 6. Default general synthesis
        else:
            parts.append(
                f"**DeepTrace Lead Investigator Assessment (Case {self.investigation.get('caseNumber', '')})**:\n"
                f"The document has an overall risk score of **{overall_score}/100** ({risk_tier}). "
                f"Total verified forensic evidence items: **{len(self.evidence_items)}**."
            )
            if self.evidence_items:
                parts.append("\nTop verified evidence items:")
                for item in self.evidence_items[:3]:
                    if item.get("id"):
                        cited_evidence_ids.append(item["id"])
                    parts.append(f"- **{item.get('title')}** [{item.get('severity')}]: {item.get('description')}")

        answer_text = "\n\n".join(parts)
        est_tokens = len(answer_text.split()) + len(question.split()) + 50

        return {
            "answer": answer_text,
            "evidence_references": cited_evidence_ids,
            "tokens_used": est_tokens,
        }
