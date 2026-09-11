"use client";

import React from "react";
import { RiskAssessment } from "@/lib/types/forensics";

interface RiskGaugeBlockProps {
  assessment?: RiskAssessment;
  onOpenOverride?: () => void;
}

export function RiskGaugeBlock({
  assessment,
  onOpenOverride,
}: RiskGaugeBlockProps) {
  const score = assessment?.overallScore ?? 0;
  const tier = assessment?.riskTier ?? "LOW";
  const directive = assessment?.actionDirective ?? "STRAIGHT_THROUGH_APPROVAL";
  const isOverridden = !!assessment?.overriddenScore;

  const getTierColor = (t: string) => {
    switch (t) {
      case "CRITICAL":
        return "text-forensic-red border-forensic-red bg-forensic-red/10";
      case "HIGH":
        return "text-forensic-amber border-forensic-amber bg-forensic-amber/10";
      case "MEDIUM":
        return "text-amber-700 border-amber-600 bg-amber-50";
      default:
        return "text-forensic-green border-forensic-green bg-forensic-green/10";
    }
  };

  return (
    <div className="bg-paper-0 border border-rule p-5 select-none">
      <div className="flex items-start justify-between mb-4">
        <div>
          <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-ink-500 block mb-1">
            § 01 / CALIBRATED FRAUD RISK METER
          </span>
          <div className="flex items-baseline gap-3">
            <span className="font-serif text-5xl font-semibold tracking-tight text-ink-900 tabular-nums">
              {score}
            </span>
            <span className="font-mono text-xs text-ink-500">/ 100</span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <span
            className={`font-mono text-xs font-bold px-2.5 py-1 border uppercase tracking-wider ${getTierColor(
              tier
            )}`}
          >
            {tier} RISK
          </span>
          {isOverridden && (
            <span className="font-mono text-[9px] text-forensic-amber uppercase tracking-wider font-semibold">
              ● ANALYST OVERRIDE APPLIED
            </span>
          )}
        </div>
      </div>

      {/* Discrete 4-Tier Risk Notch Bar */}
      <div className="w-full mb-3">
        <div className="h-2 w-full bg-paper-2 border border-rule flex overflow-hidden">
          <div
            style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
            className={`h-full transition-all duration-300 ${
              score >= 80
                ? "bg-forensic-red"
                : score >= 60
                ? "bg-forensic-amber"
                : score >= 30
                ? "bg-amber-500"
                : "bg-forensic-green"
            }`}
          />
        </div>
        <div className="flex justify-between font-mono text-[9px] text-ink-500 mt-1 px-0.5">
          <span>0 (CLEAN)</span>
          <span>30 (MED)</span>
          <span>60 (HIGH)</span>
          <span>80 (CRITICAL)</span>
          <span>100</span>
        </div>
      </div>

      {/* Action Directive & Override Button */}
      <div className="pt-3 border-t border-rule flex items-center justify-between font-mono text-xs">
        <div>
          <span className="text-ink-500 text-[10px] block uppercase">
            REGULATORY ACTION DIRECTIVE:
          </span>
          <span className="font-semibold text-ink-900 tracking-wide">
            {directive.replace(/_/g, " ")}
          </span>
        </div>

        {onOpenOverride && (
          <button
            onClick={onOpenOverride}
            className="px-3 py-1.5 bg-paper-1 hover:bg-paper-2 border border-rule text-ink-900 font-mono text-[11px] uppercase tracking-wider transition-colors"
          >
            Override Score
          </button>
        )}
      </div>
    </div>
  );
}
