"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Masthead } from "@/components/editorial/Masthead";
import { FolioTag } from "@/components/editorial/FolioTag";
import { HairlineRule } from "@/components/editorial/HairlineRule";
import {
  createInvestigation,
  uploadDocument,
  triggerPipeline,
} from "@/lib/api/client";
import { Upload, ShieldCheck, FileText, CheckCircle2 } from "lucide-react";

export default function NewCaseIntakePage() {
  const router = useRouter();
  const [title, setTitle] = useState<string>(
    "Bank Statement & Financial Ledger Forensic Audit"
  );
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [step, setStep] = useState<string>("");
  const [sha256, setSha256] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const computeSHA256 = async (f: File): Promise<string> => {
    const buffer = await f.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  };

  const handleFileChange = async (selectedFile: File) => {
    setFile(selectedFile);
    setError(null);
    try {
      const hash = await computeSHA256(selectedFile);
      setSha256(hash);
    } catch {
      setSha256("SHA-256 computation in progress...");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a bank statement PDF for custody acquisition.");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      setStep("1/4: Registering case docket and custody record...");
      const inv = await createInvestigation({
        title: title.trim() || "Bank Statement & Financial Ledger Forensic Audit",
        notes: "Acquired via DeepTrace Institutional Bank Statement Gateway",
      });

      setStep("2/4: Uploading statement & rendering 150 DPI canvas pages...");
      const doc = await uploadDocument(inv.id, file, "BANK_STATEMENT");

      setStep("3/4: Dispatching 8-stage forensic pipeline...");
      await triggerPipeline(inv.id, doc.id);

      setStep("4/4: Finalizing evidence ledger & opening Forensic Studio...");
      setTimeout(() => {
        router.push(`/investigations/${inv.id}`);
      }, 800);
    } catch (err: any) {
      console.error("Intake failed:", err);
      setIsProcessing(false);
      setError(
        err.message ||
          "Failed to ingest bank statement. Please verify the backend API server is running on port 8000."
      );
    }
  };

  return (
    <div className="min-h-screen bg-paper-0 text-ink-900 flex flex-col font-sans">
      <Masthead />

      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-12">
        <FolioTag
          section="§ 01"
          label="CHAIN OF CUSTODY INTAKE & SEEDING PROTOCOL"
        />

        <h1 className="font-serif text-3xl md:text-5xl text-ink-900 font-normal tracking-tight mt-2 mb-3">
          Bank Statement Intake &amp; Custody Lock
        </h1>

        <p className="text-sm md:text-base text-ink-700 leading-relaxed max-w-2xl">
          Ingested bank statements are immediately cryptographically fingerprinted under
          SHA-256, locked against alteration pursuant to Pakistan’s Electronic
          Transactions Ordinance (ETO 2002), and rasterized at 150 DPI for
          dual-anchor ledger reconciliation and sub-pixel forensic inspection.
        </p>

        <HairlineRule className="my-8" />

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Institutional Forensic Protocol Banner (Dedicated Bank Statement Engine) */}
          <div className="bg-paper-1 border border-rule p-4 font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-2.5 h-2.5 rounded-full bg-forensic-green animate-pulse flex-shrink-0" />
              <div>
                <span className="font-semibold text-ink-900 block text-xs tracking-wider uppercase">
                  Institutional Intake: Bank Statement &amp; Financial Ledger
                </span>
                <span className="text-[11px] text-ink-600 block mt-0.5 font-sans">
                  Enforcing SBP clearing standards, Lakh/Crore ledger reconciliation, and IBAN checksum verification.
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-center flex-shrink-0">
              <span className="px-2.5 py-1 bg-paper-0 border border-rule text-ink-700 font-mono text-[10px] uppercase tracking-wider font-semibold">
                SBP ENFORCED
              </span>
              <span className="px-2.5 py-1 bg-paper-0 border border-rule text-ink-700 font-mono text-[10px] uppercase tracking-wider font-semibold">
                LEDGER ENGINE
              </span>
            </div>
          </div>

          {/* Case Title Input */}
          <div>
            <label htmlFor="new-case-title" className="block font-mono text-xs uppercase tracking-wider text-ink-700 mb-2">
              Case Docket Title:
            </label>
            <input
              id="new-case-title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-paper-1 border border-rule px-4 py-3 text-sm text-ink-900 font-serif focus:outline-none focus:border-ink-900"
            />
          </div>

          {/* Drag & Drop Custody Area */}
          <div>
            <label htmlFor="file-input" className="block font-mono text-xs uppercase tracking-wider text-ink-700 mb-2">
              Forensic Evidence File (PDF, PNG, JPEG):
            </label>

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={`border-2 border-dashed p-10 text-center transition-all bg-paper-1/60 ${
                file
                  ? "border-forensic-green/60 bg-forensic-green/5"
                  : "border-rule hover:border-ink-900 cursor-pointer"
              }`}
            >
              <input
                type="file"
                id="file-input"
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                onChange={(e) =>
                  e.target.files?.[0] && handleFileChange(e.target.files[0])
                }
                className="hidden"
              />

              {file ? (
                <div className="space-y-2 font-mono text-xs">
                  <CheckCircle2 className="w-8 h-8 text-forensic-green mx-auto" />
                  <div className="font-bold text-ink-900 text-sm">
                    {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </div>
                  <div className="text-[11px] text-ink-500 break-all max-w-lg mx-auto bg-paper-0 p-2 border border-rule">
                    SHA-256 FINGERPRINT:{" "}
                    <span className="text-ink-900 font-semibold">{sha256}</span>
                  </div>
                  <label
                    htmlFor="file-input"
                    className="inline-block mt-2 text-ink-500 hover:text-ink-900 underline cursor-pointer text-[11px]"
                  >
                    Select different document
                  </label>
                </div>
              ) : (
                <label htmlFor="file-input" className="cursor-pointer block">
                  <Upload className="w-8 h-8 text-ink-500 mx-auto mb-3" />
                  <span className="font-serif text-lg text-ink-900 block mb-1">
                    Drag and drop statement PDF here
                  </span>
                  <span className="font-mono text-xs text-ink-500 block mb-3">
                    or click to browse local files (max 50 MB)
                  </span>
                  <span className="inline-block px-3 py-1 bg-paper-0 border border-rule font-mono text-[10px] uppercase tracking-wider text-ink-700">
                    Supports Born-Digital & Scanned Bank Statements
                  </span>
                </label>
              )}
            </div>
          </div>

          {/* Forensic Protocol Checklist */}
          <div className="bg-paper-1 border border-rule p-4 font-mono text-xs grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-ink-900 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-ink-900 block">
                  Custody Fingerprinting
                </span>
                <span className="text-[11px] text-ink-500">
                  Immutable SHA-256 hash sealing on acquisition.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <FileText className="w-4 h-4 text-ink-900 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-ink-900 block">
                  150 DPI Rasterization
                </span>
                <span className="text-[11px] text-ink-500">
                  Sub-pixel canvas generation for baseline jitter audit.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-ink-900 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-ink-900 block">
                  8-Stage Pipeline
                </span>
                <span className="text-[11px] text-ink-500">
                  Automated math, ELA, and metadata checks.
                </span>
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-forensic-red/10 border border-forensic-red/40 p-4 font-mono text-xs text-forensic-red flex items-start gap-3">
              <div className="w-2.5 h-2.5 rounded-full bg-forensic-red mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <span className="font-bold tracking-wider uppercase block text-forensic-red text-xs">
                  {error.includes("strictly accepts and analyzes Bank Statements")
                    ? "NON-BANK STATEMENT MATERIAL REJECTED"
                    : "INTAKE ERROR"}
                </span>
                <p className="text-ink-800 font-sans text-xs leading-relaxed">
                  {error}
                </p>
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="bg-paper-1 border border-rule p-4 font-mono text-xs">
              <div className="flex items-center gap-2 font-semibold text-ink-900 mb-1">
                <div className="w-2 h-2 rounded-full bg-forensic-red animate-ping" />
                <span>FORENSIC INGESTION PROTOCOL ACTIVE:</span>
              </div>
              <p className="text-ink-700">{step}</p>
            </div>
          )}

          {/* Submit Button */}
          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={isProcessing || !file}
              className="px-8 py-3 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold transition-colors disabled:opacity-40"
            >
              {isProcessing ? "Processing Custody Lock..." : "Seal & Analyze Statement →"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
