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
  onNavigatePage?: (page: number) => void;
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
  onNavigatePage,
  showRuler,
  mousePos,
  pinnedBaselines = [],
  selectedCategory = "ALL",
}: BoundingBoxLayerProps) {
  // Deterministic 1-based finding index mapping for adverse findings
  const adverseFindings = evidence.filter((e) => e.severity !== "INFO");
  const findingIndexMap = new Map<string, number>();
  adverseFindings.forEach((ev, idx) => {
    findingIndexMap.set(ev.id, idx + 1);
  });

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

  // Flatten and calculate all bounding boxes and smart pin placements on current page
  interface PageBoxItem {
    boxId: string;
    evidenceId: string;
    findingNum: number;
    pinLabel: string;
    ev: EvidenceItem;
    box: { id: string; x: number; y: number; width: number; height: number; label?: string };
    strokeColor: string;
    isSelected: boolean;
    anchorX: number;
    anchorY: number;
    pinX: number;
    pinY: number;
    isRightHalf: boolean;
  }

  const pageBoxes: PageBoxItem[] = [];
  pageEvidence.forEach((ev) => {
    const isSelected = activeEvidenceId === ev.id;
    const evBoxes = (ev.boundingBoxes || []).filter(
      (b) => b.pageNumber === currentPage
    );
    const findingNum =
      findingIndexMap.get(ev.id) ?? (evidence.indexOf(ev) + 1);
    const strokeColor =
      ev.severity === "CRITICAL"
        ? "#BA2518"
        : ev.severity === "HIGH"
        ? "#C27803"
        : "#1E5E3A";

    evBoxes.forEach((box, boxIdx) => {
      const pinLabel =
        evBoxes.length > 1
          ? `${findingNum}${String.fromCharCode(65 + boxIdx)}`
          : `${findingNum}`;

      const x = box.x;
      const y = box.y;
      const w = Math.max(12, box.width);
      const h = Math.max(12, box.height);
      const cy = y + h / 2;

      // Position pin safely outside the text area into margins/gutters
      const isRightHalf = x + w / 2 > canvasWidth * 0.45;
      let anchorX = isRightHalf ? x + w : x;
      let anchorY = cy;
      let pinX = isRightHalf ? x + w + 55 : x - 55;
      let pinY = cy;

      // Ensure pin stays within canvas margins
      if (pinX > canvasWidth - 32) {
        anchorX = x;
        pinX = Math.max(32, x - 55);
      } else if (pinX < 32) {
        anchorX = x + w;
        pinX = Math.min(canvasWidth - 32, x + w + 55);
      }

      pageBoxes.push({
        boxId: box.id,
        evidenceId: ev.id,
        findingNum,
        pinLabel,
        ev,
        box: { ...box, width: w, height: h },
        strokeColor,
        isSelected,
        anchorX,
        anchorY,
        pinX,
        pinY,
        isRightHalf,
      });
    });
  });

  // Vertical anti-collision staggering for co-located or closely spaced pins
  for (let i = 0; i < pageBoxes.length; i++) {
    for (let j = i + 1; j < pageBoxes.length; j++) {
      const b1 = pageBoxes[i];
      const b2 = pageBoxes[j];
      const dx = Math.abs(b1.pinX - b2.pinX);
      const dy = Math.abs(b1.pinY - b2.pinY);
      if (dx < 50 && dy < 48) {
        b1.pinY -= 24;
        b2.pinY += 24;
      }
    }
  }

  return (
    <svg
      className="absolute inset-0 pointer-events-auto"
      viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
      style={{ width: "100%", height: "100%", overflow: "visible" }}
    >
      <defs>
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

      {/* Pinned Reference Baselines Layer */}
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
              y={Math.max(4, pinnedY - 24)}
              width={175}
              height={22}
              fill="#141413"
              rx={2}
            />
            <text
              x={12}
              y={Math.max(4, pinnedY - 24) + 15}
              fill="#FBF9F5"
              fontSize="14"
              fontFamily="monospace"
              fontWeight="bold"
            >
              PINNED #{idx + 1}: {(pinnedY * (72 / 150)).toFixed(1)} pt
            </text>
          </g>
        ))}

      {/* Live Mouse Laser Guideline Layer */}
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
            x={canvasWidth - 195}
            y={Math.max(4, mousePos.y - 24)}
            width={185}
            height={22}
            fill="#141413"
            rx={2}
          />
          <text
            x={canvasWidth - 188}
            y={Math.max(4, mousePos.y - 24) + 15}
            fill="#FBF9F5"
            fontSize="14"
            fontFamily="monospace"
            fontWeight="bold"
          >
            Y: {(mousePos.y * (72 / 150)).toFixed(1)} PT ({Math.round(mousePos.y)} PX)
          </text>
        </g>
      )}

      {/* Intra-Page Outer Margin Connector (Multi-Box Financial Reconciliations) */}
      {pageEvidence.map((ev) => {
        const isSelected = activeEvidenceId === ev.id;
        const boxes = (ev.boundingBoxes || []).filter(
          (b) => b.pageNumber === currentPage
        );

        if (ev.ruleId === "RULE_CV_COPY_MOVE_FORGERY" && boxes.length >= 2) {
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
              key={`cmfd-${ev.id}`}
              className={`select-none pointer-events-none transition-opacity ${
                isSelected ? "opacity-100" : "opacity-40 group-hover:opacity-100"
              }`}
            >
              <path
                d={`M ${sx} ${sy} Q ${mx} ${my} ${dx} ${dy}`}
                fill="none"
                stroke="#BA2518"
                strokeWidth={isSelected ? 3 : 2}
                strokeDasharray="6 3"
                markerEnd="url(#arrow-cmfd)"
              />
              <rect
                x={mx - 50}
                y={my - 14}
                width={100}
                height={22}
                fill="#BA2518"
                rx={2}
              />
              <text
                x={mx}
                y={my + 2}
                fill="#FFFFFF"
                fontSize="14"
                fontFamily="monospace"
                fontWeight="bold"
                textAnchor="middle"
              >
                Δ: {Math.round(dx - sx)}px
              </text>
            </g>
          );
        }

        if (boxes.length >= 2) {
          const sorted = [...boxes].sort((a, b) => a.y - b.y);
          const topBox = sorted[0];
          const bottomBox = sorted[sorted.length - 1];
          const marginX = 20;
          const ty = topBox.y + topBox.height / 2;
          const by = bottomBox.y + bottomBox.height / 2;
          const strokeColor = ev.severity === "CRITICAL" ? "#BA2518" : "#C27803";

          return (
            <g
              key={`margin-conn-${ev.id}`}
              className={`select-none pointer-events-none transition-opacity ${
                isSelected ? "opacity-100" : "opacity-45 group-hover:opacity-100"
              }`}
            >
              <path
                d={`M ${topBox.x} ${ty} L ${marginX} ${ty} L ${marginX} ${by} L ${bottomBox.x} ${by}`}
                fill="none"
                stroke={strokeColor}
                strokeWidth={isSelected ? 2.5 : 1.5}
                strokeDasharray={isSelected ? "none" : "5 3"}
              />
              <circle cx={topBox.x} cy={ty} r={4} fill={strokeColor} />
              <circle cx={bottomBox.x} cy={by} r={4} fill={strokeColor} />
              <g transform={`translate(${marginX + 4}, ${(ty + by) / 2 - 12})`}>
                <rect
                  x={0}
                  y={0}
                  width={ev.pattern ? 190 : 160}
                  height={24}
                  fill="#141413"
                  rx={2}
                />
                <text
                  x={8}
                  y={16}
                  fill="#FBF9F5"
                  fontSize="13"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {ev.pattern
                    ? `PROOF: ${ev.pattern.replace(/_/g, " ").toUpperCase()}`
                    : "RECONCILIATION ↔"}
                </text>
              </g>
            </g>
          );
        }

        return null;
      })}

      {/* Primary Evidence Bounding Boxes, HUD Reticles, Leader Lines, and Numbered Pins */}
      {pageBoxes.map((item) => {
        const {
          box,
          ev,
          strokeColor,
          isSelected,
          anchorX,
          anchorY,
          pinX,
          pinY,
          pinLabel,
          findingNum,
        } = item;

        const x = box.x;
        const y = box.y;
        const w = box.width;
        const h = box.height;
        const cornerLen = Math.min(8, w / 3, h / 3);

        const isPinRight = pinX > anchorX;
        const elbowX = isPinRight
          ? anchorX + Math.max(16, (pinX - anchorX) * 0.45)
          : anchorX - Math.max(16, (anchorX - pinX) * 0.45);

        return (
          <g
            key={box.id}
            className="cursor-pointer group"
            onClick={(e) => {
              e.stopPropagation();
              onSelectEvidence(isSelected ? null : ev.id);
            }}
            onMouseEnter={() => onSelectEvidence(ev.id)}
          >
            {/* Bounding Box: 100% Transparent Interior (Zero Evidence Obstruction) */}
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill={isSelected ? "rgba(186, 37, 24, 0.04)" : "none"}
              stroke={strokeColor}
              strokeWidth={isSelected ? 2.5 : 1.5}
              strokeDasharray={
                ev.category === "FONT_BASELINE_INCONSISTENCY" ? "5 3" : "none"
              }
              className="transition-all duration-150"
            />

            {/* Selection Outer Glow Ring */}
            {isSelected && (
              <rect
                x={x - 4}
                y={y - 4}
                width={w + 8}
                height={h + 8}
                fill="none"
                stroke={strokeColor}
                strokeWidth={1.5}
                strokeDasharray="4 2"
                opacity={0.65}
                className="animate-pulse"
              />
            )}

            {/* Forensic Corner HUD Brackets */}
            {cornerLen > 2 && (
              <>
                {/* Top-Left */}
                <path
                  d={`M ${x} ${y + cornerLen} L ${x} ${y} L ${x + cornerLen} ${y}`}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={isSelected ? 3 : 2}
                />
                {/* Top-Right */}
                <path
                  d={`M ${x + w - cornerLen} ${y} L ${x + w} ${y} L ${x + w} ${y + cornerLen}`}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={isSelected ? 3 : 2}
                />
                {/* Bottom-Left */}
                <path
                  d={`M ${x} ${y + h - cornerLen} L ${x} ${y + h} L ${x + cornerLen} ${y + h}`}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={isSelected ? 3 : 2}
                />
                {/* Bottom-Right */}
                <path
                  d={`M ${x + w - cornerLen} ${y + h} L ${x + w} ${y + h} L ${x + w} ${y + h - cornerLen}`}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={isSelected ? 3 : 2}
                />
              </>
            )}

            {/* Leader Line: Anchor Dot on Bounding Box Perimeter */}
            <circle cx={anchorX} cy={anchorY} r={4} fill={strokeColor} />

            {/* Leader Line: Vector Dogleg Path from Box to Pin */}
            <path
              d={`M ${anchorX} ${anchorY} L ${elbowX} ${anchorY} L ${elbowX} ${pinY} L ${pinX} ${pinY}`}
              fill="none"
              stroke={strokeColor}
              strokeWidth={isSelected ? 2.5 : 1.8}
              strokeDasharray={isSelected ? "none" : "4 2"}
              className="transition-all duration-150"
            />

            {/* Pin Active Selection Halo */}
            {isSelected && (
              <circle
                cx={pinX}
                cy={pinY}
                r={27}
                fill="none"
                stroke={strokeColor}
                strokeWidth={2}
                strokeDasharray="4 2"
                className="animate-pulse opacity-75"
              />
            )}

            {/* Numbered Pin Circular Badge */}
            <circle
              cx={pinX}
              cy={pinY}
              r={20}
              fill={strokeColor}
              stroke="#FFFFFF"
              strokeWidth={2.5}
              className="transition-transform duration-150 group-hover:scale-110 shadow-md"
            />

            {/* Pin Number / Label */}
            <text
              x={pinX}
              y={pinY}
              fill="#FFFFFF"
              fontSize="16"
              fontFamily="monospace"
              fontWeight="bold"
              textAnchor="middle"
              dominantBaseline="central"
              className="select-none pointer-events-none"
            >
              {pinLabel}
            </text>

            {/* Non-intrusive Hover Tooltip */}
            <title>{`Finding #${findingNum}: ${ev.title || ev.ruleId}`}</title>
          </g>
        );
      })}

      {/* Sub-pixel Baseline Projection on Active Selection */}
      {pageEvidence.map((ev) => {
        const isSelected = activeEvidenceId === ev.id;
        if (!isSelected) return null;
        const boxes = (ev.boundingBoxes || []).filter(
          (b) => b.pageNumber === currentPage
        );
        const strokeColor = ev.severity === "CRITICAL" ? "#BA2518" : "#C27803";

        return boxes.map((box) => {
          const y = box.y;
          const h = box.height;
          return (
            <g key={`proj-${box.id}`} className="select-none pointer-events-none">
              <line
                x1={0}
                y1={y + h}
                x2={canvasWidth}
                y2={y + h}
                stroke={strokeColor}
                strokeWidth={1.5}
                strokeDasharray="6 3"
                opacity="0.8"
              />
              <rect
                x={canvasWidth - 180}
                y={Math.max(4, y + h - 24)}
                width={175}
                height={22}
                fill={strokeColor}
                rx={2}
              />
              <text
                x={canvasWidth - 172}
                y={Math.max(4, y + h - 24) + 15}
                fill="#FFFFFF"
                fontSize="14"
                fontFamily="monospace"
                fontWeight="bold"
              >
                BASELINE: {((y + h) * (72 / 150)).toFixed(1)} pt
              </text>
            </g>
          );
        });
      })}
    </svg>
  );
}
