"use client";

import React from "react";
import { formatPKR } from "@/lib/formatters";
import { EvidenceItem } from "@/lib/types/forensics";
import { AlertTriangle, CheckCircle, ArrowRight } from "lucide-react";

interface LedgerRow {
  date: string;
  particulars: string;
  debit?: number;
  credit?: number;
  expectedBalance: number;
  recordedBalance: number;
  discrepancy: number;
  isTampered: boolean;
  pageNumber?: number;
  rowType?: string;
}

interface LedgerMathTableProps {
  rows?: LedgerRow[];
  evidence?: EvidenceItem[];
  onSelectRow?: (row: LedgerRow) => void;
  onSelectEvidence?: (evidenceId: string) => void;
  onFocusCanvas?: (pageNumber: number) => void;
}

export function LedgerMathTable({
  rows = [],
  evidence,
  onSelectRow,
  onSelectEvidence,
  onFocusCanvas,
}: LedgerMathTableProps) {
  const [currentPage, setCurrentPage] = React.useState(1);
  const pageSize = 25;
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const paginatedRows = rows.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const openingMismatch = evidence?.find(
    (e) => e.ruleId === "RULE_PK_OPENING_BALANCE_MISMATCH"
  );
  const closingMismatch = evidence?.find(
    (e) => e.ruleId === "RULE_PK_CLOSING_BALANCE_MISMATCH"
  );
  const ledgerRowMismatch = evidence?.find(
    (e) =>
      e.ruleId === "RULE_PK_LEDGER_RECONCILIATION_FAIL" ||
      (e.category === "MATHEMATICAL_MISMATCH" &&
        e.ruleId !== "RULE_PK_OPENING_BALANCE_MISMATCH" &&
        e.ruleId !== "RULE_PK_CLOSING_BALANCE_MISMATCH")
  );

  const hasHeaderDiscrepancy = Boolean(openingMismatch || closingMismatch);

  return (
    <div className="space-y-4">
      {/* Header Balance Discrepancy Audit Section */}
      {hasHeaderDiscrepancy && (
        <div className="bg-paper-0 border-2 border-forensic-red/60 p-4 font-mono text-xs space-y-3 shadow-sm">
          <div className="flex items-center justify-between border-b border-rule pb-2">
            <div className="flex items-center gap-2 text-forensic-red font-bold uppercase tracking-wider">
              <AlertTriangle className="w-4 h-4 text-forensic-red flex-shrink-0" />
              <span>DETERMINISTIC BALANCE AUDIT: HEADER TAMPERING DETECTED</span>
            </div>
            <span className="bg-forensic-red text-white text-[9px] px-2 py-0.5 uppercase font-bold tracking-wider">
              CRITICAL FRAUD SIGNAL
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Opening Balance Card */}
            {openingMismatch ? (
              <div
                onClick={() => {
                  onSelectEvidence?.(openingMismatch.id);
                  onFocusCanvas?.(openingMismatch.pageNumber || 1);
                }}
                className="bg-forensic-red/5 border border-forensic-red/40 p-3 hover:bg-forensic-red/10 cursor-pointer transition-colors space-y-2 group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-bold text-forensic-red uppercase text-[10px] tracking-wider">
                      Opening Balance Discrepancy
                    </span>
                    <span className="bg-forensic-red/20 text-forensic-red border border-forensic-red/40 px-1 py-0.2 text-[8.5px] font-bold rounded-xs">
                      {(() => {
                        const sPage = openingMismatch.endpoints?.find((ep) => ep.role === "stated")?.page || 1;
                        const dPage = openingMismatch.endpoints?.find((ep) => ep.role === "derived")?.page || openingMismatch.pageNumber || 1;
                        return sPage !== dPage ? `P.${sPage} ↔ P.${dPage}` : `P.${sPage} (Header ↔ Ledger)`;
                      })()}
                    </span>
                    {openingMismatch.pattern && (
                      <span className="bg-forensic-red/20 text-forensic-red border border-forensic-red/40 px-1 py-0.2 text-[8.5px] font-bold rounded-xs">
                        {openingMismatch.pattern === "magnitude_power_of_ten"
                          ? `MAGNITUDE (${openingMismatch.multiplier}×)`
                          : openingMismatch.pattern.replace(/_/g, " ").toUpperCase()}
                      </span>
                    )}
                    {openingMismatch.corroboration && (
                      <span className="bg-blue-900/30 text-blue-400 border border-blue-700/40 px-1 py-0.2 text-[8.5px] font-bold rounded-xs">
                        {openingMismatch.corroboration.shared_factor}× SYMMETRIC
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {openingMismatch.endpoints && openingMismatch.endpoints.length > 0 ? (
                      openingMismatch.endpoints.map((ep, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEvidence?.(openingMismatch.id);
                            onFocusCanvas?.(ep.page);
                          }}
                          className="text-[9px] bg-forensic-red/15 hover:bg-forensic-red text-forensic-red hover:text-white px-1.5 py-0.5 rounded-sm transition-colors font-bold cursor-pointer"
                          title={ep.label}
                        >
                          P.{ep.page} {ep.role === "stated" ? "Stated" : "Origin"} ↗
                        </button>
                      ))
                    ) : (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectEvidence?.(openingMismatch.id);
                          onFocusCanvas?.(openingMismatch.pageNumber || 1);
                        }}
                        className="text-[10px] bg-forensic-red/15 hover:bg-forensic-red text-forensic-red hover:text-white px-2 py-0.5 rounded-sm transition-colors flex items-center gap-1 font-bold"
                      >
                        Locate P.{openingMismatch.pageNumber || 1} <ArrowRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-forensic-red/20">
                  <div>
                    <span className="text-[10px] text-ink-500 block uppercase">Stated on PDF</span>
                    <span className="font-bold text-ink-900 tabular-nums">
                      {openingMismatch.actualValue || "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-500 block uppercase">Calculated Ledger</span>
                    <span className="font-bold text-forensic-green tabular-nums">
                      {openingMismatch.expectedValue || "—"}
                    </span>
                  </div>
                </div>
                <div className="bg-forensic-red/15 px-2 py-1 text-[10px] text-forensic-red font-bold flex justify-between">
                  <span>UNRECONCILED VARIANCE:</span>
                  <span className="tabular-nums">{openingMismatch.discrepancy || "MISMATCH"}</span>
                </div>
              </div>
            ) : (
              <div className="bg-paper-1 border border-rule p-3 space-y-1">
                <div className="flex items-center gap-1.5 text-forensic-green text-[10px] font-bold uppercase tracking-wider">
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>Opening Balance Reconciled</span>
                </div>
                <p className="text-[11px] text-ink-600">
                  Stated opening balance matches initial transaction baseline.
                </p>
              </div>
            )}

            {/* Closing Balance Card */}
            {closingMismatch ? (
              <div
                onClick={() => {
                  onSelectEvidence?.(closingMismatch.id);
                  onFocusCanvas?.(closingMismatch.pageNumber || 23);
                }}
                className="bg-forensic-red/5 border border-forensic-red/40 p-3 hover:bg-forensic-red/10 cursor-pointer transition-colors space-y-2 group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-bold text-forensic-red uppercase text-[10px] tracking-wider">
                      Closing Balance Discrepancy
                    </span>
                    <span className="bg-forensic-red/20 text-forensic-red border border-forensic-red/40 px-1 py-0.2 text-[8.5px] font-bold rounded-xs">
                      {(() => {
                        const sPage = closingMismatch.endpoints?.find((ep) => ep.role === "stated")?.page || 1;
                        const dPage = closingMismatch.endpoints?.find((ep) => ep.role === "derived")?.page || closingMismatch.pageNumber || 23;
                        return sPage !== dPage ? `P.${sPage} ↔ P.${dPage}` : `P.${sPage} (Header ↔ Ledger)`;
                      })()}
                    </span>
                    {closingMismatch.pattern && (
                      <span className="bg-forensic-red/20 text-forensic-red border border-forensic-red/40 px-1 py-0.2 text-[8.5px] font-bold rounded-xs">
                        {closingMismatch.pattern === "magnitude_power_of_ten"
                          ? `MAGNITUDE (${closingMismatch.multiplier}×)`
                          : closingMismatch.pattern.replace(/_/g, " ").toUpperCase()}
                      </span>
                    )}
                    {closingMismatch.corroboration && (
                      <span className="bg-blue-900/30 text-blue-400 border border-blue-700/40 px-1 py-0.2 text-[8.5px] font-bold rounded-xs">
                        {closingMismatch.corroboration.shared_factor}× SYMMETRIC
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {closingMismatch.endpoints && closingMismatch.endpoints.length > 0 ? (
                      closingMismatch.endpoints.map((ep, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEvidence?.(closingMismatch.id);
                            onFocusCanvas?.(ep.page);
                          }}
                          className="text-[9px] bg-forensic-red/15 hover:bg-forensic-red text-forensic-red hover:text-white px-1.5 py-0.5 rounded-sm transition-colors font-bold cursor-pointer"
                          title={ep.label}
                        >
                          P.{ep.page} {ep.role === "stated" ? "Stated" : "Terminal"} ↗
                        </button>
                      ))
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEvidence?.(closingMismatch.id);
                            onFocusCanvas?.(1);
                          }}
                          className="text-[9px] bg-forensic-red/15 hover:bg-forensic-red text-forensic-red hover:text-white px-1.5 py-0.5 rounded-sm transition-colors font-bold cursor-pointer"
                          title="Jump to Stated Closing Balance on Page 1 Summary"
                        >
                          P.1 Stated ↗
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEvidence?.(closingMismatch.id);
                            onFocusCanvas?.(closingMismatch.pageNumber || 23);
                          }}
                          className="text-[9px] bg-forensic-red/15 hover:bg-forensic-red text-forensic-red hover:text-white px-1.5 py-0.5 rounded-sm transition-colors font-bold cursor-pointer"
                          title="Jump to Final Transaction Balance on Page 23 Ledger Terminal"
                        >
                          P.{closingMismatch.pageNumber || 23} Terminal ↗
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-forensic-red/20">
                  <div>
                    <span className="text-[10px] text-ink-500 block uppercase">Stated on PDF</span>
                    <span className="font-bold text-ink-900 tabular-nums">
                      {closingMismatch.actualValue || "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-500 block uppercase">Calculated Ledger</span>
                    <span className="font-bold text-forensic-green tabular-nums">
                      {closingMismatch.expectedValue || "—"}
                    </span>
                  </div>
                </div>
                <div className="bg-forensic-red/15 px-2 py-1 text-[10px] text-forensic-red font-bold flex justify-between">
                  <span>UNRECONCILED VARIANCE:</span>
                  <span className="tabular-nums">{closingMismatch.discrepancy || "MISMATCH"}</span>
                </div>
              </div>
            ) : (
              <div className="bg-paper-1 border border-rule p-3 space-y-1">
                <div className="flex items-center gap-1.5 text-forensic-green text-[10px] font-bold uppercase tracking-wider">
                  <CheckCircle className="w-3.5 h-3.5" />
                  <span>Closing Balance Reconciled</span>
                </div>
                <p className="text-[11px] text-ink-600">
                  Terminal balance matches cumulative mathematical credit/debit sum.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ledger Table */}
      <div className="bg-paper-0 border border-rule overflow-hidden">
        <div className="bg-paper-1 px-4 py-2.5 border-b border-rule flex items-center justify-between font-mono text-xs">
          <span className="font-semibold text-ink-900 tracking-wider uppercase">
            § 02 / DETERMINISTIC RUNNING LEDGER MATH RECONCILIATION
          </span>
          <span className="text-[10px] text-ink-500">
            {rows.length > 0
              ? `${rows.length} Total Transactions Extracted`
              : "ISO FORMULA: B[i] = B[i-1] + CR - DR"}
          </span>
        </div>

        {rows.length === 0 ? (
          <div className="p-8 text-center text-xs text-ink-500 font-mono bg-paper-1">
            No transaction ledger rows extracted yet.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs border-collapse">
                <thead>
                  <tr className="bg-paper-1/60 border-b border-rule text-[10px] text-ink-500 uppercase">
                    <th className="py-2 px-3">Date</th>
                    <th className="py-2 px-3">Transaction Description</th>
                    <th className="py-2 px-3 text-right">Debit (PKR)</th>
                    <th className="py-2 px-3 text-right">Credit (PKR)</th>
                    <th className="py-2 px-3 text-right">Recorded Bal</th>
                    <th className="py-2 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-rule/60 text-[11px]">
                  {paginatedRows.map((r, idx) => (
                    <tr
                      key={idx}
                      onClick={() => {
                        onSelectRow?.(r);
                        if (r.isTampered && ledgerRowMismatch) {
                          onSelectEvidence?.(ledgerRowMismatch.id);
                        }
                      }}
                      className={`transition-colors cursor-pointer ${
                        r.isTampered
                          ? "bg-forensic-red/10 hover:bg-forensic-red/15 font-semibold text-forensic-red"
                          : "hover:bg-paper-1 text-ink-700"
                      }`}
                    >
                      <td className="py-2.5 px-3 tabular-nums text-ink-900 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          {r.pageNumber && (
                            <span
                              className="text-[9px] font-mono text-ink-500 border border-rule px-1 py-0.2 bg-paper-1"
                              title={`Statement Page ${r.pageNumber}`}
                            >
                              P.{r.pageNumber}
                            </span>
                          )}
                          <span>{r.date}</span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 max-w-[240px]" title={r.particulars}>
                        <div className="flex items-center gap-1.5 truncate">
                          <span className="truncate">{r.particulars}</span>
                          {r.rowType && r.rowType !== "TRANSACTION" && (
                            <span className="text-[8px] tracking-wider uppercase font-mono px-1 py-0.5 border border-rule text-ink-600 bg-paper-2 flex-shrink-0">
                              {r.rowType.replace(/_/g, " ")}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-ink-900">
                        {r.debit ? formatPKR(r.debit) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums text-ink-900">
                        {r.credit ? formatPKR(r.credit) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right tabular-nums font-semibold">
                        {formatPKR(r.recordedBalance)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {r.isTampered ? (
                          <span className="bg-forensic-red text-white text-[9px] px-2 py-0.5 uppercase tracking-wider font-bold">
                            MISMATCH
                          </span>
                        ) : (
                          <span className="text-forensic-green text-[10px] font-bold">
                            ✓ MATCH
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="bg-paper-1 px-4 py-2 border-t border-rule flex items-center justify-between font-mono text-[11px] text-ink-700">
                <span>
                  Showing {(currentPage - 1) * pageSize + 1}–
                  {Math.min(currentPage * pageSize, rows.length)} of {rows.length} rows
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="px-2 py-1 border border-rule bg-paper-0 disabled:opacity-40 hover:bg-paper-2 transition-colors cursor-pointer"
                  >
                    Prev
                  </button>
                  <span className="tabular-nums">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="px-2 py-1 border border-rule bg-paper-0 disabled:opacity-40 hover:bg-paper-2 transition-colors cursor-pointer"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Discrepancy Forensic Callout if tampered */}
        {rows.some((r) => r.isTampered) && (
          <div className="bg-forensic-red/10 border-t border-forensic-red/30 p-3 text-xs font-mono">
            <div className="flex items-center gap-2 text-forensic-red font-bold uppercase mb-1">
              <span>CRITICAL MATHEMATICAL DISCREPANCY DETECTED:</span>
            </div>
            <p className="text-[11px] text-ink-700 leading-relaxed">
              Row balance diverges from expected mathematical reconciliation.
              Net artificial ledger inflation detected.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
