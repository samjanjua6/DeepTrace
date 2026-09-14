"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Masthead } from "@/components/editorial/Masthead";
import { FolioTag } from "@/components/editorial/FolioTag";
import { HairlineRule } from "@/components/editorial/HairlineRule";
import { Investigation } from "@/lib/types/forensics";
import { getInvestigations } from "@/lib/api/client";
import { formatDatePKT } from "@/lib/formatters";

// Default authentic sample dockets for immediate display
const SAMPLE_DOCKETS: any[] = [
  {
    id: "sample",
    caseNumber: "DT-PK-2026-000001",
    title: "Meezan Bank Limited — Corporate Facilities Statement Exhibit",
    status: "REVIEW_REQUIRED",
    riskScore: 85,
    riskTier: "CRITICAL",
    directive: "IMMEDIATE_REJECTION",
    sha256: "97dd4aa213113a69a0d5...",
    pages: 2,
    createdAt: "2026-09-09T10:00:00Z",
  },
  {
    id: "sample-hbl",
    caseNumber: "DT-PK-2026-000002",
    title: "Habib Bank Limited (HBL) — Commercial Credit Application",
    status: "CLEARED",
    riskScore: 8,
    riskTier: "LOW",
    directive: "STRAIGHT_THROUGH_APPROVAL",
    sha256: "4b87e29a9f018cd...",
    pages: 1,
    createdAt: "2026-09-09T11:30:00Z",
  },
  {
    id: "sample-alfh",
    caseNumber: "DT-PK-2026-000003",
    title: "Bank Alfalah — SBP Clearing IBAN Verification Audit",
    status: "FAILED_CHECKSUM",
    riskScore: 68,
    riskTier: "HIGH",
    directive: "MANUAL_SUPERVISOR_REVIEW",
    sha256: "c18f92100e4b789...",
    pages: 1,
    createdAt: "2026-09-09T13:15:00Z",
  },
];

export default function InvestigationsDocketPage() {
  const [investigations, setInvestigations] = useState<any[]>(SAMPLE_DOCKETS);
  const [filter, setFilter] = useState<string>("ALL");

  useEffect(() => {
    async function load() {
      try {
        const apiData = await getInvestigations();
        if (apiData && apiData.length > 0) {
          // Merge real cases with sample cases
          const formatted = apiData.map((inv) => ({
            id: inv.id,
            caseNumber: inv.caseNumber,
            title: inv.title,
            status: inv.status,
            riskScore: inv.riskAssessment?.overallScore ?? 50,
            riskTier: inv.riskAssessment?.riskTier ?? "MEDIUM",
            directive:
              inv.riskAssessment?.actionDirective ?? "MANUAL_SUPERVISOR_REVIEW",
            sha256: inv.documents?.[0]?.sha256Hash?.substring(0, 16) + "...",
            pages: inv.documents?.[0]?.pageCount || 1,
            createdAt: inv.createdAt,
          }));
          setInvestigations(formatted);
        }
      } catch {
        // Keeps sample dockets
      }
    }
    load();
  }, []);

  const filtered = investigations.filter((inv) => {
    if (filter === "ALL") return true;
    if (filter === "CRITICAL") return inv.riskTier === "CRITICAL";
    if (filter === "LOW") return inv.riskTier === "LOW";
    return true;
  });

  return (
    <div className="min-h-screen bg-paper-0 text-ink-900 flex flex-col font-sans">
      <Masthead />

      <main className="flex-1 max-w-6xl w-full mx-auto p-6 md:p-12">
        <div className="flex items-baseline justify-between flex-wrap gap-4">
          <div>
            <FolioTag
              section="§ 02"
              label="INSTITUTIONAL CASE REGISTER & RISK DOCKET"
            />
            <h1 className="font-serif text-3xl md:text-5xl text-ink-900 font-normal tracking-tight mt-2">
              Case Docket
            </h1>
          </div>

          <Link
            href="/investigations/new"
            className="px-6 py-2.5 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold transition-colors"
          >
            + Intake New Document
          </Link>
        </div>

        <HairlineRule className="my-6" />

        {/* Filter Bar */}
        <div className="flex items-center justify-between mb-4 font-mono text-xs">
          <div className="flex gap-2">
            {["ALL", "CRITICAL", "LOW"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 border transition-colors uppercase ${
                  filter === f
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                {f} ({f === "ALL" ? investigations.length : investigations.filter((i) => i.riskTier === f).length})
              </button>
            ))}
          </div>

          <span className="text-ink-500 text-[11px]">
            ACTIVE TENANT: SBP REGULATED ENTITY
          </span>
        </div>

        {/* Docket Broadside Table */}
        <div className="bg-paper-0 border border-rule overflow-hidden">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="bg-paper-1 border-b border-rule text-[10px] text-ink-500 uppercase tracking-wider">
                <th className="py-3 px-4">Case Docket No.</th>
                <th className="py-3 px-4">Entity & Investigation Title</th>
                <th className="py-3 px-4 text-center">Score</th>
                <th className="py-3 px-4 text-center">Risk Tier</th>
                <th className="py-3 px-4">Action Directive</th>
                <th className="py-3 px-4">Acquired Date (PKT)</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule text-[11px]">
              {filtered.map((inv) => (
                <tr
                  key={inv.id}
                  className="hover:bg-paper-1/60 transition-colors"
                >
                  <td className="py-3.5 px-4 font-semibold text-ink-900 whitespace-nowrap">
                    {inv.caseNumber}
                  </td>
                  <td className="py-3.5 px-4 font-serif text-sm text-ink-900">
                    {inv.title}
                  </td>
                  <td className="py-3.5 px-4 text-center font-bold tabular-nums text-base">
                    {inv.riskScore}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <span
                      className={`inline-block px-2 py-0.5 border text-[9px] font-bold uppercase tracking-wider ${
                        inv.riskTier === "CRITICAL"
                          ? "bg-forensic-red/10 text-forensic-red border-forensic-red"
                          : inv.riskTier === "HIGH"
                          ? "bg-forensic-amber/10 text-forensic-amber border-forensic-amber"
                          : "bg-forensic-green/10 text-forensic-green border-forensic-green"
                      }`}
                    >
                      {inv.riskTier}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-ink-700 text-[10px] uppercase font-semibold">
                    {inv.directive.replace(/_/g, " ")}
                  </td>
                  <td className="py-3.5 px-4 tabular-nums text-ink-500 whitespace-nowrap">
                    {formatDatePKT(inv.createdAt)}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      href={`/investigations/${inv.id}`}
                      className="px-3 py-1 bg-paper-1 hover:bg-paper-2 border border-rule text-ink-900 font-semibold uppercase text-[10px] tracking-wider transition-colors inline-block"
                    >
                      Open Studio →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
