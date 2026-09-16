"use client";

import React from "react";
import { AlertTriangle, Lock } from "lucide-react";

export function SecurityComplianceBanner() {
  return (
    <div className="bg-paper-1 border border-ink-900/80 p-3.5 font-mono text-xs space-y-2 mb-6 select-none">
      <div className="flex items-center justify-between text-ink-900 border-b border-rule/80 pb-1.5 font-bold uppercase tracking-wider text-[10.5px]">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-forensic-amber shrink-0" />
          <span>STATUTORY SECURITY ADVISORY & PENAL WARNING</span>
        </div>
        <span className="text-[9px] px-1.5 py-0.2 bg-ink-900 text-paper-0 font-bold">
          PECA 2016 §3
        </span>
      </div>

      <p className="text-[11px] text-ink-900 font-semibold leading-relaxed">
        Unauthorized access to bank document verification infrastructure is
        punishable under Section 3 of PECA 2016.
      </p>

      <div className="text-[10px] text-ink-600 leading-snug space-y-1">
        <p>
          State Bank of Pakistan Enterprise Cyber Security Framework (BPRD
          Circular No. 05 of 2020): All terminal sessions, hardware identifiers,
          and cryptographic tokens are recorded into an immutable audit chain
          under ETO 2002 §29/§30 and QSO 1984 Art 164.
        </p>
      </div>
    </div>
  );
}
