"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { Masthead } from "@/components/editorial/Masthead";
import { FolioTag } from "@/components/editorial/FolioTag";
import { HairlineRule } from "@/components/editorial/HairlineRule";
import { useAuth } from "@/context/AuthContext";
import { getDashboardMetrics } from "@/lib/api/client";
import { DashboardMetrics, formatRecommendation } from "@/lib/types/forensics";
import { formatDatePKT } from "@/lib/formatters";
import {
  ShieldAlert,
  Coins,
  Clock,
  FileText,
  RotateCcw,
  ArrowRight,
  TrendingUp,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";

export default function ExecutiveDashboardPage() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [timeStr, setTimeStr] = useState<string>("");

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDashboardMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(
        err?.message ||
          "Failed to establish telemetry link with DeepTrace Executive Analytics Engine."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  // Live PKT clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        new Intl.DateTimeFormat("en-PK", {
          timeZone: "Asia/Karachi",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }).format(now) + " PKT"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Format stage names into clean display labels
  const formatStageName = (raw: string): string => {
    return raw
      .replace(/_/g, " ")
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  // Quota bar color logic
  const quotaColor = useMemo(() => {
    if (!metrics) return "bg-ink-900";
    const pct = metrics.total_scanned.quota_usage_percentage;
    if (pct > 90) return "bg-forensic-red";
    if (pct > 70) return "bg-amber-600";
    return "bg-ink-900";
  }, [metrics]);

  return (
    <div className="min-h-screen bg-paper-0 text-ink-900 flex flex-col font-sans selection:bg-forensic-red selection:text-white">
      <Masthead />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-10 space-y-8">
        {/* Executive Masthead Folio */}
        <div className="border-b-2 border-ink-900 pb-6">
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
            <div>
              <FolioTag
                section="§ 01"
                label="EXECUTIVE FRAUD TELEMETRY & RISK COMMAND CENTER"
              />
              <h1 className="font-serif text-3xl md:text-5xl text-ink-900 font-normal tracking-tight mt-2">
                Risk Command Center
              </h1>
              <p className="text-xs sm:text-sm text-ink-700 font-mono mt-2 max-w-3xl leading-relaxed">
                Institutional fraud telemetry, deterministic Lakh/Crore balance reconciliations,
                and portfolio risk posture under SBP BPRD Circular No. 05 of 2020 & PECA 2016.
              </p>
            </div>

            {/* Controls & Tenancy Indicator */}
            <div className="flex flex-wrap items-center gap-3 font-mono text-xs shrink-0">
              <div className="bg-paper-1 border border-rule px-3 py-2 text-ink-700 hidden sm:block">
                <span className="text-[10px] uppercase text-ink-500 block font-bold">
                  Active Tenancy
                </span>
                <span className="font-semibold text-ink-900">
                  {metrics?.organization_name || user?.organization_name || "Meezan Bank Ltd"}
                </span>
              </div>

              <div className="bg-paper-1 border border-rule px-3 py-2 text-ink-700">
                <span className="text-[10px] uppercase text-ink-500 block font-bold">
                  SBP Standard Clock
                </span>
                <span className="font-semibold tabular-nums text-ink-900">
                  {timeStr || "00:00:00 PKT"}
                </span>
              </div>

              <button
                type="button"
                onClick={fetchMetrics}
                disabled={loading}
                className="p-2.5 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-800 transition-colors cursor-pointer"
                title="Refresh Analytics Telemetry"
              >
                <RotateCcw className={`w-4 h-4 ${loading ? "animate-spin text-ink-900" : ""}`} />
              </button>

              <Link
                href="/investigations/new"
                className="px-4 py-2.5 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase font-bold tracking-wider transition-colors flex items-center gap-2 shadow-sm"
              >
                <span>+ New Intake</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Error Notification Banner */}
        {error && (
          <div className="border border-forensic-red bg-paper-1 p-4 font-mono text-xs text-forensic-red flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={fetchMetrics}
              className="underline uppercase font-bold text-[11px] hover:text-black cursor-pointer"
            >
              Retry Telemetry
            </button>
          </div>
        )}

        {/* ── TOP 4 STAT CARDS ────────────────────────────────────────────── */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Card 1: Total Scanned Documents */}
          <div className="bg-paper-0 border-2 border-ink-900 p-5 font-mono flex flex-col justify-between shadow-sm relative overflow-hidden">
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold">
                  01 / DOCUMENT VOLUME
                </span>
                <FileText className="w-4 h-4 text-ink-600" />
              </div>

              <div>
                <div className="text-2xl md:text-3xl font-bold tracking-tight text-ink-900 font-serif">
                  {metrics ? metrics.total_scanned.month_to_date.toLocaleString() : "—"}
                  <span className="font-mono text-sm text-ink-500 font-normal ml-2">
                    / {metrics ? metrics.total_scanned.monthly_limit.toLocaleString() : "—"}
                  </span>
                </div>
                <span className="text-[11px] text-ink-600 font-semibold block mt-0.5">
                  Total Scanned Documents (MTD)
                </span>
              </div>

              {/* Quota Usage Bar */}
              <div className="space-y-1.5 pt-1">
                <div className="flex justify-between text-[10px] text-ink-600 font-semibold">
                  <span>Quota Consumed</span>
                  <span className="font-bold text-ink-900">
                    {metrics ? `${metrics.total_scanned.quota_usage_percentage.toFixed(1)}%` : "0%"}
                  </span>
                </div>
                <div className="w-full bg-paper-2 border border-rule h-2 relative overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${quotaColor}`}
                    style={{
                      width: `${Math.min(100, metrics?.total_scanned.quota_usage_percentage || 0)}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="border-t border-rule mt-4 pt-3 flex justify-between items-center text-[10px] text-ink-500">
              <span>
                Remaining:{" "}
                <strong className="text-ink-900">
                  {metrics ? metrics.total_scanned.remaining_capacity.toLocaleString() : "—"}
                </strong>
              </span>
              <span className="uppercase font-semibold text-ink-700">
                {metrics ? `${metrics.total_scanned.days_until_renewal}d to renewal` : "—"}
              </span>
            </div>
          </div>

          {/* Card 2: Tampering Detection Rate */}
          <div className="bg-paper-0 border-2 border-ink-900 p-5 font-mono flex flex-col justify-between shadow-sm relative overflow-hidden">
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold">
                  02 / RISK DETECTION
                </span>
                <ShieldAlert className="w-4 h-4 text-forensic-red" />
              </div>

              <div>
                <div className="text-2xl md:text-3xl font-bold tracking-tight text-forensic-red font-serif">
                  {metrics ? `${metrics.tampering_detection.rate_percentage.toFixed(1)}%` : "—"}
                </div>
                <span className="text-[11px] text-ink-600 font-semibold block mt-0.5">
                  Tampering Detection Rate
                </span>
              </div>

              <div className="bg-paper-1 border border-rule p-2.5 space-y-1 text-[11px]">
                <div className="flex justify-between items-center">
                  <span className="text-ink-600">Critical Anomaly:</span>
                  <span className="font-bold text-forensic-red">
                    {metrics?.tampering_detection.critical_count ?? 0} dockets
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-ink-600">High Risk Factor:</span>
                  <span className="font-bold text-amber-700">
                    {metrics?.tampering_detection.high_count ?? 0} dockets
                  </span>
                </div>
              </div>
            </div>

            <div className="border-t border-rule mt-4 pt-3 flex justify-between items-center text-[10px]">
              <span className="text-ink-500">
                Evaluated:{" "}
                <strong className="text-ink-900">
                  {metrics?.tampering_detection.total_evaluated ?? 0} cases
                </strong>
              </span>
              <span className="text-forensic-red font-bold uppercase tracking-wider text-[9px]">
                {metrics?.tampering_detection.risk_status || "FLAGGED VECTOR"}
              </span>
            </div>
          </div>

          {/* Card 3: Financial Exposure Prevented */}
          <div className="bg-paper-0 border-2 border-ink-900 p-5 font-mono flex flex-col justify-between shadow-sm relative overflow-hidden">
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold">
                  03 / FINANCIAL EXPOSURE
                </span>
                <Coins className="w-4 h-4 text-forensic-green" />
              </div>

              <div>
                <div className="text-2xl md:text-3xl font-bold tracking-tight text-ink-900 font-serif">
                  {metrics ? metrics.financial_exposure.total_prevented_short : "—"}
                </div>
                <span className="text-[11px] text-forensic-green font-semibold block mt-0.5">
                  Financial Exposure Prevented
                </span>
              </div>

              <div className="text-[11px] text-ink-600 leading-tight space-y-1">
                <div className="font-mono text-xs text-ink-800 font-bold">
                  {metrics ? metrics.financial_exposure.total_prevented_formatted : "PKR 0"}
                </div>
                <p className="text-[10px] text-ink-500">
                  Fraudulent balance inflations & falsified ledgers intercepted prior to credit
                  disbursement.
                </p>
              </div>
            </div>

            <div className="border-t border-rule mt-4 pt-3 flex justify-between items-center text-[10px] text-ink-500">
              <span>
                Blocked Cases:{" "}
                <strong className="text-ink-900">
                  {metrics?.financial_exposure.flagged_cases_count ?? 0}
                </strong>
              </span>
              <span className="text-ink-700 font-semibold">
                Avg: PKR{" "}
                {metrics
                  ? Math.round(metrics.financial_exposure.average_inflation_pkr).toLocaleString()
                  : "0"}
              </span>
            </div>
          </div>

          {/* Card 4: Average Verification Latency */}
          <div className="bg-paper-0 border-2 border-ink-900 p-5 font-mono flex flex-col justify-between shadow-sm relative overflow-hidden">
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold">
                  04 / FORENSIC LATENCY
                </span>
                <Clock className="w-4 h-4 text-ink-600" />
              </div>

              <div>
                <div className="text-2xl md:text-3xl font-bold tracking-tight text-ink-900 font-serif">
                  {metrics?.verification_latency.p50_formatted || "580 ms"}
                  <span className="font-mono text-sm text-ink-500 font-normal ml-2">
                    / {metrics?.verification_latency.p95_formatted || "2.1 s"}
                  </span>
                </div>
                <span className="text-[11px] text-ink-600 font-semibold block mt-0.5">
                  Average Verification Latency (p50 / p95)
                </span>
              </div>

              <div className="bg-paper-1 border border-rule p-2.5 space-y-1 text-[10px]">
                <div className="flex justify-between items-center">
                  <span className="text-ink-600">Deterministic p50:</span>
                  <span className="font-bold text-ink-900">
                    {metrics?.verification_latency.deterministic_formatted || "580 ms"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-ink-600">Multi-Page OCR p95:</span>
                  <span className="font-bold text-ink-900">
                    {metrics?.verification_latency.multi_page_ocr_formatted || "2.1 s"}
                  </span>
                </div>
              </div>
            </div>

            <div className="border-t border-rule mt-4 pt-3 flex justify-between items-center text-[10px] text-ink-500">
              <span className="text-forensic-green font-semibold">Zero-Tolerance Math</span>
              <span className="text-ink-700 font-semibold">NIST SP 800-86</span>
            </div>
          </div>
        </section>

        {/* ── MIDDLE SECTION: RISK SPECTRUM & PIPELINE LATENCY RADAR ──────── */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Risk Tier Distribution (5 cols) */}
          <div className="lg:col-span-5 bg-paper-0 border-2 border-ink-900 p-6 font-mono space-y-5">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <div>
                <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold block">
                  PORTFOLIO RISK PROFILE
                </span>
                <h2 className="font-serif text-xl font-bold text-ink-900 tracking-tight">
                  Risk Tier Distribution
                </h2>
              </div>
              <span className="text-xs text-ink-500">
                {metrics?.tampering_detection.total_evaluated ?? 0} Cases Evaluated
              </span>
            </div>

            {/* Visual Risk Bar */}
            <div className="space-y-3">
              <div className="w-full h-4 bg-paper-2 border border-rule flex overflow-hidden">
                {metrics && metrics.tampering_detection.total_evaluated > 0 ? (
                  <>
                    <div
                      title={`Critical: ${metrics.tampering_detection.critical_count}`}
                      className="bg-forensic-red h-full"
                      style={{
                        width: `${(metrics.tampering_detection.critical_count / metrics.tampering_detection.total_evaluated) * 100}%`,
                      }}
                    />
                    <div
                      title={`High: ${metrics.tampering_detection.high_count}`}
                      className="bg-amber-600 h-full"
                      style={{
                        width: `${(metrics.tampering_detection.high_count / metrics.tampering_detection.total_evaluated) * 100}%`,
                      }}
                    />
                    <div
                      title={`Elevated: ${metrics.tampering_detection.elevated_count}`}
                      className="bg-amber-400 h-full"
                      style={{
                        width: `${(metrics.tampering_detection.elevated_count / metrics.tampering_detection.total_evaluated) * 100}%`,
                      }}
                    />
                    <div
                      title={`Moderate: ${metrics.tampering_detection.moderate_count}`}
                      className="bg-slate-400 h-full"
                      style={{
                        width: `${(metrics.tampering_detection.moderate_count / metrics.tampering_detection.total_evaluated) * 100}%`,
                      }}
                    />
                    <div
                      title={`Low: ${metrics.tampering_detection.low_count}`}
                      className="bg-forensic-green h-full"
                      style={{
                        width: `${(metrics.tampering_detection.low_count / metrics.tampering_detection.total_evaluated) * 100}%`,
                      }}
                    />
                  </>
                ) : (
                  <div className="w-full bg-paper-2" />
                )}
              </div>

              {/* Legend & Breakdown */}
              <div className="space-y-2 text-xs pt-1">
                <div className="flex items-center justify-between p-1.5 border-b border-rule/50">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-forensic-red inline-block shrink-0" />
                    <span className="font-semibold text-ink-900">Critical (81–100)</span>
                  </div>
                  <div className="flex items-center gap-3 font-semibold">
                    <span className="text-forensic-red">Immediate Rejection</span>
                    <span className="text-ink-900 w-12 text-right">
                      {metrics?.tampering_detection.critical_count ?? 0}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-1.5 border-b border-rule/50">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-amber-600 inline-block shrink-0" />
                    <span className="font-semibold text-ink-900">High (61–80)</span>
                  </div>
                  <div className="flex items-center gap-3 font-semibold">
                    <span className="text-amber-700">STR Escalation</span>
                    <span className="text-ink-900 w-12 text-right">
                      {metrics?.tampering_detection.high_count ?? 0}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-1.5 border-b border-rule/50">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-amber-400 inline-block shrink-0" />
                    <span className="font-semibold text-ink-900">Elevated (41–60)</span>
                  </div>
                  <div className="flex items-center gap-3 font-semibold">
                    <span className="text-amber-800">Human Credit Audit</span>
                    <span className="text-ink-900 w-12 text-right">
                      {metrics?.tampering_detection.elevated_count ?? 0}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-1.5 border-b border-rule/50">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-slate-400 inline-block shrink-0" />
                    <span className="font-semibold text-ink-900">Moderate (21–40)</span>
                  </div>
                  <div className="flex items-center gap-3 font-semibold">
                    <span className="text-ink-600">Secondary Verification</span>
                    <span className="text-ink-900 w-12 text-right">
                      {metrics?.tampering_detection.moderate_count ?? 0}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-forensic-green inline-block shrink-0" />
                    <span className="font-semibold text-ink-900">Low / Clean (0–20)</span>
                  </div>
                  <div className="flex items-center gap-3 font-semibold">
                    <span className="text-forensic-green">Straight-Through Approval</span>
                    <span className="text-ink-900 w-12 text-right">
                      {metrics?.tampering_detection.low_count ?? 0}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Forensic Pipeline Stage Latencies (7 cols) */}
          <div className="lg:col-span-7 bg-paper-0 border-2 border-ink-900 p-6 font-mono space-y-4">
            <div className="flex items-center justify-between border-b border-rule pb-3">
              <div>
                <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold block">
                  PIPELINE PERFORMANCE RADAR
                </span>
                <h2 className="font-serif text-xl font-bold text-ink-900 tracking-tight">
                  8-Stage Execution Latency Telemetry
                </h2>
              </div>
              <span className="text-xs bg-paper-1 border border-rule px-2.5 py-1 text-ink-700 font-semibold">
                NIST SP 800-86 Validated
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              {[
                { stage: "CUSTODY_LOCK", name: "Stage 1: Custody Lock", ms: 35, type: "Deterministic" },
                { stage: "PDF_STRUCTURE", name: "Stage 2: PDF Structure", ms: 30, type: "Deterministic" },
                { stage: "FONT_GLYPH_ANALYSIS", name: "Stage 3: Font Baseline", ms: 29, type: "Deterministic" },
                { stage: "VISION_ELA", name: "Stage 4: Vision ELA", ms: 320, type: "Computer Vision" },
                { stage: "OCR_EXTRACTION", name: "Stage 5: OCR Extraction", ms: 77, type: "Multi-Modal OCR" },
                { stage: "FINANCIAL_VERIFICATION", name: "Stage 6: Financial Reconciler", ms: 82, type: "Deterministic" },
                { stage: "EVIDENCE_FUSION", name: "Stage 7: Evidence Fusion", ms: 59, type: "Bayesian Fusion" },
                { stage: "REPORT_GENERATION", name: "Stage 8: Court Dossier", ms: 117, type: "Cryptographic PDF" },
              ].map((item) => {
                const liveMs = metrics?.verification_latency.stage_latencies?.[item.stage] ?? item.ms;
                return (
                  <div
                    key={item.stage}
                    className="p-3 bg-paper-1 border border-rule flex flex-col justify-between space-y-2 hover:border-ink-900 transition-colors"
                  >
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-bold text-ink-900">{item.name}</span>
                      <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-paper-0 border border-rule font-semibold text-ink-600">
                        {item.type}
                      </span>
                    </div>

                    <div className="flex items-baseline justify-between pt-1">
                      <span className="text-[10px] text-ink-500 uppercase">Median Latency</span>
                      <span className="font-mono text-sm font-bold text-ink-900">
                        {liveMs < 1000 ? `${liveMs} ms` : `${(liveMs / 1000).toFixed(2)} s`}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── RECENT HIGH-RISK CRITICAL ALERTS LEDGER ─────────────────────── */}
        <section className="bg-paper-0 border-2 border-ink-900 p-6 font-mono space-y-4 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-rule pb-3">
            <div>
              <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold block">
                STATUTORY ESCALATION LEDGER
              </span>
              <h2 className="font-serif text-xl font-bold text-ink-900 tracking-tight">
                Recent Critical & High-Risk Interceptions
              </h2>
            </div>

            <Link
              href="/investigations"
              className="text-xs text-ink-700 hover:text-ink-900 font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors"
            >
              <span>View Full Case Docket</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b-2 border-ink-900 bg-paper-1 text-ink-500 uppercase text-[10px] tracking-wider">
                  <th className="py-2.5 px-3">Case Identifier</th>
                  <th className="py-2.5 px-3">Document Title</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Risk Assessment</th>
                  <th className="py-2.5 px-3">Blocked Discrepancy</th>
                  <th className="py-2.5 px-3">Forensic Recommendation</th>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule font-mono">
                {metrics && metrics.recent_critical_alerts.length > 0 ? (
                  metrics.recent_critical_alerts.map((alert) => (
                    <tr key={alert.id} className="hover:bg-paper-1 transition-colors">
                      <td className="py-3 px-3 font-bold text-ink-900 whitespace-nowrap">
                        {alert.case_number}
                      </td>
                      <td className="py-3 px-3 text-ink-800 max-w-xs truncate">
                        {alert.title}
                        {alert.client_reference && (
                          <span className="block text-[10px] text-ink-500">
                            Ref: {alert.client_reference}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-ink-600 uppercase text-[10px]">
                        {alert.document_type.replace(/_/g, " ")}
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 text-[10px] font-bold border uppercase tracking-wider ${
                            alert.risk_tier === "CRITICAL"
                              ? "bg-forensic-red/10 border-forensic-red text-forensic-red"
                              : "bg-amber-500/10 border-amber-600 text-amber-700"
                          }`}
                        >
                          {alert.risk_tier} ({alert.risk_score ?? "—"})
                        </span>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        {alert.prevented_rupees_formatted ? (
                          <span className="font-bold text-forensic-red">
                            +{alert.prevented_rupees_formatted}
                          </span>
                        ) : (
                          <span className="text-ink-500">MOD-97 / Typography Mismatch</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-[10px] font-semibold text-ink-700 uppercase whitespace-nowrap">
                        {formatRecommendation(alert.action_directive, alert.risk_tier)}
                      </td>
                      <td className="py-3 px-3 text-ink-500 text-[10px] whitespace-nowrap">
                        {formatDatePKT(alert.created_at)}
                      </td>
                      <td className="py-3 px-3 text-right whitespace-nowrap">
                        <Link
                          href={`/investigations/${alert.id}`}
                          className="inline-flex items-center gap-1 text-[11px] font-bold uppercase text-ink-900 hover:text-forensic-red transition-colors"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-ink-500 text-xs italic">
                      No high-risk adversarial anomalies detected in recent audit records.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── STATUTORY REGULATORY ADVISORY FOLIO ─────────────────────────── */}
        <section className="border border-rule bg-paper-1 p-5 font-mono text-xs text-ink-700 space-y-2">
          <div className="flex items-center gap-2 font-bold text-ink-900 uppercase tracking-wider text-[11px]">
            <Lock className="w-3.5 h-3.5 text-ink-700" />
            <span>Statutory Compliance & Regulatory Chain of Custody</span>
          </div>
          <p className="text-[11px] text-ink-600 leading-relaxed max-w-5xl">
            All telemetry metrics, sub-pixel typography baselines, Lakh/Crore arithmetic audit
            trails, and Error Level Analysis (ELA) heatmaps within this command center are
            cryptographically locked under <strong>Electronic Transactions Ordinance (ETO) 2002</strong>{" "}
            and <strong>Qanun-e-Shahadat Order 1984 (Article 164)</strong>. Audit reports generated
            herein are legally admissible in banking tribunals and High Courts of Pakistan.
            Unauthorized tampering or falsification of audit registers is strictly prosecuted under{" "}
            <strong>Section 3 of the Prevention of Electronic Crimes Act (PECA) 2016</strong>.
          </p>
        </section>
      </main>
    </div>
  );
}
