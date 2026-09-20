"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { formatRecommendation } from "@/lib/types/forensics";

interface AnalystOverrideModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentScore: number;
  authenticityScore?: number;
  transactionRiskScore?: number;
  onSave: (newScore: number, reason: string) => Promise<void>;
}

export function AnalystOverrideModal({
  isOpen,
  onClose,
  currentScore,
  authenticityScore,
  transactionRiskScore,
  onSave,
}: AnalystOverrideModalProps) {
  const [score, setScore] = useState<number>(currentScore);
  const [reason, setReason] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const getProjectedTier = (s: number): string => {
    if (s <= 20) return "LOW";
    if (s <= 40) return "MODERATE";
    if (s <= 60) return "ELEVATED";
    if (s <= 80) return "HIGH";
    return "CRITICAL";
  };

  const projectedTier = getProjectedTier(score);
  const projectedDirective =
    score >= 81
      ? "IMMEDIATE_REJECTION"
      : score >= 61
      ? "ESCALATION_REQUIRED"
      : score >= 41
      ? "HUMAN_REVIEW"
      : score >= 21
      ? "SECONDARY_SCAN"
      : "STRAIGHT_THROUGH_APPROVAL";
  const projectedRecommendation = formatRecommendation(projectedDirective, projectedTier);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim().length < 10) {
      setError(
        "A formal compliance justification of at least 10 characters is mandatory under SBP audit regulations."
      );
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onSave(score, reason.trim());
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to commit override");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      category="REGULATORY COMPLIANCE OVERRIDE"
      title="Analyst Risk Score Override"
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 text-xs">
        {/* Baseline Forensic Radar Badges */}
        <div className="grid grid-cols-2 gap-2 p-2.5 bg-paper-1 border border-rule">
          <div>
            <span className="text-[10px] text-ink-500 uppercase block font-mono">
              Document Authenticity
            </span>
            <span className="font-mono text-sm font-bold text-ink-900">
              {authenticityScore !== undefined ? `${authenticityScore}%` : `${Math.max(0, 100 - currentScore)}%`}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-ink-500 uppercase block font-mono">
              Transaction & AML Risk
            </span>
            <span className="font-mono text-sm font-bold text-ink-900">
              {transactionRiskScore !== undefined ? `${transactionRiskScore}/100` : "0/100"}
            </span>
          </div>
        </div>

        <div>
          <label htmlFor="override-score" className="block text-ink-700 uppercase tracking-wider mb-1 font-semibold">
            Adjusted Composite Fraud Risk Score (0 - 100):
          </label>

          <div className="flex items-center gap-3">
            <Input
              id="override-score"
              type="number"
              min={0}
              max={100}
              value={score}
              onChange={(e) => setScore(Math.min(100, Math.max(0, parseInt(e.target.value) || 0)))}
              className="w-24 text-base font-bold tabular-nums"
            />
            <span className="text-[11px] text-ink-500">
              Current Engine Score:{" "}
              <span className="font-bold text-ink-900">{currentScore}</span>
            </span>
          </div>

          <div className="mt-2 p-2 bg-paper-1 border border-rule flex items-center justify-between text-[11px] font-mono">
            <span className="text-ink-500">Projected Forensic Recommendation:</span>
            <span className="font-bold text-ink-900">{projectedRecommendation} ({projectedTier})</span>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label htmlFor="override-reason" className="block text-ink-700 uppercase tracking-wider font-semibold">
              Mandatory Compliance Justification:
            </label>
            <span className={`text-[10px] font-mono ${reason.trim().length >= 10 ? "text-forensic-green" : "text-ink-400"}`}>
              {reason.trim().length} / 10 min chars
            </span>
          </div>
          <textarea
            id="override-reason"
            rows={3}
            required
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Branch operational audit confirmed cash receipt and verified counter teller stamp directly."
            className="w-full bg-paper-1 border border-rule p-2.5 text-ink-900 placeholder:text-ink-500 text-xs focus:outline-none focus:border-ink-900 focus:bg-paper-0 transition-colors font-mono"
          />
        </div>

        {error && (
          <div className="bg-forensic-red/10 border border-forensic-red/40 p-2 text-forensic-red text-[11px]">
            {error}
          </div>
        )}

        <div className="pt-3 border-t border-rule flex items-center justify-end gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            disabled={reason.trim().length < 10}
          >
            Commit SBP Audit Override
          </Button>
        </div>
      </form>
    </Modal>
  );
}
