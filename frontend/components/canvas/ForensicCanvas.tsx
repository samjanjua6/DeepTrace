"use client";

import React, { useState, useRef, useEffect } from "react";
import { DocumentPage, EvidenceItem } from "@/lib/types/forensics";
import { CanvasToolbar } from "./CanvasToolbar";
import { BoundingBoxLayer } from "./BoundingBoxLayer";

interface ForensicCanvasProps {
  pages: DocumentPage[];
  evidence: EvidenceItem[];
  activeEvidenceId: string | null;
  onSelectEvidence: (id: string | null) => void;
}

export function ForensicCanvas({
  pages,
  evidence,
  activeEvidenceId,
  onSelectEvidence,
}: ForensicCanvasProps) {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(1.0);
  const [showELA, setShowELA] = useState<boolean>(false);
  const [elaOpacity, setElaOpacity] = useState<number>(0.45);
  const [showRuler, setShowRuler] = useState<boolean>(true);
  const [pinnedBaselines, setPinnedBaselines] = useState<number[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);

  // Category counts
  const categoryCounts = React.useMemo(() => {
    let financial = 0;
    let visual = 0;
    let dates = 0;
    for (const ev of evidence) {
      const rId = (ev.ruleId || "").toUpperCase();
      const cat = (ev.category || "").toUpperCase();
      if (
        cat.includes("MATH") ||
        rId.includes("BALANCE") ||
        rId.includes("FINANCIAL") ||
        rId.includes("OPENING") ||
        rId.includes("CLOSING")
      ) {
        financial++;
      } else if (
        cat.includes("IMAGE") ||
        cat.includes("ELA") ||
        rId.includes("TRUFOR") ||
        rId.includes("COPY_MOVE") ||
        rId.includes("ELA")
      ) {
        visual++;
      } else if (
        cat.includes("DATE") ||
        cat.includes("TIMESTAMP") ||
        rId.includes("HOLIDAY") ||
        rId.includes("DATE") ||
        rId.includes("TIMESTAMP")
      ) {
        dates++;
      }
    }
    return {
      all: evidence.length,
      financial,
      visual,
      dates,
    };
  }, [evidence]);

  // Pan and drag state with single-click drag resolution
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const isMouseDownRef = useRef<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const hasDraggedRef = useRef<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);

  const activePage = pages.find((p) => p.pageNumber === currentPage) || pages[0];
  const widthPx = activePage?.widthPx || 1240;
  const heightPx = activePage?.heightPx || 1755;

  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return; // Left mouse only
    // Capture pointer on the viewport container for fluid, uninterrupted dragging
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {}
    isMouseDownRef.current = true;
    hasDraggedRef.current = false;
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    // 1. Panning document
    if (isMouseDownRef.current) {
      const dx = e.clientX - (dragStartRef.current.x + pan.x);
      const dy = e.clientY - (dragStartRef.current.y + pan.y);
      if (Math.hypot(dx, dy) > 3) {
        hasDraggedRef.current = true;
        setIsDragging(true);
      }
      setPan({
        x: e.clientX - dragStartRef.current.x,
        y: e.clientY - dragStartRef.current.y,
      });
    }

    // 2. Baseline laser ruler coordinate tracking over sheet
    if (showRuler && sheetRef.current) {
      const rect = sheetRef.current.getBoundingClientRect();
      if (
        e.clientX >= rect.left &&
        e.clientX <= rect.right &&
        e.clientY >= rect.top &&
        e.clientY <= rect.bottom &&
        rect.width > 0 &&
        rect.height > 0
      ) {
        const x = ((e.clientX - rect.left) / rect.width) * widthPx;
        const y = ((e.clientY - rect.top) / rect.height) * heightPx;
        setMousePos({ x, y });
      } else {
        setMousePos(null);
      }
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {}
    isMouseDownRef.current = false;
    setIsDragging(false);
    hasDraggedRef.current = false;
  };

  // Pin baseline: triggered intentionally via double-click or HUD button (never accidental single-click drags)
  const pinCurrentBaseline = () => {
    if (!mousePos) return;
    const y = mousePos.y;
    if (y >= 0 && y <= heightPx) {
      setPinnedBaselines((prev) => {
        if (prev.length >= 6) return [...prev.slice(1), y];
        return [...prev, y];
      });
    }
  };

  const handleSheetDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    pinCurrentBaseline();
  };

  // Center pan when active finding changes
  useEffect(() => {
    if (!activeEvidenceId) return;
    const targetEv = evidence.find((e) => e.id === activeEvidenceId);
    if (!targetEv || !targetEv.boundingBoxes?.length) return;

    const box = targetEv.boundingBoxes[0];
    if (box.pageNumber !== currentPage) {
      setCurrentPage(box.pageNumber);
    }
  }, [activeEvidenceId, evidence, currentPage]);

  const imageUrl = activePage?.renderedImageUrl
    ? activePage.renderedImageUrl.startsWith("http")
      ? activePage.renderedImageUrl
      : activePage.renderedImageUrl
    : null;

  const [imgError, setImgError] = useState<boolean>(false);

  useEffect(() => {
    setImgError(false);
  }, [imageUrl, currentPage]);

  return (
    <div className="flex flex-col h-full w-full bg-paper-1 border-r border-rule select-none">
      {/* Top Controls Toolbar */}
      <CanvasToolbar
        zoom={zoom}
        onZoomChange={setZoom}
        currentPage={currentPage}
        totalPages={pages.length || 1}
        onPageChange={setCurrentPage}
        showELA={showELA}
        onToggleELA={setShowELA}
        elaOpacity={elaOpacity}
        onElaOpacityChange={setElaOpacity}
        showRuler={showRuler}
        onToggleRuler={setShowRuler}
        pinnedBaselinesCount={pinnedBaselines.length}
        onClearPinnedBaselines={() => setPinnedBaselines([])}
        selectedCategory={selectedCategory}
        onCategoryChange={setSelectedCategory}
        categoryCounts={categoryCounts}
      />

      {/* Main Viewport */}
      <div
        ref={containerRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        className={`flex-1 overflow-hidden relative flex items-center justify-center p-6 bg-paper-1 ${
          isDragging
            ? "cursor-grabbing"
            : showRuler
            ? "cursor-crosshair"
            : "cursor-grab"
        }`}
      >
        {/* Floating Baseline Laser HUD (Institutional Theme) */}
        {showRuler && mousePos && (
          <div className="absolute top-4 left-4 bg-paper-0/95 backdrop-blur-sm border border-rule px-3 py-1.5 font-mono text-[11px] text-ink-900 flex items-center gap-2 shadow-sm select-none z-30">
            <span className="w-1.5 h-1.5 bg-ink-900" />
            <span className="font-semibold uppercase tracking-wider text-ink-900">BASELINE GUIDE:</span>
            <span className="tabular-nums font-semibold">
              Y = {(mousePos.y * (72 / 150)).toFixed(1)} PT ({Math.round(mousePos.y)} PX)
            </span>
            <span className="text-ink-300">|</span>
            <button
              type="button"
              onClick={pinCurrentBaseline}
              className="px-2 py-0.5 bg-ink-900 text-paper-0 text-[10px] uppercase font-bold hover:bg-ink-700 transition-colors cursor-pointer"
            >
              Pin Baseline
            </button>
            <span className="text-ink-400 text-[9px] uppercase hidden sm:inline">(or Double-Click Sheet)</span>
          </div>
        )}

        {/* Transform Container */}
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "center center",
            transition: isDragging ? "none" : "transform 0.1s ease-out",
          }}
          className="relative shadow-2xl bg-white border border-rule"
        >
          <div
            ref={sheetRef}
            onDoubleClick={handleSheetDoubleClick}
            style={{ width: `${widthPx * 0.65}px`, height: `${heightPx * 0.65}px` }}
            className="relative overflow-hidden bg-white"
          >
            {imageUrl && !imgError ? (
              /* Layer 0: Original Rendered Canvas Image */
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={imageUrl}
                alt={`Page ${currentPage}`}
                draggable={false}
                onError={() => setImgError(true)}
                className="w-full h-full object-contain pointer-events-none select-none"
              />
            ) : (
              /* High-End Vector Document Sheet Fallback */
              <div className="w-full h-full p-10 flex flex-col justify-between border-8 border-paper-1 bg-white text-ink-700 font-mono">
                <div className="border-b border-rule pb-4 flex justify-between items-center text-xs">
                  <div>
                    <span className="font-bold text-sm text-ink-900 block font-serif">
                      Document Page Exhibit {currentPage}
                    </span>
                    <span className="text-[10px] text-ink-500">
                      Raster Geometry: {widthPx} × {heightPx} PX (150 DPI)
                    </span>
                  </div>
                  <span className="bg-paper-1 border border-rule px-2 py-0.5 text-[10px] text-ink-700 font-semibold uppercase">
                    CANVAS SHEET ACTIVE
                  </span>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
                  <div className="w-12 h-12 rounded-full border border-rule flex items-center justify-center mb-3 bg-paper-0">
                    <span className="font-serif text-lg font-bold text-ink-900">
                      {currentPage}
                    </span>
                  </div>
                  <span className="font-serif text-base text-ink-900 block mb-1">
                    Document Page Raster Sealed
                  </span>
                  <p className="text-[11px] text-ink-500 max-w-xs leading-relaxed">
                    High-resolution 150 DPI canvas layer. All vector bounding boxes
                    and sub-pixel typography guidelines remain active.
                  </p>
                </div>

                <div className="border-t border-rule pt-3 flex justify-between text-[10px] text-ink-500">
                  <span>NIST SP 800-86 AUDIT LAYER</span>
                  <span>PAGE {currentPage} OF {pages.length || 1}</span>
                </div>
              </div>
            )}

            {/* Layer 1: ELA Error Level Analysis Heatmap Blend */}
            {showELA && (
              <div
                style={{ opacity: elaOpacity }}
                className="absolute inset-0 mix-blend-difference pointer-events-none bg-forensic-red/35"
              />
            )}

            {/* Layer 2: Vector Bounding Boxes & Sub-pixel Baseline Guides */}
            <BoundingBoxLayer
              evidence={evidence}
              currentPage={currentPage}
              canvasWidth={widthPx}
              canvasHeight={heightPx}
              activeEvidenceId={activeEvidenceId}
              onSelectEvidence={onSelectEvidence}
              showRuler={showRuler}
              mousePos={mousePos}
              pinnedBaselines={pinnedBaselines}
              selectedCategory={selectedCategory}
            />
          </div>
        </div>

        {/* Viewport Floating Indicator */}
        <div className="absolute bottom-4 left-4 bg-paper-0/90 backdrop-blur-sm border border-rule px-3 py-1.5 font-mono text-[11px] text-ink-700 pointer-events-none flex items-center gap-3">
          <span>
            CANVAS: {widthPx} × {heightPx} PX (150 DPI)
          </span>
          <span>•</span>
          <span className="tabular-nums">ZOOM: {Math.round(zoom * 100)}%</span>
        </div>
      </div>
    </div>
  );
}
