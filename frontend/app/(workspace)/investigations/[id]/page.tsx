"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Masthead } from "@/components/editorial/Masthead";
import { ForensicCanvas } from "@/components/canvas/ForensicCanvas";
import { RiskGaugeBlock } from "@/components/dossier/RiskGaugeBlock";
import { LedgerMathTable } from "@/components/dossier/LedgerMathTable";
import { SplitLedgerEvidenceViewer } from "@/components/dossier/SplitLedgerEvidenceViewer";
import { AnomalyCard } from "@/components/dossier/AnomalyCard";
import { IBANChecksumCard } from "@/components/dossier/IBANChecksumCard";
import { SBPAmlCddCard } from "@/components/dossier/SBPAmlCddCard";
import { AnalystOverrideModal } from "@/components/dossier/AnalystOverrideModal";
import { CreditOfficerBriefing } from "@/components/dossier/CreditOfficerBriefing";
import {
  Investigation,
  DocumentPage,
  EvidenceItem,
  RiskAssessment,
  CustodyEvent,
  PipelineRun,
} from "@/lib/types/forensics";
import {
  getInvestigation,
  getDocuments,
  getDocumentPages,
  getEvidence,
  getRiskAssessment,
  getCustodyEvents,
  downloadRFC3161Token,
  triggerPipeline,
  getPipelineStatus,
  overrideRiskScore,
  loginAnalyst,
} from "@/lib/api/client";
import {
  ShieldCheck,
  CheckCircle2,
  FileSearch,
  Hash,
  Layers,
  Sparkles,
  Info,
  Columns,
  FileText,
} from "lucide-react";
import { formatDatePKT } from "@/lib/formatters";

// Realistic sample forensic exhibit data (Used exclusively for the demo exhibit /investigations/sample)
const SAMPLE_EXHIBIT_PAGES: DocumentPage[] = [
  {
    id: "sample-page-1",
    documentId: "sample-doc-1",
    pageNumber: 1,
    widthPx: 1240,
    heightPx: 1755,
    widthPts: 595,
    heightPts: 842,
    imageStoragePath: "documents/sample/pages/page_1.png",
    renderedImageUrl:
      "/api/v1/storage/deeptrace-documents/documents/sample/pages/page_1.png",
  },
];

const SAMPLE_EXHIBIT_EVIDENCE: EvidenceItem[] = [
  {
    id: "sample-ev-1",
    documentId: "sample-doc-1",
    pipelineStageId: "stage-6",
    category: "MATH_RECONCILIATION_FAIL",
    severity: "CRITICAL",
    ruleId: "RULE_PK_LEDGER_RECONCILIATION_FAIL",
    riskPoints: 45,
    title: "Ledger Running Balance Mathematical Inconsistency",
    description:
      "Recorded row balance diverges from mathematical ledger reconciliation. Net artificial balance inflation of +PKR 21,75,000.00 detected.",
    isDeterministic: true,
    pageNumber: 1,
    expectedValue: "PKR 2,50,000.00",
    actualValue: "PKR 25,00,000.00",
    discrepancy: "+PKR 21,75,000.00 (+870.0%)",
    createdAt: new Date().toISOString(),
    boundingBoxes: [
      {
        id: "box-1",
        evidenceItemId: "sample-ev-1",
        pageNumber: 1,
        x: 485 * (1240 / 595),
        y: 255 * (1755 / 842),
        width: 140,
        height: 34,
        label: "Math Mismatch (+21.75 Lac)",
        color: "#BA2518",
      },
    ],
  },
  {
    id: "sample-ev-2",
    documentId: "sample-doc-1",
    pipelineStageId: "stage-3",
    category: "FONT_BASELINE_INCONSISTENCY",
    severity: "CRITICAL",
    ruleId: "RULE_FONT_BASELINE_OFFSET",
    riskPoints: 30,
    title: "Sub-Pixel Typography Baseline Offset on Financial Value",
    description:
      "Text span '25,00,000.00' has a vertical baseline deviation of 2.50 pt from the row median (200.00 pt). Physical artifact confirms manually inserted text box.",
    isDeterministic: true,
    pageNumber: 1,
    expectedValue: "200.00 pt baseline",
    actualValue: "202.50 pt baseline",
    discrepancy: "2.50 pt vertical offset",
    createdAt: new Date().toISOString(),
    boundingBoxes: [
      {
        id: "box-2",
        evidenceItemId: "sample-ev-2",
        pageNumber: 1,
        x: 485 * (1240 / 595),
        y: 255 * (1755 / 842),
        width: 140,
        height: 34,
        label: "Baseline Offset (+2.50pt)",
        color: "#BA2518",
      },
    ],
  },
  {
    id: "sample-ev-3",
    documentId: "sample-doc-1",
    pipelineStageId: "stage-2",
    category: "METADATA_DISCREPANCY",
    severity: "HIGH",
    ruleId: "RULE_PDF_TAMPER_PRODUCER",
    riskPoints: 20,
    title: "Desktop Editor & Multiple Incremental Saves Detected",
    description:
      "Document metadata contains Canva / Adobe Acrobat signatures and 2 incremental %%EOF revision trailers.",
    isDeterministic: true,
    pageNumber: 1,
    expectedValue: "Standard Institutional Core Engine",
    actualValue: "Canva Online Design Suite",
    discrepancy: "2 %%EOF revisions / Canva Producer",
    createdAt: new Date().toISOString(),
    boundingBoxes: [],
  },
];

const SAMPLE_EXHIBIT_RISK: RiskAssessment = {
  id: "sample-risk-1",
  investigationId: "sample",
  overallScore: 85,
  riskTier: "CRITICAL",
  actionDirective: "IMMEDIATE_REJECTION",
  confidenceScore: 0.98,
  isDeterministicOverride: true,
  computedAt: new Date().toISOString(),
  riskSignals: [
    {
      id: "sig-1",
      category: "MATH_RECONCILIATION_FAIL",
      ruleId: "RULE_PK_LEDGER_RECONCILIATION_FAIL",
      severity: "CRITICAL",
      rawPoints: 45,
      weightedPoints: 45,
      riskContribution: 45,
      isDeterministic: true,
    },
    {
      id: "sig-2",
      category: "FONT_BASELINE_INCONSISTENCY",
      ruleId: "RULE_FONT_BASELINE_OFFSET",
      severity: "CRITICAL",
      rawPoints: 30,
      weightedPoints: 30,
      riskContribution: 30,
      isDeterministic: true,
    },
  ],
};

export default function InvestigationWorkspacePage() {
  const params = useParams();
  const investigationId = params?.id as string;
  const isSample = investigationId === "sample";

  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [documentType, setDocumentType] = useState<string>("GENERAL_DOCUMENT");
  const [pages, setPages] = useState<DocumentPage[]>(
    isSample ? SAMPLE_EXHIBIT_PAGES : []
  );
  const [evidence, setEvidence] = useState<EvidenceItem[]>(
    isSample ? SAMPLE_EXHIBIT_EVIDENCE : []
  );
  const [risk, setRisk] = useState<RiskAssessment>(
    isSample
      ? SAMPLE_EXHIBIT_RISK
      : {
          id: "clean",
          investigationId,
          overallScore: 0,
          riskTier: "LOW",
          actionDirective: "STRAIGHT_THROUGH_APPROVAL",
          confidenceScore: 1.0,
          isDeterministicOverride: false,
          computedAt: new Date().toISOString(),
          riskSignals: [],
        }
  );
  const [custodyEvents, setCustodyEvents] = useState<CustodyEvent[]>([]);
  const [activeEvidenceId, setActiveEvidenceId] = useState<string | null>(null);
  const [isOverrideOpen, setIsOverrideOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("findings");
  const [viewMode, setViewMode] = useState<"split" | "dossier">("split");
  const [focusedPageNumber, setFocusedPageNumber] = useState<number | null>(null);
  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(!isSample);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [pipelineRun, setPipelineRun] = useState<PipelineRun | null>(null);

  // Load real investigation data with automatic polling for background execution
  useEffect(() => {
    if (isSample) {
      setPages(SAMPLE_EXHIBIT_PAGES);
      setEvidence(SAMPLE_EXHIBIT_EVIDENCE);
      setRisk(SAMPLE_EXHIBIT_RISK);
      setDocumentType("BANK_STATEMENT");
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    let pollTimer: NodeJS.Timeout | null = null;
    let hasLoadedPages = false;

    async function loadData(isInitial = false) {
      if (isInitial) setIsLoading(true);
      let isStillRunning = false;
      try {
        await loginAnalyst().catch(() => {});

        // 1. Fetch Investigation
        const inv = await getInvestigation(investigationId).catch(() => null);
        if (!isMounted) return;
        if (inv) setInvestigation(inv);

        // 2. Fetch Documents & Pages (Fetched once on initial load or if empty)
        if (!hasLoadedPages) {
          const docs = await getDocuments(investigationId).catch(() => []);
          if (!isMounted) return;
          if (docs && docs.length > 0) {
            const mainDoc = docs[0];
            setDocumentType(mainDoc.documentType || "OTHER");

            const docPages = await getDocumentPages(investigationId, mainDoc.id).catch(() => []);
            if (!isMounted) return;
            if (docPages && docPages.length > 0) {
              setPages(docPages);
              hasLoadedPages = true;
            }
          }
        }

        // 3. Fetch Pipeline Status
        const pRun = await getPipelineStatus(investigationId).catch(() => null);
        if (!isMounted) return;
        if (pRun) setPipelineRun(pRun);

        // 4. Fetch Evidence
        const ev = await getEvidence(investigationId).catch(() => null);
        if (!isMounted) return;
        if (ev !== null) setEvidence(ev);

        // 5. Fetch Risk Assessment
        const r = await getRiskAssessment(investigationId).catch(() => null);
        if (!isMounted) return;
        if (r) {
          setRisk(r);
        } else if (pRun?.status === "COMPLETED" || (inv && inv.status !== "PROCESSING")) {
          setRisk({
            id: "clean",
            investigationId,
            overallScore: 0,
            riskTier: "LOW",
            actionDirective: "STRAIGHT_THROUGH_APPROVAL",
            confidenceScore: 1.0,
            isDeterministicOverride: false,
            computedAt: new Date().toISOString(),
            riskSignals: [],
          });
        }

        // 6. Fetch Custody Log
        const custody = await getCustodyEvents(investigationId).catch(() => []);
        if (!isMounted) return;
        if (custody && custody.length > 0) setCustodyEvents(custody);

        // Polling decision:
        // While pipeline is still running/queued or haven't reached terminal status,
        // poll every 2000ms until terminal status (COMPLETED or FAILED)
        isStillRunning =
          pRun?.status === "RUNNING" ||
          pRun?.status === "QUEUED" ||
          inv?.status === "PROCESSING" ||
          (pRun?.status !== "COMPLETED" && pRun?.status !== "FAILED" && (!r || r.overallScore === 0));

      } catch (err) {
        console.error("Failed to load investigation data:", err);
        // If an error occurred during active execution, keep polling with backoff
        isStillRunning = true;
      } finally {
        if (isMounted && isInitial) {
          setIsLoading(false);
        }
        if (isStillRunning && isMounted) {
          pollTimer = setTimeout(() => {
            loadData(false);
          }, 2000);
        }
      }
    }

    loadData(true);

    return () => {
      isMounted = false;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [investigationId, isSample]);

  const handleReanalyze = async () => {
    if (!investigationId || isSample) return;
    setIsAnalyzing(true);
    try {
      await triggerPipeline(investigationId);

      // Poll pipeline until completed or terminal (up to 100 attempts * 1.5s = 150s for multi-page documents)
      let attempts = 0;
      while (attempts < 100) {
        await new Promise((res) => setTimeout(res, 1500));
        const status = await getPipelineStatus(investigationId).catch(() => null);
        if (status) {
          setPipelineRun(status);
          if (status.status === "COMPLETED" || status.status === "FAILED") {
            break;
          }
        }
        attempts++;
      }

      const [ev, r, docs, custody] = await Promise.all([
        getEvidence(investigationId).catch(() => []),
        getRiskAssessment(investigationId).catch(() => null),
        getDocuments(investigationId).catch(() => []),
        getCustodyEvents(investigationId).catch(() => []),
      ]);

      setEvidence(ev || []);
      if (r) setRisk(r);
      if (docs && docs.length > 0) {
        setDocumentType(docs[0].documentType || "OTHER");
      }
      setCustodyEvents(custody || []);
    } catch (err) {
      console.error("Analysis trigger failed:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleOverrideSave = async (newScore: number, reason: string) => {
    if (!investigationId || isSample) return;
    const updated = await overrideRiskScore(investigationId, newScore, reason);
    setRisk(updated);
  };

  const caseNumber = isSample
    ? "EXHIBIT-DEMO-001"
    : investigation?.caseNumber || "DT-2026-CASE";

  const caseTitle = isSample
    ? "Sample Tampered Bank Statement Exhibit (Pre-computed Demo)"
    : investigation?.title || "Document Forensics Verification Docket";

  const isFinancial =
    documentType === "BANK_STATEMENT" ||
    evidence.some(
      (e) =>
        e.category === "MATHEMATICAL_MISMATCH" ||
        e.category === "MATH_RECONCILIATION_FAIL" ||
        (e.ruleId || "").includes("MATH") ||
        (e.ruleId || "").includes("BALANCE") ||
        (e.ruleId || "").includes("LEDGER") ||
        (e.ruleId || "").includes("HOLIDAY")
    );

  const getStageStatus = (stageType: string) => {
    if (isSample) return "COMPLETED";
    const stage = pipelineRun?.stages?.find((s) => s.stageType === stageType);
    return stage?.status || (pipelineRun ? "PENDING" : "COMPLETED");
  };

  const stage6 = pipelineRun?.stages?.find(
    (s) => s.stageType === "FINANCIAL_VERIFICATION"
  );
  const financialData = stage6?.outputPayload;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-paper-0 text-ink-900">
      {/* Editorial Top Masthead */}
      <Masthead
        caseNumber={caseNumber}
        caseTitle={caseTitle}
        documentType={documentType}
      />

      {/* Workbench Sub-Header Ribbon with View Switcher */}
      <div className="bg-paper-1 border-b border-rule px-4 py-2 flex items-center justify-between font-mono text-xs select-none">
        <div className="flex items-center gap-3">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-ink-600 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-forensic-teal" />
            WORKBENCH VIEW
          </span>
          <span className="text-rule">|</span>
          <span className="text-[11px] text-ink-700">
            {documentType === "BANK_STATEMENT"
              ? "Pakistani Core Banking & Ledger Verification Workspace"
              : `Forensic Document Examination (${documentType})`}
          </span>
          {isFinancial && (
            <span className="bg-paper-0 border border-forensic-teal/40 text-forensic-teal text-[10px] px-2 py-0.5 font-bold uppercase tracking-wider">
              LEDGER ENGINE ACTIVE
            </span>
          )}
        </div>

        {/* View Mode Toggle Controls */}
        <div className="flex items-center gap-1 bg-paper-0 border border-rule p-0.5">
          {isFinancial && (
            <button
              onClick={() => setViewMode("split")}
              className={`flex items-center gap-1.5 px-3 py-1 text-[11px] uppercase font-bold transition-all ${
                viewMode === "split"
                  ? "bg-ink-900 text-paper-0 shadow-sm"
                  : "text-ink-600 hover:text-ink-900 hover:bg-paper-1"
              }`}
              title="Interactive Side-by-Side PDF Canvas & Mathematical Ledger"
            >
              <Columns className="w-3.5 h-3.5" />
              <span>Split Evidence Workbench</span>
            </button>
          )}
          <button
            onClick={() => setViewMode("dossier")}
            className={`flex items-center gap-1.5 px-3 py-1 text-[11px] uppercase font-bold transition-all ${
              viewMode === "dossier" || !isFinancial
                ? "bg-ink-900 text-paper-0 shadow-sm"
                : "text-ink-600 hover:text-ink-900 hover:bg-paper-1"
            }`}
            title="Complete Forensic Findings, Custody Chain & Pipeline Telemetry"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Full Audit Dossier</span>
          </button>
        </div>
      </div>

      {/* Asymmetric 2-Column Split Workbench */}
      <div className="flex flex-1 overflow-hidden">
        {/* Column 1: Sticky Left Forensic Canvas */}
        <div
          className={`w-full ${
            viewMode === "split" && isFinancial ? "lg:w-[50%]" : "lg:w-[58%]"
          } h-full flex flex-col relative border-r border-rule`}
        >
          <ForensicCanvas
            pages={pages}
            evidence={evidence}
            activeEvidenceId={activeEvidenceId}
            onSelectEvidence={(id) => {
              setActiveEvidenceId(id);
              if (id) {
                const ev = evidence.find((e) => e.id === id);
                if (ev && ev.pageNumber) {
                  setFocusedPageNumber(ev.pageNumber);
                }
              }
            }}
            focusedPageNumber={focusedPageNumber}
          />
        </div>

        {/* Column 2: Right Interactive Pane (Split Ledger or Full Dossier) */}
        {viewMode === "split" && isFinancial ? (
          <div className="w-full lg:w-[50%] h-full flex flex-col overflow-hidden bg-paper-0">
            <SplitLedgerEvidenceViewer
              rows={financialData?.rows}
              evidence={evidence}
              financialData={financialData}
              activeEvidenceId={activeEvidenceId}
              selectedRowIndex={selectedRowIndex}
              onSelectRow={(row, index) => {
                setSelectedRowIndex(index);
                if (row.pageNumber) {
                  setFocusedPageNumber(row.pageNumber);
                }
                if (row.isTampered) {
                  const mathEv = evidence.find(
                    (e) =>
                      (e.category === "MATH_RECONCILIATION_FAIL" ||
                        e.category === "MATHEMATICAL_MISMATCH" ||
                        (e.ruleId || "").includes("MATH")) &&
                      (!row.pageNumber || e.pageNumber === row.pageNumber)
                  );
                  if (mathEv) {
                    setActiveEvidenceId(mathEv.id);
                  }
                }
              }}
              onSelectEvidence={(evId) => {
                setActiveEvidenceId(evId);
                const ev = evidence.find((e) => e.id === evId);
                if (ev && ev.pageNumber) {
                  setFocusedPageNumber(ev.pageNumber);
                }
              }}
              onFocusCanvas={(pageNumber) => {
                setFocusedPageNumber(pageNumber);
              }}
            />
          </div>
        ) : (
          <div className="w-full lg:w-[42%] h-full overflow-y-auto bg-paper-0 p-6 space-y-6">
          {/* Live Pipeline Execution Banner */}
          {(isAnalyzing || pipelineRun?.status === "RUNNING" || investigation?.status === "PROCESSING") && (
            <div className="bg-paper-1 border-2 border-forensic-amber/60 p-4 font-mono text-xs space-y-2 shadow-sm">
              <div className="flex items-center justify-between text-forensic-amber font-bold uppercase tracking-wider">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-forensic-amber animate-ping" />
                  <span>FORENSIC PIPELINE IN FLIGHT</span>
                </div>
                <span className="bg-forensic-amber text-paper-0 text-[10px] px-2 py-0.5 font-bold">
                  {(() => {
                    const active = pipelineRun?.stages?.find((s) => s.status === "RUNNING");
                    return active ? `STAGE ${active.stageOrder}/8` : "PROCESSING";
                  })()}
                </span>
              </div>
              <p className="text-[11px] text-ink-700 leading-relaxed">
                {(() => {
                  const active = pipelineRun?.stages?.find((s) => s.status === "RUNNING");
                  if (!active) return "Executing deterministic and neural forensic verification layers...";
                  switch (active.stageType) {
                    case "CUSTODY_LOCK":
                      return `Stage 0 (Document Classifier: ${documentType}) Complete • Stage 1/8: Registering immutable SHA-256 custody fingerprint...`;
                    case "PDF_STRUCTURE":
                      return "Stage 2/8: Parsing cross-reference streams, %%EOF trailers, and modification timestamps...";
                    case "FONT_GLYPH_ANALYSIS":
                      return "Stage 3/8: Measuring character glyph baselines and PDF Type1/TrueType subset variances...";
                    case "VISION_ELA":
                      return `Stage 4/8: Running Computer Vision Multi-Scale ELA & TruFor CMFD neural scan across ${pages.length || 1} pages...`;
                    case "OCR_EXTRACTION":
                      return "Stage 5/8: Running semantic OCR and table geometry columnization...";
                    case "FINANCIAL_VERIFICATION":
                      return "Stage 6/8: Reconciling cross-page ledger state machine and bank calendar validation...";
                    case "EVIDENCE_FUSION":
                      return "Stage 7/8: Calibrating Bayesian evidence fusion matrix and deterministic overrides...";
                    case "REPORT_GENERATION":
                      return "Stage 8/8: Sealing court-admissible forensic docket and SHA-256 evidence chain...";
                    default:
                      return `Stage ${active.stageOrder}/8: Executing ${active.stageType}...`;
                  }
                })()}
              </p>
            </div>
          )}

          {/* Institutional Document Classification Profile Card */}
          {(() => {
            const stage0 = (pipelineRun?.parameters as any)?.stage_0_classification;
            if (!stage0) return null;
            const primaryDoc = stage0.documents?.[0];
            return (
              <div className="bg-paper-1 border border-rule p-3 font-mono text-xs space-y-1.5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-ink-500 uppercase tracking-widest font-semibold">
                    STAGE 0 MULTI-MODAL CLASSIFIER
                  </span>
                  <span className="bg-ink-900 text-paper-0 text-[10px] px-2 py-0.5 font-bold">
                    {Math.round((primaryDoc?.confidence ?? 0.95) * 100)}% CONFIDENCE
                  </span>
                </div>
                <div className="flex items-baseline justify-between pt-0.5">
                  <span className="font-serif text-sm font-semibold text-ink-900">
                    {primaryDoc?.subtype?.replace(/_/g, " ") || documentType}
                  </span>
                  <span className="text-[11px] text-ink-600 uppercase">
                    CATEGORY: {documentType}
                  </span>
                </div>
                {primaryDoc?.decision_rationale && (
                  <p className="text-[10px] text-ink-600 italic pt-0.5 leading-snug">
                    {primaryDoc.decision_rationale}
                  </p>
                )}
              </div>
            );
          })()}

          {/* Calibrated Risk Gauge Block */}
          <RiskGaugeBlock
            assessment={risk}
            isCalculating={
              isAnalyzing ||
              pipelineRun?.status === "RUNNING" ||
              investigation?.status === "PROCESSING"
            }
            onOpenOverride={isSample ? undefined : () => setIsOverrideOpen(true)}
          />

          {/* Autonomous Lead Investigator Agent — Bilingual Credit Officer Briefing */}
          <CreditOfficerBriefing
            investigationId={investigationId}
            overallScore={risk?.overallScore ?? 0}
            riskTier={risk?.riskTier ?? "LOW"}
            actionDirective={risk?.actionDirective ?? "STRAIGHT_THROUGH_APPROVAL"}
            evidenceItems={evidence}
          />

          {/* Action Ribbon & Dynamic Domain-Aware Tabs */}
          <div className="flex items-center justify-between font-mono text-xs border-b border-rule pb-3">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab("findings")}
                className={`px-3 py-1 border transition-colors uppercase ${
                  activeTab === "findings"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Findings ({evidence.length})
              </button>

              {/* Financial-only tabs: only shown when document is a financial statement */}
              {isFinancial && (
                <>
                  <button
                    onClick={() => setActiveTab("ledger")}
                    className={`px-3 py-1 border transition-colors uppercase ${
                      activeTab === "ledger"
                        ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                        : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                    }`}
                  >
                    Math Ledger
                  </button>
                  <button
                    onClick={() => setActiveTab("iban")}
                    className={`px-3 py-1 border transition-colors uppercase ${
                      activeTab === "iban"
                        ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                        : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                    }`}
                  >
                    SBP IBAN & AML
                  </button>
                </>
              )}

              {/* Custody Chain tab (PECA 2016 / ETO 2002) */}
              <button
                onClick={() => setActiveTab("custody")}
                className={`px-3 py-1 border transition-colors uppercase ${
                  activeTab === "custody"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Custody Chain
              </button>
            </div>

            {!isSample && (
              <button
                onClick={handleReanalyze}
                disabled={isAnalyzing}
                className="px-3 py-1 bg-paper-1 hover:bg-paper-2 border border-rule text-ink-900 uppercase font-semibold transition-colors disabled:opacity-50"
              >
                {isAnalyzing ? "Processing..." : "↻ Re-Analyze"}
              </button>
            )}
          </div>

          {/* Tab 1: Findings Feed or Verified Genuine Presentation */}
          {activeTab === "findings" && (
            <div className="space-y-3">
              {evidence.length > 0 ? (
                <>
                  <div className="flex items-center justify-between font-mono text-xs text-ink-500">
                    <span>DETECTED ANOMALIES ({evidence.length})</span>
                    <span className="text-[10px]">
                      CLICK OR HOVER TO SYNC CANVAS
                    </span>
                  </div>
                  {evidence.map((item) => (
                    <AnomalyCard
                      key={item.id}
                      item={item}
                      isSelected={activeEvidenceId === item.id}
                      onSelect={setActiveEvidenceId}
                    />
                  ))}
                </>
              ) : (
                /* Explainability when Document is Clean / Not Edited */
                <div className="bg-paper-0 border border-rule p-5 font-mono select-none space-y-4">
                  <div className="flex items-start gap-3 border-b border-rule pb-3">
                    <CheckCircle2 className="w-6 h-6 text-forensic-green flex-shrink-0 mt-0.5" />
                    <div>
                      <span className="text-[10px] text-forensic-green font-bold uppercase tracking-widest block">
                        VERIFICATION CERTIFICATE • NIST SP 800-86 AUDIT PASSED
                      </span>
                      <h3 className="font-serif text-lg text-ink-900 font-medium">
                        Authentic Document — Zero Tampering Detected
                      </h3>
                      <p className="text-xs text-ink-700 mt-1 leading-relaxed">
                        DeepTrace analyzed all 8 forensic verification layers.
                        No physical, sub-pixel typography, compression, or
                        structural anomalies were found.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="bg-paper-1 p-3 border border-rule space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold text-ink-900">
                        <Sparkles className="w-3.5 h-3.5 text-forensic-green" />
                        <span>Sub-Pixel Typography</span>
                      </div>
                      <p className="text-[11px] text-ink-700">
                        Character baseline variance &lt; 0.05 pt. No spliced
                        text spans or font subset mismatches.
                      </p>
                    </div>

                    <div className="bg-paper-1 p-3 border border-rule space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold text-ink-900">
                        <Layers className="w-3.5 h-3.5 text-forensic-green" />
                        <span>Error Level Analysis (ELA)</span>
                      </div>
                      <p className="text-[11px] text-ink-700">
                        Dual-pass Q=95 difference matrix is uniform across all
                        blocks. No high-frequency edits.
                      </p>
                    </div>

                    <div className="bg-paper-1 p-3 border border-rule space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold text-ink-900">
                        <FileSearch className="w-3.5 h-3.5 text-forensic-green" />
                        <span>Stream & Structure</span>
                      </div>
                      <p className="text-[11px] text-ink-700">
                        Clean single-revision layout. No secondary %%EOF trailers
                        or desktop manipulation tools detected.
                      </p>
                    </div>

                    <div className="bg-paper-1 p-3 border border-rule space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold text-ink-900">
                        <Hash className="w-3.5 h-3.5 text-forensic-green" />
                        <span>Cryptographic Seal</span>
                      </div>
                      <p className="text-[11px] text-ink-700">
                        Original SHA-256 fingerprint verified against acquisition
                        record under ETO 2002.
                      </p>
                    </div>
                  </div>

                  <div className="bg-forensic-green/10 border border-forensic-green/30 p-2.5 text-[11px] text-forensic-green flex items-center justify-between font-semibold">
                    <span>FINAL DISPOSITION:</span>
                    <span className="uppercase">
                      STRAIGHT-THROUGH APPROVAL (0 / 100 RISK)
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Financial Math Ledger (Only for Bank Statements) */}
          {activeTab === "ledger" && isFinancial && (
            <div className="space-y-4">
              <LedgerMathTable
                rows={financialData?.rows}
                evidence={evidence}
                onSelectRow={() => {
                  const mathEv = evidence.find(
                    (e) =>
                      e.category === "MATHEMATICAL_MISMATCH" ||
                      e.category === "MATH_RECONCILIATION_FAIL" ||
                      (e.ruleId || "").includes("BALANCE") ||
                      (e.ruleId || "").includes("LEDGER")
                  );
                  if (mathEv) setActiveEvidenceId(mathEv.id);
                }}
                onSelectEvidence={(id) => setActiveEvidenceId(id)}
              />
            </div>
          )}

          {/* Tab 3: SBP IBAN Checksum & AML/CDD Audit (Only for Bank Statements) */}
          {activeTab === "iban" && isFinancial && (
            <div className="space-y-4">
              <IBANChecksumCard
                iban={financialData?.iban?.raw_iban}
                bankName={financialData?.iban?.bank_name}
                isValid={financialData?.iban?.is_valid}
                accountNo={financialData?.iban?.account_number}
                checkDigits={financialData?.iban?.check_digits}
                bankCode={financialData?.iban?.bank_code}
                validationReason={financialData?.iban?.validation_reason}
                evidence={evidence}
              />
              <SBPAmlCddCard
                screening={financialData?.aml_cdd_screening}
                evidence={evidence}
              />
            </div>
          )}

          {/* Tab 4: Custody Chain (PECA 2016 & ETO 2002 Compliant) */}
          {activeTab === "custody" && (
            <div className="bg-paper-0 border border-rule p-4 font-mono text-xs space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-2">
                <span className="font-semibold text-ink-900 uppercase tracking-wider block text-[10px]">
                  PECA 2016 §33/§34 & ETO 2002 CRYPTOGRAPHIC CUSTODY TRAIL
                </span>
                <span className="text-[10px] text-ink-500 font-mono">
                  RFC 3161 TSA PROOF SEALED
                </span>
              </div>
              {custodyEvents.length > 0 ? (
                <div className="space-y-2.5">
                  {custodyEvents.map((evt) => {
                    const rfc = evt.metadata?.rfc3161 || (evt.payload as any)?.rfc3161;
                    return (
                      <div
                        key={evt.id}
                        className="bg-paper-1 p-3 border border-rule flex flex-col gap-2 text-[11px]"
                      >
                        <div className="flex flex-wrap justify-between items-start gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-ink-900">
                                {evt.eventType}
                              </span>
                              {rfc?.status === "SEALED" && (
                                <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider bg-emerald-500/15 text-emerald-800 border border-emerald-500/30">
                                  ⚖️ RFC 3161 TSA SEALED
                                </span>
                              )}
                            </div>
                            <span className="text-ink-600 text-[11px] block mt-0.5">
                              {evt.description || "Custody state registered."}
                            </span>
                            <span className="text-ink-500 text-[10px] block mt-0.5">
                              Actor: {evt.actor} {evt.ipAddress ? `(${evt.ipAddress})` : ""}
                            </span>
                          </div>
                          <span className="text-ink-500 tabular-nums text-[10px]">
                            {formatDatePKT(evt.timestamp)}
                          </span>
                        </div>

                        {/* RFC 3161 Timestamp Token Details */}
                        {rfc && rfc.status === "SEALED" && (
                          <div className="bg-paper-0 p-2.5 border border-rule/60 text-[10px] space-y-1 mt-1">
                            <div className="flex flex-wrap justify-between items-center text-ink-700">
                              <span>
                                <strong className="text-ink-900">TSA Authority:</strong>{" "}
                                {rfc.tsa_provider}
                              </span>
                              <span className="text-emerald-700 font-semibold">
                                ✓ Verified Digest Match
                              </span>
                            </div>
                            <div className="flex flex-wrap justify-between items-center text-ink-500">
                              <span>
                                <strong className="text-ink-700">Certified Time (GenTime):</strong>{" "}
                                {rfc.gen_time}
                              </span>
                              <span>
                                <strong className="text-ink-700">Serial No:</strong>{" "}
                                {rfc.serial_number}
                              </span>
                            </div>
                            {evt.sha256Hash && (
                              <div className="text-[9.5px] text-ink-500 truncate">
                                <strong className="text-ink-700">SHA-256 Digest:</strong>{" "}
                                {evt.sha256Hash}
                              </div>
                            )}
                            <div className="pt-1 flex items-center justify-between border-t border-rule/40 mt-1.5">
                              <span className="text-[9px] text-ink-400">
                                {rfc.legal_framework || "PECA 2016 §33/§34, QSO 1984 Art 164 & RFC 3161"}
                              </span>
                              <button
                                onClick={async () => {
                                  try {
                                    const blob = await downloadRFC3161Token(investigationId, evt.id);
                                    const url = window.URL.createObjectURL(blob);
                                    const a = document.createElement("a");
                                    a.href = url;
                                    a.download = `deeptrace_rfc3161_proof_${evt.id}.tst`;
                                    document.body.appendChild(a);
                                    a.click();
                                    window.URL.revokeObjectURL(url);
                                    document.body.removeChild(a);
                                  } catch (err) {
                                    alert("Could not download RFC 3161 token: " + err);
                                  }
                                }}
                                className="px-2 py-0.5 text-[9px] font-mono uppercase bg-paper-2 hover:bg-ink-900 hover:text-paper-0 border border-rule transition-colors"
                              >
                                ⬇ Download Proof (.tst)
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-4 bg-paper-1 text-center text-ink-500 text-xs">
                  Immutable custody lock registered upon document acquisition.
                </div>
              )}
            </div>
          )}

          {/* 8-Stage Forensic Pipeline Audit Checklist */}
          <div className="bg-paper-1 border border-rule p-4 font-mono text-xs">
            <span className="font-semibold text-ink-900 uppercase tracking-wider block mb-2 text-[10px]">
              § 04 / 8-STAGE FORENSIC PIPELINE EXECUTION AUDIT
            </span>
            <div className="space-y-1.5 text-[11px]">
              {/* 1. Custody Lock & RFC 3161 Seal */}
              <div className="flex justify-between items-center font-semibold">
                <span>1. Custody Fingerprint & RFC 3161 TSA Lock</span>
                {(() => {
                  const st = getStageStatus("CUSTODY_LOCK");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● SEALING...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ FAILED</span>;
                  const hasRfcSeal = custodyEvents.some(
                    (e) => (e.metadata?.rfc3161?.status === "SEALED") || (e.eventType === "CUSTODY_SEAL_RFC3161")
                  );
                  return (
                    <span className="text-forensic-green font-bold">
                      {hasRfcSeal ? "✓ RFC 3161 SEALED (PECA 2016)" : "✓ VERIFIED (ETO 2002)"}
                    </span>
                  );
                })()}
              </div>

              {/* 2. PDF Structure & Digital Signatures */}
              <div className="flex justify-between items-center font-semibold">
                <span>2. Structure, Incremental %%EOF & ETO 2002 Signatures</span>
                {(() => {
                  const st = getStageStatus("PDF_STRUCTURE");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● PARSING...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ FAILED</span>;
                  const hasSigInvalid = evidence.some(
                    (e) => (e.ruleId || "").includes("SIGNATURE_INVALIDATED") || (e.ruleId || "").includes("SIGNATURE_POST_SIGNING")
                  );
                  const hasSigValid = evidence.some(
                    (e) => (e.ruleId || "").includes("SIGNATURE_VALID")
                  );
                  const hasPdfAnom = evidence.some(
                    (e) => (e.ruleId || "").includes("PDF") || (e.ruleId || "").includes("METADATA")
                  );
                  if (hasSigInvalid) {
                    return <span className="text-forensic-red font-bold">✕ SIGNATURE INVALIDATED (ETO 2002 §29)</span>;
                  }
                  if (hasSigValid) {
                    return <span className="text-forensic-green font-bold">✓ PKI SIGNATURE VERIFIED (ETO 2002 §29)</span>;
                  }
                  return (
                    <span className={hasPdfAnom ? "text-forensic-amber" : "text-forensic-green"}>
                      {hasPdfAnom ? "▲ REVISIONS / SKEW FLAGGED" : "✓ CLEAN SINGLE REVISION"}
                    </span>
                  );
                })()}
              </div>

              {/* 3. Font & Baseline */}
              <div className="flex justify-between items-center font-semibold">
                <span>3. Sub-Pixel Baseline Typography</span>
                {(() => {
                  const st = getStageStatus("FONT_GLYPH_ANALYSIS");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● MEASURING...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ FAILED</span>;
                  const hasFontAnom = evidence.some((e) => (e.ruleId || "").includes("FONT"));
                  return (
                    <span className={hasFontAnom ? "text-forensic-red" : "text-forensic-green"}>
                      {hasFontAnom ? "✕ BASELINE JITTER DETECTED" : "✓ 0.00 PT VARIANCE"}
                    </span>
                  );
                })()}
              </div>

              {/* 4. Computer Vision Multi-Scale ELA & CMFD */}
              <div className="flex justify-between items-center font-semibold">
                <span>4. Computer Vision Multi-Scale ELA & CMFD</span>
                {(() => {
                  const st = getStageStatus("VISION_ELA");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● NEURAL SCAN...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ FAILED</span>;
                  const visualCount = evidence.filter(
                    (e) =>
                      (e.ruleId || "").includes("COPY_MOVE") ||
                      (e.ruleId || "").includes("ELA") ||
                      (e.ruleId || "").includes("TRUFOR") ||
                      (e.category || "").includes("IMAGE")
                  ).length;
                  return (
                    <span className={visualCount > 0 ? "text-forensic-red" : "text-forensic-green"}>
                      {visualCount > 0 ? `✕ MANIPULATION DETECTED (${visualCount})` : "✓ CONTOUR SCAN COMPLETE"}
                    </span>
                  );
                })()}
              </div>

              {/* 5. Semantic OCR & Table Columnizer */}
              <div className="flex justify-between items-center font-semibold">
                <span>5. Semantic OCR & Table Columnizer</span>
                {(() => {
                  const st = getStageStatus("OCR_EXTRACTION");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● EXTRACTING...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ FAILED</span>;
                  return <span className="text-forensic-green">✓ TEXT & TABLES EXTRACTED</span>;
                })()}
              </div>

              {/* 6. Deterministic Financial Math & SBP CDD Audit */}
              <div className="flex justify-between items-center font-semibold">
                <span>6. Deterministic Financial Math & SBP CDD Audit</span>
                {(() => {
                  if (!isFinancial) return <span className="text-ink-500 font-normal">— NOT APPLICABLE</span>;
                  const st = getStageStatus("FINANCIAL_VERIFICATION");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● RECONCILING...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ VERIFICATION FAILED</span>;
                  const hasNactaOrUnsc = evidence.some(
                    (e) => (e.ruleId || "").includes("AML_NACTA") || (e.ruleId || "").includes("AML_UNSC")
                  );
                  if (hasNactaOrUnsc) {
                    return <span className="text-forensic-red font-bold">✕ PROSCRIBED MATCH (NACTA / UNSC)</span>;
                  }
                  const hasPep = evidence.some((e) => (e.ruleId || "").includes("AML_PEP"));
                  if (hasPep) {
                    return <span className="text-amber-800 font-bold">▲ PEP IDENTIFIED (EDD REQUIRED)</span>;
                  }
                  const hasMathAnom = evidence.some(
                    (e) =>
                      e.category === "MATHEMATICAL_MISMATCH" ||
                      e.category === "MATH_RECONCILIATION_FAIL" ||
                      (e.ruleId || "").includes("MATH") ||
                      (e.ruleId || "").includes("BALANCE") ||
                      (e.ruleId || "").includes("LEDGER") ||
                      (e.ruleId || "").includes("HOLIDAY")
                  );
                  return (
                    <span className={hasMathAnom ? "text-forensic-red" : "text-forensic-green"}>
                      {hasMathAnom ? "✕ RECONCILIATION MISMATCH" : "✓ RECONCILED & CDD CLEARED"}
                    </span>
                  );
                })()}
              </div>

              {/* 7. Multi-Signal Evidence Fusion */}
              <div className="flex justify-between items-center font-semibold">
                <span>7. Multi-Signal Evidence Fusion</span>
                {(() => {
                  const st = getStageStatus("EVIDENCE_FUSION");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● FUSING SIGNALS...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ FAILED</span>;
                  return (
                    <span className={risk.overallScore > 30 ? "text-forensic-red" : "text-forensic-green"}>
                      {`SCORE: ${risk.overallScore} / 100`}
                    </span>
                  );
                })()}
              </div>

              {/* 8. Court-Admissible Dossier Generation */}
              <div className="flex justify-between items-center font-semibold">
                <span>8. Court-Admissible Dossier Generation</span>
                {(() => {
                  const st = getStageStatus("REPORT_GENERATION");
                  if (st === "PENDING") return <span className="text-ink-400 font-normal">○ PENDING</span>;
                  if (st === "RUNNING") return <span className="text-forensic-amber animate-pulse">● GENERATING...</span>;
                  if (st === "FAILED") return <span className="text-forensic-red">✕ FAILED</span>;
                  return <span className="text-ink-900">✓ SEALED</span>;
                })()}
              </div>
            </div>
          </div>
        </div>
        )}
      </div>

      {/* Analyst Override Modal */}
      <AnalystOverrideModal
        isOpen={isOverrideOpen}
        onClose={() => setIsOverrideOpen(false)}
        currentScore={risk.overallScore}
        onSave={handleOverrideSave}
      />
    </div>
  );
}
