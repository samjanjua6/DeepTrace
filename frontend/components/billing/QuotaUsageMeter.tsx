"use client";

import React from "react";
import { Gauge, AlertTriangle, CheckCircle2, Clock, ShieldCheck } from "lucide-react";

interface QuotaUsageMeterProps {
  used: number;
  limit: number;
  remaining: number;
  usagePercentage: number;
  daysUntilRenewal: number;
  billingCycleStart?: string | null;
}

export function QuotaUsageMeter({
  used,
  limit,
  remaining,
  usagePercentage,
  daysUntilRenewal,
  billingCycleStart,
}: QuotaUsageMeterProps) {
  const isHigh = usagePercentage >= 90;
  const isElevated = usagePercentage >= 70 && usagePercentage < 90;

  const barColor = isHigh
    ? "bg-rose-600"
    : isElevated
    ? "bg-amber-600"
    : "bg-emerald-600";

  const statusLabel = isHigh
    ? "CAPACITY THRESHOLD CRITICAL"
    : isElevated
    ? "ELEVATED INTAKE VOLUME"
    : "INTAKE QUOTA OPTIMAL";

  const statusBg = isHigh
    ? "bg-rose-50 border-rose-300 text-rose-800"
    : isElevated
    ? "bg-amber-50 border-amber-300 text-amber-800"
    : "bg-emerald-50 border-emerald-300 text-emerald-800";

  return (
    <div className="bg-paper-0 border-2 border-ink-900 p-6 font-mono shadow-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-rule pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-ink-900 text-paper-0">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Real-Time Metering
            </span>
            <h2 className="text-base font-bold uppercase tracking-wider text-ink-900">
              Monthly Document Intake Capacity
            </h2>
          </div>
        </div>

        <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 border text-[11px] font-bold uppercase tracking-wider ${statusBg}`}>
          {isHigh ? (
            <AlertTriangle className="w-3.5 h-3.5 text-rose-700" />
          ) : (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
          )}
          <span>{statusLabel}</span>
        </div>
      </div>

      {/* Main Consumption Gauge & Numbers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
        {/* Big Numbers */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-baseline gap-3">
            <span className="text-4xl sm:text-5xl font-bold font-mono tracking-tight text-ink-900">
              {used.toLocaleString()}
            </span>
            <span className="text-lg sm:text-xl text-ink-400 font-mono">
              / {limit.toLocaleString()} Documents
            </span>
          </div>

          {/* Progress Track */}
          <div className="space-y-1.5">
            <div className="w-full h-4 bg-paper-2 border border-rule overflow-hidden relative">
              <div
                className={`h-full transition-all duration-500 ${barColor}`}
                style={{ width: `${Math.min(100, Math.max(0, usagePercentage))}%` }}
              />
              {/* Tick marks */}
              <div className="absolute inset-0 flex justify-between px-1 pointer-events-none text-[8px] text-ink-300">
                <span className="border-r border-ink-300/40 h-full" />
                <span className="border-r border-ink-300/40 h-full" />
                <span className="border-r border-ink-300/40 h-full" />
              </div>
            </div>

            <div className="flex justify-between text-[10px] text-ink-500">
              <span>0%</span>
              <span className="font-bold text-ink-900">{usagePercentage}% Utilized</span>
              <span>100% (Limit)</span>
            </div>
          </div>
        </div>

        {/* Remaining & Renewal Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-1 gap-3 border-t lg:border-t-0 lg:border-l border-rule pt-4 lg:pt-0 lg:pl-6">
          <div className="p-3 bg-paper-1 border border-rule">
            <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
              Remaining Allowance
            </span>
            <span className="text-xl font-bold text-ink-900 block mt-0.5">
              {remaining.toLocaleString()}
            </span>
            <span className="text-[10px] text-ink-400">Documents available</span>
          </div>

          <div className="p-3 bg-paper-1 border border-rule">
            <div className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-ink-500">
              <Clock className="w-3 h-3 text-ink-500" />
              <span>Cycle Renewal</span>
            </div>
            <span className="text-xl font-bold text-ink-900 block mt-0.5">
              {daysUntilRenewal} Days
            </span>
            <span className="text-[10px] text-ink-400">
              {billingCycleStart
                ? `Started ${new Date(billingCycleStart).toLocaleDateString("en-PK", { month: "short", day: "numeric" })}`
                : "Standard 30-day window"}
            </span>
          </div>
        </div>
      </div>

      {/* Compliance Footer */}
      <div className="flex items-center gap-2 pt-4 border-t border-rule text-[11px] text-ink-600">
        <ShieldCheck className="w-4 h-4 text-ink-700 shrink-0" />
        <span>
          Under SBP Cybersecurity Guidelines (BPRD/2020), document intake volumes and RFC 3161
          timestamps are audited per institutional tenancy quota.
        </span>
      </div>
    </div>
  );
}
