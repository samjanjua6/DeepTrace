"use client";

import React from "react";
import { Masthead } from "@/components/editorial/Masthead";
import { Loader2 } from "lucide-react";

interface DocketLoadingViewProps {
  documentType: string;
}

export function DocketLoadingView({ documentType }: DocketLoadingViewProps) {
  return (
    <div className="flex flex-col h-screen w-screen bg-paper-0 text-ink-900 font-mono">
      <Masthead
        caseNumber="LOADING"
        caseTitle="Retrieving Forensic Docket..."
        documentType={documentType}
      />
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin text-ink-900 mb-3" />
        <span className="text-xs uppercase tracking-widest text-ink-600 font-semibold">
          Reconciling Forensic Chain-of-Custody Ledger...
        </span>
      </div>
    </div>
  );
}
