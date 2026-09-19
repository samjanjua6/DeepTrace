"use client";

import React from "react";
import { CustodyEvent, EvidenceItem } from "@/lib/types/forensics";

interface PipelineAuditChecklistProps {
  getStageStatus: (stageType: string) => string;
  custodyEvents: CustodyEvent[];
  evidence: EvidenceItem[];
  isFinancial: boolean;
  isIdentity: boolean;
  isTaxOrSalary: boolean;
  riskScore: number;
}

export function PipelineAuditChecklist({
  getStageStatus,
  custodyEvents,
  evidence,
  isFinancial,
  isIdentity,
  isTaxOrSalary,
  riskScore,
}: PipelineAuditChecklistProps) {
  return (
    <div className="bg-paper-1 border border-rule p-4 font-mono text-xs">
      <span className="font-semibold text-ink-900 uppercase tracking-wider block mb-2 text-[10px]">
        § 04 / 8-STAGE FORENSIC PIPELINE EXECUTION AUDIT
      </span>
      <div className="space-y-1.5 text-[11px]">
        {/* 1. Custody Lock & RFC 3161 Seal */}
        <div className="flex justify-between items-center font-semibold">
          <span>1. Custody Fingerprint & RFC 3161 TSA Lock</span>
          {(() => {
            const st = getStageStatus("CUSTODY_LOCK");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● SEALING...
                </span>
              );
            if (st === "FAILED")
              return <span className="text-forensic-red">✕ FAILED</span>;
            const hasRfcSeal = custodyEvents.some(
              (e) =>
                e.metadata?.rfc3161?.status === "SEALED" ||
                e.eventType === "CUSTODY_SEAL_RFC3161"
            );
            return (
              <span className="text-forensic-green font-bold">
                {hasRfcSeal
                  ? "✓ RFC 3161 SEALED (PECA 2016)"
                  : "✓ VERIFIED (ETO 2002)"}
              </span>
            );
          })()}
        </div>

        {/* 2. PDF Structure & Digital Signatures */}
        <div className="flex justify-between items-center font-semibold">
          <span>2. Structure, Incremental %%EOF & ETO 2002 Signatures</span>
          {(() => {
            const st = getStageStatus("PDF_STRUCTURE");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● PARSING...
                </span>
              );
            if (st === "FAILED")
              return <span className="text-forensic-red">✕ FAILED</span>;
            const hasSigInvalid = evidence.some(
              (e) =>
                (e.ruleId || "").includes("SIGNATURE_INVALIDATED") ||
                (e.ruleId || "").includes("SIGNATURE_POST_SIGNING")
            );
            const hasSigValid = evidence.some((e) =>
              (e.ruleId || "").includes("SIGNATURE_VALID")
            );
            const hasPdfAnom = evidence.some(
              (e) =>
                (e.ruleId || "").includes("PDF") ||
                (e.ruleId || "").includes("METADATA")
            );
            if (hasSigInvalid) {
              return (
                <span className="text-forensic-red font-bold">
                  ✕ SIGNATURE INVALIDATED (ETO 2002 §29)
                </span>
              );
            }
            if (hasSigValid) {
              return (
                <span className="text-forensic-green font-bold">
                  ✓ PKI SIGNATURE VERIFIED (ETO 2002 §29)
                </span>
              );
            }
            return (
              <span
                className={
                  hasPdfAnom ? "text-forensic-amber" : "text-forensic-green"
                }
              >
                {hasPdfAnom
                  ? "▲ REVISIONS / SKEW FLAGGED"
                  : "✓ CLEAN SINGLE REVISION"}
              </span>
            );
          })()}
        </div>

        {/* 3. Font & Baseline */}
        <div className="flex justify-between items-center font-semibold">
          <span>3. Sub-Pixel Baseline Typography</span>
          {(() => {
            const st = getStageStatus("FONT_GLYPH_ANALYSIS");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● MEASURING...
                </span>
              );
            if (st === "FAILED")
              return <span className="text-forensic-red">✕ FAILED</span>;
            const hasFontAnom = evidence.some(
              (e) => (e.ruleId || "").includes("FONT") && e.severity !== "INFO"
            );
            return (
              <span
                className={
                  hasFontAnom ? "text-forensic-red" : "text-forensic-green"
                }
              >
                {hasFontAnom
                  ? "✕ BASELINE JITTER DETECTED"
                  : "✓ 0.00 PT VARIANCE"}
              </span>
            );
          })()}
        </div>

        {/* 4. Computer Vision Multi-Scale ELA & CMFD */}
        <div className="flex justify-between items-center font-semibold">
          <span>4. Computer Vision Multi-Scale ELA & CMFD</span>
          {(() => {
            const st = getStageStatus("VISION_ELA");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● NEURAL SCAN...
                </span>
              );
            if (st === "FAILED")
              return <span className="text-forensic-red">✕ FAILED</span>;
            const visualCount = evidence.filter(
              (e) =>
                (e.ruleId || "").includes("COPY_MOVE") ||
                (e.ruleId || "").includes("ELA") ||
                (e.ruleId || "").includes("TRUFOR") ||
                (e.category || "").includes("IMAGE")
            ).length;
            return (
              <span
                className={
                  visualCount > 0 ? "text-forensic-red" : "text-forensic-green"
                }
              >
                {visualCount > 0
                  ? `✕ MANIPULATION DETECTED (${visualCount})`
                  : "✓ CONTOUR SCAN COMPLETE"}
              </span>
            );
          })()}
        </div>

        {/* 5. Semantic OCR & Table Columnizer */}
        <div className="flex justify-between items-center font-semibold">
          <span>5. Semantic OCR & Table Columnizer</span>
          {(() => {
            const st = getStageStatus("OCR_EXTRACTION");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● EXTRACTING...
                </span>
              );
            if (st === "FAILED")
              return <span className="text-forensic-red">✕ FAILED</span>;
            return (
              <span className="text-forensic-green">
                ✓ TEXT & TABLES EXTRACTED
              </span>
            );
          })()}
        </div>

        {/* 6. Financial Math & Statutory Compliance (SBP, NADRA & FBR) */}
        <div className="flex justify-between items-center font-semibold">
          <span>6. Financial Math & Statutory Compliance (SBP, NADRA & FBR)</span>
          {(() => {
            if (!isFinancial && !isIdentity && !isTaxOrSalary)
              return (
                <span className="text-ink-500 font-normal">
                  — NOT APPLICABLE
                </span>
              );
            const st = getStageStatus("FINANCIAL_VERIFICATION");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● AUDITING...
                </span>
              );
            if (st === "FAILED")
              return (
                <span className="text-forensic-red">✕ VERIFICATION FAILED</span>
              );
            const hasNactaOrUnsc = evidence.some(
              (e) =>
                (e.ruleId || "").includes("AML_NACTA") ||
                (e.ruleId || "").includes("AML_UNSC")
            );
            if (hasNactaOrUnsc) {
              return (
                <span className="text-forensic-red font-bold">
                  ✕ PROSCRIBED MATCH (NACTA / UNSC)
                </span>
              );
            }
            const hasCnicTamper = evidence.some(
              (e) =>
                (e.ruleId || "").includes("RULE_CNIC_PROVINCE_CODE_INVALID") ||
                (e.ruleId || "").includes("RULE_CNIC_GENDER_PARITY_MISMATCH") ||
                (e.ruleId || "").includes("RULE_CNIC_MRZ_CHECKSUM_INVALID") ||
                (e.ruleId || "").includes("RULE_CNIC_MRZ_FRONT_MISMATCH")
            );
            if (hasCnicTamper) {
              return (
                <span className="text-forensic-red font-bold">
                  ✕ NADRA CNIC / MRZ FORGERY
                </span>
              );
            }
            const hasFbrTamper = evidence.some(
              (e) =>
                (e.ruleId || "").includes("RULE_FBR_NTN_INVALID") ||
                (e.ruleId || "").includes("RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY") ||
                (e.ruleId || "").includes("RULE_FBR_WHT_DISCREPANCY") ||
                (e.ruleId || "").includes("RULE_FBR_CPR_")
            );
            if (hasFbrTamper) {
              return (
                <span className="text-forensic-red font-bold">
                  ✕ FBR STATUTORY TAX VIOLATION
                </span>
              );
            }
            const hasPep = evidence.some((e) =>
              (e.ruleId || "").includes("AML_PEP")
            );
            if (hasPep) {
              return (
                <span className="text-amber-800 font-bold">
                  ▲ PEP IDENTIFIED (EDD REQUIRED)
                </span>
              );
            }
            const hasMathAnom = evidence.some(
              (e) =>
                e.severity !== "INFO" &&
                (e.category === "MATHEMATICAL_MISMATCH" ||
                  e.category === "MATH_RECONCILIATION_FAIL" ||
                  (e.ruleId || "").includes("MATH") ||
                  (e.ruleId || "").includes("BALANCE") ||
                  (e.ruleId || "").includes("LEDGER") ||
                  (e.ruleId || "").includes("HOLIDAY"))
            );
            if (hasMathAnom) {
              return (
                <span className="text-forensic-red font-bold">
                  ✕ RECONCILIATION MISMATCH
                </span>
              );
            }
            const hasCnicVerified = evidence.some((e) =>
              (e.ruleId || "").includes("RULE_CNIC_VERIFIED")
            );
            if (hasCnicVerified && !isFinancial && !isTaxOrSalary) {
              return (
                <span className="text-forensic-green">
                  ✓ NADRA & ICAO 9303 VERIFIED
                </span>
              );
            }
            const hasFbrVerified = evidence.some((e) =>
              (e.ruleId || "").includes("RULE_FBR_WHT_VERIFIED")
            );
            if (hasFbrVerified && !isFinancial && !isIdentity) {
              return (
                <span className="text-forensic-green">
                  ✓ FBR §149 & NTN COMPLIANT
                </span>
              );
            }
            const hasBankTemplateVerified = evidence.some((e) =>
              (e.ruleId || "").includes("RULE_BANK_TEMPLATE_VERIFIED")
            );
            if (hasBankTemplateVerified && isFinancial) {
              return (
                <span className="text-forensic-green">
                  ✓ CBS TEMPLATE & STATUTORY CLEARED
                </span>
              );
            }
            return (
              <span className="text-forensic-green">
                ✓ RECONCILED & STATUTORY CLEARED
              </span>
            );
          })()}
        </div>

        {/* 7. Multi-Signal Evidence Fusion */}
        <div className="flex justify-between items-center font-semibold">
          <span>7. Multi-Signal Evidence Fusion</span>
          {(() => {
            const st = getStageStatus("EVIDENCE_FUSION");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● FUSING SIGNALS...
                </span>
              );
            if (st === "FAILED")
              return <span className="text-forensic-red">✕ FAILED</span>;
            return (
              <span
                className={
                  riskScore > 30 ? "text-forensic-red" : "text-forensic-green"
                }
              >
                {`SCORE: ${riskScore} / 100`}
              </span>
            );
          })()}
        </div>

        {/* 8. Court-Admissible Dossier Generation */}
        <div className="flex justify-between items-center font-semibold">
          <span>8. Court-Admissible Dossier Generation</span>
          {(() => {
            const st = getStageStatus("REPORT_GENERATION");
            if (st === "PENDING")
              return <span className="text-ink-400 font-normal">○ PENDING</span>;
            if (st === "RUNNING")
              return (
                <span className="text-forensic-amber animate-pulse">
                  ● GENERATING...
                </span>
              );
            if (st === "FAILED")
              return <span className="text-forensic-red">✕ FAILED</span>;
            return <span className="text-ink-900">✓ SEALED</span>;
          })()}
        </div>
      </div>
    </div>
  );
}
