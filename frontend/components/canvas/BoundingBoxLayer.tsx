"use client";

import React from "react";
import { EvidenceItem } from "@/lib/types/forensics";

interface BoundingBoxLayerProps {
  evidence: EvidenceItem[];
  currentPage: number;
  canvasWidth: number;
  canvasHeight: number;
  activeEvidenceId: string | null;
  onSelectEvidence: (id: string | null) => void;
  showRuler: boolean;
  mousePos?: { x: number; y: number } | null;
  pinnedBaselines?: number[];
  selectedCategory?: string;
}

export function BoundingBoxLayer({
  evidence,
  currentPage,
  canvasWidth,
  canvasHeight,
  activeEvidenceId,
  onSelectEvidence,
  showRuler,
  mousePos,
  pinnedBaselines = [],
  selectedCategory = "ALL",
}: BoundingBoxLayerProps) {
  // Filter evidence items that have bounding boxes on this page and match category
  const pageEvidence = evidence.filter((ev) => {
    const hasBoxOnPage =
      ev.boundingBoxes &&
      ev.boundingBoxes.some((b) => b.pageNumber === currentPage);
    if (!hasBoxOnPage) return false;

    if (!selectedCategory || selectedCategory === "ALL") return true;

    const rId = (ev.ruleId || "").toUpperCase();
    const cat = (ev.category || "").toUpperCase();

    if (selectedCategory === "FINANCIAL") {
      return (
        cat.includes("MATH") ||
        rId.includes("BALANCE") ||
        rId.includes("FINANCIAL") ||
        rId.includes("OPENING") ||
        rId.includes("CLOSING")
      );
    }
    if (selectedCategory === "VISUAL") {
      return (
        cat.includes("IMAGE") ||
        cat.includes("ELA") ||
        rId.includes("TRUFOR") ||
        rId.includes("COPY_MOVE") ||
        rId.includes("ELA")
      );
    }
    if (selectedCategory === "DATES") {
      return (
        cat.includes("DATE") ||
        cat.includes("TIMESTAMP") ||
        rId.includes("HOLIDAY") ||
        rId.includes("DATE") ||
        rId.includes("TIMESTAMP")
      );
    }
    return true;
  });

  return (
    <svg
      className="absolute inset-0 pointer-events-auto"
      viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
      style={{ width: "100%", height: "100%" }}
    >
      <defs>
        <pattern
          id="hatch-red"
          width="8"
          height="8"
          patternTransform="rotate(45 0 0)"
          patternUnits="userSpaceOnUse"
        >
          <line
            x1="0"
            y1="0"
            x2="0"
            y2="8"
            stroke="#BA2518"
            strokeWidth="1"
            opacity="0.3"
          />
        </pattern>
        {/* Arrow marker for copy-move vectors */}
        <marker
          id="arrow-cmfd"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#BA2518" />
        </marker>
      </defs>

      {/* Pinned Reference Baselines Layer (Institutional Archival Ink Rule) */}
      {showRuler &&
        pinnedBaselines.map((pinnedY, idx) => (
          <g key={`pinned-${idx}`} className="select-none pointer-events-none">
            <line
              x1={0}
              y1={pinnedY}
              x2={canvasWidth}
              y2={pinnedY}
              stroke="#141413"
              strokeWidth={1.5}
              strokeDasharray="6 3"
              opacity="0.85"
            />
            <rect
              x={6}
              y={Math.max(4, pinnedY - 18)}
              width={125}
              height={16}
              fill="#141413"
              rx={1}
            />
            <text
              x={10}
              y={Math.max(4, pinnedY - 18) + 11}
              fill="#FBF9F5"
              fontSize="9"
              fontFamily="monospace"
              fontWeight="bold"
            >
              PINNED #{idx + 1}: {(pinnedY * (72 / 150)).toFixed(1)} pt
            </text>
          </g>
        ))}

      {/* Live Mouse Laser Guideline Layer (Institutional Theme) */}
      {showRuler && mousePos && (
        <g className="select-none pointer-events-none">
          <line
            x1={0}
            y1={mousePos.y}
            x2={canvasWidth}
            y2={mousePos.y}
            stroke="#141413"
            strokeWidth={1}
            strokeDasharray="4 2"
            opacity="0.85"
          />
          <rect
            x={canvasWidth - 150}
            y={Math.max(4, mousePos.y - 18)}
            width={145}
            height={16}
            fill="#141413"
          />
          <text
            x={canvasWidth - 143}
            y={Math.max(4, mousePos.y - 18) + 11}
            fill="#FBF9F5"
            fontSize="9"
            fontFamily="monospace"
            fontWeight="bold"
          >
            Y: {(mousePos.y * (72 / 150)).toFixed(1)} PT ({Math.round(mousePos.y)} PX)
          </text>
        </g>
      )}

      {/* Bounding Boxes and Evidence Highlights */}
      {pageEvidence.map((ev) => {
        const isSelected = activeEvidenceId === ev.id;
        const boxes = (ev.boundingBoxes || []).filter(
          (b) => b.pageNumber === currentPage
        );

        return (
          <g
            key={ev.id}
            className="cursor-pointer group"
            onClick={() => onSelectEvidence(isSelected ? null : ev.id)}
            onMouseEnter={() => onSelectEvidence(ev.id)}
          >
            {/* Copy-Move Directional Vector Connector */}
            {ev.ruleId === "RULE_CV_COPY_MOVE_FORGERY" && boxes.length >= 2 && (
              (() => {
                const srcBox =
                  boxes.find((b) => b.label?.toLowerCase().includes("source")) ||
                  boxes[0];
                const dstBox =
                  boxes.find((b) =>
                    b.label?.toLowerCase().includes("destination")
                  ) || boxes[1];
                const sx = srcBox.x + srcBox.width / 2;
                const sy = srcBox.y + srcBox.height / 2;
                const dx = dstBox.x + dstBox.width / 2;
                const dy = dstBox.y + dstBox.height / 2;
                const mx = (sx + dx) / 2;
                const my = Math.min(sy, dy) - 35;

                return (
                  <g
                    className={`select-none pointer-events-none transition-opacity ${
                      isSelected
                        ? "opacity-100"
                        : "opacity-40 group-hover:opacity-100"
                    }`}
                  >
                    <path
                      d={`M ${sx} ${sy} Q ${mx} ${my} ${dx} ${dy}`}
                      fill="none"
                      stroke="#BA2518"
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      strokeDasharray="6 3"
                      markerEnd="url(#arrow-cmfd)"
                    />
                    <rect
                      x={mx - 40}
                      y={my - 12}
                      width={80}
                      height={16}
                      fill="#BA2518"
                      rx={2}
                    />
                    <text
                      x={mx}
                      y={my}
                      fill="#FFFFFF"
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      Δ: {Math.round(dx - sx)}px
                    </text>
                  </g>
                );
              })()
            )}

            {boxes.map((box) => {
              const strokeColor =
                ev.severity === "CRITICAL"
                  ? "#BA2518"
                  : ev.severity === "HIGH"
                  ? "#C27803"
                  : "#1E5E3A";

              const x = box.x;
              const y = box.y;
              const w = Math.max(8, box.width);
              const h = Math.max(8, box.height);

              return (
                <g key={box.id}>
                  {/* Bounding Rectangle */}
                  <rect
                    x={x}
                    y={y}
                    width={w}
                    height={h}
                    fill={isSelected ? "url(#hatch-red)" : `${strokeColor}14`}
                    stroke={strokeColor}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    strokeDasharray={
                      ev.category === "FONT_BASELINE_INCONSISTENCY"
                        ? "4 2"
                        : "none"
                    }
                    className="transition-all duration-150"
                  />

                  {/* Active Selection Glow Ring */}
                  {isSelected && (
                    <rect
                      x={x - 4}
                      y={y - 4}
                      width={w + 8}
                      height={h + 8}
                      fill="none"
                      stroke="#BA2518"
                      strokeWidth={1.5}
                      strokeDasharray="4 2"
                      opacity={0.85}
                      className="animate-pulse"
                    />
                  )}


                  {/* Corner Crosshairs */}
                  <line
                    x1={x - 4}
                    y1={y}
                    x2={x + 4}
                    y2={y}
                    stroke={strokeColor}
                    strokeWidth={1}
                  />
                  <line
                    x1={x}
                    y1={y - 4}
                    x2={x}
                    y2={y + 4}
                    stroke={strokeColor}
                    strokeWidth={1}
                  />

                  {/* Label Tag on Top */}
                  <g
                    transform={`translate(${x}, ${Math.max(16, y - 4)})`}
                    className="select-none"
                  >
                    <rect
                      x={0}
                      y={-14}
                      width={Math.max(70, (box.label?.length || 10) * 6.5)}
                      height={14}
                      fill={strokeColor}
                    />
                    <text
                      x={4}
                      y={-3}
                      fill="#FFFFFF"
                      fontSize="9"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      {box.label || ev.ruleId}
                    </text>
                  </g>

                  {/* Bottom Baseline Projection on Selected Box */}
                  {isSelected && (
                    <g className="select-none pointer-events-none">
                      <line
                        x1={0}
                        y1={y + h}
                        x2={canvasWidth}
                        y2={y + h}
                        stroke={strokeColor}
                        strokeWidth={1.2}
                        strokeDasharray="6 3"
                        opacity="0.8"
                      />
                      <rect
                        x={canvasWidth - 145}
                        y={Math.max(4, y + h - 18)}
                        width={140}
                        height={16}
                        fill={strokeColor}
                        rx={2}
                      />
                      <text
                        x={canvasWidth - 140}
                        y={Math.max(4, y + h - 18) + 11}
                        fill="#FFFFFF"
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        BASELINE: {((y + h) * (72 / 150)).toFixed(1)} pt
                      </text>
                    </g>
                  )}

                  {/* Sub-pixel baseline ruler projection across the canvas */}
                  {showRuler &&
                    ev.category === "FONT_BASELINE_INCONSISTENCY" && (
                      <g className="select-none pointer-events-none">
                        {/* Reference Median Baseline Guide (Blue) */}
                        <line
                          x1={0}
                          y1={y + h}
                          x2={canvasWidth}
                          y2={y + h}
                          stroke="#1D4ED8"
                          strokeWidth={1}
                          strokeDasharray="6 3"
                          opacity="0.8"
                        />
                        {/* Actual Offset Baseline (Red) */}
                        <line
                          x1={x - 20}
                          y1={y + h + 4}
                          x2={x + w + 20}
                          y2={y + h + 4}
                          stroke="#BA2518"
                          strokeWidth={1.5}
                          strokeDasharray="2 2"
                        />
                        <text
                          x={x + w + 8}
                          y={y + h + 3}
                          fill="#BA2518"
                          fontSize="10"
                          fontFamily="monospace"
                          fontWeight="bold"
                        >
                          {ev.discrepancy || "Δy: +2.50 pt"}
                        </text>
                      </g>
                    )}
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}
