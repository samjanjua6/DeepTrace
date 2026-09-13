"use client";

import React from "react";
import { AlertTriangle, CheckCircle, ShieldAlert, ShieldCheck, UserCheck, UserX, FileWarning } from "lucide-react";
import { EvidenceItem } from "@/lib/types/forensics";

interface MatchedEntity {
  list_type: string;
  entity_name: string;
  candidate_name: string;
  match_score: number;
  match_type: string;
  category?: string;
  role?: string;
  public_office?: string;
  statutory_reference?: string;
  action_directive: string;
  risk_points: number;
  severity: string;
  unsc_id?: string;
}

interface NarrationRedFlag {
  row_number?: number;
  page_number?: number;
  narration: string;
  matched_term: string;
  category: string;
  description: string;
  amount?: string | number;
  date?: string;
}

interface AmlCddScreeningData {
  overall_status?: "PROSCRIBED_MATCH" | "SANCTIONS_MATCH" | "PEP_DETECTED" | "HIGH_RISK_NARRATION" | "CLEARED";
  action_directive?: string;
  account_title?: string | null;
  cnic?: string | null;
  nacta_match?: boolean;
  unsc_match?: boolean;
  pep_detected?: boolean;
  high_risk_narration_count?: number;
  matched_entities?: MatchedEntity[];
  narration_red_flags?: NarrationRedFlag[];
  findings?: any[];
}

interface SBPAmlCddCardProps {
  screening?: AmlCddScreeningData | null;
  evidence?: EvidenceItem[];
}

export function SBPAmlCddCard({ screening, evidence }: SBPAmlCddCardProps) {
  // Infer screening state from evidence items if screening payload not directly present
  const nactaEv = evidence?.find((e) => (e.ruleId || "").includes("AML_NACTA"));
  const unscEv = evidence?.find((e) => (e.ruleId || "").includes("AML_UNSC"));
  const pepEv = evidence?.find((e) => (e.ruleId || "").includes("AML_PEP"));
  const hawalaEv = evidence?.find((e) => (e.ruleId || "").includes("AML_HIGH_RISK"));
  const clearedEv = evidence?.find((e) => (e.ruleId || "").includes("AML_CDD_CLEARED"));

  const hasNacta = Boolean(screening?.nacta_match || nactaEv);
  const hasUnsc = Boolean(screening?.unsc_match || unscEv);
  const hasPep = Boolean(screening?.pep_detected || pepEv);
  const hasHawala = Boolean(
    (screening?.high_risk_narration_count && screening.high_risk_narration_count > 0) || hawalaEv
  );

  let effectiveStatus = screening?.overall_status || "CLEARED";
  if (hasNacta) effectiveStatus = "PROSCRIBED_MATCH";
  else if (hasUnsc) effectiveStatus = "SANCTIONS_MATCH";
  else if (hasPep) effectiveStatus = "PEP_DETECTED";
  else if (hasHawala) effectiveStatus = "HIGH_RISK_NARRATION";

  const isClean = effectiveStatus === "CLEARED" && !hasNacta && !hasUnsc && !hasPep && !hasHawala;

  const accountTitle =
    screening?.account_title ||
    (nactaEv?.technicalDetails as any)?.candidate_name ||
    (pepEv?.technicalDetails as any)?.candidate_name ||
    (clearedEv?.technicalDetails as any)?.account_title ||
    "Statement Account Holder";

  const cnic =
    screening?.cnic ||
    (clearedEv?.technicalDetails as any)?.cnic ||
    null;

  const matchedEntities = screening?.matched_entities || [];
  const narrationFlags = screening?.narration_red_flags || [];

  return (
    <div
      className={`bg-paper-0 border p-4 font-mono select-none space-y-3 rounded-none ${
        isClean ? "border-rule" : "border-forensic-red/60 shadow-sm"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-rule pb-2 text-xs">
        <div className="flex items-center gap-2">
          {isClean ? (
            <ShieldCheck className="w-4 h-4 text-forensic-green flex-shrink-0" />
          ) : (
            <ShieldAlert className="w-4 h-4 text-forensic-red flex-shrink-0" />
          )}
          <span className="font-semibold text-ink-900 uppercase tracking-wider text-[10px]">
            § 03B / SBP AML/CFT & CUSTOMER DUE DILIGENCE (CDD) AUDIT
          </span>
        </div>
        <span
          className={`px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider border rounded-none ${
            isClean
              ? "bg-forensic-green/10 text-forensic-green border-forensic-green"
              : effectiveStatus === "PEP_DETECTED"
              ? "bg-amber-500/15 text-amber-800 border-amber-500/40"
              : "bg-forensic-red text-white border-forensic-red"
          }`}
        >
          {isClean
            ? "CDD CLEARED (PASS)"
            : effectiveStatus === "PEP_DETECTED"
            ? "PEP IDENTIFIED (EDD REQUIRED)"
            : "ADVERSE AML MATCH"}
        </span>
      </div>

      {/* Statutory Mandate Citation */}
      <div className="text-[10px] text-ink-500 uppercase tracking-wider">
        Statutory Framework: SBP BPRD Circular No. 1/2021 • ATA 1997 §11EE • UNSC Act 1948
      </div>

      {/* Screened Entity Banner */}
      <div className="bg-paper-1 border border-rule p-3 rounded-none">
        <div className="flex flex-wrap justify-between items-center gap-2">
          <div>
            <span className="text-[10px] text-ink-500 block uppercase tracking-wider">
              Screened Account Title / Legal Entity:
            </span>
            <span className="text-sm md:text-base font-bold text-ink-900 tracking-wider block">
              {accountTitle}
            </span>
          </div>
          {cnic && (
            <div className="text-right font-mono">
              <span className="text-[10px] text-ink-500 block uppercase tracking-wider">
                Stated CNIC Number:
              </span>
              <span className="text-xs font-bold text-ink-900 tabular-nums block">
                {cnic}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 4 Screening Vectors Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-[10px]">
        {/* Vector 1: NACTA 4th Schedule */}
        <div
          className={`p-2 border rounded-none ${
            hasNacta
              ? "bg-forensic-red/10 border-forensic-red/50"
              : "bg-paper-1 border-rule"
          }`}
        >
          <span className="text-ink-500 block uppercase">NACTA 4th Schedule</span>
          <span
            className={`text-xs font-bold block mt-0.5 ${
              hasNacta ? "text-forensic-red" : "text-forensic-green"
            }`}
          >
            {hasNacta ? "PROSCRIBED MATCH" : "CLEARED"}
          </span>
        </div>

        {/* Vector 2: UNSC 1267 Sanctions */}
        <div
          className={`p-2 border rounded-none ${
            hasUnsc
              ? "bg-forensic-red/10 border-forensic-red/50"
              : "bg-paper-1 border-rule"
          }`}
        >
          <span className="text-ink-500 block uppercase">UNSC 1267 Sanctions</span>
          <span
            className={`text-xs font-bold block mt-0.5 ${
              hasUnsc ? "text-forensic-red" : "text-forensic-green"
            }`}
          >
            {hasUnsc ? "SANCTIONED ENTITY" : "CLEARED"}
          </span>
        </div>

        {/* Vector 3: Politically Exposed Persons (PEPs) */}
        <div
          className={`p-2 border rounded-none ${
            hasPep
              ? "bg-amber-500/10 border-amber-500/40"
              : "bg-paper-1 border-rule"
          }`}
        >
          <span className="text-ink-500 block uppercase">PEP Registry (SBP)</span>
          <span
            className={`text-xs font-bold block mt-0.5 ${
              hasPep ? "text-amber-800" : "text-forensic-green"
            }`}
          >
            {hasPep ? "PEP IDENTIFIED" : "CLEARED"}
          </span>
        </div>

        {/* Vector 4: Hawala / Hundi Narrations */}
        <div
          className={`p-2 border rounded-none ${
            hasHawala
              ? "bg-forensic-red/10 border-forensic-red/50"
              : "bg-paper-1 border-rule"
          }`}
        >
          <span className="text-ink-500 block uppercase">Hawala / Hundi Scan</span>
          <span
            className={`text-xs font-bold block mt-0.5 ${
              hasHawala ? "text-forensic-red" : "text-forensic-green"
            }`}
          >
            {hasHawala
              ? `${screening?.high_risk_narration_count || 1} FLAGGED`
              : "0 RED FLAGS"}
          </span>
        </div>
      </div>

      {/* Detailed Matched Entities (if any adverse hit) */}
      {matchedEntities.length > 0 && (
        <div className="space-y-2 pt-1">
          <span className="text-[10px] text-ink-500 uppercase tracking-wider block font-bold">
            Matched Regulatory Sanctions / PEP Records ({matchedEntities.length}):
          </span>
          {matchedEntities.map((m, idx) => {
            const isCritical = m.severity === "CRITICAL";
            return (
              <div
                key={idx}
                className={`p-3 border text-xs space-y-1.5 rounded-none ${
                  isCritical
                    ? "bg-forensic-red/5 border-forensic-red/40 text-ink-900"
                    : "bg-amber-500/5 border-amber-500/30 text-ink-900"
                }`}
              >
                <div className="flex flex-wrap justify-between items-start gap-1">
                  <div className="font-bold text-ink-900 text-xs">
                    {m.list_type.replace(/_/g, " ")}: {m.entity_name}
                  </div>
                  <span
                    className={`px-1.5 py-0.5 text-[9px] font-bold uppercase rounded-none border ${
                      isCritical
                        ? "bg-forensic-red text-white border-forensic-red"
                        : "bg-amber-500/20 text-amber-900 border-amber-500/40"
                    }`}
                  >
                    {Math.round(m.match_score * 100)}% Confidence ({m.match_type})
                  </span>
                </div>

                <div className="text-[11px] text-ink-700 space-y-0.5">
                  {m.role && <div><span className="text-ink-500">Designation / Role:</span> {m.role}</div>}
                  {m.public_office && <div><span className="text-ink-500">Public Office:</span> {m.public_office}</div>}
                  {m.statutory_reference && (
                    <div><span className="text-ink-500">Statutory Ground:</span> {m.statutory_reference}</div>
                  )}
                  {m.unsc_id && <div><span className="text-ink-500">UN Committee Reference:</span> {m.unsc_id}</div>}
                </div>

                <div className="pt-1 border-t border-rule/40 flex justify-between items-center text-[10px]">
                  <span className="text-ink-500 uppercase">Directive:</span>
                  <span className="font-bold text-forensic-red">{m.action_directive.replace(/_/g, " ")}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Hawala / Hundi Red Flag Narrations (if any) */}
      {narrationFlags.length > 0 && (
        <div className="space-y-2 pt-1">
          <span className="text-[10px] text-ink-500 uppercase tracking-wider block font-bold">
            Prohibited Informal Value Transfer Narratives ({narrationFlags.length}):
          </span>
          <div className="border border-rule divide-y divide-rule rounded-none">
            {narrationFlags.slice(0, 5).map((n, idx) => (
              <div key={idx} className="p-2 bg-paper-1 text-[11px] flex justify-between items-center">
                <div>
                  <span className="font-semibold text-ink-900">{n.narration}</span>
                  <span className="text-[10px] text-forensic-red block">
                    Triggered Keyword: &quot;{n.matched_term}&quot; ({n.category})
                  </span>
                </div>
                {n.amount && (
                  <span className="font-mono text-xs font-bold text-ink-900">
                    PKR {n.amount}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Directive Summary Callout */}
      {!isClean ? (
        <div className="bg-forensic-red/10 border border-forensic-red/30 p-3 text-xs font-mono space-y-1 rounded-none">
          <div className="flex items-center gap-1.5 text-forensic-red font-bold uppercase text-[10px]">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>SBP STATUTORY COMPLIANCE DIRECTIVE</span>
          </div>
          <p className="text-[11px] text-ink-800 leading-relaxed">
            {hasNacta || hasUnsc
              ? "Immediate Mandatory Action: Under SBP BPRD Circular No. 1/2021 & Section 11EE of ATA 1997, regulated lending institutions must immediately freeze account balances, refuse disbursement, and submit a Suspicious Transaction Report (STR) to the Financial Monitoring Unit (FMU)."
              : hasPep
              ? "Mandatory Enhanced Due Diligence (EDD): Politically Exposed Person detected under SBP BPRD guidelines. Establishment or maintenance of credit facility requires Senior Management Approval (SMA) and independent verification of Source of Wealth."
              : "High Risk Informal Transfer Indicators: Prohibited under SBP BPRD Circular No. 3/2018. Enhanced transaction monitoring and verification of underlying commercial contracts required."}
          </p>
        </div>
      ) : (
        <div className="bg-paper-1 p-2.5 border border-rule text-[11px] space-y-1 rounded-none">
          <div className="flex items-center gap-1.5 text-forensic-green font-bold text-[10px] uppercase">
            <CheckCircle className="w-3 h-3 flex-shrink-0" />
            <span>CDD STATUTORY VERIFICATION CLEARED</span>
          </div>
          <p className="text-ink-600 text-[10px] leading-relaxed">
            Customer credentials cross-referenced against NACTA proscribed entities and UNSC 1267 counter-terrorism lists. No adverse PEP or Hawala/Hundi red flags identified. Customer Due Diligence (CDD) satisfies SBP BPRD Circular No. 1 of 2021 requirements.
          </p>
        </div>
      )}
    </div>
  );
}
