"use client";

import React from "react";
import { FileText, Layers, PieChart } from "lucide-react";

interface DocumentBreakdownCardProps {
  breakdown: Record<string, number>;
  totalUsed: number;
}

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  BANK_STATEMENT: "Bank Account Statements",
  SALARY_SLIP: "Salary & Payroll Slips",
  TAX_CERTIFICATE: "FBR Tax Certificates & Challans",
  UTILITY_BILL: "Utility Bills (K-Electric / SNGPL)",
  IDENTITY_DOCUMENT: "NADRA Identity Documents (CNIC)",
  COMMERCIAL_INVOICE: "Commercial Trade Invoices",
  DIGITAL_WALLET_LEDGER: "Fintech Wallet Ledgers (Easypaisa/JazzCash)",
  OTHER: "General Legal Evidences",
};

export function DocumentBreakdownCard({ breakdown, totalUsed }: DocumentBreakdownCardProps) {
  const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);

  return (
    <div className="bg-paper-0 border-2 border-ink-900 p-6 font-mono shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-rule pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-ink-900 text-paper-0">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Classification Breakdown
            </span>
            <h3 className="text-base font-bold uppercase tracking-wider text-ink-900">
              Intake by Document Category
            </h3>
          </div>
        </div>

        <span className="text-xs text-ink-500">
          {totalUsed.toLocaleString()} Total Ingested
        </span>
      </div>

      {entries.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-rule bg-paper-1">
          <FileText className="w-6 h-6 text-ink-400 mx-auto mb-2" />
          <span className="text-xs text-ink-500 uppercase tracking-wider block">
            No Documents Ingested This Billing Cycle
          </span>
          <span className="text-[11px] text-ink-400 mt-1 block">
            Documents submitted to case dockets will populate classification analytics automatically.
          </span>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map(([dtype, count]) => {
            const label = DOCUMENT_TYPE_LABELS[dtype] || dtype;
            const pct = totalUsed > 0 ? Math.round((count / totalUsed) * 100) : 0;

            return (
              <div key={dtype} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="font-bold text-ink-900">{label}</span>
                  <span className="text-ink-600 font-mono">
                    {count.toLocaleString()} ({pct}%)
                  </span>
                </div>
                <div className="w-full h-2 bg-paper-2 border border-rule overflow-hidden">
                  <div
                    className="h-full bg-ink-900 transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
