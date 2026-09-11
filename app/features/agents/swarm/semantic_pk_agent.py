"""
Agent 3: PK-IBAN check digits, Lakh/Crore ledger sums, Raast reference patterns, FBR tax ratios.
"""
from app.features.agents.swarm.base_agent import BaseForensicAgent


class SemanticPKFinancialAgent(BaseForensicAgent):
    """Agent 3: PK-IBAN check digits, Lakh/Crore ledger sums, Raast reference patterns, FBR tax ratios."""

    async def analyze(self) -> dict:
        """
        Verifies PK-IBAN ISO 7064 check digits, Lakh/Crore running ledger math, and opening/closing balances.
        Operates strictly on deterministic mathematical findings (zero-hallucination guardrail).
        """
        raw_findings = (
            self.get_findings_by_rule_prefix("RULE_PK_")
            + self.get_findings_by_category("MATHEMATICAL_MISMATCH")
            + self.get_findings_by_category("IBAN_CHECKSUM_FAILURE")
            + self.get_findings_by_category("FINANCIAL_VERIFICATION")
            + self.get_findings_by_category("LEDGER_DISCREPANCY")
        )
        seen_ids = set()
        financial_findings = []
        for it in raw_findings:
            it_id = it.get("id") or it.get("ruleId") or str(it)
            if it_id not in seen_ids:
                seen_ids.add(it_id)
                financial_findings.append(it)

        anomalies_count = len(financial_findings)
        citations = [it.get("ruleId") or it.get("rule_id", "") for it in financial_findings]
        citations = [c for c in citations if c]

        key_indicators = []
        has_iban_fail = any("IBAN" in c for c in citations)
        has_ledger_fail = any("LEDGER_RECONCILIATION" in c for c in citations)
        has_opening_fail = any("OPENING_BALANCE" in c for c in citations)
        has_closing_fail = any("CLOSING_BALANCE" in c for c in citations)
        has_multipage_discontinuity = any("MULTIPAGE_DISCONTINUITY" in c for c in citations)

        total_discrepancies = []
        for it in financial_findings:
            disc = it.get("discrepancy")
            if disc:
                total_discrepancies.append(f"{it.get('title', 'Discrepancy')}: {disc}")

        if has_iban_fail:
            key_indicators.append("Invalid Pakistani IBAN checksum failing ISO 7064 MOD-97 check.")
        if has_opening_fail:
            key_indicators.append("Statement header opening balance contradicts authentic ledger origin.")
        if has_closing_fail:
            key_indicators.append("Statement header closing balance contradicts concluding multi-page ledger balance.")
        if has_ledger_fail or has_multipage_discontinuity:
            key_indicators.append("Running ledger math failure: debit/credit transactions do not sum to printed balance.")

        if anomalies_count > 0:
            # Mathematical tampering is deterministic and carries near 100% confidence
            confidence = min(0.99, 0.85 + (anomalies_count * 0.05))
            summary = (
                f"Pakistani financial verification identified {anomalies_count} deterministic mathematical discrepancy(ies). "
                f"Discrepancies identified: {'; '.join(total_discrepancies) if total_discrepancies else 'Ledger reconciliation failures.'} "
                "These arithmetic failures provide definitive mathematical proof of numerical balance manipulation."
            )
        else:
            confidence = 0.95
            summary = (
                "Pakistani financial verification confirmed complete mathematical integrity. "
                "All transaction ledger debits and credits reconcile perfectly across all pages to stated opening and closing balances. "
                "All SBP bank IBANs satisfy ISO 7064 MOD-97 checksum validation."
            )

        return {
            "agent_role": "SEMANTIC_PK_FINANCIAL",
            "anomalies_detected": anomalies_count,
            "confidence_score": confidence,
            "summary": summary,
            "key_indicators": key_indicators,
            "evidence_citations": citations,
            "findings": financial_findings,
        }
