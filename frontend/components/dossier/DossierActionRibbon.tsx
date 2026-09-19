"use client";

import React from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

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
    <div className="space-y-2.5 font-mono border-b border-rule pb-3">
      {/* Top Utility Bar: Section Identifier & Global Action Controls */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 whitespace-nowrap">
            § 03 / Forensic Dossier
          </span>
          {evidenceCount > 0 ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[9px] font-bold bg-forensic-red/10 text-forensic-red border border-forensic-red/30 whitespace-nowrap">
              <span className="w-1.5 h-1.5 rounded-full bg-forensic-red animate-pulse shrink-0" />
              {evidenceCount} {evidenceCount === 1 ? "Anomaly" : "Anomalies"}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-[9px] font-bold bg-forensic-green/10 text-forensic-green border border-forensic-green/30 whitespace-nowrap">
              <span className="w-1.5 h-1.5 rounded-full bg-forensic-green shrink-0" />
              Clean Record
            </span>
          )}
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onToggleChatDrawer}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase tracking-wider transition-all whitespace-nowrap shrink-0 border cursor-pointer select-none focus:outline-none focus:ring-1 focus:ring-ink-900",
              isChatDrawerOpen
                ? "bg-ink-900 text-paper-0 border-ink-900 shadow-sm ring-1 ring-ink-900"
                : "bg-amber-500/10 hover:bg-amber-500/20 text-ink-900 border-amber-600/30 hover:border-amber-600/50 shadow-xs"
            )}
            title="Toggle interactive Lead Investigator Q&A drawer"
          >
            <Sparkles
              className={cn(
                "w-3.5 h-3.5 shrink-0",
                isChatDrawerOpen
                  ? "text-amber-400 animate-pulse"
                  : "text-amber-600"
              )}
            />
            <span>Ask Investigator</span>
            {isChatDrawerOpen && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 ml-0.5" />
            )}
          </button>

          {!isSample && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onReanalyze}
              isLoading={isAnalyzing}
              leftIcon={
                !isAnalyzing ? <RefreshCw className="w-3.5 h-3.5" /> : undefined
              }
              className="whitespace-nowrap shrink-0 text-xs py-1.5 px-3 h-auto"
            >
              Re-Analyze
            </Button>
          )}
        </div>
      </div>

      {/* Domain-Aware Tab Navigation Strip */}
      <div
        role="tablist"
        aria-label="Forensic Dossier Tabs"
        className="flex flex-wrap items-center gap-1.5"
      >
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "findings"}
          onClick={() => onSelectTab("findings")}
          className={cn(
            "px-3 py-1.5 border text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap focus:outline-none focus:ring-1 focus:ring-ink-900",
            activeTab === "findings"
              ? "bg-ink-900 text-paper-0 border-ink-900 font-bold shadow-xs"
              : "bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-ink-900 border-rule hover:border-ink-500 font-medium"
          )}
        >
          <span>Findings</span>
          <span
            className={cn(
              "px-1.5 py-0.2 text-[10px] font-bold tabular-nums leading-none",
              activeTab === "findings"
                ? "bg-paper-0 text-ink-900"
                : evidenceCount > 0
                ? "bg-forensic-red text-white"
                : "bg-paper-2 text-ink-600 border border-rule"
            )}
          >
            {evidenceCount}
          </span>
        </button>

        {isFinancial && (
          <>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "ledger"}
              onClick={() => onSelectTab("ledger")}
              className={cn(
                "px-3 py-1.5 border text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap focus:outline-none focus:ring-1 focus:ring-ink-900",
                activeTab === "ledger"
                  ? "bg-ink-900 text-paper-0 border-ink-900 font-bold shadow-xs"
                  : "bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-ink-900 border-rule hover:border-ink-500 font-medium"
              )}
            >
              Math Ledger
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "iban"}
              onClick={() => onSelectTab("iban")}
              className={cn(
                "px-3 py-1.5 border text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap focus:outline-none focus:ring-1 focus:ring-ink-900",
                activeTab === "iban"
                  ? "bg-ink-900 text-paper-0 border-ink-900 font-bold shadow-xs"
                  : "bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-ink-900 border-rule hover:border-ink-500 font-medium"
              )}
            >
              SBP IBAN & AML
            </button>
          </>
        )}

        {(isIdentity || isFinancial || hasCnic) && (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "cnic"}
            onClick={() => onSelectTab("cnic")}
            className={cn(
              "px-3 py-1.5 border text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap focus:outline-none focus:ring-1 focus:ring-ink-900",
              activeTab === "cnic"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-bold shadow-xs"
                : "bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-ink-900 border-rule hover:border-ink-500 font-medium"
            )}
          >
            NADRA CNIC Audit
          </button>
        )}

        {(isTaxOrSalary || isFinancial || hasFbr) && (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "fbr"}
            onClick={() => onSelectTab("fbr")}
            className={cn(
              "px-3 py-1.5 border text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap focus:outline-none focus:ring-1 focus:ring-ink-900",
              activeTab === "fbr"
                ? "bg-ink-900 text-paper-0 border-ink-900 font-bold shadow-xs"
                : "bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-ink-900 border-rule hover:border-ink-500 font-medium"
            )}
          >
            FBR Tax & WHT
          </button>
        )}

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "custody"}
          onClick={() => onSelectTab("custody")}
          className={cn(
            "px-3 py-1.5 border text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap focus:outline-none focus:ring-1 focus:ring-ink-900",
            activeTab === "custody"
              ? "bg-ink-900 text-paper-0 border-ink-900 font-bold shadow-xs"
              : "bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-ink-900 border-rule hover:border-ink-500 font-medium"
          )}
        >
          Custody Chain
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "swarm"}
          onClick={() => onSelectTab("swarm")}
          className={cn(
            "px-3 py-1.5 border text-xs uppercase tracking-wider transition-all flex items-center gap-1.5 cursor-pointer select-none whitespace-nowrap focus:outline-none focus:ring-1 focus:ring-ink-900",
            activeTab === "swarm"
              ? "bg-ink-900 text-paper-0 border-ink-900 font-bold shadow-xs"
              : "bg-paper-1 hover:bg-paper-2 text-ink-700 hover:text-ink-900 border-rule hover:border-ink-500 font-medium"
          )}
        >
          <Sparkles
            className={cn(
              "w-3.5 h-3.5 shrink-0",
              activeTab === "swarm" ? "text-amber-400" : "text-amber-600"
            )}
          />
          <span>Agent Swarm</span>
        </button>
      </div>
    </div>
  );
}
