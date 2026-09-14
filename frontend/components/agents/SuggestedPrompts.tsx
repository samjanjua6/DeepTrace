"use client";

import React from "react";
import { MessageSquarePlus, Sparkles } from "lucide-react";

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
  className?: string;
}

const FORENSIC_PROMPTS = [
  {
    category: "TAX / FBR",
    text: "Explain the Section 149 tax withholding discrepancy and Active Taxpayer status.",
  },
  {
    category: "MATH LEDGER",
    text: "Reconcile the running balance math and detail any artificial inflation.",
  },
  {
    category: "TYPOGRAPHY",
    text: "What sub-pixel font baseline offsets or external editor artifacts were found?",
  },
  {
    category: "SBP / AML",
    text: "Verify SBP AML/CFT, NACTA 4th Schedule, and UNSC Sanctions screening status.",
  },
  {
    category: "NADRA CNIC",
    text: "Is the 13-digit CNIC format, security barcode, and gender parity valid?",
  },
  {
    category: "خلاصہ برائے کریڈٹ آفیسر",
    text: "اس دستاویز کی فارنزک رپورٹ کا تفصیلی خلاصہ اردو میں پیش کریں۔",
  },
];

export function SuggestedPrompts({
  onSelectPrompt,
  disabled = false,
  className = "",
}: SuggestedPromptsProps) {
  return (
    <div className={`font-mono text-xs ${className}`}>
      <div className="flex items-center gap-1.5 text-ink-600 mb-2 font-bold text-[10px] uppercase tracking-wider">
        <Sparkles className="w-3 h-3 text-amber-500" />
        <span>SUGGESTED FORENSIC INQUIRIES</span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {FORENSIC_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(prompt.text)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 bg-paper-0 hover:bg-paper-2 border border-rule hover:border-ink-900 text-ink-800 text-[11px] transition-all text-left group disabled:opacity-50 cursor-pointer"
          >
            <MessageSquarePlus className="w-3 h-3 text-ink-400 group-hover:text-ink-900 transition-colors shrink-0" />
            <span className="font-semibold text-ink-900 text-[10px] uppercase tracking-wider">
              [{prompt.category}]:
            </span>
            <span className="truncate max-w-[280px] sm:max-w-[340px] text-ink-700">
              {prompt.text}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
