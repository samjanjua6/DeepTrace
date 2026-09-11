"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Masthead } from "@/components/editorial/Masthead";
import { FolioTag } from "@/components/editorial/FolioTag";
import { HairlineRule } from "@/components/editorial/HairlineRule";
import { ArrowRight, ShieldCheck, Cpu, Sliders, FileCode } from "lucide-react";

export default function EditorialHomePage() {
  const [sliderPos, setSliderPos] = useState<number>(50);

  return (
    <div className="min-h-screen bg-paper-0 text-ink-900 flex flex-col font-sans selection:bg-forensic-red selection:text-white">
      <Masthead />

      {/* Hero Editorial Section */}
      <section className="max-w-6xl w-full mx-auto px-6 pt-12 pb-8 md:pt-20 md:pb-14">
        <FolioTag
          section="DISPATCH NO. 01"
          label="STATE BANK OF PAKISTAN FINANCIAL FRAUD AUDIT INITIATIVE"
        />

        <h1 className="font-serif text-4xl sm:text-6xl md:text-7xl text-ink-900 font-normal tracking-tight mt-4 mb-6 leading-[1.08] max-w-4xl">
          Explainable Document Forensics & Verification API.
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
          <div className="md:col-span-8">
            <p className="font-serif text-xl sm:text-2xl text-ink-700 leading-relaxed italic mb-6">
              “From academic matric and university certificates to commercial banking ledgers,
              synthetic document fraud is accelerating. DeepTrace delivers explainable,
              mathematically verifiable document forensics across all industries.”
            </p>
            <p className="text-sm sm:text-base text-ink-700 leading-relaxed max-w-2xl mb-8">
              Rather than probabilistic black boxes, DeepTrace combines sub-pixel
              typography baseline geometry, computer vision Error Level Analysis (ELA),
              cryptographic custody locking (ETO 2002), and deterministic math reconciliation
              to verify authentic educational credentials, utility bills, and financial statements
              with evidentiary certainty.
            </p>

            <div className="flex flex-wrap items-center gap-4">
              <Link
                href="/investigations/new"
                className="px-8 py-3.5 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold transition-colors flex items-center gap-2"
              >
                <span>Intake Document for Verification</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/investigations/sample"
                className="px-6 py-3.5 bg-paper-1 hover:bg-paper-2 border border-rule text-ink-900 font-mono text-xs uppercase tracking-widest font-semibold transition-colors"
              >
                View Tampered Specimen (85% Demo) →
              </Link>
            </div>
          </div>

          <div className="md:col-span-4 bg-paper-1 border border-rule p-5 font-mono text-xs space-y-3">
            <span className="text-[10px] text-ink-500 uppercase tracking-widest block font-bold border-b border-rule pb-1.5">
              FORENSIC TELEMETRY METRICS
            </span>
            <div className="flex justify-between">
              <span className="text-ink-500">Pipeline Stages:</span>
              <span className="font-bold text-ink-900">8 Formal Stages</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-500">Execution Latency:</span>
              <span className="font-bold text-ink-900">~613 ms / statement</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-500">Coordinate Scale:</span>
              <span className="font-bold text-ink-900">72 DPI pt ➔ 150 DPI px</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-500">Math Tolerances:</span>
              <span className="font-bold text-ink-900">Zero-Tolerance (Exact)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-500">SBP Compliance:</span>
              <span className="font-bold text-forensic-green">BPRD & ETO 2002</span>
            </div>
          </div>
        </div>
      </section>

      <HairlineRule label="EXHIBIT A: INTERACTIVE SPECIMEN LABORATORY" />

      {/* Interactive Specimen Lab: Before / After Slider */}
      <section className="max-w-6xl w-full mx-auto px-6 py-8">
        <div className="mb-4 flex items-baseline justify-between flex-wrap gap-2">
          <div>
            <FolioTag section="§ 02" label="SYNTHETIC TAMPERING DEMONSTRATION" />
            <h2 className="font-serif text-2xl md:text-3xl text-ink-900 mt-1">
              The Sub-Pixel & Ledger Mismatch
            </h2>
          </div>
          <span className="font-mono text-xs text-ink-500">
            DRAG SLIDER TO REVEAL DEEPTRACE FORENSIC OVERLAY
          </span>
        </div>

        {/* The Comparison Box */}
        <div className="relative border-2 border-rule bg-white overflow-hidden select-none">
          <div className="p-6 md:p-8 font-mono text-xs">
            {/* Header of Exhibit */}
            <div className="border-b border-rule pb-4 mb-6 flex justify-between items-start">
              <div>
                <span className="font-bold text-base text-ink-900 block font-serif">
                  Meezan Bank Limited — Account Statement
                </span>
                <span className="text-ink-500 text-[11px]">
                  Branch: I.I. Chundrigar Road, Karachi • IBAN: PK36MEZN0001020102030405
                </span>
              </div>
              <span className="bg-paper-1 border border-rule px-2 py-1 text-[10px] text-ink-700 font-semibold uppercase">
                EXHIBIT SPECIMEN #DT-PK-001
              </span>
            </div>

            {/* Transactions Table Simulation */}
            <div className="space-y-4">
              {/* Row 1 */}
              <div className="flex justify-between items-center py-2 border-b border-rule/50">
                <span className="w-24">01/03/2026</span>
                <span className="flex-1">Cheque Clearing Deposit (NIFT Clg)</span>
                <span className="w-32 text-right">Credit: 4,00,000.00</span>
                <span className="w-32 text-right font-semibold">4,00,000.00</span>
              </div>

              {/* Row 2 */}
              <div className="flex justify-between items-center py-2 border-b border-rule/50">
                <span className="w-24">05/03/2026</span>
                <span className="flex-1">Raast P2P Outflow Transfer</span>
                <span className="w-32 text-right text-ink-500">Debit: 1,50,000.00</span>
                <span className="w-32 text-right font-semibold">2,50,000.00</span>
              </div>

              {/* Row 3 (The Tampered Row) */}
              <div className="relative flex justify-between items-center py-3 bg-forensic-red/5 border border-forensic-red/30 px-3">
                <span className="w-24">12/03/2026</span>
                <span className="flex-1">Counter Cash Withdrawal</span>
                <span className="w-32 text-right text-ink-500">Debit: 75,000.00</span>

                <div className="w-32 text-right relative">
                  <span className="font-bold text-forensic-red text-sm tracking-tight">
                    25,00,000.00
                  </span>
                  {/* Bounding box marker */}
                  <div className="absolute -inset-1 border-2 border-forensic-red pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Forensic Finding Annotation */}
            <div className="mt-8 pt-4 border-t border-rule grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-paper-1 p-3 border border-rule">
                <span className="text-[10px] text-ink-500 block uppercase font-bold mb-1">
                  1. Deterministic Math Inconsistency:
                </span>
                <p className="text-[11px] text-ink-700">
                  Balance expected: <span className="font-bold text-ink-900">PKR 1,75,000.00</span>.
                  Actual reported: <span className="font-bold text-forensic-red">PKR 25,00,000.00</span>.
                  Discrepancy: <span className="font-bold text-forensic-red">+PKR 23,25,000.00 (+870%)</span>.
                </p>
              </div>

              <div className="bg-paper-1 p-3 border border-rule">
                <span className="text-[10px] text-ink-500 block uppercase font-bold mb-1">
                  2. Sub-Pixel Typography Baseline Sag:
                </span>
                <p className="text-[11px] text-ink-700">
                  Row baseline median: <span className="font-bold text-ink-900">200.00 pt</span>.
                  Number span baseline: <span className="font-bold text-forensic-red">202.50 pt</span>.
                  Offset: <span className="font-bold text-forensic-red">+2.50 pt vertical sag</span>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <HairlineRule label="THE 8-STAGE DETERMINISTIC & CV PIPELINE" />

      {/* Architecture Grid Section */}
      <section className="max-w-6xl w-full mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 font-mono text-xs">
          <div className="bg-paper-1 border border-rule p-5 space-y-2">
            <span className="text-[10px] text-ink-500 uppercase tracking-widest block font-bold">
              01 / CUSTODY LOCK
            </span>
            <h3 className="font-serif text-lg text-ink-900">SHA-256 Sealing</h3>
            <p className="text-[11px] text-ink-700 leading-relaxed">
              Magic-byte header verification rejects extension spoofing; produces
              immutable append-only ETO 2002 custody events.
            </p>
          </div>

          <div className="bg-paper-1 border border-rule p-5 space-y-2">
            <span className="text-[10px] text-ink-500 uppercase tracking-widest block font-bold">
              02 / STRUCTURE & METADATA
            </span>
            <h3 className="font-serif text-lg text-ink-900">Incremental Saves</h3>
            <p className="text-[11px] text-ink-700 leading-relaxed">
              Exposes multiple %%EOF trailers and signatures from Canva,
              Photoshop, or Acrobat Pro DC with timestamp divergence.
            </p>
          </div>

          <div className="bg-paper-1 border border-rule p-5 space-y-2">
            <span className="text-[10px] text-ink-500 uppercase tracking-widest block font-bold">
              03 / SUB-PIXEL GEOMETRY
            </span>
            <h3 className="font-serif text-lg text-ink-900">Baseline y-Jitter</h3>
            <p className="text-[11px] text-ink-700 leading-relaxed">
              Measures median vertical baselines across rows. Catches manual
              desktop insertions with &gt;0.75 pt offset.
            </p>
          </div>

          <div className="bg-paper-1 border border-rule p-5 space-y-2">
            <span className="text-[10px] text-ink-500 uppercase tracking-widest block font-bold">
              04 / FINANCIAL MATH
            </span>
            <h3 className="font-serif text-lg text-ink-900">Lakh/Crore Reconciler</h3>
            <p className="text-[11px] text-ink-700 leading-relaxed">
              Deterministic row-by-row equation audit across Pakistani banking
              numbering formats and ISO 7064 MOD-97 IBANs.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-rule bg-paper-1 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 font-mono text-xs text-ink-500">
          <div>
            <span className="text-ink-900 font-semibold">DEEPTRACE FORENSIC ENGINE</span>
            {" • "}
            <span>NIST SP 800-86 AUDIT COMPLIANT</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/investigations" className="hover:text-ink-900 transition-colors">
              Case Docket
            </Link>
            <Link href="/investigations/new" className="hover:text-ink-900 transition-colors">
              Intake
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink-900 transition-colors"
            >
              Swagger API
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
