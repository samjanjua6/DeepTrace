"use client";

import React from "react";
import { PipelineRun } from "@/lib/types/forensics";

interface PipelineExecutionBannerProps {
  isAnalyzing: boolean;
  pipelineRun: PipelineRun | null;
  investigationStatus?: string;
  documentType: string;
  pagesCount: number;
}

export function PipelineExecutionBanner({
  isAnalyzing,
  pipelineRun,
  investigationStatus,
  documentType,
  pagesCount,
}: PipelineExecutionBannerProps) {
  const isRunning =
    isAnalyzing ||
    pipelineRun?.status === "RUNNING" ||
    investigationStatus === "PROCESSING";

  if (!isRunning) return null;

  const activeStage = pipelineRun?.stages?.find((s) => s.status === "RUNNING");

  const getStageDescription = () => {
    if (!activeStage) {
      return "Executing deterministic and neural forensic verification layers...";
    }
    switch (activeStage.stageType) {
      case "CUSTODY_LOCK":
        return `Stage 0 (Document Classifier: ${documentType}) Complete - Stage 1/8: Registering immutable SHA-256 custody fingerprint...`;
      case "PDF_STRUCTURE":
        return "Stage 2/8: Parsing cross-reference streams, %%EOF trailers, and modification timestamps...";
      case "FONT_GLYPH_ANALYSIS":
        return "Stage 3/8: Measuring character glyph baselines and PDF Type1/TrueType subset variances...";
      case "VISION_ELA":
        return `Stage 4/8: Running Computer Vision Multi-Scale ELA & TruFor CMFD neural scan across ${pagesCount || 1} pages...`;
      case "OCR_EXTRACTION":
        return "Stage 5/8: Running semantic OCR and table geometry columnization...";
      case "FINANCIAL_VERIFICATION":
        return "Stage 6/8: Reconciling cross-page ledger state machine and bank calendar validation...";
      case "EVIDENCE_FUSION":
        return "Stage 7/8: Calibrating Bayesian evidence fusion matrix and deterministic overrides...";
      case "REPORT_GENERATION":
        return "Stage 8/8: Sealing court-admissible forensic docket and SHA-256 evidence chain...";
      default:
        return `Stage ${activeStage.stageOrder}/8: Executing ${activeStage.stageType}...`;
    }
  };

  return (
    <div className="bg-paper-1 border-2 border-forensic-amber/60 p-4 font-mono text-xs space-y-2 shadow-sm">
      <div className="flex items-center justify-between text-forensic-amber font-bold uppercase tracking-wider">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-forensic-amber animate-ping" />
          <span>FORENSIC PIPELINE IN FLIGHT</span>
        </div>
        <span className="bg-forensic-amber text-paper-0 text-[10px] px-2 py-0.5 font-bold">
          {activeStage ? `STAGE ${activeStage.stageOrder}/8` : "PROCESSING"}
        </span>
      </div>
      <p className="text-[11px] text-ink-700 leading-relaxed">
        {getStageDescription()}
      </p>
    </div>
  );
}
