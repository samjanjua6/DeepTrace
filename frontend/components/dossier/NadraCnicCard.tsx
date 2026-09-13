"use client";

import React from "react";
import {
  AlertTriangle,
  CheckCircle,
  ShieldAlert,
  ShieldCheck,
  CreditCard,
  User,
  MapPin,
  Barcode,
} from "lucide-react";
import { EvidenceItem } from "@/lib/types/forensics";

interface CnicStructure {
  raw_cnic?: string;
  formatted_cnic?: string;
  is_valid?: boolean;
  errors?: string[];
  province_code?: string;
  province_name?: string;
  division_code?: string;
  district_code?: string;
  tehsil_code?: string;
  family_number?: string;
  check_digit?: string;
  gender_parity?: "MALE" | "FEMALE";
}

interface IcaoFieldCheck {
  value: string;
  check_digit: string;
  calculated: number;
  is_valid: boolean;
}

interface MrzResult {
  mrz_detected: boolean;
  is_valid: boolean;
  failures?: string[];
  document_type?: string;
  country_code?: string;
  document_number?: IcaoFieldCheck;
  date_of_birth?: IcaoFieldCheck;
  sex?: string;
  expiry_date?: IcaoFieldCheck;
  nationality?: string;
  optional_data?: string;
  composite_check?: {
    check_digit: string;
    calculated: number;
    is_valid: boolean;
  };
  raw_lines?: string[];
}

interface NadraCnicVerificationData {
  overall_status?: "VERIFIED" | "TAMPERED" | "ANOMALY_DETECTED";
  primary_cnic?: string | null;
  cnic_structure?: CnicStructure | null;
  gender_parity_verified?: boolean;
  gender_explanation?: string;
  mrz_result?: MrzResult | null;
  findings?: any[];
  is_conforming?: boolean;
}

interface NadraCnicCardProps {
  verification?: NadraCnicVerificationData | null;
  evidence?: EvidenceItem[];
}

export function NadraCnicCard({ verification, evidence }: NadraCnicCardProps) {
  // Infer state from evidence items if payload not directly provided
  const provinceEv = evidence?.find((e) => (e.ruleId || "").includes("RULE_CNIC_PROVINCE_CODE_INVALID"));
  const genderEv = evidence?.find((e) => (e.ruleId || "").includes("RULE_CNIC_GENDER_PARITY_MISMATCH"));
  const mrzChecksumEv = evidence?.find((e) => (e.ruleId || "").includes("RULE_CNIC_MRZ_CHECKSUM_INVALID"));
  const mrzMismatchEv = evidence?.find((e) => (e.ruleId || "").includes("RULE_CNIC_MRZ_FRONT_MISMATCH"));
  const temporalEv = evidence?.find((e) => (e.ruleId || "").includes("RULE_CNIC_TEMPORAL_INVALID"));
  const verifiedEv = evidence?.find((e) => (e.ruleId || "").includes("RULE_CNIC_VERIFIED"));

  const hasProvinceFail = Boolean(provinceEv);
  const hasGenderFail = Boolean(genderEv);
  const hasMrzChecksumFail = Boolean(mrzChecksumEv);
  const hasMrzMismatchFail = Boolean(mrzMismatchEv);
  const hasTemporalFail = Boolean(temporalEv);

  const isTampered =
    verification?.overall_status === "TAMPERED" ||
    hasProvinceFail ||
    hasGenderFail ||
    hasMrzChecksumFail ||
    hasMrzMismatchFail;

  const isAnomaly =
    verification?.overall_status === "ANOMALY_DETECTED" ||
    hasTemporalFail;

  const isVerified =
    (verification?.overall_status === "VERIFIED" || verifiedEv) &&
    !isTampered &&
    !isAnomaly;

  const primaryCnic =
    verification?.primary_cnic ||
    (verifiedEv?.technicalDetails as any)?.cnic ||
    (genderEv?.technicalDetails as any)?.cnic ||
    (provinceEv?.technicalDetails as any)?.cnic ||
    "—";

  const struct = verification?.cnic_structure;
  const mrz = verification?.mrz_result;

  return (
    <div
      className={`bg-paper-0 border p-4 font-mono select-none space-y-4 rounded-none ${
        isTampered
          ? "border-forensic-red/70 shadow-sm"
          : isAnomaly
          ? "border-amber-500/60"
          : "border-rule"
      }`}
    >
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between border-b border-rule pb-2 gap-2 text-xs">
        <div className="flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-ink-700" />
          <span className="font-bold uppercase tracking-wider text-ink-900">
            NADRA CNIC & SMART CARD IDENTITY AUDIT
          </span>
          <span className="text-[10px] text-ink-400 font-mono hidden sm:inline">
            (NADRA Ord 2000 §30 & ICAO 9303)
          </span>
        </div>

        {isTampered ? (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-rose-500/10 text-forensic-red border border-forensic-red/30 text-[10px] font-bold uppercase tracking-wider">
            <ShieldAlert className="w-3.5 h-3.5 text-forensic-red" />
            <span>✕ FORGERY / ANOMALY DETECTED</span>
          </div>
        ) : isAnomaly ? (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-amber-500/10 text-amber-800 border border-amber-500/30 text-[10px] font-bold uppercase tracking-wider">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
            <span>▲ TEMPORAL INCONSISTENCY</span>
          </div>
        ) : isVerified ? (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 text-emerald-800 border border-emerald-500/30 text-[10px] font-bold uppercase tracking-wider">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
            <span>✓ VERIFIED AUTHENTIC</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-paper-2 text-ink-600 border border-rule text-[10px] font-bold uppercase tracking-wider">
            <span>● 13-DIGIT SCHEMA AUDITED</span>
          </div>
        )}
      </div>

      {/* Primary CNIC Display Box */}
      <div className="bg-paper-1 border border-rule p-3 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase text-ink-500 font-semibold tracking-wider">
            Cardholder CNIC / Identity Number
          </div>
          <div className="text-lg font-bold text-ink-900 font-mono tracking-widest mt-0.5">
            {primaryCnic}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          {struct?.province_name && (
            <div className="flex items-center gap-1 text-ink-700">
              <MapPin className="w-3.5 h-3.5 text-ink-500" />
              <span>{struct.province_name}</span>
            </div>
          )}
          {struct?.gender_parity && (
            <div className="flex items-center gap-1 text-ink-700">
              <User className="w-3.5 h-3.5 text-ink-500" />
              <span className="font-semibold">{struct.gender_parity} Parity</span>
            </div>
          )}
        </div>
      </div>

      {/* 13-Digit Administrative Architecture Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
        {/* Box 1: Province & Administrative Codes */}
        <div className="border border-rule bg-paper-1 p-2.5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-ink-500 flex items-center justify-between">
            <span>1st-Digit Province</span>
            {hasProvinceFail ? (
              <span className="text-forensic-red font-bold">INVALID CODE</span>
            ) : struct?.province_code ? (
              <span className="text-emerald-700 font-bold">VALID (1-8)</span>
            ) : null}
          </div>
          <div className="font-mono text-sm font-bold text-ink-900">
            {struct?.province_code ? (
              <span>
                Code {struct.province_code} — {struct.province_name}
              </span>
            ) : hasProvinceFail ? (
              <span className="text-forensic-red">Non-Existent Territory (0 or 9)</span>
            ) : (
              <span className="text-ink-400">Not Decoded</span>
            )}
          </div>
          <div className="text-[10px] text-ink-500 leading-tight">
            NADRA Ordinance 2000 Section 30 mandates strict territorial prefix: 1=KP, 2=FATA, 3=Punjab, 4=Sindh, 5=Balochistan, 6=ICT, 7=GB, 8=AJK.
          </div>
        </div>

        {/* Box 2: 13th-Digit Gender Parity */}
        <div className="border border-rule bg-paper-1 p-2.5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-ink-500 flex items-center justify-between">
            <span>13th Digit Parity</span>
            {hasGenderFail ? (
              <span className="text-forensic-red font-bold">CONTRADICTION</span>
            ) : struct?.check_digit ? (
              <span className="text-emerald-700 font-bold">CONFORMING</span>
            ) : null}
          </div>
          <div className="font-mono text-sm font-bold text-ink-900">
            {struct?.check_digit ? (
              <span>
                Digit {struct.check_digit} ({struct.gender_parity})
              </span>
            ) : (
              <span className="text-ink-400">Not Decoded</span>
            )}
          </div>
          <div className="text-[10px] text-ink-500 leading-tight">
            {verification?.gender_explanation || "Statutory gender invariant: Odd terminal digit = Male; Even terminal digit = Female."}
          </div>
        </div>

        {/* Box 3: Family Tree Serial & Division */}
        <div className="border border-rule bg-paper-1 p-2.5 space-y-1.5">
          <div className="text-[10px] uppercase font-bold text-ink-500 flex items-center justify-between">
            <span>Administrative Invariant</span>
            <span className="text-ink-500">5-7-1 Format</span>
          </div>
          <div className="font-mono text-xs text-ink-800 space-y-0.5">
            <div>
              <span className="text-ink-500">Family Number: </span>
              <span className="font-semibold">{struct?.family_number || "—"}</span>
            </div>
            <div>
              <span className="text-ink-500">Tehsil Code: </span>
              <span className="font-semibold">{struct?.tehsil_code || "—"}</span>
            </div>
          </div>
          <div className="text-[10px] text-ink-500 leading-tight">
            Middle 7-digits correlate directly with family tree registry under the national registration database.
          </div>
        </div>
      </div>

      {/* Smart CNIC Reverse Machine Readable Zone (MRZ) - ICAO 9303 Part 5 */}
      {mrz && mrz.mrz_detected && (
        <div className="border border-rule bg-paper-1 p-3 space-y-3">
          <div className="flex flex-wrap items-center justify-between border-b border-rule pb-2 gap-2 text-xs">
            <div className="flex items-center gap-1.5">
              <Barcode className="w-4 h-4 text-ink-700" />
              <span className="font-bold uppercase text-ink-900">
                Smart CNIC Machine Readable Zone (ICAO Doc 9303 TD1)
              </span>
            </div>

            {mrz.is_valid && !hasMrzChecksumFail && !hasMrzMismatchFail ? (
              <div className="px-2 py-0.5 bg-emerald-500/10 text-emerald-800 border border-emerald-500/30 text-[10px] font-bold">
                ✓ 7-3-1 MODULUS-10 CHECKSUMS SATISFIED
              </div>
            ) : (
              <div className="px-2 py-0.5 bg-rose-500/10 text-forensic-red border border-forensic-red/30 text-[10px] font-bold">
                ✕ ICAO 9303 CHECKSUM / VIZ MISMATCH
              </div>
            )}
          </div>

          {/* Raw MRZ 3 Lines */}
          {mrz.raw_lines && mrz.raw_lines.length > 0 && (
            <div className="bg-ink-900 text-paper-0 p-2.5 font-mono text-[11px] leading-relaxed tracking-wider border border-ink-950">
              <div className="text-[9px] uppercase text-ink-400 mb-1">Raw Optical TD1 Lines:</div>
              {mrz.raw_lines.map((line, idx) => (
                <div key={idx} className="overflow-x-auto whitespace-pre">
                  {line}
                </div>
              ))}
            </div>
          )}

          {/* ICAO Field Checksum Indicators */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
            <div className="border border-rule bg-paper-0 p-2 space-y-1">
              <span className="text-[9px] uppercase text-ink-500 font-bold block">Doc Number Check</span>
              <div className="flex items-center justify-between">
                <span className="font-bold">
                  {mrz.document_number?.check_digit ?? "—"} (Calc: {mrz.document_number?.calculated ?? "—"})
                </span>
                {mrz.document_number?.is_valid ? (
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-forensic-red" />
                )}
              </div>
            </div>

            <div className="border border-rule bg-paper-0 p-2 space-y-1">
              <span className="text-[9px] uppercase text-ink-500 font-bold block">DOB Check Digit</span>
              <div className="flex items-center justify-between">
                <span className="font-bold">
                  {mrz.date_of_birth?.check_digit ?? "—"} (Calc: {mrz.date_of_birth?.calculated ?? "—"})
                </span>
                {mrz.date_of_birth?.is_valid ? (
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-forensic-red" />
                )}
              </div>
            </div>

            <div className="border border-rule bg-paper-0 p-2 space-y-1">
              <span className="text-[9px] uppercase text-ink-500 font-bold block">Expiry Check Digit</span>
              <div className="flex items-center justify-between">
                <span className="font-bold">
                  {mrz.expiry_date?.check_digit ?? "—"} (Calc: {mrz.expiry_date?.calculated ?? "—"})
                </span>
                {mrz.expiry_date?.is_valid ? (
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-forensic-red" />
                )}
              </div>
            </div>

            <div className="border border-rule bg-paper-0 p-2 space-y-1">
              <span className="text-[9px] uppercase text-ink-500 font-bold block">Composite Check</span>
              <div className="flex items-center justify-between">
                <span className="font-bold">
                  {mrz.composite_check?.check_digit ?? "—"} (Calc: {mrz.composite_check?.calculated ?? "—"})
                </span>
                {mrz.composite_check?.is_valid ? (
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-forensic-red" />
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Identified Anomalies & Violations */}
      {(hasProvinceFail || hasGenderFail || hasMrzChecksumFail || hasMrzMismatchFail || hasTemporalFail) && (
        <div className="border border-forensic-red/50 bg-rose-500/5 p-3 space-y-2 text-xs">
          <div className="flex items-center gap-1.5 font-bold text-forensic-red uppercase">
            <AlertTriangle className="w-4 h-4" />
            <span>Forensic Tampering & Identity Violations</span>
          </div>
          <div className="space-y-1 text-ink-800 text-[11px]">
            {hasProvinceFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-forensic-red font-bold">●</span>
                <span>
                  <strong>Province Code Violation:</strong> CNIC first digit does not map to any legitimate Pakistani administrative territory. Violates NADRA Ordinance 2000 Section 30.
                </span>
              </div>
            )}
            {hasGenderFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-forensic-red font-bold">●</span>
                <span>
                  <strong>Gender Parity Contradiction:</strong> 13th digit check parity directly contradicts declared sex or title (Mr./Mrs./Ms.). Indication of synthetic identity generation.
                </span>
              </div>
            )}
            {hasMrzChecksumFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-forensic-red font-bold">●</span>
                <span>
                  <strong>ICAO 9303 Checksum Failure:</strong> Reverse 3-line TD1 Machine Readable Zone fails repeating 7-3-1 modulus-10 algorithm. Confirms fabricated MRZ data block.
                </span>
              </div>
            )}
            {hasMrzMismatchFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-forensic-red font-bold">●</span>
                <span>
                  <strong>VIZ vs MRZ Splicing Discrepancy:</strong> Card front identity number diverges from reverse machine-readable optical string, indicating physical or graphic credential splicing.
                </span>
              </div>
            )}
            {hasTemporalFail && (
              <div className="flex items-start gap-1.5">
                <span className="text-amber-700 font-bold">●</span>
                <span>
                  <strong>Temporal Inconsistency:</strong> Issuance date, date of birth, or expiration date violates standard NADRA lifespan invariants.
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Statutory Footer Citation */}
      <div className="text-[10px] text-ink-500 border-t border-rule pt-2 flex flex-wrap justify-between items-center gap-2">
        <span>
          Statutory Authority: National Database and Registration Authority Ordinance, 2000 (§30) | ICAO Doc 9303 Part 5 (TD1)
        </span>
        <span className="font-semibold uppercase tracking-wider text-ink-600">
          Zero-Hallucination Deterministic Engine
        </span>
      </div>
    </div>
  );
}
