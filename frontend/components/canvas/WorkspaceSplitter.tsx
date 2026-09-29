"use client";

import React from "react";
import { GripVertical } from "lucide-react";

interface WorkspaceSplitterProps {
  splitRatio: number;
  isDragging: boolean;
  onPointerDown: (e: React.PointerEvent) => void;
  onDoubleClick: () => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
}

export function WorkspaceSplitter({
  splitRatio,
  isDragging,
  onPointerDown,
  onDoubleClick,
  onKeyDown,
}: WorkspaceSplitterProps) {
  return (
    <>
      {/* Fullscreen transparent shield during active drag to prevent canvas / iframe pointer event loss */}
      {isDragging && (
        <div
          className="fixed inset-0 z-50 cursor-col-resize select-none pointer-events-auto"
          style={{ userSelect: "none" }}
        />
      )}

      {/* Draggable Divider Handle */}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Adjust division between viewer and explanation windows"
        aria-valuenow={Math.round(splitRatio)}
        aria-valuemin={20}
        aria-valuemax={80}
        tabIndex={0}
        onPointerDown={onPointerDown}
        onDoubleClick={onDoubleClick}
        onKeyDown={onKeyDown}
        className={`w-2.5 -mx-1.25 h-full relative z-30 cursor-col-resize select-none flex items-center justify-center group outline-none transition-colors shrink-0 ${
          isDragging
            ? "bg-ink-900/10"
            : "hover:bg-ink-900/5 active:bg-ink-900/15"
        }`}
        title="Drag to resize viewer and explanation windows • Double-click to reset"
      >
        {/* Hairline Central Divider Line */}
        <div
          className={`absolute inset-y-0 w-px transition-colors ${
            isDragging
              ? "bg-ink-900 w-0.5"
              : "bg-rule group-hover:bg-ink-600"
          }`}
        />

        {/* Tactile Ergonomic Grip Pill */}
        <div
          className={`relative z-10 w-2 h-10 rounded-full border flex items-center justify-center shadow-xs transition-all ${
            isDragging
              ? "bg-ink-900 border-ink-900 ring-2 ring-ink-900/20 scale-y-110"
              : "bg-paper-0 border-rule group-hover:border-ink-900 group-hover:bg-paper-1 group-focus-visible:ring-2 group-focus-visible:ring-ink-900"
          }`}
        >
          <GripVertical
            className={`w-2.5 h-2.5 transition-colors ${
              isDragging ? "text-paper-0" : "text-ink-400 group-hover:text-ink-900"
            }`}
          />
        </div>

        {/* Live HUD Tooltip during active drag */}
        {isDragging && (
          <div className="absolute top-10 left-1/2 -translate-x-1/2 z-50 bg-ink-900 text-paper-0 px-2.5 py-1 font-mono text-[10px] font-bold shadow-xl border border-ink-700 whitespace-nowrap pointer-events-none flex items-center gap-2">
            <span>VIEWER {Math.round(splitRatio)}%</span>
            <span className="text-ink-500">•</span>
            <span>EXPLANATION {100 - Math.round(splitRatio)}%</span>
          </div>
        )}
      </div>
    </>
  );
}
