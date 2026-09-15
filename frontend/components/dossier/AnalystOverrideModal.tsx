"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface AnalystOverrideModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentScore: number;
  onSave: (newScore: number, reason: string) => Promise<void>;
}

export function AnalystOverrideModal({
  isOpen,
  onClose,
  currentScore,
  onSave,
}: AnalystOverrideModalProps) {
  const [score, setScore] = useState<number>(currentScore);
  const [reason, setReason] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError(
        "A formal justification is mandatory under SBP audit regulations."
      );
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onSave(score, reason);
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
        <div>
          <label className="block text-ink-700 uppercase tracking-wider mb-1 font-semibold">
            Adjusted Fraud Risk Score (0 - 100):
          </label>
          <div className="flex items-center gap-3">
            <Input
              type="number"
              min={0}
              max={100}
              value={score}
              onChange={(e) => setScore(parseInt(e.target.value) || 0)}
              className="w-24 text-base font-bold tabular-nums"
            />
            <span className="text-[11px] text-ink-500">
              Current Engine Score:{" "}
              <span className="font-bold text-ink-900">{currentScore}</span>
            </span>
          </div>
        </div>

        <div>
          <label className="block text-ink-700 uppercase tracking-wider mb-1 font-semibold">
            Mandatory Compliance Justification:
          </label>
          <textarea
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
          >
            Commit SBP Audit Override
          </Button>
        </div>
      </form>
    </Modal>
  );
}
