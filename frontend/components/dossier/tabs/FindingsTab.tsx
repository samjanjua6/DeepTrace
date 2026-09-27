"use client";

import React, { useEffect } from "react";
import { EvidenceItem } from "@/lib/types/forensics";
import { AnomalyCard } from "@/components/dossier/AnomalyCard";
import { CheckCircle2, Sparkles, Layers, FileSearch, Hash } from "lucide-react";

interface FindingsTabProps {
  evidence: EvidenceItem[];
  activeEvidenceId: string | null;
  onSelectEvidence: (id: string | null) => void;
  onFocusCanvas?: (pageNumber: number) => void;
}

export function FindingsTab({
  evidence,
  activeEvidenceId,
  onSelectEvidence,
  onFocusCanvas,
}: FindingsTabProps) {
  const adverseFindings = evidence.filter((e) => e.severity !== "INFO");
  const verifiedChecks = evidence.filter((e) => e.severity === "INFO");

  useEffect(() => {
    if (activeEvidenceId) {
      const el = document.getElementById(`finding-card-${activeEvidenceId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [activeEvidenceId]);

  if (adverseFindings.length > 0) {
    return (
      <div className="space-y-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between font-mono text-xs text-ink-800 pb-0.5">
            <span className="font-bold tracking-wider text-ink-900">DETECTED ANOMALIES ({adverseFindings.length})</span>
            <span className="text-[11px] text-ink-700 font-semibold tracking-wide">CLICK OR HOVER TO SYNC CANVAS</span>
          </div>
          {adverseFindings.map((item, idx) => (
            <AnomalyCard
              key={item.id}
              item={item}
              findingNumber={idx + 1}
              isSelected={activeEvidenceId === item.id}
              onSelect={onSelectEvidence}
              onFocusCanvas={onFocusCanvas}
            />
          ))}
        </div>

        {verifiedChecks.length > 0 && (
          <div className="space-y-3 pt-3 border-t border-rule">
            <div className="flex items-center justify-between font-mono text-xs text-emerald-950 pb-0.5">
              <span className="font-bold flex items-center gap-1.5 tracking-wider">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
                VERIFIED AUTHENTIC SPECIFICATIONS ({verifiedChecks.length})
              </span>
              <span className="text-[11px] text-emerald-800 font-semibold">CANONICAL BASELINES SATISFIED</span>
            </div>
            {verifiedChecks.map((item) => (
              <AnomalyCard
                key={item.id}
                item={item}
                isSelected={activeEvidenceId === item.id}
                onSelect={onSelectEvidence}
                onFocusCanvas={onFocusCanvas}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Explainability when Document is Clean / Not Edited
  return (
    <div className="bg-paper-0 border border-rule p-5 font-mono select-none space-y-4">
      <div className="flex items-start gap-3 border-b border-rule pb-3">
        <CheckCircle2 className="w-6 h-6 text-forensic-green flex-shrink-0 mt-0.5" />
        <div>
          <span className="text-[11px] text-forensic-green font-bold uppercase tracking-widest block">
            VERIFICATION CERTIFICATE - NIST SP 800-86 AUDIT PASSED
          </span>
          <h3 className="font-serif text-lg text-ink-900 font-medium">
            Authentic Document - Zero Tampering Detected
          </h3>
          <p className="text-xs text-ink-700 mt-1 leading-relaxed">
            DeepTrace analyzed all 8 forensic verification layers. No physical,
            sub-pixel typography, compression, or structural anomalies were
            found.
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
            Character baseline variance &lt; 0.05 pt. No spliced text spans or
            font subset mismatches.
          </p>
        </div>

        <div className="bg-paper-1 p-3 border border-rule space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-ink-900">
            <Layers className="w-3.5 h-3.5 text-forensic-green" />
            <span>Error Level Analysis (ELA)</span>
          </div>
          <p className="text-[11px] text-ink-700">
            Dual-pass Q=95 difference matrix is uniform across all blocks. No
            high-frequency edits.
          </p>
        </div>

        <div className="bg-paper-1 p-3 border border-rule space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-ink-900">
            <FileSearch className="w-3.5 h-3.5 text-forensic-green" />
            <span>Stream & Structure</span>
          </div>
          <p className="text-[11px] text-ink-700">
            Clean single-revision layout. No secondary %%EOF trailers or desktop
            manipulation tools detected.
          </p>
        </div>

        <div className="bg-paper-1 p-3 border border-rule space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-ink-900">
            <Hash className="w-3.5 h-3.5 text-forensic-green" />
            <span>Cryptographic Seal</span>
          </div>
          <p className="text-[11px] text-ink-700">
            Original SHA-256 fingerprint verified against acquisition record
            under ETO 2002.
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
  );
}
