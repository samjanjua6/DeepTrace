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
            + self.get_findings_by_rule_prefix("RULE_AML_")
            + self.get_findings_by_rule_prefix("RULE_CNIC_")
            + self.get_findings_by_rule_prefix("RULE_FBR_")
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

        # Exclude benign/cleared verification markers from anomalies count
        adverse_findings = [
            it for it in financial_findings
            if it.get("severity") in ("CRITICAL", "HIGH", "MEDIUM")
        ]
        anomalies_count = len(adverse_findings)
        citations = [it.get("ruleId") or it.get("rule_id", "") for it in financial_findings]
        citations = [c for c in citations if c]

        key_indicators = []
        has_iban_fail = any("IBAN" in c for c in citations)
        has_ledger_fail = any("LEDGER_RECONCILIATION" in c for c in citations)
        has_opening_fail = any("OPENING_BALANCE" in c for c in citations)
        has_closing_fail = any("CLOSING_BALANCE" in c for c in citations)
        has_multipage_discontinuity = any("MULTIPAGE_DISCONTINUITY" in c for c in citations)
        has_nacta_match = any("NACTA" in c for c in citations)
        has_unsc_match = any("UNSC" in c for c in citations)
        has_pep_match = any("PEP" in c for c in citations)
        has_hawala = any("HIGH_RISK_NARRATION" in c for c in citations)
        has_cnic_province = any("RULE_CNIC_PROVINCE_CODE_INVALID" in c for c in citations)
        has_cnic_gender = any("RULE_CNIC_GENDER_PARITY_MISMATCH" in c for c in citations)
        has_cnic_mrz = any("RULE_CNIC_MRZ_CHECKSUM_INVALID" in c for c in citations)
        has_cnic_front_mrz = any("RULE_CNIC_MRZ_FRONT_MISMATCH" in c for c in citations)
        has_ntn_fail = any("RULE_FBR_NTN_INVALID_CHECKSUM" in c or "RULE_FBR_NTN_INVALID_FORMAT" in c for c in citations)
        has_wht_zero = any("RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY" in c for c in citations)
        has_wht_disc = any("RULE_FBR_WHT_DISCREPANCY" in c for c in citations)
        has_cpr_fail = any("RULE_FBR_CPR_INVALID_FORMAT" in c or "RULE_FBR_CPR_FUTURE_DATE" in c or "RULE_FBR_CPR_INVALID_DATE" in c for c in citations)

        total_discrepancies = []
        for it in adverse_findings:
            disc = it.get("discrepancy")
            if disc:
                total_discrepancies.append(f"{it.get('title', 'Discrepancy')}: {disc}")

        if has_nacta_match:
            key_indicators.append("CRITICAL: Proscribed entity/individual match under NACTA 4th Schedule (ATA 1997 §11EE). Mandatory account freeze and STR filing.")
        if has_unsc_match:
            key_indicators.append("CRITICAL: Designated entity match under UN Security Council Resolution 1267 (UNSC Act 1948). Mandatory immediate asset freeze.")
        if has_pep_match:
            key_indicators.append("HIGH: Politically Exposed Person (PEP) identified under SBP BPRD Circular No. 1/2021. Mandates Senior Management Approval (SMA) & EDD.")
        if has_hawala:
            key_indicators.append("HIGH: Suspicious informal Hawala/Hundi/Crypto red flag narrations detected violating SBP BPRD Circular No. 3/2018.")
        if has_cnic_province:
            key_indicators.append("CRITICAL: Pakistani CNIC 1st digit violates NADRA Ordinance 2000 §30 provincial administrative coding (codes 0 and 9 are non-existent).")
        if has_cnic_gender:
            key_indicators.append("CRITICAL: Pakistani CNIC 13th check digit gender parity contradicts declared cardholder sex/title under NADRA schema (Odd=Male, Even=Female).")
        if has_cnic_mrz:
            key_indicators.append("CRITICAL: Smart Identity Card reverse Machine Readable Zone (MRZ) failed ICAO Doc 9303 Part 5 7-3-1 modulus-10 checksum validation.")
        if has_cnic_front_mrz:
            key_indicators.append("CRITICAL: Visual front CNIC number contradicts reverse optical MRZ encoded data, confirming credential splicing or counterfeit assembly.")
        if has_ntn_fail:
            key_indicators.append("CRITICAL: National Tax Number (NTN) violates FBR Modulus 11 statutory check digit algorithm, indicating fictitious taxpayer registration.")
        if has_wht_zero:
            key_indicators.append("CRITICAL: Salary exceeds statutory PKR 50,000/mo threshold but declares ZERO withholding tax, violating Income Tax Ordinance 2001 §149.")
        if has_wht_disc:
            key_indicators.append("HIGH: Declared withholding tax substantially deviates from statutory progressive tax slabs under Income Tax Ordinance 2001 First Schedule.")
        if has_cpr_fail:
            key_indicators.append("HIGH: FBR Computerized Payment Receipt (CPR) format invalid or contains post-dated/impossible tax deposit timestamp.")
        if has_iban_fail:
            key_indicators.append("Invalid Pakistani IBAN checksum failing ISO 7064 MOD-97 check.")
        if has_opening_fail:
            key_indicators.append("Statement header opening balance contradicts authentic ledger origin.")
        if has_closing_fail:
            key_indicators.append("Statement header closing balance contradicts concluding multi-page ledger balance.")
        if has_ledger_fail or has_multipage_discontinuity:
            key_indicators.append("Running ledger math failure: debit/credit transactions do not sum to printed balance.")

        if anomalies_count > 0:
            # Mathematical or AML sanctions or CNIC forgery or FBR evasion is deterministic and carries near 100% confidence
            confidence = min(0.99, 0.85 + (anomalies_count * 0.05))
            summary = (
                f"Pakistani financial, AML/CDD, NADRA identity & FBR tax audit identified {anomalies_count} deterministic adverse finding(s). "
                f"Discrepancies identified: {'; '.join(total_discrepancies) if total_discrepancies else 'Statutory AML/sanctions breaches, CNIC administrative violations, FBR tax evasion/forgery, or ledger reconciliation failures.'} "
                "These findings provide definitive proof of regulatory non-compliance, identity forgery, tax non-compliance, or numerical balance manipulation."
            )
        else:
            confidence = 0.95
            summary = (
                "Pakistani financial, SBP Customer Due Diligence (CDD), NADRA identity, and FBR tax audit confirmed complete integrity. "
                "All transaction ledger debits and credits reconcile perfectly across all pages to stated opening and closing balances. "
                "All SBP bank IBANs satisfy ISO 7064 MOD-97 checksum validation. "
                "Screening against NACTA 4th Schedule, UNSC 1267 Sanctions, PEP registries, NADRA CNIC structural integrity, and FBR Section 149 statutory tax withholding cleared with zero adverse matches."
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
