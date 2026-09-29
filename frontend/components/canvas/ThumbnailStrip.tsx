"use client";

import React, { useMemo, useState, useRef, useEffect } from "react";
import { DocumentPage, EvidenceItem, FindingSeverity } from "@/lib/types/forensics";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Filter,
  PanelLeftClose,
  Layers,
  ChevronRight,
  Sparkles,
} from "lucide-react";

interface ThumbnailStripProps {
  pages: DocumentPage[];
  currentPage: number;
  onSelectPage: (pageNumber: number) => void;
  evidence: EvidenceItem[];
  isOpen: boolean;
  onToggleOpen: () => void;
  density: "expanded" | "compact";
  onToggleDensity: () => void;
}

interface PageAnomalyTelemetry {
  items: EvidenceItem[];
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  maxSeverity: FindingSeverity | null;
  categories: Set<string>;
  boundingBoxes: Array<{
    xPct: number;
    yPct: number;
    wPct: number;
    hPct: number;
    severity: FindingSeverity;
  }>;
}

export function ThumbnailStrip({
  pages,
  currentPage,
  onSelectPage,
  evidence,
  isOpen,
  onToggleOpen,
  density,
  onToggleDensity,
}: ThumbnailStripProps) {
  const [filterMode, setFilterMode] = useState<"ALL" | "FLAGGED">("ALL");
  const [hoveredPage, setHoveredPage] = useState<number | null>(null);
  const cardRefs = useRef<Record<number, HTMLDivElement | null>>({});

  // ── 1. Telemetry Aggregation per Page ──────────────────────────────────────
  const { pageTelemetry, flaggedPageNumbers, totalAnomalies } = useMemo(() => {
    const map = new Map<number, PageAnomalyTelemetry>();
    let adverseCount = 0;

    for (const page of pages) {
      map.set(page.pageNumber, {
        items: [],
        criticalCount: 0,
        highCount: 0,
        mediumCount: 0,
        lowCount: 0,
        maxSeverity: null,
        categories: new Set<string>(),
        boundingBoxes: [],
      });
    }

    const adverseEvidence = evidence.filter((e) => e.severity !== "INFO");
    adverseCount = adverseEvidence.length;

    for (const ev of adverseEvidence) {
      const pageNum =
        ev.pageNumber ??
        ev.boundingBoxes?.[0]?.pageNumber ??
        ev.anchors?.[0]?.pageNumber;

      if (!pageNum || !map.has(pageNum)) continue;

      const entry = map.get(pageNum)!;
      entry.items.push(ev);

      if (ev.severity === "CRITICAL") entry.criticalCount++;
      else if (ev.severity === "HIGH") entry.highCount++;
      else if (ev.severity === "MEDIUM") entry.mediumCount++;
      else if (ev.severity === "LOW") entry.lowCount++;

      // Max severity calculation
      if (ev.severity === "CRITICAL") {
        entry.maxSeverity = "CRITICAL";
      } else if (ev.severity === "HIGH" && entry.maxSeverity !== "CRITICAL") {
        entry.maxSeverity = "HIGH";
      } else if (
        ev.severity === "MEDIUM" &&
        !["CRITICAL", "HIGH"].includes(entry.maxSeverity || "")
      ) {
        entry.maxSeverity = "MEDIUM";
      } else if (ev.severity === "LOW" && !entry.maxSeverity) {
        entry.maxSeverity = "LOW";
      }

      // Category extraction for micro-chips
      const cat = (ev.category || "").toUpperCase();
      const rId = (ev.ruleId || "").toUpperCase();
      if (cat.includes("MATH") || rId.includes("BALANCE") || rId.includes("FINANCIAL")) {
        entry.categories.add("MATH");
      } else if (cat.includes("IMAGE") || cat.includes("ELA") || rId.includes("TRUFOR")) {
        entry.categories.add("ELA");
      } else if (rId.includes("FONT") || rId.includes("BASELINE") || rId.includes("GLYPH")) {
        entry.categories.add("FONT");
      } else if (cat.includes("DATE") || rId.includes("TIMESTAMP") || rId.includes("HOLIDAY")) {
        entry.categories.add("DATE");
      }

      // Collect bounding box ghost minimap coordinates
      const pageMeta = pages.find((p) => p.pageNumber === pageNum);
      const wPx = pageMeta?.widthPx || 1240;
      const hPx = pageMeta?.heightPx || 1755;

      if (ev.boundingBoxes && ev.boundingBoxes.length > 0) {
        for (const box of ev.boundingBoxes) {
          if (box.pageNumber === pageNum) {
            entry.boundingBoxes.push({
              xPct: Math.max(0, Math.min(100, (box.x / wPx) * 100)),
              yPct: Math.max(0, Math.min(100, (box.y / hPx) * 100)),
              wPct: Math.max(2, Math.min(100, (box.width / wPx) * 100)),
              hPct: Math.max(1.5, Math.min(100, (box.height / hPx) * 100)),
              severity: ev.severity,
            });
          }
        }
      }
    }

    const flaggedPages = Array.from(map.entries())
      .filter(([_, data]) => data.items.length > 0)
      .map(([num]) => num);

    return {
      pageTelemetry: map,
      flaggedPageNumbers: flaggedPages,
      totalAnomalies: adverseCount,
    };
  }, [pages, evidence]);

  // Filtered page list
  const visiblePages = useMemo(() => {
    if (filterMode === "FLAGGED") {
      return pages.filter((p) => (pageTelemetry.get(p.pageNumber)?.items.length || 0) > 0);
    }
    return pages;
  }, [pages, filterMode, pageTelemetry]);

  // ── 2. Auto-scroll active card into view ──────────────────────────────────
  useEffect(() => {
    const el = cardRefs.current[currentPage];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [currentPage]);

  if (!isOpen) return null;

  return (
    <div
      className={`h-full bg-paper-1 border-r border-rule flex flex-col select-none transition-all duration-200 z-20 flex-shrink-0 ${
        density === "expanded" ? "w-36 md:w-40" : "w-14"
      }`}
    >
      {/* Filmstrip Header */}
      <div className="p-2 border-b border-rule bg-paper-0/80 backdrop-blur-xs flex flex-col gap-1.5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 overflow-hidden">
            <Layers className="w-3.5 h-3.5 text-ink-900 flex-shrink-0" />
            {density === "expanded" && (
              <span className="font-mono text-[11px] font-bold tracking-wider text-ink-900 uppercase truncate">
                FOLIO ({pages.length})
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={onToggleDensity}
              className="p-1 text-ink-500 hover:text-ink-900 hover:bg-paper-2 rounded-xs transition-colors cursor-pointer"
              title={density === "expanded" ? "Switch to Compact View" : "Expand Filmstrip"}
            >
              <span className="font-mono text-[10px] font-bold">
                {density === "expanded" ? "⇥" : "⇤"}
              </span>
            </button>
            <button
              onClick={onToggleOpen}
              className="p-1 text-ink-500 hover:text-ink-900 hover:bg-paper-2 rounded-xs transition-colors cursor-pointer"
              title="Close Filmstrip"
            >
              <PanelLeftClose className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Triage Filter Toggle (Expanded Mode Only) */}
        {density === "expanded" && (
          <div className="grid grid-cols-2 gap-1 font-mono text-[10px] pt-0.5">
            <button
              type="button"
              onClick={() => setFilterMode("ALL")}
              className={`py-1 px-1.5 text-center font-semibold uppercase border transition-colors cursor-pointer ${
                filterMode === "ALL"
                  ? "bg-ink-900 text-paper-0 border-ink-900"
                  : "bg-paper-0 text-ink-600 border-rule hover:bg-paper-2"
              }`}
            >
              ALL ({pages.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterMode("FLAGGED")}
              className={`py-1 px-1.5 text-center font-semibold uppercase border transition-colors flex items-center justify-center gap-1 cursor-pointer ${
                filterMode === "FLAGGED"
                  ? "bg-rose-700 text-paper-0 border-rose-700"
                  : flaggedPageNumbers.length > 0
                  ? "bg-paper-0 text-rose-700 border-rose-300 hover:bg-rose-50"
                  : "bg-paper-0 text-ink-400 border-rule opacity-60 cursor-not-allowed"
              }`}
              disabled={flaggedPageNumbers.length === 0}
            >
              <span>FLAGGED</span>
              {flaggedPageNumbers.length > 0 && (
                <span className="inline-block px-1 rounded-full text-[9px] bg-rose-600 text-white leading-tight">
                  {flaggedPageNumbers.length}
                </span>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Filmstrip Scroll Body */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 space-y-2.5 scrollbar-thin">
        {visiblePages.length === 0 ? (
          <div className="text-center py-8 px-2 font-mono text-[11px] text-ink-500">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 mx-auto mb-1.5" />
            <span>NO FLAGGED PAGES</span>
          </div>
        ) : (
          visiblePages.map((page) => {
            const isSelected = page.pageNumber === currentPage;
            const telem = pageTelemetry.get(page.pageNumber);
            const findingCount = telem?.items.length || 0;
            const maxSeverity = telem?.maxSeverity;

            // Border color by severity
            let severityBorder = "border-rule";
            let severityBg = "bg-paper-0";
            let runnerBg = "bg-transparent";

            if (maxSeverity === "CRITICAL") {
              severityBorder = isSelected ? "border-rose-700 ring-2 ring-rose-700/30" : "border-rose-400/80";
              runnerBg = "bg-rose-600";
            } else if (maxSeverity === "HIGH") {
              severityBorder = isSelected ? "border-amber-600 ring-2 ring-amber-600/30" : "border-amber-400/80";
              runnerBg = "bg-amber-500";
            } else if (maxSeverity === "MEDIUM") {
              severityBorder = isSelected ? "border-yellow-600 ring-2 ring-yellow-600/30" : "border-yellow-400/80";
              runnerBg = "bg-yellow-500";
            } else if (maxSeverity === "LOW") {
              severityBorder = isSelected ? "border-blue-600 ring-2 ring-blue-600/30" : "border-blue-300";
              runnerBg = "bg-blue-500";
            } else {
              runnerBg = "bg-emerald-500/30";
              if (isSelected) severityBorder = "border-ink-900 ring-2 ring-ink-900/20";
            }

            return (
              <div
                key={`thumb-p-${page.pageNumber}`}
                ref={(el) => {
                  cardRefs.current[page.pageNumber] = el;
                }}
                onMouseEnter={() => setHoveredPage(page.pageNumber)}
                onMouseLeave={() => setHoveredPage(null)}
                onClick={() => onSelectPage(page.pageNumber)}
                className={`group relative flex flex-col cursor-pointer transition-all duration-150 ${
                  isSelected ? "scale-[1.02]" : "hover:scale-[1.01]"
                }`}
              >
                {/* Thumbnail Card Sheet */}
                <div
                  className={`relative overflow-hidden bg-white border shadow-xs aspect-[1/1.414] ${severityBorder}`}
                >
                  {/* Miniature Image View */}
                  {page.renderedImageUrl ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={page.renderedImageUrl}
                      alt={`Page ${page.pageNumber}`}
                      loading="lazy"
                      draggable={false}
                      className="w-full h-full object-cover select-none pointer-events-none"
                    />
                  ) : (
                    <div className="w-full h-full bg-paper-1 flex items-center justify-center font-mono text-[10px] text-ink-400">
                      P.{page.pageNumber}
                    </div>
                  )}

                  {/* Spatial Anomaly Ghost Minimap Overlay */}
                  {telem && telem.boundingBoxes.length > 0 && (
                    <svg
                      viewBox="0 0 100 100"
                      preserveAspectRatio="none"
                      className="absolute inset-0 w-full h-full pointer-events-none z-10"
                    >
                      {telem.boundingBoxes.map((box, idx) => {
                        const boxStroke =
                          box.severity === "CRITICAL"
                            ? "#e11d48"
                            : box.severity === "HIGH"
                            ? "#d97706"
                            : box.severity === "MEDIUM"
                            ? "#ca8a04"
                            : "#2563eb";
                        return (
                          <rect
                            key={`ghost-${idx}`}
                            x={box.xPct}
                            y={box.yPct}
                            width={box.wPct}
                            height={box.hPct}
                            fill={boxStroke}
                            fillOpacity="0.25"
                            stroke={boxStroke}
                            strokeWidth="1.2"
                            strokeDasharray="2,1"
                          />
                        );
                      })}
                    </svg>
                  )}

                  {/* Finding Badge (Top Right) */}
                  {findingCount > 0 && (
                    <div className="absolute top-1 right-1 z-20">
                      <span
                        className={`inline-flex items-center justify-center font-mono text-[9px] font-bold px-1.5 py-0.5 rounded-xs shadow-sm text-white ${
                          maxSeverity === "CRITICAL"
                            ? "bg-rose-700"
                            : maxSeverity === "HIGH"
                            ? "bg-amber-600"
                            : maxSeverity === "MEDIUM"
                            ? "bg-yellow-600"
                            : "bg-blue-600"
                        }`}
                      >
                        {findingCount}
                      </span>
                    </div>
                  )}

                  {/* Active Page Indicator Reticle */}
                  {isSelected && (
                    <div className="absolute top-1 left-1 z-20">
                      <span className="w-2 h-2 rounded-full bg-ink-900 block ring-2 ring-white animate-pulse" />
                    </div>
                  )}

                  {/* Bottom Severity Accent Ribbon */}
                  <div className={`absolute bottom-0 left-0 right-0 h-1 z-20 ${runnerBg}`} />
                </div>

                {/* Expanded Mode Card Footer */}
                {density === "expanded" && (
                  <div className="pt-1 px-0.5 flex flex-col gap-0.5 font-mono text-[10px]">
                    <div className="flex items-center justify-between">
                      <span
                        className={`font-semibold ${
                          isSelected ? "text-ink-900 font-bold" : "text-ink-700"
                        }`}
                      >
                        P. {page.pageNumber}
                      </span>
                      {findingCount > 0 ? (
                        <span
                          className={`font-semibold uppercase tracking-wider text-[9px] ${
                            maxSeverity === "CRITICAL"
                              ? "text-rose-700"
                              : maxSeverity === "HIGH"
                              ? "text-amber-700"
                              : "text-ink-600"
                          }`}
                        >
                          {findingCount} {findingCount === 1 ? "FLAG" : "FLAGS"}
                        </span>
                      ) : (
                        <span className="text-emerald-700 text-[9px] flex items-center gap-0.5">
                          ✓ CLEAN
                        </span>
                      )}
                    </div>

                    {/* Category Micro-Pills */}
                    {telem && telem.categories.size > 0 && (
                      <div className="flex flex-wrap gap-1 pt-0.5">
                        {Array.from(telem.categories).map((cat) => (
                          <span
                            key={cat}
                            className="px-1 py-0.2 bg-paper-2 border border-rule text-[8px] font-semibold text-ink-700 uppercase"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Compact Mode Card Footer (Page Number Only) */}
                {density === "compact" && (
                  <div className="text-center pt-0.5 font-mono text-[9px] font-bold text-ink-800">
                    {page.pageNumber}
                  </div>
                )}

                {/* Quick-Peek Popover on Hover (Institutional Tooltip) */}
                {hoveredPage === page.pageNumber && telem && telem.items.length > 0 && (
                  <div className="absolute left-full top-0 ml-2.5 w-60 bg-paper-0 border-2 border-ink-900 shadow-xl p-2.5 font-mono text-xs z-50 pointer-events-none animate-in fade-in zoom-in-95 duration-100">
                    <div className="flex items-center justify-between border-b border-rule pb-1.5 mb-1.5">
                      <span className="font-bold text-ink-900 uppercase">
                        PAGE {page.pageNumber} AUDIT
                      </span>
                      <span
                        className={`px-1.5 py-0.5 text-[9px] font-bold uppercase text-white ${
                          maxSeverity === "CRITICAL"
                            ? "bg-rose-700"
                            : maxSeverity === "HIGH"
                            ? "bg-amber-600"
                            : "bg-blue-600"
                        }`}
                      >
                        {maxSeverity}
                      </span>
                    </div>

                    <div className="space-y-1.5 max-h-40 overflow-hidden">
                      {telem.items.slice(0, 3).map((item, i) => (
                        <div key={item.id || i} className="text-[10px] leading-tight">
                          <span className="font-bold text-ink-900 block truncate">
                            • {item.title || item.ruleId}
                          </span>
                          {item.discrepancy && (
                            <span className="text-rose-700 font-semibold block text-[9px] pl-2 font-mono">
                              {item.discrepancy}
                            </span>
                          )}
                        </div>
                      ))}
                      {telem.items.length > 3 && (
                        <span className="text-[9px] text-ink-500 italic block pt-0.5">
                          +{telem.items.length - 3} more finding(s)...
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Filmstrip Footer */}
      <div className="p-2 border-t border-rule bg-paper-0/80 font-mono text-[9px] text-ink-500 flex flex-col gap-0.5 flex-shrink-0">
        <div className="flex justify-between items-center">
          <span className="uppercase">TOTAL ANOMALIES:</span>
          <span className="font-bold text-rose-700 tabular-nums">
            {totalAnomalies}
          </span>
        </div>
        {density === "expanded" && (
          <span className="text-[8px] text-ink-400 truncate">
            Press [ / ] to navigate • Shift+[ / ] for flags
          </span>
        )}
      </div>
    </div>
  );
}
