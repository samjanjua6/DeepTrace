"use client";

import React from "react";
import { EvidenceItem } from "@/lib/types/forensics";

interface AnomalyCardProps {
  item: EvidenceItem;
  isSelected: boolean;
  onSelect: (id: string | null) => void;
  onFocusCanvas?: (pageNumber: number) => void;
}

export function AnomalyCard({
  item,
  isSelected,
  onSelect,
  onFocusCanvas,
}: AnomalyCardProps) {
  const isInfo = item.severity === "INFO" || item.ruleId.endsWith("_VERIFIED");

  const getSeverityStyle = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return "border-forensic-red/50 bg-forensic-red/5 text-forensic-red";
      case "HIGH":
        return "border-forensic-amber/50 bg-forensic-amber/5 text-forensic-amber";
      case "INFO":
        return "border-emerald-500/50 bg-emerald-500/10 text-emerald-800 font-bold";
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
          : isInfo
          ? "border-emerald-500/30 bg-paper-0 hover:bg-emerald-50/20"
          : "border-rule bg-paper-0 hover:bg-paper-1/60"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span
          className={`text-[9px] font-bold px-2 py-0.5 border uppercase tracking-wider ${getSeverityStyle(
            item.severity
          )}`}
        >
          {isInfo ? "✓ VERIFIED AUTHENTIC" : item.severity}
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
                {isInfo ? "Observed Value:" : "Detected Value:"}
              </span>
              <span
                className={`font-semibold tabular-nums ${
                  isInfo ? "text-emerald-700" : "text-forensic-red"
                }`}
              >
                {item.actualValue}
              </span>
            </div>
          )}
          {item.discrepancy && (
            <div className="flex justify-between items-center pt-1 border-t border-rule/60">
              <span className="text-ink-500 uppercase text-[10px] font-bold">
                {isInfo ? "Verification Status:" : "Forensic Discrepancy:"}
              </span>
              <span
                className={`font-bold tabular-nums ${
                  isInfo ? "text-emerald-700" : "text-forensic-red"
                }`}
              >
                {item.discrepancy}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10px] text-ink-500 pt-2 border-t border-rule/40">
        {/* Anchor Location Display */}
        <div className="flex items-center gap-1.5">
          {item.technicalDetails?.anchor_type === "DOCUMENT_METADATA" || (!item.pageNumber && !item.technicalDetails?.row_number) ? (
            <span className="bg-ink-800 text-paper-0 px-1.5 py-0.5 font-bold">
              DOC METADATA
            </span>
          ) : item.technicalDetails?.anchor_type === "MULTI_PAGE_SPAN" ? (
            <div className="flex items-center gap-1">
              <span className="bg-forensic-red text-white px-1.5 py-0.5 font-bold">
                P.1–{item.pageNumber || 23} LEDGER
              </span>
              {item.technicalDetails?.anchors?.map((anc: any, aIdx: number) => (
                <button
                  key={aIdx}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect(item.id);
                    if (anc.pageNumber) onFocusCanvas?.(anc.pageNumber);
                  }}
                  className="px-1.5 py-0.5 bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/20 rounded-sm transition-colors text-[9px] font-bold cursor-pointer"
                  title={`Jump to ${anc.label}`}
                >
                  {anc.label} ↗
                </button>
              )) || (
                <>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(item.id);
                      onFocusCanvas?.(1);
                    }}
                    className="px-1.5 py-0.5 bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/20 rounded-sm transition-colors text-[9px] font-bold cursor-pointer"
                  >
                    P.1 Summary ↗
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(item.id);
                      onFocusCanvas?.(item.pageNumber || 23);
                    }}
                    className="px-1.5 py-0.5 bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/20 rounded-sm transition-colors text-[9px] font-bold cursor-pointer"
                  >
                    P.{item.pageNumber || 23} Ledger ↗
                  </button>
                </>
              )}
            </div>
          ) : item.technicalDetails?.row_number ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelect(item.id);
                if (item.pageNumber) onFocusCanvas?.(item.pageNumber);
              }}
              className="bg-ink-900 hover:bg-forensic-blue text-paper-0 px-1.5 py-0.5 font-bold transition-colors cursor-pointer"
            >
              Page {item.pageNumber}, Row {item.technicalDetails.row_number} ↗
            </button>
          ) : item.technicalDetails?.anchor_type === "DOCUMENT_HEADER" ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelect(item.id);
                if (item.pageNumber) onFocusCanvas?.(item.pageNumber);
              }}
              className="bg-ink-900 hover:bg-forensic-blue text-paper-0 px-1.5 py-0.5 font-bold transition-colors cursor-pointer"
            >
              Page {item.pageNumber} Header ↗
            </button>
          ) : item.pageNumber ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelect(item.id);
                onFocusCanvas?.(item.pageNumber!);
              }}
              className="bg-ink-900 hover:bg-forensic-blue text-paper-0 px-1.5 py-0.5 font-bold transition-colors cursor-pointer"
            >
              Page {item.pageNumber} ↗
            </button>
          ) : (
            <span className="bg-ink-800 text-paper-0 px-1.5 py-0.5 font-bold">
              DOC METADATA
            </span>
          )}
        </div>

        <span className="text-ink-900 font-semibold hover:underline">
          {isSelected ? "● Synchronized with Canvas" : "Click to Inspect ↗"}
        </span>
      </div>
    </div>
  );
}
