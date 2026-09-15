"use client";

import React from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface DossierActionRibbonProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  evidenceCount: number;
  isFinancial: boolean;
  isIdentity: boolean;
  isTaxOrSalary: boolean;
  hasCnic: boolean;
  hasFbr: boolean;
  isChatDrawerOpen: boolean;
  onToggleChatDrawer: () => void;
  isSample: boolean;
  isAnalyzing: boolean;
  onReanalyze: () => void;
}

export function DossierActionRibbon({
  activeTab,
  onSelectTab,
  evidenceCount,
  isFinancial,
  isIdentity,
  isTaxOrSalary,
  hasCnic,
  hasFbr,
  isChatDrawerOpen,
  onToggleChatDrawer,
  isSample,
  isAnalyzing,
  onReanalyze,
}: DossierActionRibbonProps) {
  return (
    <div className="flex items-center justify-between font-mono text-xs border-b border-rule pb-3">
      {/* Domain-Aware Tab Navigation */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onSelectTab("findings")}
          className={`px-3 py-1 border transition-colors uppercase ${
            activeTab === "findings"
              ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
              : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
          }`}
        >
          Findings ({evidenceCount})
        </button>

        {isFinancial && (
          <>
            <button
              onClick={() => onSelectTab("ledger")}
              className={`px-3 py-1 border transition-colors uppercase ${
                activeTab === "ledger"
                  ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                  : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
              }`}
            >
              Math Ledger
            </button>
            <button
              onClick={() => onSelectTab("iban")}
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

        {(isIdentity || isFinancial || hasCnic) && (
          <button
            onClick={() => onSelectTab("cnic")}
            className={`px-3 py-1 border transition-colors uppercase ${
              activeTab === "cnic"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
            }`}
          >
            NADRA CNIC Audit
          </button>
        )}

        {(isTaxOrSalary || isFinancial || hasFbr) && (
          <button
            onClick={() => onSelectTab("fbr")}
            className={`px-3 py-1 border transition-colors uppercase ${
              activeTab === "fbr"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
            }`}
          >
            FBR Tax & WHT
          </button>
        )}

        <button
          onClick={() => onSelectTab("custody")}
          className={`px-3 py-1 border transition-colors uppercase ${
            activeTab === "custody"
              ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
              : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
          }`}
        >
          Custody Chain
        </button>

        <button
          onClick={() => onSelectTab("swarm")}
          className={`px-3 py-1 border transition-colors uppercase flex items-center gap-1.5 ${
            activeTab === "swarm"
              ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold shadow-[1px_1px_0px_0px_rgba(0,0,0,1)]"
              : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>Agent Swarm</span>
        </button>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleChatDrawer}
          className={`px-3 py-1 border text-xs font-mono font-bold uppercase transition-all flex items-center gap-1.5 cursor-pointer ${
            isChatDrawerOpen
              ? "bg-ink-900 text-paper-0 border-ink-900 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
              : "bg-amber-50 hover:bg-amber-100 text-ink-900 border-ink-900 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
          }`}
          title="Toggle interactive Lead Investigator Q&A drawer"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-600" />
          <span>[ ASK LEAD INVESTIGATOR ]</span>
        </button>

        {!isSample && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onReanalyze}
            isLoading={isAnalyzing}
            leftIcon={
              !isAnalyzing ? <RefreshCw className="w-3 h-3" /> : undefined
            }
          >
            Re-Analyze
          </Button>
        )}
      </div>
    </div>
  );
}
