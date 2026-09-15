"use client";

import React from "react";
import Link from "next/link";
import { Masthead } from "@/components/editorial/Masthead";
import { ShieldAlert, ArrowLeft } from "lucide-react";

interface DocketErrorViewProps {
  investigationId: string;
  documentType: string;
  fetchError: string | null;
}

export function DocketErrorView({
  investigationId,
  documentType,
  fetchError,
}: DocketErrorViewProps) {
  return (
    <div className="flex flex-col h-screen w-screen bg-paper-0 text-ink-900 font-mono">
      <Masthead
        caseNumber="ERROR"
        caseTitle="Forensic Case Docket Inaccessible"
        documentType={documentType}
      />
      <main className="flex-1 max-w-2xl mx-auto p-6 flex flex-col justify-center">
        <div className="bg-paper-0 border-2 border-rose-900 p-8 shadow-2xl space-y-4">
          <div className="flex items-center gap-3 border-b border-rose-900/40 pb-4 text-rose-950">
            <ShieldAlert className="w-6 h-6 text-rose-700 shrink-0" />
            <div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-rose-700 block">
                Docket Error [404 / Unavailable]
              </span>
              <h1 className="text-base font-bold uppercase tracking-wider">
                Forensic Case Docket Inaccessible
              </h1>
            </div>
          </div>
          <p className="text-xs text-ink-700 leading-relaxed">
            The requested investigation docket (
            <span className="font-bold text-ink-900">{investigationId}</span>)
            could not be retrieved from the central institutional repository.
          </p>
          <div className="p-3 bg-paper-1 border border-rose-300 text-rose-900 text-xs">
            {fetchError || "Docket record not found or clearance denied."}
          </div>
          <p className="text-[11px] text-ink-500">
            Under SBP BPRD/2020 regulatory compliance, DeepTrace does not
            fabricate synthetic docket data when a requested case cannot be
            located.
          </p>
          <div className="pt-4 border-t border-rule flex items-center gap-4">
            <Link
              href="/investigations"
              className="px-4 py-2 bg-ink-900 text-paper-0 hover:bg-black text-xs font-bold uppercase tracking-wider transition-colors inline-flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Return to Case Register</span>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
