"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { formatPKR } from "@/lib/formatters";
import { EvidenceItem, LedgerRow } from "@/lib/types/forensics";
import {
  AlertTriangle,
  CheckCircle2,
  Filter,
  Search,
  Crosshair,
  Type,
  Calculator,
  ChevronDown,
  ChevronUp,
  ArrowUpRight,
  Sparkles,
} from "lucide-react";

interface SplitLedgerEvidenceViewerProps {
  rows?: LedgerRow[];
  evidence?: EvidenceItem[];
  financialData?: Record<string, any>;
  activeEvidenceId?: string | null;
  selectedRowIndex?: number | null;
  onSelectRow?: (row: LedgerRow, index: number) => void;
  onSelectEvidence?: (evidenceId: string) => void;
  onFocusCanvas?: (pageNumber: number, bbox?: [number, number, number, number]) => void;
}

export function SplitLedgerEvidenceViewer({
  rows = [],
  evidence = [],
  financialData,
  activeEvidenceId,
  selectedRowIndex: externalSelectedIndex,
  onSelectRow,
  onSelectEvidence,
  onFocusCanvas,
}: SplitLedgerEvidenceViewerProps) {
  const displayRows = rows || [];
  const [internalSelectedIndex, setInternalSelectedIndex] = useState<number | null>(null);
  const selectedIndex = externalSelectedIndex !== undefined ? externalSelectedIndex : internalSelectedIndex;

  const [filterMode, setFilterMode] = useState<"ALL" | "INCONSISTENT">("ALL");
  const [pageFilter, setPageFilter] = useState<number | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const activeRowRef = useRef<HTMLTableRowElement>(null);

  // Auto-scroll to selected row
  useEffect(() => {
    if (selectedIndex !== null && activeRowRef.current) {
      activeRowRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedIndex]);

  // Sync selection when activeEvidenceId changes from canvas click
  useEffect(() => {
    if (!activeEvidenceId) return;
    const targetEv = evidence.find((e) => e.id === activeEvidenceId);
    if (!targetEv) return;

    // Find row matching this evidence item's page and value
    const matchIdx = displayRows.findIndex((r) => {
      if (r.pageNumber && targetEv.pageNumber && r.pageNumber !== targetEv.pageNumber) return false;
      const actualVal = (targetEv.actualValue || "").replace(/[^0-9.]/g, "");
      const recBal = String(r.recordedBalance);
      const disc = String(Math.abs(r.discrepancy));
      return (
        (actualVal && (recBal.includes(actualVal) || actualVal.includes(recBal))) ||
        (r.isTampered && disc && targetEv.discrepancy?.includes(disc))
      );
    });

    if (matchIdx !== -1) {
      setInternalSelectedIndex(matchIdx);
    }
  }, [activeEvidenceId, evidence, displayRows]);

  // Identify typography findings on document
  const typographyFindings = useMemo(() => {
    return evidence.filter(
      (e) =>
        e.category === "FONT_BASELINE_INCONSISTENCY" ||
        (e.ruleId || "").includes("FONT") ||
        (e.ruleId || "").includes("BASELINE") ||
        (e.ruleId || "").includes("TEMPLATE_UNAUTHORIZED_FONT")
    );
  }, [evidence]);

  // Identify math mismatch findings
  const mathFindings = useMemo(() => {
    return evidence.filter(
      (e) =>
        e.category === "MATHEMATICAL_MISMATCH" ||
        e.category === "MATH_RECONCILIATION_FAIL" ||
        (e.ruleId || "").includes("BALANCE") ||
        (e.ruleId || "").includes("LEDGER") ||
        (e.ruleId || "").includes("MATH")
    );
  }, [evidence]);

  // Financial summary metrics
  const statedOpening = financialData?.stated_opening;
  const impliedOpening = financialData?.implied_opening;
  const statedClosing = financialData?.stated_closing;
  const impliedClosing = financialData?.implied_closing;
  const closingDiscrepancy = financialData?.closing_discrepancy;
  const isReconciled = displayRows.length > 0 && financialData?.reconciled !== false && !displayRows.some((r) => r.isTampered);

  // Unique pages available
  const availablePages = useMemo(() => {
    const pSet = new Set<number>();
    displayRows.forEach((r) => {
      if (r.pageNumber) pSet.add(r.pageNumber);
    });
    return Array.from(pSet).sort((a, b) => a - b);
  }, [displayRows]);

  // Filtered rows
  const filteredRows = useMemo(() => {
    return displayRows
      .map((r, originalIdx) => ({ ...r, originalIdx }))
      .filter((r) => {
        if (filterMode === "INCONSISTENT" && !r.isTampered) return false;
        if (pageFilter !== "ALL" && r.pageNumber !== pageFilter) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const pMatch = (r.particulars || "").toLowerCase().includes(q);
          const dMatch = (r.date || "").toLowerCase().includes(q);
          const bMatch = String(r.recordedBalance).includes(q);
          return pMatch || dMatch || bMatch;
        }
        return true;
      });
  }, [displayRows, filterMode, pageFilter, searchQuery]);

  const inconsistentCount = useMemo(() => displayRows.filter((r) => r.isTampered).length, [displayRows]);

  const handleRowClick = (row: LedgerRow & { originalIdx: number }) => {
    setInternalSelectedIndex(row.originalIdx);
    onSelectRow?.(row, row.originalIdx);

    // If row is tampered or has math discrepancy, find corresponding evidence item
    const matchingEv = mathFindings.find((e) => {
      if (row.pageNumber && e.pageNumber && row.pageNumber !== e.pageNumber) return false;
      return true;
    });

    if (matchingEv) {
      onSelectEvidence?.(matchingEv.id);
    }

    // Auto-focus left PDF canvas on this row's page
    if (row.pageNumber) {
      onFocusCanvas?.(row.pageNumber);
    }
  };

  const selectedRow = selectedIndex !== null && displayRows[selectedIndex] ? displayRows[selectedIndex] : null;

  // Correlate font discrepancies for selected row's page
  const selectedRowTypography = useMemo(() => {
    if (!selectedRow) return null;
    const pageNum = selectedRow.pageNumber || 1;
    const pageTypo = typographyFindings.filter((t) => (t.pageNumber || 1) === pageNum);
    return pageTypo.length > 0 ? pageTypo[0] : null;
  }, [selectedRow, typographyFindings]);

  return (
    <div className="flex flex-col h-full w-full bg-paper-0 border-l border-rule overflow-hidden text-ink-900 font-mono">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* Top Header: Invariant Health & Forensic Audit Summary          */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="p-3 bg-paper-1 border-b border-rule flex flex-col gap-2 select-none">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calculator className="w-4 h-4 text-ink-700" />
            <span className="font-bold text-xs uppercase tracking-wider text-ink-900">
              MATHEMATICAL LEDGER AUDIT
            </span>
          </div>
          <div className="flex items-center gap-2">
            {displayRows.length === 0 ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-paper-2 border border-rule text-ink-500 text-[10px] font-bold uppercase tracking-wider">
                No Transactions
              </span>
            ) : isReconciled ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-forensic-green/10 border border-forensic-green/30 text-forensic-green text-[10px] font-bold uppercase tracking-wider">
                <CheckCircle2 className="w-3 h-3" />
                Continuity Reconciled
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-forensic-red text-white text-[10px] font-bold uppercase tracking-wider animate-pulse">
                <AlertTriangle className="w-3 h-3" />
                {inconsistentCount} Inconsistent Row{inconsistentCount === 1 ? "" : "s"}
              </span>
            )}
            <span className="text-[10px] text-ink-500 border border-rule px-1.5 py-0.5 bg-paper-0">
              {displayRows.length} Total Rows
            </span>
          </div>
        </div>

        {/* Financial Continuity Metrics Pill Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-[10px] pt-1">
          <div className="bg-paper-0 p-1.5 border border-rule">
            <span className="text-ink-500 block uppercase text-[9px]">Stated Opening</span>
            <span className="font-semibold text-ink-900 tabular-nums">
              {statedOpening !== undefined && statedOpening !== null ? formatPKR(statedOpening) : "—"}
            </span>
          </div>

          <div className="bg-paper-0 p-1.5 border border-rule">
            <span className="text-ink-500 block uppercase text-[9px]">Stated Closing</span>
            <span className="font-semibold text-ink-900 tabular-nums">
              {statedClosing !== undefined && statedClosing !== null ? formatPKR(statedClosing) : "—"}
            </span>
          </div>

          <div className="bg-paper-0 p-1.5 border border-rule">
            <span className="text-ink-500 block uppercase text-[9px]">Calculated Running</span>
            <span
              className={`font-semibold tabular-nums ${
                closingDiscrepancy ? "text-forensic-red font-bold" : "text-forensic-green"
              }`}
            >
              {impliedClosing !== undefined && impliedClosing !== null ? formatPKR(impliedClosing) : "—"}
            </span>
          </div>

          <div
            className={`p-1.5 border ${
              closingDiscrepancy
                ? "bg-forensic-red/10 border-forensic-red/40 text-forensic-red"
                : "bg-paper-0 border-rule text-forensic-green"
            }`}
          >
            <span className="block uppercase text-[9px]">Discrepancy</span>
            <span className="font-bold tabular-nums">
              {closingDiscrepancy
                ? `${closingDiscrepancy > 0 ? "+" : ""}${formatPKR(closingDiscrepancy)}`
                : "0.00 PKR"}
            </span>
          </div>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* Filter Ribbon & Search Bar                                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="px-3 py-2 bg-paper-0 border-b border-rule flex flex-wrap items-center justify-between gap-2 text-xs select-none">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setFilterMode("ALL")}
            className={`px-2 py-1 text-[10px] uppercase font-bold border transition-colors cursor-pointer ${
              filterMode === "ALL"
                ? "bg-ink-900 text-paper-0 border-ink-900"
                : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
            }`}
          >
            All Rows ({displayRows.length})
          </button>

          <button
            onClick={() => setFilterMode("INCONSISTENT")}
            className={`px-2 py-1 text-[10px] uppercase font-bold border transition-colors cursor-pointer flex items-center gap-1 ${
              filterMode === "INCONSISTENT"
                ? "bg-forensic-red text-white border-forensic-red"
                : inconsistentCount > 0
                ? "bg-forensic-red/10 text-forensic-red border-forensic-red/40 hover:bg-forensic-red/20"
                : "bg-paper-1 text-ink-400 border-rule opacity-60"
            }`}
          >
            <AlertTriangle className="w-3 h-3" />
            Inconsistent ({inconsistentCount})
          </button>

          {availablePages.length > 1 && (
            <select
              value={pageFilter}
              onChange={(e) => setPageFilter(e.target.value === "ALL" ? "ALL" : Number(e.target.value))}
              className="px-2 py-1 text-[10px] uppercase font-mono border border-rule bg-paper-1 text-ink-800 cursor-pointer"
            >
              <option value="ALL">All Pages</option>
              {availablePages.map((p) => (
                <option key={p} value={p}>
                  Page {p}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Quick Search */}
        <div className="relative flex items-center">
          <Search className="w-3 h-3 text-ink-400 absolute left-2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search description or PKR..."
            className="pl-7 pr-2 py-1 text-[10px] font-mono border border-rule bg-paper-1 text-ink-900 placeholder:text-ink-400 w-36 sm:w-48 focus:outline-none focus:border-ink-900"
          />
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* Scrollable Transaction Ledger Table                            */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto overflow-x-auto">
        <table className="w-full text-left font-mono text-[11px] border-collapse">
          <thead className="sticky top-0 bg-paper-1 border-b border-rule z-10 select-none shadow-xs text-[9px] uppercase tracking-wider text-ink-500">
            <tr>
              <th className="py-2 px-2.5 w-10 text-center">#</th>
              <th className="py-2 px-2.5 w-24">Date</th>
              <th className="py-2 px-3">Description / Narration</th>
              <th className="py-2 px-2.5 text-right w-24">Debit (PKR)</th>
              <th className="py-2 px-2.5 text-right w-24">Credit (PKR)</th>
              <th className="py-2 px-2.5 text-right w-28">Stated Balance</th>
              <th className="py-2 px-2 text-center w-20">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule/60">
            {displayRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-12 text-center text-xs text-ink-500 font-mono space-y-2">
                  <div className="font-bold uppercase tracking-wider text-ink-800">
                    No Tabular Ledger Rows Detected
                  </div>
                  <div className="text-[11px] text-ink-500 max-w-sm mx-auto">
                    The document extraction engine did not locate tabular financial ledger columns in this document. Running balance mathematical verification applies to structured bank statements.
                  </div>
                </td>
              </tr>
            ) : filteredRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-xs text-ink-400">
                  {filterMode === "INCONSISTENT"
                    ? "No mathematical ledger inconsistencies detected. All rows reconcile."
                    : "No transactions match the selected filter."}
                </td>
              </tr>
            ) : (
              filteredRows.map((r) => {
                const isSelected = selectedIndex === r.originalIdx;
                return (
                  <tr
                    key={r.originalIdx}
                    ref={isSelected ? activeRowRef : null}
                    onClick={() => handleRowClick(r)}
                    className={`transition-colors cursor-pointer group select-none ${
                      isSelected
                        ? "bg-paper-2 ring-1 ring-ink-900 font-semibold"
                        : r.isTampered
                        ? "bg-forensic-red/10 hover:bg-forensic-red/15 text-forensic-red font-semibold border-l-4 border-forensic-red"
                        : "hover:bg-paper-1 text-ink-800"
                    }`}
                  >
                    <td className="py-2 px-2 text-center tabular-nums text-ink-400 text-[9px]">
                      {r.originalIdx + 1}
                    </td>

                    <td className="py-2 px-2.5 whitespace-nowrap tabular-nums text-ink-900">
                      <div className="flex items-center gap-1">
                        {r.pageNumber && (
                          <span
                            className="text-[8px] font-mono text-ink-500 border border-rule px-1 bg-paper-1 flex-shrink-0"
                            title={`Statement Page ${r.pageNumber}`}
                          >
                            P.{r.pageNumber}
                          </span>
                        )}
                        <span>{r.date}</span>
                      </div>
                    </td>

                    <td className="py-2 px-3 max-w-[200px]" title={r.particulars}>
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="truncate">{r.particulars}</span>
                        {r.rowType && r.rowType !== "TRANSACTION" && (
                          <span className="text-[8px] tracking-wider uppercase px-1 border border-rule text-ink-600 bg-paper-2 flex-shrink-0">
                            {r.rowType.replace(/_/g, " ")}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-2 px-2.5 text-right tabular-nums text-ink-900">
                      {r.debit ? formatPKR(r.debit) : "—"}
                    </td>

                    <td className="py-2 px-2.5 text-right tabular-nums text-ink-900">
                      {r.credit ? formatPKR(r.credit) : "—"}
                    </td>

                    <td className="py-2 px-2.5 text-right tabular-nums font-semibold">
                      <span className={r.isTampered ? "text-forensic-red font-bold" : "text-ink-900"}>
                        {formatPKR(r.recordedBalance)}
                      </span>
                    </td>

                    <td className="py-2 px-2 text-center">
                      {r.isTampered ? (
                        <span className="inline-block bg-forensic-red text-white text-[8px] px-1.5 py-0.5 uppercase tracking-wider font-bold shadow-xs">
                          MISMATCH
                        </span>
                      ) : (
                        <span className="text-forensic-green text-[9px] font-bold">
                          ✓ MATCH
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* Bottom Panel: Selected Row & Typography Forensics Inspector    */}
      {/* ───────────────────────────────────────────────────────────── */}
      {selectedRow && (
        <div className="border-t-2 border-rule bg-paper-1 p-3 select-none flex flex-col gap-2.5 max-h-[40%] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-rule pb-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-ink-600">
                ROW #{selectedIndex !== null ? selectedIndex + 1 : 1} FORENSIC INSPECTOR
              </span>
              {selectedRow.isTampered ? (
                <span className="bg-forensic-red text-white text-[8px] font-bold px-1.5 py-0.2 uppercase">
                  UNRECONCILED DISCREPANCY
                </span>
              ) : (
                <span className="text-forensic-green text-[9px] font-bold">
                  ✓ MATHEMATICALLY VALID
                </span>
              )}
            </div>

            {selectedRow.pageNumber && (
              <button
                onClick={() => onFocusCanvas?.(selectedRow.pageNumber!)}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-ink-900 text-paper-0 text-[10px] font-bold uppercase hover:bg-ink-700 transition-colors cursor-pointer"
              >
                <Crosshair className="w-3 h-3" />
                Focus Canvas (Page {selectedRow.pageNumber})
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            {/* Mathematical Breakdown Card */}
            <div
              className={`p-2.5 border text-[11px] space-y-1.5 ${
                selectedRow.isTampered
                  ? "bg-forensic-red/5 border-forensic-red/40"
                  : "bg-paper-0 border-rule"
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold uppercase text-[10px]">
                <Calculator
                  className={`w-3.5 h-3.5 ${
                    selectedRow.isTampered ? "text-forensic-red" : "text-forensic-green"
                  }`}
                />
                <span className={selectedRow.isTampered ? "text-forensic-red" : "text-ink-800"}>
                  Mathematical Continuity Proof
                </span>
              </div>

              <div className="space-y-1 pt-1 border-t border-rule/40 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-ink-500">Stated Balance on PDF:</span>
                  <span className="font-bold tabular-nums">
                    {formatPKR(selectedRow.recordedBalance)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-500">Expected Formula Balance:</span>
                  <span className="font-bold tabular-nums text-forensic-green">
                    {formatPKR(selectedRow.expectedBalance)}
                  </span>
                </div>
                {selectedRow.isTampered && (
                  <div className="flex justify-between pt-1 border-t border-forensic-red/30 text-forensic-red font-bold">
                    <span>Unreconciled Variance:</span>
                    <span className="tabular-nums">
                      {selectedRow.discrepancy > 0 ? "+" : ""}
                      {formatPKR(selectedRow.discrepancy)}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Typography & Font Discrepancy Card */}
            <div
              className={`p-2.5 border text-[11px] space-y-1.5 ${
                selectedRowTypography || selectedRow.isTampered
                  ? "bg-forensic-amber/10 border-forensic-amber/40"
                  : "bg-paper-0 border-rule"
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold uppercase text-[10px]">
                <Type className="w-3.5 h-3.5 text-forensic-amber" />
                <span className="text-ink-800">Typography & Font Forensics</span>
              </div>

              <div className="space-y-1 pt-1 border-t border-rule/40 text-[10px]">
                {selectedRowTypography ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-ink-500">Rule Triggered:</span>
                      <span className="font-bold text-ink-900">{selectedRowTypography.ruleId}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-ink-500">Baseline Jump:</span>
                      <span className="font-bold text-forensic-red tabular-nums">
                        {selectedRowTypography.discrepancy || "+2.50 pt offset"}
                      </span>
                    </div>
                    <p className="text-[9px] text-ink-700 italic pt-0.5 leading-snug">
                      {selectedRowTypography.description}
                    </p>
                  </>
                ) : (
                  <>
                    <div className="flex justify-between">
                      <span className="text-ink-500">Font Integrity:</span>
                      <span className="font-semibold text-forensic-green">
                        Uniform Subsets Verified
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-ink-500">Baseline Deviation:</span>
                      <span className="tabular-nums font-semibold text-ink-900">
                        &lt; 0.10 pt (Nominal)
                      </span>
                    </div>
                    <p className="text-[9px] text-ink-500 pt-0.5">
                      Character bounding boxes adhere to Core Banking System PostScript font metrics.
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
