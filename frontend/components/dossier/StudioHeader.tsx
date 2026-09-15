"use client";

import React from "react";
import { Masthead } from "@/components/editorial/Masthead";
import { AlertTriangle, Columns, FileText } from "lucide-react";
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

export function StudioHeader({
  caseNumber,
  caseTitle,
  documentType,
  isSample,
  isFinancial,
  viewMode,
  onViewModeChange,
}: StudioHeaderProps) {
  return (
    <header className="shrink-0">
      {/* Editorial Top Masthead */}
      <Masthead
        caseNumber={caseNumber}
        caseTitle={caseTitle}
        documentType={documentType}
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

      {/* Workbench Sub-Header Ribbon with View Switcher */}
      <div className="bg-paper-1 border-b border-rule px-4 py-2 flex items-center justify-between font-mono text-xs select-none">
        <div className="flex items-center gap-3">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-ink-600 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-forensic-teal" />
            WORKBENCH VIEW
          </span>
          <span className="text-rule">|</span>
          <span className="text-[11px] text-ink-700">
            {documentType === "BANK_STATEMENT"
              ? "Pakistani Core Banking & Ledger Verification Workspace"
              : `Forensic Document Examination (${documentType})`}
          </span>
          {isFinancial && (
            <span className="bg-paper-0 border border-forensic-teal/40 text-forensic-teal text-[10px] px-2 py-0.5 font-bold uppercase tracking-wider">
              LEDGER ENGINE ACTIVE
            </span>
          )}
        </div>

        {/* View Mode Toggle Controls */}
        <div className="flex items-center gap-1 bg-paper-0 border border-rule p-0.5">
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
