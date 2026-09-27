"use client";

import React from "react";
import {
  AlertOctagon,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
} from "lucide-react";
import { EvidenceItem } from "@/lib/types/forensics";

interface AnomalyCardProps {
  item: EvidenceItem;
  findingNumber?: number | string;
  isSelected: boolean;
  onSelect: (id: string | null) => void;
  onFocusCanvas?: (pageNumber: number) => void;
}

export function AnomalyCard({
  item,
  findingNumber,
  isSelected,
  onSelect,
  onFocusCanvas,
}: AnomalyCardProps) {
  const isInfo = item.severity === "INFO" || item.ruleId.endsWith("_VERIFIED");

  const renderSeverityBadge = (sev: string) => {
    if (isInfo) {
      return (
        <span className="text-xs font-bold px-2.5 py-1 border border-emerald-700/80 bg-emerald-100 text-emerald-950 uppercase tracking-wider inline-flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700 shrink-0 stroke-[2.5]" />
          VERIFIED AUTHENTIC
        </span>
      );
    }
    switch (sev) {
      case "CRITICAL":
        return (
          <span className="text-xs font-bold px-2.5 py-1 border border-rose-700/80 bg-rose-100 text-rose-950 uppercase tracking-wider inline-flex items-center gap-1.5">
            <AlertOctagon className="w-3.5 h-3.5 text-rose-700 shrink-0 stroke-[2.5]" />
            CRITICAL
          </span>
        );
      case "HIGH":
        return (
          <span className="text-xs font-bold px-2.5 py-1 border border-amber-700/80 bg-amber-100 text-amber-950 uppercase tracking-wider inline-flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-800 shrink-0 stroke-[2.5]" />
            HIGH RISK
          </span>
        );
      case "MEDIUM":
        return (
          <span className="text-xs font-bold px-2.5 py-1 border border-yellow-700/80 bg-yellow-100 text-yellow-950 uppercase tracking-wider inline-flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-yellow-800 shrink-0 stroke-[2.5]" />
            MEDIUM RISK
          </span>
        );
      case "LOW":
        return (
          <span className="text-xs font-bold px-2.5 py-1 border border-sky-700/80 bg-sky-100 text-sky-950 uppercase tracking-wider inline-flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-sky-700 shrink-0 stroke-[2.5]" />
            LOW RISK
          </span>
        );
      default:
        return (
          <span className="text-xs font-bold px-2.5 py-1 border border-rule-dark bg-paper-1 text-ink-800 uppercase tracking-wider inline-flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-ink-700 shrink-0 stroke-[2.5]" />
            {sev}
          </span>
        );
    }
  };

  return (
    <div
      id={`finding-card-${item.id}`}
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
        <div className="flex items-center gap-1.5 flex-wrap">
          {findingNumber !== undefined && (
            <span
              className={`w-6 h-6 rounded-full font-mono font-bold text-xs flex items-center justify-center shrink-0 shadow-xs ${
                item.severity === "CRITICAL"
                  ? "bg-rose-700 text-white"
                  : item.severity === "HIGH"
                  ? "bg-amber-700 text-white"
                  : isInfo
                  ? "bg-emerald-700 text-white"
                  : "bg-ink-800 text-white"
              }`}
              title={`Finding #${findingNumber}`}
            >
              {findingNumber}
            </span>
          )}
          {renderSeverityBadge(item.severity)}
          {item.technicalDetails?.pattern === "magnitude_inflation" && (
            <span className="text-[11px] font-bold px-2 py-0.5 bg-amber-100 border border-amber-600 text-amber-950 uppercase">
              MAGNITUDE ({item.technicalDetails.multiplier ? `${item.technicalDetails.multiplier}×` : "1000×"})
            </span>
          )}
          {item.technicalDetails?.corroborated_with && (
            <span className="text-[11px] font-bold px-2 py-0.5 bg-blue-100 border border-blue-600 text-blue-950 uppercase">
              CORROBORATED
            </span>
          )}
        </div>
        <span className="text-[11px] text-ink-700 font-bold tracking-wider uppercase">
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
        <div className="bg-paper-1 border border-rule p-3 space-y-2 text-xs">
          {item.expectedValue && (
            <div className="flex justify-between items-center">
              <span className="text-ink-700 uppercase text-[11px] font-bold tracking-wider">
                Expected Value:
              </span>
              <span className="font-bold text-ink-900 tabular-nums">
                {item.expectedValue}
              </span>
            </div>
          )}
          {item.actualValue && (
            <div className="flex justify-between items-center">
              <span className="text-ink-700 uppercase text-[11px] font-bold tracking-wider">
                {isInfo ? "Observed Value:" : "Detected Value:"}
              </span>
              <span
                className={`font-bold tabular-nums ${
                  isInfo ? "text-emerald-700" : "text-forensic-red"
                }`}
              >
                {item.actualValue}
              </span>
            </div>
          )}
          {item.discrepancy && (
            <div className="flex justify-between items-center pt-1.5 border-t border-rule/60">
              <span className="text-ink-700 uppercase text-[11px] font-bold tracking-wider">
                {isInfo ? "Verification Status:" : "Forensic Discrepancy:"}
              </span>
              <span
                className={`font-bold tabular-nums text-xs ${
                  isInfo ? "text-emerald-700" : "text-forensic-red"
                }`}
              >
                {item.discrepancy}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Typography / Font Irregularity Chip if detected */}
      {(item.technicalDetails?.font_detected || item.description?.match(/([A-Za-z0-9_-]+)\s+instead/i)) && (
        <div className="mt-2 text-[11px] text-ink-800 font-mono">
          <span className="bg-purple-500/15 border border-purple-500/30 text-purple-950 px-2 py-0.5 inline-block font-medium">
            Font: <strong>{item.technicalDetails?.font_detected || item.description?.match(/([A-Za-z0-9_-]+)\s+instead/i)?.[1]}</strong>
            {item.technicalDetails?.expected_font ? ` vs ${item.technicalDetails.expected_font}` : ""}
          </span>
        </div>
      )}

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink-700 pt-2 border-t border-rule/50">
        {/* Anchor Location Display */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {item.technicalDetails?.anchor_type === "DOCUMENT_METADATA" || (!item.pageNumber && !item.technicalDetails?.row_number) ? (
            <span className="bg-ink-900 text-paper-0 px-2 py-0.5 font-bold text-[11px]">
              DOC METADATA
            </span>
          ) : (item.technicalDetails?.endpoints && item.technicalDetails.endpoints.length > 0) ? (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="bg-forensic-red text-white px-2 py-0.5 font-bold text-[11px]">
                P.{item.technicalDetails.page_start || 1}–{item.pageNumber || 23} SPAN
              </span>
              {item.technicalDetails.endpoints.map((ep: any, epIdx: number) => (
                <button
                  key={epIdx}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect(item.id);
                    if (ep.page) onFocusCanvas?.(ep.page);
                  }}
                  className="px-2 py-0.5 bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/30 rounded-none transition-colors text-[11px] font-bold cursor-pointer"
                  title={`Jump to ${ep.label || ep.role}`}
                >
                  {ep.label || ep.role} ↗
                </button>
              ))}
            </div>
          ) : item.technicalDetails?.anchor_type === "MULTI_PAGE_SPAN" ? (
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="bg-forensic-red text-white px-2 py-0.5 font-bold text-[11px]">
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
                  className="px-2 py-0.5 bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/30 rounded-none transition-colors text-[11px] font-bold cursor-pointer"
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
                    className="px-2 py-0.5 bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/30 rounded-none transition-colors text-[11px] font-bold cursor-pointer"
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
                    className="px-2 py-0.5 bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/30 rounded-none transition-colors text-[11px] font-bold cursor-pointer"
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
              className="bg-ink-900 hover:bg-forensic-blue text-paper-0 px-2 py-0.5 font-bold transition-colors cursor-pointer text-[11px]"
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
              className="bg-ink-900 hover:bg-forensic-blue text-paper-0 px-2 py-0.5 font-bold transition-colors cursor-pointer text-[11px]"
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
              className="bg-ink-900 hover:bg-forensic-blue text-paper-0 px-2 py-0.5 font-bold transition-colors cursor-pointer text-[11px]"
            >
              Page {item.pageNumber} ↗
            </button>
          ) : (
            <span className="bg-ink-800 text-paper-0 px-2 py-0.5 font-bold text-[11px]">
              DOC METADATA
            </span>
          )}
        </div>

        <span className="text-ink-900 font-bold hover:underline text-[11px]">
          {isSelected ? "● Synchronized with Canvas" : "Click to Inspect ↗"}
        </span>
      </div>
    </div>
  );
}
