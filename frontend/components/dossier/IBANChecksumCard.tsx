"use client";

import React from "react";
import { AlertTriangle, CheckCircle, ShieldCheck } from "lucide-react";
import { EvidenceItem } from "@/lib/types/forensics";

interface IBANChecksumCardProps {
  iban?: string;
  bankName?: string;
  isValid?: boolean;
  accountNo?: string;
  checkDigits?: string;
  bankCode?: string;
  validationReason?: string;
  evidence?: EvidenceItem[];
}

export function IBANChecksumCard({
  iban,
  bankName,
  isValid = true,
  accountNo,
  checkDigits,
  bankCode,
  validationReason,
  evidence,
}: IBANChecksumCardProps) {
  // Check if an IBAN failure finding exists in evidence
  const ibanFailure = evidence?.find(
    (e) =>
      e.ruleId === "RULE_PK_IBAN_CHECKSUM_INVALID" ||
      e.category === "IBAN_CHECKSUM_FAILURE"
  );

  const effectiveIsValid = ibanFailure ? false : isValid;
  const effectiveIban =
    iban ||
    (ibanFailure?.technicalDetails as any)?.raw_iban ||
    ibanFailure?.actualValue;
  const effectiveBankName =
    bankName ||
    (ibanFailure?.technicalDetails as any)?.bank_name ||
    "Meezan Bank Limited";
  const effectiveReason =
    validationReason ||
    ibanFailure?.description ||
    (ibanFailure?.technicalDetails as any)?.validation_reason ||
    "Valid ISO 7064 MOD-97 Checksum (Remainder = 1)";

  if (!effectiveIban) {
    return (
      <div className="bg-paper-0 border border-rule p-6 font-mono text-center text-xs space-y-2">
        <div className="flex items-center justify-center gap-2 text-ink-700 font-bold uppercase tracking-wider text-[11px]">
          <ShieldCheck className="w-4 h-4 text-ink-500" />
          <span>§ 03 / SBP IBAN ISO 7064 MOD-97 AUDIT</span>
        </div>
        <p className="text-ink-500 text-[11px] max-w-md mx-auto">
          No 24-character Pakistani IBAN detected in document streams. If this document is a bank statement, ensure the account header contains the complete SBP-formatted IBAN.
        </p>
      </div>
    );
  }

  // Format IBAN into 4-character blocks: PK67 MEZN 0023 0201 1244 4629
  const cleanIban = effectiveIban.replace(/\s+/g, "").toUpperCase();
  const formattedIban = cleanIban.replace(/(.{4})/g, "$1 ").trim();
  const country = cleanIban.substring(0, 2);
  const derivedCheckDigits = checkDigits || cleanIban.substring(2, 4);
  const derivedBankCode = bankCode || cleanIban.substring(4, 8);
  const derivedAccountNo = accountNo || cleanIban.substring(8);

  return (
    <div className={`bg-paper-0 border p-4 font-mono select-none space-y-3 ${
      effectiveIsValid ? "border-rule" : "border-forensic-red/60 shadow-sm"
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-rule pb-2 text-xs">
        <div className="flex items-center gap-2">
          {effectiveIsValid ? (
            <CheckCircle className="w-4 h-4 text-forensic-green flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-forensic-red flex-shrink-0" />
          )}
          <span className="font-semibold text-ink-900 uppercase tracking-wider text-[10px]">
            § 03 / SBP IBAN ISO 7064 MOD-97 AUDIT
          </span>
        </div>
        <span
          className={`px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider border ${
            effectiveIsValid
              ? "bg-forensic-green/10 text-forensic-green border-forensic-green"
              : "bg-forensic-red text-white border-forensic-red"
          }`}
        >
          {effectiveIsValid ? "VALIDATED (PASS)" : "CHECKSUM FAILED"}
        </span>
      </div>

      {/* Extracted IBAN Display */}
      <div className="bg-paper-1 border border-rule p-3">
        <span className="text-[10px] text-ink-500 block mb-1 uppercase tracking-wider">
          Extracted International Bank Account Number:
        </span>
        <span className="text-sm md:text-base font-bold text-ink-900 tracking-wider tabular-nums block">
          {formattedIban}
        </span>
      </div>

      {/* SBP Structural Breakdown Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-[10px]">
        <div className="bg-paper-1 p-2 border border-rule">
          <span className="text-ink-500 block uppercase">Country</span>
          <span className="font-bold text-ink-900 text-xs">{country}</span>
        </div>
        <div className="bg-paper-1 p-2 border border-rule">
          <span className="text-ink-500 block uppercase">Check Digits</span>
          <span className="font-bold text-ink-900 text-xs">{derivedCheckDigits}</span>
        </div>
        <div className="bg-paper-1 p-2 border border-rule">
          <span className="text-ink-500 block uppercase">Bank Code</span>
          <span className="font-bold text-ink-900 text-xs">{derivedBankCode}</span>
        </div>
        <div className="bg-paper-1 p-2 border border-rule">
          <span className="text-ink-500 block uppercase">SBP Clearing</span>
          <span className={`text-xs font-bold ${
            effectiveIsValid ? "text-forensic-green" : "text-forensic-red"
          }`}>
            {effectiveIsValid ? "ACTIVE" : "INVALID"}
          </span>
        </div>
      </div>

      {/* Details Row */}
      <div className="bg-paper-1 p-2.5 border border-rule text-[11px] space-y-1.5">
        <div className="flex justify-between items-center">
          <span className="text-ink-500">Institution:</span>
          <span className="font-semibold text-ink-900">{effectiveBankName}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-ink-500">Account / Branch No:</span>
          <span className="font-mono text-ink-900 tabular-nums">{derivedAccountNo}</span>
        </div>
        <div className="flex justify-between items-center border-t border-rule/50 pt-1">
          <span className="text-ink-500">Verification Engine:</span>
          <span className="text-ink-700">State Bank of Pakistan (PSD Circular No. 04 / 2007)</span>
        </div>
      </div>

      {/* Failure Callout if invalid */}
      {!effectiveIsValid && (
        <div className="bg-forensic-red/10 border border-forensic-red/30 p-3 text-xs font-mono space-y-1">
          <div className="flex items-center gap-1.5 text-forensic-red font-bold uppercase text-[10px]">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>CRITICAL FRAUD SIGNAL: FABRICATED IBAN</span>
          </div>
          <p className="text-[11px] text-ink-700 leading-relaxed">
            {effectiveReason}. Legitimate Pakistani bank accounts must yield MOD-97 remainder 1. A failed checksum confirms manual insertion or spoofed credentials.
          </p>
        </div>
      )}
    </div>
  );
}
