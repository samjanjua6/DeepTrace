"use client";

import React from "react";
import { RiskAssessment, formatRecommendation } from "@/lib/types/forensics";

interface RiskGaugeBlockProps {
  assessment?: RiskAssessment;
  onOpenOverride?: () => void;
  isCalculating?: boolean;
}

export function RiskGaugeBlock({
  assessment,
  onOpenOverride,
  isCalculating = false,
}: RiskGaugeBlockProps) {
  const isOverridden = assessment?.overriddenScore !== undefined && assessment?.overriddenScore !== null;
  const rawScore = assessment?.overallScore ?? 0;
  const rawTier = assessment?.riskTier ?? "LOW";
  const displayScore = isOverridden ? assessment.overriddenScore! : rawScore;
  const displayTier = isOverridden ? (assessment.overriddenTier ?? rawTier) : rawTier;
  const directive = assessment?.actionDirective ?? "STRAIGHT_THROUGH_APPROVAL";

  const authScore = assessment?.authenticityScore ?? Math.max(0, 100 - displayScore);
  const tamperScore = assessment?.tamperScore ?? displayScore;
  const authTier = assessment?.authenticityTier ?? (authScore >= 90 ? "VERIFIED_AUTHENTIC" : (authScore >= 60 ? "SUSPECT_DOCUMENT" : "FORGERY_DETECTED"));

  const txnScore = assessment?.transactionRiskScore ?? 0;
  const txnTier = assessment?.transactionRiskTier ?? (txnScore <= 20 ? "CLEAN" : (txnScore <= 40 ? "MONITORED" : (txnScore <= 70 ? "HIGH_AML_RISK" : "CRITICAL_PROSCRIBED")));

  const getTierColor = (t: string) => {
    if (isCalculating) {
      return "text-ink-700 border-rule bg-paper-1 animate-pulse";
    }
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

  const getAuthBadge = (t: string) => {
    if (isCalculating) return "text-ink-700 border-rule bg-paper-1 animate-pulse";
    switch (t) {
      case "VERIFIED_AUTHENTIC":
        return "text-forensic-green border-forensic-green bg-forensic-green/10";
      case "SUSPECT_DOCUMENT":
        return "text-amber-700 border-amber-600 bg-amber-50";
      case "FORGERY_DETECTED":
      default:
        return "text-forensic-red border-forensic-red bg-forensic-red/10";
    }
  };

  const getTxnBadge = (t: string) => {
    if (isCalculating) return "text-ink-700 border-rule bg-paper-1 animate-pulse";
    switch (t) {
      case "CLEAN":
        return "text-forensic-green border-forensic-green bg-forensic-green/10";
      case "MONITORED":
        return "text-blue-700 border-blue-600 bg-blue-50";
      case "HIGH_AML_RISK":
        return "text-amber-700 border-amber-600 bg-amber-50";
      case "CRITICAL_PROSCRIBED":
      default:
        return "text-forensic-red border-forensic-red bg-forensic-red/10";
    }
  };

  return (
    <div className="bg-paper-0 border border-rule p-5 select-none space-y-4">
      {/* Top Section: Composite Decision Radar & Regulatory Directive */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-rule">
        <div>
          <span className="font-mono text-[10px] tracking-[0.15em] uppercase text-ink-500 block">
            § 01 / DUAL-RADAR FORENSIC DECISION METER
          </span>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-mono text-xs text-ink-600">Evaluated Fraud Risk:</span>
            <span className="font-mono text-sm font-bold text-ink-900 tabular-nums">
              {isCalculating ? "..." : `${displayScore}/100`}
            </span>
            <span
              className={`font-mono text-[10px] font-bold px-2 py-0.5 border uppercase tracking-wider ${getTierColor(
                displayTier
              )}`}
            >
              {isCalculating ? "● PROCESSING" : `${displayTier} RISK`}
            </span>
            {isOverridden && !isCalculating && (
              <span className="font-mono text-[9px] text-forensic-amber uppercase tracking-wider font-semibold">
                ● ANALYST ADJUDICATED (Baseline: {rawScore}/100)
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onOpenOverride && (
            <button
              onClick={onOpenOverride}
              className="px-3 py-1.5 bg-paper-1 hover:bg-paper-2 border border-rule text-ink-900 font-mono text-[11px] uppercase tracking-wider transition-colors"
            >
              {isOverridden ? "Edit Adjudication" : "Override Score"}
            </button>
          )}
        </div>
      </div>

      {/* Audited Human Override Banner */}
      {isOverridden && !isCalculating && (
        <div className="bg-amber-500/10 border border-amber-500/30 p-3 text-xs font-mono space-y-1.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-bold text-amber-900 flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-500" />
              HUMAN ANALYST AUDIT OVERRIDE (SBP BPRD COMPLIANT)
            </span>
            <span className="text-[10px] text-amber-700">
              {assessment.overriddenAt ? new Date(assessment.overriddenAt).toLocaleString() : "Adjudicated"}
            </span>
          </div>
          <div className="text-[11px] text-amber-900/90">
            <span className="font-semibold text-ink-700">Adjudication Justification: </span>
            <span className="italic">"{assessment.overrideReason}"</span>
          </div>
          <div className="text-[10px] text-amber-700/80 flex items-center gap-3">
            <span>Adjudicating Officer: {assessment.overriddenById || "Authorized Officer"}</span>
            <span>•</span>
            <span>Engine Baseline: {rawScore}/100 ({rawTier}) → Final: {displayScore}/100 ({displayTier})</span>
          </div>
        </div>
      )}

      {/* Dual Decoupled Forensic Meters (Side-by-Side) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Radar 1: Document Authenticity */}
        <div className="border border-rule bg-paper-1/60 p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-mono text-[9px] tracking-[0.12em] uppercase text-ink-500 block">
                DIMENSION A • DOCUMENT INTEGRITY
              </span>
              <span className="text-xs font-serif font-medium text-ink-900">
                Document Authenticity
              </span>
            </div>
            <span
              className={`font-mono text-[10px] font-bold px-2 py-0.5 border uppercase tracking-wider ${getAuthBadge(
                authTier
              )}`}
            >
              {authTier.replace(/_/g, " ")}
            </span>
          </div>

          <div className="flex items-baseline gap-2">
            {isCalculating ? (
              <span className="font-serif text-3xl font-semibold text-ink-700 animate-pulse">...</span>
            ) : (
              <>
                <span className="font-serif text-4xl font-semibold tracking-tight text-ink-900 tabular-nums">
                  {authScore}
                </span>
                <span className="font-mono text-sm text-ink-500">%</span>
              </>
            )}
            <span className="font-mono text-[10px] text-ink-500 ml-auto tabular-nums">
              Tamper Score: {tamperScore}/100
            </span>
          </div>

          {/* Authenticity Progress Bar */}
          <div className="w-full">
            <div className="h-1.5 w-full bg-paper-2 border border-rule overflow-hidden">
              <div
                style={{ width: `${Math.min(100, Math.max(0, authScore))}%` }}
                className={`h-full transition-all duration-300 ${
                  authScore >= 90
                    ? "bg-forensic-green"
                    : authScore >= 60
                    ? "bg-amber-500"
                    : "bg-forensic-red"
                }`}
              />
            </div>
            <div className="flex justify-between font-mono text-[8px] text-ink-400 mt-1">
              <span>0% (FORGED)</span>
              <span>60% (SUSPECT)</span>
              <span>100% (AUTHENTIC)</span>
            </div>
          </div>

          <div className="text-[10px] font-mono text-ink-500 pt-1 border-t border-rule/50">
            Covers typography baselines, PDF revision xref, image ELA, and ledger arithmetic.
          </div>
        </div>

        {/* Radar 2: Transaction & AML Risk */}
        <div className="border border-rule bg-paper-1/60 p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-mono text-[9px] tracking-[0.12em] uppercase text-ink-500 block">
                DIMENSION B • STATUTORY COMPLIANCE
              </span>
              <span className="text-xs font-serif font-medium text-ink-900">
                Transaction & AML Risk
              </span>
            </div>
            <span
              className={`font-mono text-[10px] font-bold px-2 py-0.5 border uppercase tracking-wider ${getTxnBadge(
                txnTier
              )}`}
            >
              {txnTier.replace(/_/g, " ")}
            </span>
          </div>

          <div className="flex items-baseline gap-2">
            {isCalculating ? (
              <span className="font-serif text-3xl font-semibold text-ink-700 animate-pulse">...</span>
            ) : (
              <>
                <span className="font-serif text-4xl font-semibold tracking-tight text-ink-900 tabular-nums">
                  {txnScore}
                </span>
                <span className="font-mono text-sm text-ink-500">/ 100</span>
              </>
            )}
            <span className="font-mono text-[10px] text-ink-500 ml-auto">
              SBP BPRD & CDD
            </span>
          </div>

          {/* Transaction Risk Progress Bar */}
          <div className="w-full">
            <div className="h-1.5 w-full bg-paper-2 border border-rule overflow-hidden">
              <div
                style={{ width: `${Math.min(100, Math.max(0, txnScore))}%` }}
                className={`h-full transition-all duration-300 ${
                  txnScore >= 75
                    ? "bg-forensic-red"
                    : txnScore >= 45
                    ? "bg-amber-500"
                    : txnScore >= 20
                    ? "bg-blue-500"
                    : "bg-forensic-green"
                }`}
              />
            </div>
            <div className="flex justify-between font-mono text-[8px] text-ink-400 mt-1">
              <span>0 (CLEAN)</span>
              <span>20 (MONITORED)</span>
              <span>45 (HIGH)</span>
              <span>75+ (PROSCRIBED)</span>
            </div>
          </div>

          <div className="text-[10px] font-mono text-ink-500 pt-1 border-t border-rule/50">
            Covers SBP BPRD circulars, NACTA, UNSC 1267, PEPs, crypto P2P & hawala red flags.
          </div>
        </div>
      </div>

      {/* Action Recommendation Strip */}
      <div className="pt-2 border-t border-rule flex flex-col sm:flex-row sm:items-center justify-between gap-1 font-mono text-xs">
        <span className="text-ink-500 text-[10px] uppercase">
          FORENSIC RECOMMENDATION (HUMAN ADJUDICATION REQUIRED):
        </span>
        <span className="font-semibold text-ink-900 tracking-wide text-right">
          {isCalculating ? "PIPELINE EXECUTION IN PROGRESS" : formatRecommendation(directive, displayTier)}
        </span>
      </div>
    </div>
  );
}

