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
  loginAnalyst,
} from "@/lib/api/client";
import { Upload, ShieldCheck, FileText, CheckCircle2 } from "lucide-react";

export default function NewCaseIntakePage() {
  const router = useRouter();
  const [documentType, setDocumentType] = useState<string>("AUTO");
  const [title, setTitle] = useState<string>(
    "Automated Forensic Docket (Stage 0 Multi-Modal Classifier)"
  );
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [step, setStep] = useState<string>("");
  const [sha256, setSha256] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const handleDocTypeChange = (newType: string) => {
    setDocumentType(newType);
    if (newType === "AUTO") {
      setTitle("Automated Forensic Docket (Stage 0 Multi-Modal Classifier)");
    } else if (newType === "OTHER") {
      setTitle("BISE Examination Certificate / Academic Result Verification");
    } else if (newType === "BANK_STATEMENT") {
      setTitle("Bank Statement & Financial Ledger Forensic Audit");
    } else if (newType === "SALARY_SLIP") {
      setTitle("Employment Verification & Salary Slip Audit");
    } else if (newType === "UTILITY_BILL") {
      setTitle("Utility Consumer Bill Verification (WAPDA / SNGPL / KE)");
    } else if (newType === "TAX_CERTIFICATE") {
      setTitle("FBR Active Taxpayer & Income Tax Return Verification");
    } else if (newType === "IDENTITY_DOCUMENT") {
      setTitle("Identity Credential & Official Document Verification");
    } else {
      setTitle("Official Document Forensics Docket");
    }
  };

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
      setError("Please select a document file for custody acquisition.");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      await loginAnalyst().catch(() => {});

      setStep("1/4: Registering case docket and custody record...");
      const inv = await createInvestigation({
        title,
        notes: `Acquired via DeepTrace Ingestion Gateway (${documentType})`,
      });

      setStep("2/4: Uploading document & rendering 150 DPI canvas pages...");
      const doc = await uploadDocument(inv.id, file, documentType);

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
          "Failed to ingest document. Please verify the backend API server is running on port 8000."
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
          Document Intake & Custody Lock
        </h1>

        <p className="text-sm md:text-base text-ink-700 leading-relaxed max-w-2xl">
          Ingested documents are immediately cryptographically fingerprinted under
          SHA-256, locked against alteration pursuant to Pakistan’s Electronic
          Transactions Ordinance (ETO 2002), and rasterized at 150 DPI for
          sub-pixel forensic inspection.
        </p>

        <HairlineRule className="my-8" />

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Document Type Selector */}
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider text-ink-700 mb-2">
              Document Category & Forensic Module:
            </label>
            <select
              value={documentType}
              onChange={(e) => handleDocTypeChange(e.target.value)}
              className="w-full bg-paper-1 border border-rule px-4 py-3 text-sm text-ink-900 font-mono focus:outline-none focus:border-ink-900 cursor-pointer"
            >
              <option value="AUTO">⚡ Auto-Detect via Stage 0 Classifier (Bank, Salary, K-Electric, FBR, CNIC)</option>
              <option value="OTHER">Academic & Educational (Matric / Inter / University Degree / BISE)</option>
              <option value="BANK_STATEMENT">Bank Statement & Financial Ledger (Lakh/Crore & IBAN)</option>
              <option value="SALARY_SLIP">Salary Slip & Employment Certificate</option>
              <option value="UTILITY_BILL">Utility Consumer Bill (Electricity / Gas / Water)</option>
              <option value="TAX_CERTIFICATE">Tax Certificate & FBR Return</option>
              <option value="IDENTITY_DOCUMENT">Identity Document & Official Credential</option>
              <option value="COMMERCIAL_INVOICE">Commercial Invoice & Trade Bill</option>
            </select>
          </div>

          {/* Case Title Input */}
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider text-ink-700 mb-2">
              Case Docket Title:
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-paper-1 border border-rule px-4 py-3 text-sm text-ink-900 font-serif focus:outline-none focus:border-ink-900"
            />
          </div>

          {/* Drag & Drop Custody Area */}
          <div>
            <label className="block font-mono text-xs uppercase tracking-wider text-ink-700 mb-2">
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
            <div className="bg-forensic-red/10 border border-forensic-red/40 p-3 font-mono text-xs text-forensic-red">
              {error}
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
              {isProcessing ? "Processing Custody Lock..." : "Seal & Analyze Document →"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
