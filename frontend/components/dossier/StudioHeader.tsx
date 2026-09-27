"use client";

import React from "react";
import { Masthead } from "@/components/editorial/Masthead";
import { AlertTriangle, Columns, FileText, ShieldCheck, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface StudioHeaderProps {
  caseNumber: string;
  caseTitle: string;
  documentType: string;
  isSample: boolean;
  isFinancial: boolean;
  viewMode: "split" | "dossier";
  onViewModeChange: (mode: "split" | "dossier") => void;
}

function getRegulatoryStatus(type: string) {
  switch (type) {
    case "BANK_STATEMENT":
      return {
        chipLabel: "SBP ENFORCED",
        shortText: "SBP Clearing Standard: Enforced • Running Balance Reconciliation: Active",
        items: [
          "SBP Clearing Standard: Enforced",
          "Running Balance Reconciliation: Active",
          "BPRD Circular 03/2018 & AML Compliance Active",
        ],
      };
    case "UTILITY_BILL":
      return {
        chipLabel: "TARIFF AUDIT",
        shortText: "Utility Tariff Audit: Enforced • K-Electric / Billing Reconciliation: Active",
        items: [
          "Utility Tariff Audit: Enforced",
          "K-Electric / Billing Reconciliation: Active",
          "PITC Utility Registry Verification Active",
        ],
      };
    case "SALARY_SLIP":
      return {
        chipLabel: "PAYROLL AUDIT",
        shortText: "Employment Payroll Audit: Enforced • Dual-Column Earnings/Deductions: Active",
        items: [
          "Employment Payroll Audit: Enforced",
          "Dual-Column Earnings/Deductions: Active",
          "Statutory Withholding Tax Bracket Check Active",
        ],
      };
    case "TAX_CERTIFICATE":
      return {
        chipLabel: "FBR REGISTER",
        shortText: "FBR CPR Payment Receipt: Enforced • NTN Tax Register: Active",
        items: [
          "FBR CPR Payment Receipt: Enforced",
          "NTN Tax Register: Active",
          "Modulus-11 Verification Active",
        ],
      };
    case "IDENTITY_DOCUMENT":
      return {
        chipLabel: "NADRA VERISYS",
        shortText: "NADRA Verisys / ICAO 9303: Enforced • Security Thread & MRZ Audit: Active",
        items: [
          "NADRA Verisys / ICAO 9303: Enforced",
          "Security Thread & MRZ Audit: Active",
          "Administrative Gender Parity Active",
        ],
      };
    default:
      return {
        chipLabel: "FORENSIC SPEC",
        shortText: "Digital Forensics Standards: Enforced",
        items: ["Digital Forensics Standards: Enforced"],
      };
  }
}

export function StudioHeader({
  caseNumber,
  caseTitle,
  documentType,
  isSample,
  isFinancial,
  viewMode,
  onViewModeChange,
}: StudioHeaderProps) {
  const regStatus = getRegulatoryStatus(documentType);

  return (
    <header className="shrink-0">
      {/* Editorial Top Masthead (Bars 1 & 2, docket banner suppressed for single merged bar) */}
      <Masthead
        documentType={documentType}
        showDocketBanner={false}
      />

      {/* Persistent Demonstration Banner for Sample Exhibit */}
      {isSample && (
        <div className="bg-amber-100 border-b-2 border-ink-900 px-4 py-2 font-mono text-xs text-ink-900 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-800 shrink-0" />
            <span className="text-[11px]">
              <strong>DEMONSTRATION EXHIBIT &mdash; SYNTHETIC BENCHMARK DATA.</strong>{" "}
              All document pages, ledger amounts, and risk scores are simulated for orientation and testing.
            </span>
          </div>
          <span className="px-2 py-0.5 bg-ink-900 text-paper-0 text-[10px] font-bold uppercase tracking-widest shrink-0 ml-4">
            Synthetic Benchmark
          </span>
        </div>
      )}

      {/* Merged Docket & Workbench Sub-Header Ribbon */}
      <div className="bg-paper-1 border-b border-rule px-4 py-1.5 flex items-center justify-between flex-wrap gap-2 font-mono text-xs select-none min-h-[38px]">
        {/* Left: Active Docket Tag, ID, Title, Engine Status & Regulatory Tooltip */}
        <div className="flex items-center gap-2.5 min-w-0 flex-wrap">
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="w-2 h-2 rounded-full bg-forensic-teal" />
            <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider">
              DOCKET:
            </span>
            <span className="font-bold text-ink-900 bg-paper-0 px-2 py-0.5 border border-rule text-xs">
              {caseNumber}
            </span>
          </div>

          {caseTitle && (
            <span
              className="text-ink-700 font-serif text-xs hidden sm:inline border-l border-rule pl-2.5 truncate max-w-[200px] md:max-w-xs lg:max-w-md"
              title={caseTitle}
            >
              {caseTitle}
            </span>
          )}

          {isFinancial ? (
            <span className="bg-paper-0 border border-forensic-teal/60 text-forensic-teal text-[11px] px-2 py-0.5 font-bold uppercase tracking-wider shrink-0 hidden md:inline">
              LEDGER ENGINE ACTIVE
            </span>
          ) : (
            <span className="text-ink-700 font-bold text-[11px] hidden md:inline shrink-0">
              ({documentType})
            </span>
          )}

          {/* Status Tooltip Chip (Decorations moved here from top bar) */}
          <div className="relative group shrink-0">
            <div
              className="flex items-center gap-1.5 px-2 py-0.5 bg-paper-0 border border-rule hover:border-ink-900 text-ink-800 hover:text-ink-900 text-[11px] font-mono font-bold transition-colors cursor-help select-none"
              title={regStatus.shortText}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span className="hidden xl:inline text-[11px] font-bold text-emerald-800">
                {regStatus.chipLabel}
              </span>
              <Info className="w-3 h-3 text-ink-500" />
            </div>

            {/* Hover Tooltip Popover */}
            <div className="absolute left-0 top-full mt-1.5 hidden group-hover:block z-50 w-80 p-3 bg-ink-900 text-paper-0 shadow-2xl border border-ink-700 text-[11px] leading-relaxed pointer-events-none font-mono">
              <div className="font-bold text-forensic-amber uppercase tracking-wider text-[11px] mb-2 flex items-center justify-between">
                <span>Regulatory & Verification Status</span>
                <span className="text-emerald-400 font-bold">● ACTIVE</span>
              </div>
              <div className="text-paper-1 space-y-1">
                {regStatus.items.map((it, idx) => (
                  <div key={idx} className="flex items-start gap-1.5">
                    <span className="text-emerald-400 shrink-0 font-bold">✓</span>
                    <span>{it}</span>
                  </div>
                ))}
              </div>
              <div className="mt-2 pt-1.5 border-t border-ink-800 text-[11px] text-paper-2 font-medium">
                Continuous background audit decoration (NIST SP 800-86).
              </div>
            </div>
          </div>
        </div>

        {/* Right: View Mode Toggle Controls */}
        <div className="flex items-center gap-1 bg-paper-0 border border-rule p-0.5 shrink-0">
          {isFinancial && (
            <button
              onClick={() => onViewModeChange("split")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1 text-[11px] uppercase font-bold transition-all select-none cursor-pointer",
                viewMode === "split"
                  ? "bg-ink-900 text-paper-0 shadow-sm"
                  : "text-ink-600 hover:text-ink-900 hover:bg-paper-1"
              )}
              title="Interactive Side-by-Side PDF Canvas & Mathematical Ledger"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Split Evidence Workbench</span>
            </button>
          )}
          <button
            onClick={() => onViewModeChange("dossier")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1 text-[11px] uppercase font-bold transition-all select-none cursor-pointer",
              viewMode === "dossier" || !isFinancial
                ? "bg-ink-900 text-paper-0 shadow-sm"
                : "text-ink-600 hover:text-ink-900 hover:bg-paper-1"
            )}
            title="Complete Forensic Findings, Custody Chain & Pipeline Telemetry"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Full Audit Dossier</span>
          </button>
        </div>
      </div>
    </header>
  );
}
