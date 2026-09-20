"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
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
} from "@/lib/api/client";

// Realistic sample forensic exhibit data (Used exclusively for demo exhibit /investigations/sample)
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
  authenticityScore: 15,
  tamperScore: 85,
  authenticityTier: "FORGERY_DETECTED",
  transactionRiskScore: 0,
  transactionRiskTier: "CLEAN",
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

export function useInvestigationDocket(investigationId: string) {
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
          id: "pending",
          investigationId,
          overallScore: 0,
          authenticityScore: 100,
          tamperScore: 0,
          authenticityTier: "VERIFIED_AUTHENTIC",
          transactionRiskScore: 0,
          transactionRiskTier: "CLEAN",
          riskTier: "LOW",
          actionDirective: "MANUAL_SUPERVISOR_REVIEW",
          confidenceScore: 0,
          isDeterministicOverride: false,
          computedAt: new Date().toISOString(),
          riskSignals: [],
        }
  );

  const [fetchError, setFetchError] = useState<string | null>(null);
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
  const [isChatDrawerOpen, setIsChatDrawerOpen] = useState<boolean>(false);

  // Citation click handler jumping to canvas evidence and domain tab
  const handleCitationClick = useCallback(
    (citationId: string) => {
      const match = evidence.find(
        (e) =>
          e.id === citationId ||
          e.ruleId === citationId ||
          (e.ruleId && e.ruleId.toLowerCase().includes(citationId.toLowerCase()))
      );

      if (match) {
        setActiveEvidenceId(match.id);
        if (match.pageNumber) {
          setFocusedPageNumber(match.pageNumber);
        }

        if (match.category?.includes("MATH") || match.ruleId?.includes("LEDGER")) {
          setActiveTab("ledger");
        } else if (
          match.ruleId?.includes("IBAN") ||
          match.ruleId?.includes("AML")
        ) {
          setActiveTab("iban");
        } else if (match.ruleId?.includes("CNIC")) {
          setActiveTab("cnic");
        } else if (match.ruleId?.includes("FBR") || match.ruleId?.includes("TAX")) {
          setActiveTab("fbr");
        } else {
          setActiveTab("findings");
        }
      }
    },
    [evidence]
  );

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
        // 1. Fetch Investigation with strict error propagation on initial load
        let inv = null;
        try {
          inv = await getInvestigation(investigationId);
          if (!isMounted) return;
          if (inv) setInvestigation(inv);
        } catch (fetchErr: any) {
          if (!isMounted) return;
          if (isInitial) {
            setFetchError(fetchErr?.message || "Investigation docket not found.");
            setIsLoading(false);
            return;
          }
        }

        if (!inv && isInitial) {
          setFetchError("Investigation docket not found in central repository.");
          setIsLoading(false);
          return;
        }

        // 2. Fetch Documents & Pages
        if (!hasLoadedPages) {
          const docs = await getDocuments(investigationId).catch(() => []);
          if (!isMounted) return;
          if (docs && docs.length > 0) {
            const mainDoc = docs[0];
            setDocumentType(mainDoc.documentType || "OTHER");

            const docPages = await getDocumentPages(
              investigationId,
              mainDoc.id
            ).catch(() => []);
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
        } else if (pRun?.status === "COMPLETED") {
          setRisk({
            id: "clean",
            investigationId,
            overallScore: 0,
            authenticityScore: 100,
            tamperScore: 0,
            authenticityTier: "VERIFIED_AUTHENTIC",
            transactionRiskScore: 0,
            transactionRiskTier: "CLEAN",
            riskTier: "LOW",
            actionDirective: "STRAIGHT_THROUGH_APPROVAL",
            confidenceScore: 1.0,
            isDeterministicOverride: false,
            computedAt: new Date().toISOString(),
            riskSignals: [],
          });
        } else if (pRun?.status === "FAILED") {
          setRisk({
            id: "failed",
            investigationId,
            overallScore: 100,
            authenticityScore: 0,
            tamperScore: 100,
            authenticityTier: "FORGERY_DETECTED",
            transactionRiskScore: 100,
            transactionRiskTier: "CRITICAL_PROSCRIBED",
            riskTier: "CRITICAL",
            actionDirective: "IMMEDIATE_REJECTION",
            confidenceScore: 1.0,
            isDeterministicOverride: true,
            computedAt: new Date().toISOString(),
            riskSignals: [],
          });
        }


        // 6. Fetch Custody Log
        const custody = await getCustodyEvents(investigationId).catch(() => []);
        if (!isMounted) return;
        if (custody && custody.length > 0) setCustodyEvents(custody);

        // Polling decision
        isStillRunning =
          pRun?.status === "RUNNING" ||
          pRun?.status === "QUEUED" ||
          inv?.status === "PROCESSING" ||
          (pRun?.status !== "COMPLETED" &&
            pRun?.status !== "FAILED" &&
            (!r || r.overallScore === 0));
      } catch (err) {
        console.error("Failed to load investigation data:", err);
        if (isInitial) {
          setFetchError("Error querying forensic pipeline data.");
        } else {
          isStillRunning = true;
        }
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

  const handleReanalyze = useCallback(async () => {
    if (!investigationId || isSample) return;
    setIsAnalyzing(true);
    try {
      await triggerPipeline(investigationId);

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
  }, [investigationId, isSample]);

  const handleOverrideSave = useCallback(
    async (newScore: number, reason: string) => {
      if (!investigationId || isSample) return;
      const updated = await overrideRiskScore(investigationId, newScore, reason);
      setRisk(updated);
    },
    [investigationId, isSample]
  );

  const handleDownloadRfcToken = useCallback(
    async (eventId: string) => {
      try {
        const blob = await downloadRFC3161Token(investigationId, eventId);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `deeptrace_rfc3161_proof_${eventId}.tst`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (err) {
        alert("Could not download RFC 3161 token: " + err);
      }
    },
    [investigationId]
  );

  const caseNumber = useMemo(() => {
    return isSample
      ? "EXHIBIT-DEMO-001"
      : investigation?.caseNumber || "DT-2026-CASE";
  }, [isSample, investigation?.caseNumber]);

  const caseTitle = useMemo(() => {
    return isSample
      ? "Sample Tampered Bank Statement Exhibit (Pre-computed Demo)"
      : investigation?.title || "Document Forensics Verification Docket";
  }, [isSample, investigation?.title]);

  const isFinancial = useMemo(() => {
    return (
      documentType === "BANK_STATEMENT" ||
      evidence.some(
        (e) =>
          e.category === "MATHEMATICAL_MISMATCH" ||
          e.category === "MATH_RECONCILIATION_FAIL" ||
          (e.ruleId || "").includes("MATH") ||
          (e.ruleId || "").includes("BALANCE") ||
          (e.ruleId || "").includes("LEDGER") ||
          (e.ruleId || "").includes("HOLIDAY")
      )
    );
  }, [documentType, evidence]);

  const stage6 = useMemo(() => {
    return pipelineRun?.stages?.find(
      (s) => s.stageType === "FINANCIAL_VERIFICATION"
    );
  }, [pipelineRun?.stages]);

  const financialData = stage6?.outputPayload;

  const isIdentity = useMemo(() => {
    return (
      documentType === "IDENTITY_DOCUMENT" ||
      evidence.some(
        (e) =>
          (e.ruleId || "").includes("CNIC") ||
          (e.technicalDetails as any)?.identity_category ===
            "NADRA_CNIC_ANOMALY" ||
          (e.technicalDetails as any)?.statutory_reference?.includes("NADRA")
      ) ||
      Boolean(financialData?.cnic_verification)
    );
  }, [documentType, evidence, financialData?.cnic_verification]);

  const isTaxOrSalary = useMemo(() => {
    return (
      documentType === "SALARY_SLIP" ||
      documentType === "TAX_RETURN" ||
      evidence.some(
        (e) =>
          (e.ruleId || "").includes("RULE_FBR_") ||
          Boolean((e.technicalDetails as any)?.fbr_audit)
      ) ||
      Boolean(financialData?.fbr_tax_verification)
    );
  }, [documentType, evidence, financialData?.fbr_tax_verification]);

  const stage0Classifier = useMemo(() => {
    return (pipelineRun?.parameters as any)?.stage_0_classification;
  }, [pipelineRun?.parameters]);

  const getStageStatus = useCallback(
    (stageType: string) => {
      if (isSample) return "COMPLETED";
      const stage = pipelineRun?.stages?.find((s) => s.stageType === stageType);
      return stage?.status || (pipelineRun ? "PENDING" : "COMPLETED");
    },
    [isSample, pipelineRun]
  );

  return {
    investigationId,
    isSample,
    investigation,
    documentType,
    pages,
    evidence,
    risk,
    fetchError,
    custodyEvents,
    activeEvidenceId,
    setActiveEvidenceId,
    isOverrideOpen,
    setIsOverrideOpen,
    activeTab,
    setActiveTab,
    viewMode,
    setViewMode,
    focusedPageNumber,
    setFocusedPageNumber,
    selectedRowIndex,
    setSelectedRowIndex,
    isLoading,
    isAnalyzing,
    pipelineRun,
    isChatDrawerOpen,
    setIsChatDrawerOpen,
    handleCitationClick,
    handleReanalyze,
    handleOverrideSave,
    handleDownloadRfcToken,
    caseNumber,
    caseTitle,
    isFinancial,
    isIdentity,
    isTaxOrSalary,
    stage6,
    financialData,
    stage0Classifier,
    getStageStatus,
  };
}
