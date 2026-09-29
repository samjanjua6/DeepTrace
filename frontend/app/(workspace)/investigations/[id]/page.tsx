"use client";

import React from "react";
import { useParams } from "next/navigation";
import { ForensicCanvas } from "@/components/canvas/ForensicCanvas";
import { RiskGaugeBlock } from "@/components/dossier/RiskGaugeBlock";
import { LedgerMathTable } from "@/components/dossier/LedgerMathTable";
import { SplitLedgerEvidenceViewer } from "@/components/dossier/SplitLedgerEvidenceViewer";
import { AnalystOverrideModal } from "@/components/dossier/AnalystOverrideModal";
import { CreditOfficerBriefing } from "@/components/dossier/CreditOfficerBriefing";
import { SwarmChatDrawer } from "@/components/agents/SwarmChatDrawer";
import { StudioHeader } from "@/components/dossier/StudioHeader";
import { PipelineExecutionBanner } from "@/components/dossier/PipelineExecutionBanner";
import { ClassificationProfileCard } from "@/components/dossier/ClassificationProfileCard";
import { DossierActionRibbon } from "@/components/dossier/DossierActionRibbon";
import { PipelineAuditChecklist } from "@/components/dossier/PipelineAuditChecklist";
import { DocketLoadingView } from "@/components/dossier/DocketLoadingView";
import { DocketErrorView } from "@/components/dossier/DocketErrorView";
import { FindingsTab } from "@/components/dossier/tabs/FindingsTab";
import { CustodyTab } from "@/components/dossier/tabs/CustodyTab";
import { RegulatoryTab } from "@/components/dossier/tabs/RegulatoryTab";
import { WorkspaceSplitter } from "@/components/canvas/WorkspaceSplitter";
import { useInvestigationDocket } from "@/lib/hooks/useInvestigationDocket";

export default function InvestigationWorkspacePage() {
  const params = useParams();
  const investigationId = params?.id as string;

  const {
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
    financialData,
    stage0Classifier,
    getStageStatus,
  } = useInvestigationDocket(investigationId);

  const adverseEvidenceCount = React.useMemo(
    () => evidence.filter((e) => e.severity !== "INFO").length,
    [evidence]
  );

  // ── Adjustable Workbench Division State (Viewer vs. Explanation) ──────────
  const workbenchRef = React.useRef<HTMLDivElement>(null);
  const [splitRatio, setSplitRatio] = React.useState<number>(() =>
    viewMode === "split" && isFinancial ? 50 : 58
  );
  const [isDragging, setIsDragging] = React.useState<boolean>(false);

  // Restore saved ratio for active viewMode or fall back to default
  React.useEffect(() => {
    try {
      const key = `deeptrace_split_pct_${viewMode}`;
      const saved = localStorage.getItem(key);
      if (saved) {
        const val = parseFloat(saved);
        if (!isNaN(val) && val >= 20 && val <= 80) {
          setSplitRatio(val);
          return;
        }
      }
    } catch {}
    setSplitRatio(viewMode === "split" && isFinancial ? 50 : 58);
  }, [viewMode, isFinancial]);

  // Persist user-adjusted split ratio to localStorage
  React.useEffect(() => {
    if (!isDragging) {
      try {
        const key = `deeptrace_split_pct_${viewMode}`;
        localStorage.setItem(key, splitRatio.toFixed(1));
      } catch {}
    }
  }, [splitRatio, isDragging, viewMode]);

  // Handle pointer down on the splitter grip
  const handleSplitterPointerDown = React.useCallback(
    (e: React.PointerEvent) => {
      if (e.button !== 0) return;
      e.preventDefault();
      setIsDragging(true);
    },
    []
  );

  // Reset split ratio to default on double-click
  const handleResetSplit = React.useCallback(() => {
    const def = viewMode === "split" && isFinancial ? 50 : 58;
    setSplitRatio(def);
    try {
      localStorage.removeItem(`deeptrace_split_pct_${viewMode}`);
    } catch {}
  }, [viewMode, isFinancial]);

  // Keyboard navigation for splitter handle
  const handleSplitterKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setSplitRatio((prev) => Math.max(20, Math.min(80, prev - 2)));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setSplitRatio((prev) => Math.max(20, Math.min(80, prev + 2)));
      } else if (e.key === "Home" || e.key === "Enter") {
        e.preventDefault();
        handleResetSplit();
      }
    },
    [handleResetSplit]
  );

  // Track global pointer movements during active drag
  React.useEffect(() => {
    if (!isDragging) return;

    const handlePointerMove = (e: PointerEvent) => {
      if (!workbenchRef.current) return;
      const rect = workbenchRef.current.getBoundingClientRect();
      if (rect.width <= 0) return;
      const mouseX = e.clientX - rect.left;
      const rawPct = (mouseX / rect.width) * 100;

      // Minimum 320px for viewer, minimum 360px for explanation pane
      const minPct = Math.max(20, (320 / rect.width) * 100);
      const maxPct = Math.min(80, ((rect.width - 360) / rect.width) * 100);
      const clamped = Math.min(Math.max(rawPct, minPct), maxPct);

      setSplitRatio(clamped);
    };

    const handlePointerUp = () => {
      setIsDragging(false);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [isDragging]);

  if (isLoading) {
    return <DocketLoadingView documentType={documentType} />;
  }

  if (!isSample && (fetchError || !investigation)) {
    return (
      <DocketErrorView
        investigationId={investigationId}
        documentType={documentType}
        fetchError={fetchError}
      />
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-paper-0 text-ink-900">
      {/* Studio Header (Masthead, Benchmark Demo Warning, Workbench Ribbon) */}
      <StudioHeader
        caseNumber={caseNumber}
        caseTitle={caseTitle}
        documentType={documentType}
        isSample={isSample}
        isFinancial={isFinancial}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      {/* Asymmetric 2-Column Split Workbench */}
      <div ref={workbenchRef} className="flex flex-1 overflow-hidden relative">
        {/* Column 1: Sticky Left Forensic Canvas (Viewer Window) */}
        <div
          style={{ width: `${splitRatio}%` }}
          className="h-full flex flex-col relative border-r border-rule shrink-0 overflow-hidden"
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

        {/* Resizable Divider Between Viewer and Explanation Windows */}
        <WorkspaceSplitter
          splitRatio={splitRatio}
          isDragging={isDragging}
          onPointerDown={handleSplitterPointerDown}
          onDoubleClick={handleResetSplit}
          onKeyDown={handleSplitterKeyDown}
        />

        {/* Column 2: Right Interactive Pane (Split Ledger or Full Dossier Explanation Window) */}
        {viewMode === "split" && isFinancial ? (
          <div
            style={{ width: `${100 - splitRatio}%` }}
            className="flex-1 h-full flex flex-col overflow-hidden bg-paper-0 min-w-0"
          >
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
          <div
            style={{ width: `${100 - splitRatio}%` }}
            className="flex-1 h-full overflow-y-auto bg-paper-0 p-6 space-y-6 min-w-0"
          >
            {/* Live Pipeline Execution Banner */}
            <PipelineExecutionBanner
              isAnalyzing={isAnalyzing}
              pipelineRun={pipelineRun}
              investigationStatus={investigation?.status}
              documentType={documentType}
              pagesCount={pages.length}
            />

            {/* Stage 0 Classifier Card */}
            <ClassificationProfileCard
              classifier={stage0Classifier}
              documentType={documentType}
            />

            {/* Calibrated Risk Gauge Block */}
            <RiskGaugeBlock
              assessment={risk}
              isCalculating={
                isAnalyzing ||
                pipelineRun?.status === "RUNNING" ||
                investigation?.status === "PROCESSING"
              }
              onOpenOverride={
                isSample ? undefined : () => setIsOverrideOpen(true)
              }
            />

            {/* Autonomous Lead Investigator Agent - Credit Officer Briefing */}
            <CreditOfficerBriefing
              investigationId={investigationId}
              overallScore={risk?.overallScore ?? 0}
              riskTier={risk?.riskTier ?? "LOW"}
              actionDirective={
                risk?.actionDirective ?? "STRAIGHT_THROUGH_APPROVAL"
              }
              overriddenScore={risk?.overriddenScore}
              overriddenTier={risk?.overriddenTier}
              overrideReason={risk?.overrideReason}
              overriddenById={risk?.overriddenById}
              overriddenAt={risk?.overriddenAt}
              authenticityScore={risk?.authenticityScore}
              tamperScore={risk?.tamperScore}
              authenticityTier={risk?.authenticityTier}
              transactionRiskScore={risk?.transactionRiskScore}
              transactionRiskTier={risk?.transactionRiskTier}
              evidenceItems={evidence}
              onFocusCanvas={(pageNum) => setFocusedPageNumber(pageNum)}
              onSelectEvidence={(id) => {
                setActiveEvidenceId(id);
                const ev = evidence.find((e) => e.id === id);
                if (ev && ev.pageNumber) {
                  setFocusedPageNumber(ev.pageNumber);
                }
              }}
            />

            {/* Action Ribbon & Dynamic Domain-Aware Tabs */}
            <DossierActionRibbon
              activeTab={activeTab}
              onSelectTab={setActiveTab}
              evidenceCount={adverseEvidenceCount}
              isFinancial={isFinancial}
              isIdentity={isIdentity}
              isTaxOrSalary={isTaxOrSalary}
              hasCnic={Boolean(financialData?.cnic_verification)}
              hasFbr={Boolean(financialData?.fbr_tax_verification)}
              isChatDrawerOpen={isChatDrawerOpen}
              onToggleChatDrawer={() => setIsChatDrawerOpen((prev) => !prev)}
              isSample={isSample}
              isAnalyzing={isAnalyzing}
              onReanalyze={handleReanalyze}
            />

            {/* Tab Views */}
            {activeTab === "findings" && (
              <FindingsTab
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
                onFocusCanvas={(pageNum) => setFocusedPageNumber(pageNum)}
              />
            )}

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
                    if (mathEv) {
                      setActiveEvidenceId(mathEv.id);
                      if (mathEv.pageNumber) setFocusedPageNumber(mathEv.pageNumber);
                    }
                  }}
                  onSelectEvidence={(id) => {
                    setActiveEvidenceId(id);
                    const ev = evidence.find((e) => e.id === id);
                    if (ev && ev.pageNumber) {
                      setFocusedPageNumber(ev.pageNumber);
                    }
                  }}
                  onFocusCanvas={(pageNum) => setFocusedPageNumber(pageNum)}
                />
              </div>
            )}

            {(activeTab === "iban" ||
              activeTab === "cnic" ||
              activeTab === "fbr") && (
              <RegulatoryTab
                activeTab={activeTab}
                financialData={financialData}
                evidence={evidence}
                onFocusCanvas={(pageNum) => setFocusedPageNumber(pageNum)}
              />
            )}

            {activeTab === "custody" && (
              <CustodyTab
                custodyEvents={custodyEvents}
                onDownloadRfcToken={handleDownloadRfcToken}
              />
            )}

            {activeTab === "swarm" && (
              <div className="space-y-3">
                <SwarmChatDrawer
                  investigationId={investigationId}
                  mode="tab"
                  onCitationClick={handleCitationClick}
                />
              </div>
            )}

            {/* 8-Stage Forensic Pipeline Audit Checklist */}
            <PipelineAuditChecklist
              getStageStatus={getStageStatus}
              custodyEvents={custodyEvents}
              evidence={evidence}
              isFinancial={isFinancial}
              isIdentity={isIdentity}
              isTaxOrSalary={isTaxOrSalary}
              riskScore={risk.overallScore}
            />
          </div>
        )}
      </div>

      {/* Workspace Status Footer */}
      <footer className="h-6 shrink-0 bg-paper-1 border-t border-rule px-4 flex items-center justify-between text-[10px] font-mono text-ink-500 select-none">
        <div className="flex items-center gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
          <span className="font-semibold text-ink-800">
            {documentType === "BANK_STATEMENT"
              ? "SBP CLEARING STANDARD: ENFORCED • RUNNING BALANCE RECONCILIATION: ACTIVE"
              : documentType === "UTILITY_BILL"
              ? "UTILITY TARIFF AUDIT: ENFORCED • K-ELECTRIC / BILLING RECONCILIATION: ACTIVE"
              : documentType === "SALARY_SLIP"
              ? "EMPLOYMENT PAYROLL AUDIT: ENFORCED • DUAL-COLUMN EARNINGS/DEDUCTIONS: ACTIVE"
              : documentType === "TAX_CERTIFICATE"
              ? "FBR CPR PAYMENT RECEIPT: ENFORCED • NTN TAX REGISTER: ACTIVE"
              : documentType === "IDENTITY_DOCUMENT"
              ? "NADRA VERISYS / ICAO 9303: ENFORCED • SECURITY THREAD & MRZ AUDIT: ACTIVE"
              : "FORENSIC SPECIFICATION: ACTIVE"}
          </span>
        </div>
        <div className="hidden md:flex items-center gap-3 text-ink-400">
          <span>NIST SP 800-86 AUDIT TRAIL</span>
          <span>•</span>
          <span>ETO 2002 §29 PRESUMPTION</span>
          <span>•</span>
          <span>RFC 3161 TSA SEALED</span>
        </div>
      </footer>

      {/* Analyst Override Modal */}
      <AnalystOverrideModal
        isOpen={isOverrideOpen}
        onClose={() => setIsOverrideOpen(false)}
        currentScore={risk.overallScore}
        authenticityScore={risk.authenticityScore}
        transactionRiskScore={risk.transactionRiskScore}
        onSave={handleOverrideSave}
      />

      {/* Floating Interactive Swarm Slide-Out Drawer */}
      <SwarmChatDrawer
        investigationId={investigationId}
        isOpen={isChatDrawerOpen}
        onClose={() => setIsChatDrawerOpen(false)}
        mode="drawer"
        onCitationClick={handleCitationClick}
      />
    </div>
  );
}
