"use client";

import React, { useState } from "react";

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

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("A formal justification is mandatory under SBP audit regulations.");
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
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 font-mono select-none">
      <div className="bg-paper-0 border-2 border-ink-900 max-w-lg w-full p-6 shadow-2xl">
        <div className="flex items-start justify-between border-b border-rule pb-3 mb-4">
          <div>
            <span className="text-[10px] text-ink-500 uppercase tracking-widest block">
              REGULATORY COMPLIANCE OVERRIDE
            </span>
            <h2 className="font-serif text-xl text-ink-900 font-semibold tracking-tight">
              Analyst Risk Score Override
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-ink-500 hover:text-ink-900 text-lg leading-none"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-ink-700 uppercase tracking-wider mb-1">
              Adjusted Fraud Risk Score (0 – 100):
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min="0"
                max="100"
                value={score}
                onChange={(e) => setScore(parseInt(e.target.value) || 0)}
                className="w-24 bg-paper-1 border border-rule px-3 py-2 text-base font-bold text-ink-900 tabular-nums focus:outline-none focus:border-ink-900"
              />
              <span className="text-[11px] text-ink-500">
                Current Engine Score:{" "}
                <span className="font-bold text-ink-900">{currentScore}</span>
              </span>
            </div>
          </div>

          <div>
            <label className="block text-ink-700 uppercase tracking-wider mb-1">
              Mandatory Compliance Justification:
            </label>
            <textarea
              rows={3}
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Branch operational audit confirmed cash receipt and verified counter teller stamp directly."
              className="w-full bg-paper-1 border border-rule p-2.5 text-ink-900 placeholder:text-ink-500 text-xs focus:outline-none focus:border-ink-900"
            />
          </div>

          {error && (
            <div className="bg-forensic-red/10 border border-forensic-red/40 p-2 text-forensic-red text-[11px]">
              {error}
            </div>
          )}

          <div className="pt-3 border-t border-rule flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-paper-1 hover:bg-paper-2 border border-rule text-ink-700 uppercase tracking-wider transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-ink-900 hover:bg-black text-paper-0 uppercase tracking-wider font-semibold transition-colors disabled:opacity-50"
            >
              {isSubmitting ? "Committing..." : "Commit SBP Audit Override"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
