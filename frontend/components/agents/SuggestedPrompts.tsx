"use client";

import React, { useState, useRef } from "react";
import {
  MessageSquarePlus,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
  className?: string;
  defaultCollapsed?: boolean;
  variant?: "tray" | "card";
}

export interface ForensicPrompt {
  id: string;
  category: string;
  shortLabel: string;
  text: string;
}

export const FORENSIC_PROMPTS: ForensicPrompt[] = [
  {
    id: "tax",
    category: "TAX / FBR",
    shortLabel: "Sec 149 Tax Discrepancy",
    text: "Explain the Section 149 tax withholding discrepancy and Active Taxpayer status.",
  },
  {
    id: "ledger",
    category: "LEDGER",
    shortLabel: "Reconcile Math Balance",
    text: "Reconcile the running balance math and detail any artificial inflation.",
  },
  {
    id: "typography",
    category: "TYPOGRAPHY",
    shortLabel: "Font Baseline Offsets",
    text: "What sub-pixel font baseline offsets or external editor artifacts were found?",
  },
  {
    id: "aml",
    category: "SBP / AML",
    shortLabel: "AML & NACTA 4th Schedule",
    text: "Verify SBP AML/CFT, NACTA 4th Schedule, and UNSC Sanctions screening status.",
  },
  {
    id: "cnic",
    category: "NADRA CNIC",
    shortLabel: "13-Digit Format & Parity",
    text: "Is the 13-digit CNIC format, security barcode, and gender parity valid?",
  },
  {
    id: "urdu",
    category: "اردو خلاصہ",
    shortLabel: "کریڈٹ آفیسر خلاصہ",
    text: "اس دستاویز کی فارنزک رپورٹ کا تفصیلی خلاصہ اردو میں پیش کریں۔",
  },
];

export function SuggestedPrompts({
  onSelectPrompt,
  disabled = false,
  className = "",
  defaultCollapsed = false,
  variant = "tray",
}: SuggestedPromptsProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: "left" | "right") => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({
        left: direction === "left" ? -200 : 200,
        behavior: "smooth",
      });
    }
  };

  // Minimized state: single sleek line taking virtually no vertical space
  if (isCollapsed) {
    return (
      <div
        className={cn(
          "font-mono text-xs flex items-center justify-between py-0.5",
          className
        )}
      >
        <button
          type="button"
          onClick={() => setIsCollapsed(false)}
          className="flex items-center gap-1.5 text-ink-600 hover:text-ink-900 transition-colors cursor-pointer select-none"
          title="Expand suggested forensic inquiries"
        >
          <Sparkles className="w-3 h-3 text-amber-500 shrink-0" />
          <span className="font-bold text-[10px] uppercase tracking-wider">
            Suggested Forensic Queries ({FORENSIC_PROMPTS.length})
          </span>
          <ChevronUp className="w-3 h-3 text-ink-400" />
        </button>

        <button
          type="button"
          onClick={() => setIsCollapsed(false)}
          className="text-[9px] uppercase font-bold text-ink-500 hover:text-ink-900 underline cursor-pointer"
        >
          Expand Pills
        </button>
      </div>
    );
  }

  // Expanded state: compact single-row horizontal pill strip
  return (
    <div className={cn("font-mono text-xs", className)}>
      {/* Header bar with controls */}
      <div className="flex items-center justify-between gap-2 text-ink-600 mb-1.5 select-none">
        <div className="flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-amber-500 shrink-0" />
          <span className="font-bold text-[10px] uppercase tracking-wider text-ink-800">
            Suggested Forensic Inquiries
          </span>
          <span className="text-[9px] text-ink-400 hidden sm:inline">
            &bull; Click to ask &bull; Scroll for more
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Scroll navigation arrows */}
          <button
            type="button"
            onClick={() => scroll("left")}
            className="p-1 hover:bg-paper-2 border border-rule text-ink-600 hover:text-ink-900 transition-colors cursor-pointer"
            title="Scroll left"
          >
            <ChevronLeft className="w-3 h-3" />
          </button>
          <button
            type="button"
            onClick={() => scroll("right")}
            className="p-1 hover:bg-paper-2 border border-rule text-ink-600 hover:text-ink-900 transition-colors cursor-pointer"
            title="Scroll right"
          >
            <ChevronRight className="w-3 h-3" />
          </button>

          {/* Minimize button */}
          <button
            type="button"
            onClick={() => setIsCollapsed(true)}
            className="flex items-center gap-1 px-1.5 py-0.5 hover:bg-paper-2 border border-rule text-ink-700 hover:text-ink-900 font-bold uppercase text-[9px] transition-colors cursor-pointer ml-1"
            title="Minimize suggested queries to maximize chat area"
          >
            <span>Minimize</span>
            <ChevronDown className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Low-profile horizontal scrollable pill strip */}
      <div
        ref={scrollRef}
        className={cn(
          "flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5",
          variant === "card" && "flex-wrap"
        )}
      >
        {FORENSIC_PROMPTS.map((prompt) => (
          <button
            key={prompt.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(prompt.text)}
            title={prompt.text}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-paper-0 hover:bg-paper-2 border border-rule hover:border-ink-900 text-ink-800 text-[11px] font-mono transition-all whitespace-nowrap shrink-0 group disabled:opacity-50 cursor-pointer shadow-xs select-none"
          >
            <MessageSquarePlus className="w-3 h-3 text-amber-600 group-hover:text-ink-900 transition-colors shrink-0" />
            <span className="font-bold text-ink-900 text-[10px] uppercase tracking-wide">
              {prompt.category}:
            </span>
            <span className="text-ink-700 group-hover:text-ink-900 text-[10.5px]">
              {prompt.shortLabel}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
