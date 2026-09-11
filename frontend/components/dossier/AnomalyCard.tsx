"use client";

import React from "react";
import { EvidenceItem } from "@/lib/types/forensics";

interface AnomalyCardProps {
  item: EvidenceItem;
  isSelected: boolean;
  onSelect: (id: string | null) => void;
}

export function AnomalyCard({ item, isSelected, onSelect }: AnomalyCardProps) {
  const getSeverityStyle = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return "border-forensic-red/50 bg-forensic-red/5 text-forensic-red";
      case "HIGH":
        return "border-forensic-amber/50 bg-forensic-amber/5 text-forensic-amber";
      default:
        return "border-rule bg-paper-1 text-ink-700";
    }
  };

  return (
    <div
      onClick={() => onSelect(isSelected ? null : item.id)}
      onMouseEnter={() => onSelect(item.id)}
      className={`p-4 border transition-all cursor-pointer font-mono select-none ${
        isSelected
          ? "border-ink-900 bg-paper-0 shadow-sm ring-1 ring-ink-900"
          : "border-rule bg-paper-0 hover:bg-paper-1/60"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span
          className={`text-[9px] font-bold px-2 py-0.5 border uppercase tracking-wider ${getSeverityStyle(
            item.severity
          )}`}
        >
          {item.severity}
        </span>
        <span className="text-[10px] text-ink-500 font-semibold tracking-wider uppercase">
          {item.ruleId}
        </span>
      </div>

      <h3 className="font-serif text-base text-ink-900 font-medium mb-1 tracking-tight">
        {item.title}
      </h3>

      <p className="text-xs text-ink-700 leading-relaxed mb-3">
        {item.description}
      </p>

      {/* Expected vs Actual Metric Chips */}
      {(item.expectedValue || item.actualValue || item.discrepancy) && (
        <div className="bg-paper-1 border border-rule p-2.5 space-y-1.5 text-[11px]">
          {item.expectedValue && (
            <div className="flex justify-between items-center">
              <span className="text-ink-500 uppercase text-[10px]">
                Expected Value:
              </span>
              <span className="font-semibold text-ink-900 tabular-nums">
                {item.expectedValue}
              </span>
            </div>
          )}
          {item.actualValue && (
            <div className="flex justify-between items-center">
              <span className="text-ink-500 uppercase text-[10px]">
                Detected Value:
              </span>
              <span className="font-semibold text-forensic-red tabular-nums">
                {item.actualValue}
              </span>
            </div>
          )}
          {item.discrepancy && (
            <div className="flex justify-between items-center pt-1 border-t border-rule/60">
              <span className="text-ink-500 uppercase text-[10px] font-bold">
                Forensic Discrepancy:
              </span>
              <span className="font-bold text-forensic-red tabular-nums">
                {item.discrepancy}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="mt-2 flex items-center justify-between text-[10px] text-ink-500">
        <span>Page {item.pageNumber || 1}</span>
        <span className="text-ink-900 font-semibold hover:underline">
          {isSelected ? "● Synchronized with Canvas" : "Click to Inspect ↗"}
        </span>
      </div>
    </div>
  );
}
