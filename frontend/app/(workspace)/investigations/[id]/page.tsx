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

      {/* Analyst Override Modal */}
      <AnalystOverrideModal
        isOpen={isOverrideOpen}
        onClose={() => setIsOverrideOpen(false)}
        currentScore={risk.overallScore}
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
