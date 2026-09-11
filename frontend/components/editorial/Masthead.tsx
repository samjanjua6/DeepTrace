"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface MastheadProps {
  caseNumber?: string;
  caseTitle?: string;
  orgName?: string;
  documentType?: string;
}

export function Masthead({
  caseNumber,
  caseTitle,
  orgName = "National Document Forensics Directorate",
  documentType = "GENERAL_DOCUMENT",
}: MastheadProps) {
  const pathname = usePathname();
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        new Intl.DateTimeFormat("en-PK", {
          timeZone: "Asia/Karachi",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }).format(now) + " PKT"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="w-full border-b border-rule bg-paper-0">
      {/* Top micro-bar */}
      <div className="flex items-center justify-between px-6 py-1.5 border-b border-rule/60 text-[11px] font-mono text-ink-500">
        <div className="flex items-center gap-4">
          <span className="font-semibold text-ink-900 tracking-wider">
            DEEPTRACE INSTITUTIONAL
          </span>
          <span className="text-ink-300">|</span>
          <span>NIST SP 800-86 & ETO 2002 STANDARDS</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-ink-700">{orgName}</span>
          <span className="text-ink-300">|</span>
          <span
            suppressHydrationWarning
            className="tabular-nums font-semibold text-ink-900"
          >
            {timeStr || "—"}
          </span>
        </div>
      </div>

      {/* Main Masthead row */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-baseline gap-6">
          <Link href="/" className="group">
            <h1 className="font-serif text-3xl md:text-4xl tracking-tight text-ink-900 font-normal">
              DeepTrace
            </h1>
          </Link>
          <span className="hidden md:inline font-mono text-[10px] tracking-[0.2em] uppercase text-ink-500 border-l border-rule pl-4">
            Document Forensics & Verification API
          </span>
        </div>

        {/* Navigation items */}
        <nav className="flex items-center gap-6 font-mono text-xs uppercase tracking-wider">
          <Link
            href="/investigations"
            className={`transition-colors hover:text-ink-900 pb-1 border-b-2 ${
              pathname.startsWith("/investigations") && !pathname.includes("/new")
                ? "border-ink-900 text-ink-900 font-semibold"
                : "border-transparent text-ink-500"
            }`}
          >
            Case Docket
          </Link>
          <Link
            href="/investigations/new"
            className={`transition-colors hover:text-ink-900 pb-1 border-b-2 ${
              pathname === "/investigations/new"
                ? "border-ink-900 text-ink-900 font-semibold"
                : "border-transparent text-ink-500"
            }`}
          >
            + New Intake
          </Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-ink-500 hover:text-ink-900 transition-colors"
          >
            API Docs ↗
          </a>
        </nav>
      </div>

      {/* Active Case Banner if provided */}
      {caseNumber && (
        <div className="bg-paper-1 px-6 py-2 border-t border-rule flex items-center justify-between flex-wrap gap-2 font-mono text-xs">
          <div className="flex items-center gap-3">
            <span className="text-ink-500">ACTIVE DOCKET:</span>
            <span className="font-semibold text-ink-900 bg-paper-2 px-2 py-0.5 border border-rule">
              {caseNumber}
            </span>
            {caseTitle && (
              <span className="text-ink-700 hidden sm:inline border-l border-rule pl-3 font-serif">
                {caseTitle}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-ink-500 text-[11px]">
            {documentType === "BANK_STATEMENT" ? (
              <>
                <span>SBP CLEARING STANDARD: ENFORCED</span>
                <span>•</span>
                <span>RUNNING BALANCE RECONCILIATION: ACTIVE</span>
              </>
            ) : (
              <>
                <span>NIST SP 800-86 AUDIT: ENFORCED</span>
                <span>•</span>
                <span>SUB-PIXEL GEOMETRY: ACTIVE</span>
                <span>•</span>
                <span>ELA COMPRESSION SCAN: ACTIVE</span>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
