"use client";

import React from "react";
import { AlertTriangle, ChevronDown } from "lucide-react";

export function SecurityComplianceBanner() {
  return (
    <details className="group bg-paper-1 border border-ink-900/80 p-2 font-mono text-xs mb-2.5 select-none">
      <summary className="flex items-center justify-between text-ink-900 font-bold uppercase tracking-wider text-[11px] cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-forensic-amber shrink-0" />
          <span>STATUTORY SECURITY ADVISORY</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] px-1.5 py-0.5 bg-ink-900 text-paper-0 font-bold shrink-0">
            PECA 2016 §3
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-ink-500 group-open:rotate-180 transition-transform shrink-0" />
        </div>
      </summary>

      <div className="pt-2 mt-2 border-t border-rule/80 space-y-1.5 text-[11px] leading-tight">
        <p className="text-ink-900 font-semibold">
          Unauthorized access to bank document verification infrastructure is
          punishable under Section 3 of PECA 2016.
        </p>
        <p className="text-ink-600">
          State Bank of Pakistan Enterprise Cyber Security Framework (BPRD
          Circular No. 05 of 2020): All terminal sessions, hardware identifiers,
          and cryptographic tokens are recorded into an immutable audit chain
          under ETO 2002 §29/§30 and QSO 1984 Art 164.
        </p>
      </div>
    </details>
  );
}

