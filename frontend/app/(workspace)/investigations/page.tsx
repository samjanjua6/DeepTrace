"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Masthead } from "@/components/editorial/Masthead";
import { FolioTag } from "@/components/editorial/FolioTag";
import { HairlineRule } from "@/components/editorial/HairlineRule";
import { getInvestigations } from "@/lib/api/client";
import { formatDatePKT } from "@/lib/formatters";
import {
  AlertTriangle,
  RotateCcw,
  FileText,
  Loader2,
  Plus,
  ShieldAlert,
} from "lucide-react";

interface DocketItem {
  id: string;
  caseNumber: string;
  title: string;
  status: string;
  riskScore: number | null;
  riskTier: string;
  directive: string;
  sha256: string;
  pages: number;
  createdAt: string;
}

export default function InvestigationsDocketPage() {
  const [investigations, setInvestigations] = useState<DocketItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

  const loadInvestigations = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiData = await getInvestigations();
      const formatted: DocketItem[] = (apiData || []).map((inv) => ({
        id: inv.id,
        caseNumber: inv.caseNumber,
        title: inv.title,
        status: inv.status,
        riskScore: inv.riskAssessment?.overallScore ?? null,
        riskTier: inv.riskAssessment?.riskTier ?? "PENDING",
        directive:
          inv.riskAssessment?.actionDirective ??
          (inv.status === "PROCESSING" ? "PROCESSING" : "PENDING_ASSESSMENT"),
        sha256: inv.documents?.[0]?.sha256Hash
          ? inv.documents[0].sha256Hash.substring(0, 16) + "..."
          : "—",
        pages: inv.documents?.[0]?.pageCount || 1,
        createdAt: inv.createdAt,
      }));
      setInvestigations(formatted);
    } catch (err: any) {
      setError(
        err?.message ||
          "Failed to establish communication with DeepTrace forensic repository."
      );
      setInvestigations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvestigations();
  }, []);

  const filtered = investigations.filter((inv) => {
    if (filter === "ALL") return true;
    if (filter === "CRITICAL") return inv.riskTier === "CRITICAL";
    if (filter === "HIGH") return inv.riskTier === "HIGH";
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

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={loadInvestigations}
              disabled={loading}
              className="p-2.5 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-700 transition-colors cursor-pointer"
              title="Refresh Case Registry"
            >
              <RotateCcw
                className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
              />
            </button>
            <Link
              href="/investigations/new"
              className="px-6 py-2.5 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold transition-colors inline-flex items-center gap-2"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>+ Intake New Document</span>
            </Link>
          </div>
        </div>

        <HairlineRule className="my-6" />

        {/* Loading State */}
        {loading && (
          <div className="bg-paper-1 border border-rule p-12 text-center font-mono text-xs text-ink-600 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-6 h-6 animate-spin text-ink-900" />
            <span className="uppercase tracking-widest text-[11px] font-semibold">
              Querying Institutional Forensics Repository...
            </span>
          </div>
        )}

        {/* Error State: Explicit Failure (No Silent Sample Data Masking) */}
        {!loading && error && (
          <div className="bg-paper-0 border-2 border-rose-900 p-6 shadow-sm font-mono space-y-4">
            <div className="flex items-center gap-3 border-b border-rose-900/40 pb-3 text-rose-950">
              <ShieldAlert className="w-6 h-6 text-rose-700 shrink-0" />
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-rose-700 block">
                  Communication Failure
                </span>
                <h2 className="text-sm font-bold uppercase tracking-wider">
                  Forensic Repository Connectivity Error
                </h2>
              </div>
            </div>

            <div className="text-xs text-ink-700 space-y-2">
              <p>
                The DeepTrace client was unable to retrieve active case dockets
                from the backend repository.
              </p>
              <div className="p-3 bg-paper-1 border border-rose-300 text-rose-900 font-mono text-[11px]">
                {error}
              </div>
              <p className="text-[11px] text-ink-500">
                Under SBP BPRD/2020 regulatory standards, offline or failed
                repository queries are never masked with simulated sample data.
              </p>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={loadInvestigations}
                className="px-4 py-2 bg-ink-900 text-paper-0 hover:bg-black font-mono text-xs uppercase tracking-wider font-bold transition-colors inline-flex items-center gap-2 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Retry Connection</span>
              </button>
            </div>
          </div>
        )}

        {/* Empty State: Zero Active Dockets in Tenancy */}
        {!loading && !error && investigations.length === 0 && (
          <div className="bg-paper-1 border border-rule p-12 text-center font-mono space-y-4">
            <div className="w-12 h-12 bg-paper-2 border border-rule flex items-center justify-center mx-auto text-ink-400">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-ink-900">
                No Forensic Dockets Found
              </h3>
              <p className="text-xs text-ink-600 mt-1 max-w-md mx-auto">
                This institutional tenancy currently contains zero active case
                dockets. Ingest a financial or statutory document to initiate
                forensic examination.
              </p>
            </div>
            <div className="pt-2">
              <Link
                href="/investigations/new"
                className="px-5 py-2 bg-ink-900 text-paper-0 hover:bg-black font-mono text-xs uppercase tracking-wider font-bold transition-colors inline-flex items-center gap-2"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Intake First Document</span>
              </Link>
            </div>
          </div>
        )}

        {/* Populated State: Table & Filters */}
        {!loading && !error && investigations.length > 0 && (
          <>
            {/* Filter Bar */}
            <div className="flex items-center justify-between mb-4 font-mono text-xs">
              <div className="flex gap-2">
                {["ALL", "CRITICAL", "HIGH", "LOW"].map((f) => {
                  const count =
                    f === "ALL"
                      ? investigations.length
                      : investigations.filter((i) => i.riskTier === f).length;
                  return (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={`px-3 py-1 border transition-colors uppercase cursor-pointer ${
                        filter === f
                          ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                          : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                      }`}
                    >
                      {f} ({count})
                    </button>
                  );
                })}
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
                  {filtered.length === 0 ? (
                    <tr>
                      <td
                        colSpan={7}
                        className="py-8 text-center text-ink-500 text-xs"
                      >
                        No case dockets match the selected &quot;{filter}&quot; filter.
                      </td>
                    </tr>
                  ) : (
                    filtered.map((inv) => (
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
                          {inv.riskScore !== null ? inv.riskScore : "—"}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <span
                            className={`inline-block px-2 py-0.5 border text-[9px] font-bold uppercase tracking-wider ${
                              inv.riskTier === "CRITICAL"
                                ? "bg-forensic-red/10 text-forensic-red border-forensic-red"
                                : inv.riskTier === "HIGH"
                                ? "bg-forensic-amber/10 text-forensic-amber border-forensic-amber"
                                : inv.riskTier === "LOW"
                                ? "bg-forensic-green/10 text-forensic-green border-forensic-green"
                                : "bg-paper-2 text-ink-600 border-rule"
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
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
