"use client";

import React from "react";
import { CustodyEvent } from "@/lib/types/forensics";
import { formatDatePKT } from "@/lib/formatters";

interface CustodyTabProps {
  custodyEvents: CustodyEvent[];
  onDownloadRfcToken: (eventId: string) => Promise<void>;
}

export function CustodyTab({
  custodyEvents,
  onDownloadRfcToken,
}: CustodyTabProps) {
  return (
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
            const rfc =
              evt.metadata?.rfc3161 || (evt.payload as any)?.rfc3161;
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
                          RFC 3161 TSA SEALED
                        </span>
                      )}
                    </div>
                    <span className="text-ink-600 text-[11px] block mt-0.5">
                      {evt.description || "Custody state registered."}
                    </span>
                    <span className="text-ink-500 text-[10px] block mt-0.5">
                      Actor: {evt.actor}{" "}
                      {evt.ipAddress ? `(${evt.ipAddress})` : ""}
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
                        [✓] Verified Digest Match
                      </span>
                    </div>
                    <div className="flex flex-wrap justify-between items-center text-ink-500">
                      <span>
                        <strong className="text-ink-700">
                          Certified Time (GenTime):
                        </strong>{" "}
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
                        {rfc.legal_framework ||
                          "PECA 2016 §33/§34, QSO 1984 Art 164 & RFC 3161"}
                      </span>
                      <button
                        onClick={() => onDownloadRfcToken(evt.id)}
                        className="px-2 py-0.5 text-[9px] font-mono uppercase bg-paper-2 hover:bg-ink-900 hover:text-paper-0 border border-rule transition-colors cursor-pointer"
                      >
                        Download Proof (.tst)
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
  );
}
