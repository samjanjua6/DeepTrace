"use client";

import React from "react";
import { ZoomIn, ZoomOut, Maximize2, Layers } from "lucide-react";

interface CanvasToolbarProps {
  zoom: number;
  onZoomChange: (newZoom: number) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showELA: boolean;
  onToggleELA: (show: boolean) => void;
  elaOpacity: number;
  onElaOpacityChange: (opacity: number) => void;
  showRuler: boolean;
  onToggleRuler: (show: boolean) => void;
  pinnedBaselinesCount?: number;
  onClearPinnedBaselines?: () => void;
  selectedCategory?: string;
  onCategoryChange?: (cat: string) => void;
  categoryCounts?: {
    all: number;
    financial: number;
    visual: number;
    dates: number;
  };
}

export function CanvasToolbar({
  zoom,
  onZoomChange,
  currentPage,
  totalPages,
  onPageChange,
  showELA,
  onToggleELA,
  elaOpacity,
  onElaOpacityChange,
  showRuler,
  onToggleRuler,
  pinnedBaselinesCount = 0,
  onClearPinnedBaselines,
  selectedCategory = "ALL",
  onCategoryChange,
  categoryCounts,
}: CanvasToolbarProps) {
  return (
    <div className="w-full bg-paper-1 border-b border-rule px-4 py-2 flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-ink-700 select-none">
      {/* Page Navigation */}
      <div className="flex items-center gap-2">
        <span className="text-ink-500 uppercase">PAGE:</span>
        <button
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
          className="px-2 py-1 bg-paper-0 border border-rule hover:bg-paper-2 disabled:opacity-40 disabled:hover:bg-paper-0 transition-colors"
        >
          ‹
        </button>
        <span className="px-2 py-1 bg-paper-0 border border-rule tabular-nums font-semibold">
          {currentPage} / {Math.max(1, totalPages)}
        </span>
        <button
          onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage >= totalPages}
          className="px-2 py-1 bg-paper-0 border border-rule hover:bg-paper-2 disabled:opacity-40 disabled:hover:bg-paper-0 transition-colors"
        >
          ›
        </button>
      </div>

      {/* Zoom Controls */}
      <div className="flex items-center gap-1.5 border-l border-r border-rule px-3">
        <button
          onClick={() => onZoomChange(Math.max(0.25, zoom - 0.15))}
          className="p-1 bg-paper-0 border border-rule hover:bg-paper-2 transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <span className="px-2 py-1 bg-paper-0 border border-rule tabular-nums min-w-[54px] text-center font-semibold">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => onZoomChange(Math.min(4.0, zoom + 0.15))}
          className="p-1 bg-paper-0 border border-rule hover:bg-paper-2 transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => onZoomChange(1.0)}
          className="p-1 bg-paper-0 border border-rule hover:bg-paper-2 transition-colors ml-1"
          title="Reset Zoom (100%)"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Finding Category Filters */}
      {categoryCounts && onCategoryChange && (
        <div className="flex items-center gap-1 border-r border-rule pr-3">
          <span className="text-[10px] text-ink-500 mr-1 hidden sm:inline uppercase tracking-wider">
            FILTER:
          </span>
          <button
            onClick={() => onCategoryChange("ALL")}
            className={`px-2 py-0.5 border text-[10px] uppercase font-mono transition-colors ${
              selectedCategory === "ALL"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
            }`}
          >
            ALL ({categoryCounts.all})
          </button>
          <button
            onClick={() => onCategoryChange("FINANCIAL")}
            className={`px-2 py-0.5 border text-[10px] uppercase font-mono transition-colors ${
              selectedCategory === "FINANCIAL"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
            }`}
            title="Show only financial balance and ledger tampering"
          >
            FINANCIAL ({categoryCounts.financial})
          </button>
          <button
            onClick={() => onCategoryChange("VISUAL")}
            className={`px-2 py-0.5 border text-[10px] uppercase font-mono transition-colors ${
              selectedCategory === "VISUAL"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
            }`}
            title="Show image ELA and copy-move forgery"
          >
            VISUAL ({categoryCounts.visual})
          </button>
          <button
            onClick={() => onCategoryChange("DATES")}
            className={`px-2 py-0.5 border text-[10px] uppercase font-mono transition-colors ${
              selectedCategory === "DATES"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
            }`}
            title="Show bank holiday and weekend transaction dates"
          >
            DATES ({categoryCounts.dates})
          </button>
        </div>
      )}

      {/* Forensic Inspection Layers */}
      <div className="flex items-center gap-3">
        {/* Baseline Ruler Toggle & Pinned Clearer */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onToggleRuler(!showRuler)}
            className={`px-2.5 py-1 border transition-colors flex items-center gap-1.5 font-mono text-[11px] ${
              showRuler
                ? "bg-ink-900 text-paper-0 border-ink-900 shadow-sm"
                : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
            }`}
            title="Toggle interactive baseline ruler (click on document to pin lines)"
          >
            <span>BASELINE GUIDE</span>
          </button>
          {pinnedBaselinesCount > 0 && onClearPinnedBaselines && (
            <button
              onClick={onClearPinnedBaselines}
              className="px-2 py-1 bg-paper-0 text-ink-700 border border-rule hover:bg-paper-2 transition-colors text-[10px] uppercase font-mono"
              title="Clear all pinned baseline guides"
            >
              CLEAR ({pinnedBaselinesCount})
            </button>
          )}
        </div>

        {/* ELA Heatmap Toggle & Slider */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onToggleELA(!showELA)}
            className={`px-2.5 py-1 border transition-colors flex items-center gap-1.5 ${
              showELA
                ? "bg-forensic-red text-white border-forensic-red"
                : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>ELA (Q=95)</span>
          </button>
          {showELA && (
            <div className="flex items-center gap-1.5 bg-paper-0 border border-rule px-2 py-0.5">
              <span className="text-[10px] text-ink-500">ALPHA:</span>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={elaOpacity}
                onChange={(e) => onElaOpacityChange(parseFloat(e.target.value))}
                className="w-16 h-1 accent-forensic-red cursor-pointer"
              />
              <span className="tabular-nums text-[10px] text-ink-700 font-semibold w-6">
                {Math.round(elaOpacity * 100)}%
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
