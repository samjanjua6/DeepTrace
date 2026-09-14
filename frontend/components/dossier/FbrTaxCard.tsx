"use client";

import React from "react";
import {
  AlertTriangle,
  CheckCircle,
  ShieldAlert,
  ShieldCheck,
  Receipt,
  Building2,
  FileCheck2,
} from "lucide-react";
import { EvidenceItem } from "@/lib/types/forensics";

interface NTNResult {
  raw_input?: string;
  formatted_ntn?: string;
  ntn_type?: "CORPORATE_AOP" | "INDIVIDUAL_CNIC";
  base_digits?: string;
  check_digit?: string;
  calculated_check_digit?: string;
  is_valid?: boolean;
  reason?: string;
}

interface WHTAudit {
  monthly_gross?: number;
  declared_wht?: number;
  tax_year?: number;
  annual_gross?: number;
  annual_tax?: number;
  expected_monthly_wht?: number;
  monthly_discrepancy?: number;
  slab_name?: string;
  slab_formula?: string;
  is_taxable?: boolean;
  is_compliant?: boolean;
  status?: string;
  reason?: string;
}

interface CPRResult {
  raw_cpr?: string;
  cpr_type?: string;
  tax_year?: string;
  date_of_payment?: string;
  is_valid?: boolean;
  is_future_dated?: boolean;
  reason?: string;
}

interface FbrTaxVerificationData {
  overall_status?:
    | "COMPLIANT"
    | "NON_COMPLIANT"
    | "TAX_EVASION_SUSPECTED"
    | "DISCREPANCY_DETECTED"
    | "NO_TAX_DATA_FOUND";
  document_type?: string;
  ntn_result?: NTNResult | null;
  wht_audit?: WHTAudit | null;
  cpr_result?: CPRResult | null;
  findings?: any[];
  is_compliant?: boolean;
}

interface FbrTaxCardProps {
  verification?: FbrTaxVerificationData | null;
  evidence?: EvidenceItem[];
}

export function FbrTaxCard({ verification, evidence }: FbrTaxCardProps) {
  // Infer state from evidence items if direct payload is not present
  const ntnChecksumEv = evidence?.find((e) =>
    (e.ruleId || "").includes("RULE_FBR_NTN_INVALID_CHECKSUM")
  );
  const ntnFormatEv = evidence?.find((e) =>
    (e.ruleId || "").includes("RULE_FBR_NTN_INVALID_FORMAT")
  );
  const whtZeroEv = evidence?.find((e) =>
    (e.ruleId || "").includes("RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY")
  );
  const whtDiscEv = evidence?.find((e) =>
    (e.ruleId || "").includes("RULE_FBR_WHT_DISCREPANCY")
  );
  const cprFailEv = evidence?.find((e) =>
    (e.ruleId || "").includes("RULE_FBR_CPR_")
  );
  const whtVerifiedEv = evidence?.find((e) =>
    (e.ruleId || "").includes("RULE_FBR_WHT_VERIFIED")
  );

  const hasNtnFail = Boolean(ntnChecksumEv || ntnFormatEv);
  const hasWhtZeroFail = Boolean(whtZeroEv);
  const hasWhtDiscrepancy = Boolean(whtDiscEv);
  const hasCprFail = Boolean(cprFailEv);

  const isCriticalViolation =
    verification?.overall_status === "TAX_EVASION_SUSPECTED" ||
    verification?.overall_status === "NON_COMPLIANT" ||
    hasNtnFail ||
    hasWhtZeroFail;

  const isDiscrepancy =
    verification?.overall_status === "DISCREPANCY_DETECTED" ||
    hasWhtDiscrepancy ||
    hasCprFail;

  const isCompliant =
    (verification?.overall_status === "COMPLIANT" ||
      verification?.is_compliant ||
      Boolean(whtVerifiedEv)) &&
    !isCriticalViolation &&
    !isDiscrepancy;

  const ntn = verification?.ntn_result;
  const wht = verification?.wht_audit;
  const cpr = verification?.cpr_result;

  return (
    <div className="bg-paper-0 border border-rule p-4 font-mono text-xs space-y-4 rounded-none">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-3">
        <div className="flex items-center gap-2">
          {isCriticalViolation ? (
            <ShieldAlert className="w-5 h-5 text-forensic-red" />
          ) : isDiscrepancy ? (
            <AlertTriangle className="w-5 h-5 text-amber-700" />
          ) : isCompliant ? (
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
          ) : (
            <Receipt className="w-5 h-5 text-ink-600" />
          )}
          <div>
            <span className="font-bold text-ink-900 uppercase tracking-wider block text-[11px]">
              FBR Tax Verification & Section 149 Withholding Audit
            </span>
            <span className="text-[10px] text-ink-500">
              Income Tax Ordinance, 2001 (ITO §149 & §181) | Finance Act Progressive Slabs
            </span>
          </div>
        </div>

        <div>
          {isCriticalViolation ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-rose-500/10 border border-forensic-red text-forensic-red text-[10px] font-bold uppercase tracking-wider">
              <ShieldAlert className="w-3.5 h-3.5" />
              Statutory Tax Violation
            </span>
          ) : isDiscrepancy ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-600 text-amber-700 text-[10px] font-bold uppercase tracking-wider">
              <AlertTriangle className="w-3.5 h-3.5" />
              Tax Discrepancy
            </span>
          ) : isCompliant ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-600 text-emerald-700 text-[10px] font-bold uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5" />
              Statutorily Reconciled
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-paper-1 border border-rule text-ink-600 text-[10px] font-semibold uppercase tracking-wider">
              <Receipt className="w-3.5 h-3.5" />
              Tax Audit Checked
            </span>
          )}
        </div>
      </div>

      {/* Grid: NTN Audit & CPR Check */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* NTN Structure Card */}
        <div className="border border-rule bg-paper-50 p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-rule pb-1.5">
            <span className="text-[10px] uppercase font-bold text-ink-700 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-ink-500" />
              National Tax Number (NTN)
            </span>
            <span className="text-[9px] uppercase font-semibold text-ink-500">
              {ntn?.ntn_type ?? (ntn?.formatted_ntn ? "Corporate/AOP" : "Format Audit")}
            </span>
          </div>

          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between items-center">
              <span className="text-ink-500">Declared NTN:</span>
              <span className="font-bold text-ink-900 tracking-wider">
                {ntn?.formatted_ntn ?? ntn?.raw_input ?? "Not Detected"}
              </span>
            </div>

            {ntn?.base_digits && (
              <div className="flex justify-between items-center">
                <span className="text-ink-500">Base Digits (Weights 8..2):</span>
                <span className="font-mono text-ink-700">{ntn.base_digits}</span>
              </div>
            )}

            <div className="flex justify-between items-center">
              <span className="text-ink-500">Mod-11 Check Digit:</span>
              <span className="font-mono font-bold">
                {ntn ? (
                  ntn.is_valid ? (
                    <span className="text-emerald-700 flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" />
                      {ntn.check_digit} (Valid)
                    </span>
                  ) : (
                    <span className="text-forensic-red flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      {ntn.check_digit} (Expected: {ntn.calculated_check_digit ?? "—"})
                    </span>
                  )
                ) : (
                  <span className="text-ink-400">—</span>
                )}
              </span>
            </div>

            {ntn?.reason && (
              <div className="text-[10px] text-ink-600 bg-paper-0 border border-rule p-1.5 mt-1">
                {ntn.reason}
              </div>
            )}
          </div>
        </div>

        {/* CPR Audit Card */}
        <div className="border border-rule bg-paper-50 p-3 space-y-2">
          <div className="flex items-center justify-between border-b border-rule pb-1.5">
            <span className="text-[10px] uppercase font-bold text-ink-700 flex items-center gap-1.5">
              <FileCheck2 className="w-3.5 h-3.5 text-ink-500" />
              Computerized Payment Receipt (CPR)
            </span>
            <span className="text-[9px] uppercase font-semibold text-ink-500">
              {cpr?.cpr_type ?? "Treasury Check"}
            </span>
          </div>

          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between items-center">
              <span className="text-ink-500">CPR Identifier:</span>
              <span className="font-bold text-ink-900 tracking-wider">
                {cpr?.raw_cpr ?? "None Cited"}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-ink-500">Tax Year / Period:</span>
              <span className="font-mono text-ink-700">{cpr?.tax_year ?? "—"}</span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-ink-500">Receipt Status:</span>
              <span className="font-mono font-bold">
                {cpr ? (
                  cpr.is_valid && !cpr.is_future_dated ? (
                    <span className="text-emerald-700 flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" />
                      Authentic Format
                    </span>
                  ) : (
                    <span className="text-forensic-red flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      {cpr.is_future_dated ? "Future-Dated" : "Invalid Format"}
                    </span>
                  )
                ) : (
                  <span className="text-ink-400">—</span>
                )}
              </span>
            </div>

            {cpr?.reason && (
              <div className="text-[10px] text-ink-600 bg-paper-0 border border-rule p-1.5 mt-1">
                {cpr.reason}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Section 149 Withholding Tax Audit Table */}
      <div className="border border-rule bg-paper-50 p-3 space-y-3">
        <div className="flex items-center justify-between border-b border-rule pb-1.5">
          <span className="text-[10px] uppercase font-bold text-ink-700 flex items-center gap-1.5">
            <Receipt className="w-3.5 h-3.5 text-ink-500" />
            Section 149 Salary Tax Reconciler (Finance Act Progressive Slabs)
          </span>
          <span className="text-[9px] uppercase font-semibold text-ink-500">
            {wht?.tax_year ? `Tax Year ${wht.tax_year}` : "Statutory First Schedule"}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
          <div className="border border-rule bg-paper-0 p-2 space-y-1">
            <span className="text-[9px] uppercase text-ink-500 font-bold block">Monthly Gross</span>
            <span className="font-bold text-ink-900 block text-xs">
              {wht?.monthly_gross !== undefined
                ? `PKR ${wht.monthly_gross.toLocaleString()}`
                : "—"}
            </span>
          </div>

          <div className="border border-rule bg-paper-0 p-2 space-y-1">
            <span className="text-[9px] uppercase text-ink-500 font-bold block">Annualized Gross</span>
            <span className="font-bold text-ink-900 block text-xs">
              {wht?.annual_gross !== undefined
                ? `PKR ${wht.annual_gross.toLocaleString()}`
                : "—"}
            </span>
          </div>

          <div className="border border-rule bg-paper-0 p-2 space-y-1">
            <span className="text-[9px] uppercase text-ink-500 font-bold block">Declared WHT</span>
            <span className={`font-bold block text-xs ${hasWhtZeroFail ? "text-forensic-red" : "text-ink-900"}`}>
              {wht?.declared_wht !== undefined
                ? `PKR ${wht.declared_wht.toLocaleString()}`
                : "—"}
            </span>
          </div>

          <div className="border border-rule bg-paper-0 p-2 space-y-1">
            <span className="text-[9px] uppercase text-ink-500 font-bold block">Expected Statutory WHT</span>
            <span className="font-bold text-emerald-700 block text-xs">
              {wht?.expected_monthly_wht !== undefined
                ? `PKR ${wht.expected_monthly_wht.toLocaleString()}`
                : "—"}
            </span>
          </div>
        </div>

        {/* Slab Formula Details */}
        {wht?.slab_name && (
          <div className="border border-rule bg-paper-0 p-2.5 space-y-1 text-[11px]">
            <div className="flex justify-between items-center text-ink-700">
              <span className="font-bold">{wht.slab_name}</span>
              <span className="text-ink-500 text-[10px] font-mono">{wht.slab_formula}</span>
            </div>
            {wht.monthly_discrepancy !== undefined && Math.abs(wht.monthly_discrepancy) > 0 && (
              <div className="flex justify-between items-center pt-1 border-t border-rule text-forensic-red font-bold">
                <span>Tax Variance / Shortfall:</span>
                <span>PKR {Math.abs(wht.monthly_discrepancy).toLocaleString()} / month</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Identified Anomalies & Statutory Violations */}
      {(hasNtnFail || hasWhtZeroFail || hasWhtDiscrepancy || hasCprFail) && (
        <div className="border border-forensic-red/50 bg-rose-500/5 p-3 space-y-2 text-xs">
          <div className="flex items-center gap-1.5 font-bold text-forensic-red uppercase">
            <AlertTriangle className="w-4 h-4" />
            <span>FBR Statutory Non-Compliance & Fraud Signals</span>
          </div>
          <div className="space-y-1.5 text-ink-800 text-[11px]">
            {hasNtnFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-forensic-red font-bold">●</span>
                <span>
                  <strong>NTN Modulus-11 Failure:</strong> The employer/corporate National Tax Number (NTN) failed weighted Modulus-11 check digit verification, indicating fabricated corporate credentials or phantom registration.
                </span>
              </div>
            )}
            {hasWhtZeroFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-forensic-red font-bold">●</span>
                <span>
                  <strong>Zero WHT on Taxable Income:</strong> Salary exceeds statutory PKR 50,000/month (PKR 600,000/year) threshold with ZERO declared withholding tax, directly violating Section 149 of the Income Tax Ordinance 2001. High probability of fabricated payslip.
                </span>
              </div>
            )}
            {hasWhtDiscrepancy && (
              <div className="flex items-start gap-1.5">
                <span className="text-amber-700 font-bold">●</span>
                <span>
                  <strong>Statutory Tax Discrepancy:</strong> Declared withholding tax departs from progressive tax brackets established under Finance Act Division I, Part I of the First Schedule.
                </span>
              </div>
            )}
            {hasCprFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-forensic-red font-bold">●</span>
                <span>
                  <strong>CPR Receipt Failure:</strong> Computerized Payment Receipt number is syntactically invalid or cites an impossible/future calendar tax deposit date.
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Statutory Citation Footer */}
      <div className="text-[10px] text-ink-500 border-t border-rule pt-2 flex flex-wrap justify-between items-center gap-2">
        <span>
          Statutory Authority: Income Tax Ordinance, 2001 (§149 & §181) | Finance Act First Schedule | FBR SRO 1007(I)/2017
        </span>
        <span className="font-semibold uppercase tracking-wider text-ink-600">
          Zero-Hallucination Deterministic Engine
        </span>
      </div>
    </div>
  );
}
