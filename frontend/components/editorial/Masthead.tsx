"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ChevronDown, Building2, LogOut, User, Check, RefreshCw, ShieldCheck } from "lucide-react";
import { TwoFactorSetupModal } from "@/components/auth/TwoFactorSetupModal";

interface MastheadProps {
  caseNumber?: string;
  caseTitle?: string;
  orgName?: string;
  documentType?: string;
}

export function Masthead({
  caseNumber,
  caseTitle,
  orgName: initialOrgName,
  documentType = "GENERAL_DOCUMENT",
}: MastheadProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, activeOrg, organizations, switchOrg, logout, isAuthenticated } = useAuth();

  const [timeStr, setTimeStr] = useState<string>("");
  const [orgDropdownOpen, setOrgDropdownOpen] = useState<boolean>(false);
  const [switching, setSwitching] = useState<boolean>(false);
  const [mfaModalOpen, setMfaModalOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOrgDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleOrgSwitch = async (orgId: string) => {
    if (activeOrg?.id === orgId) {
      setOrgDropdownOpen(false);
      return;
    }
    setSwitching(true);
    try {
      await switchOrg(orgId);
      setOrgDropdownOpen(false);
      // Refresh current page to re-scope queries under new RLS context
      router.refresh();
    } catch (err) {
      console.error("Failed to switch organization:", err);
    } finally {
      setSwitching(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const displayOrgName = activeOrg?.name || initialOrgName || "National Document Forensics Directorate";

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
          {/* Multi-Tenant Switcher Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setOrgDropdownOpen(!orgDropdownOpen)}
              className="flex items-center gap-1.5 text-ink-800 hover:text-ink-900 font-medium px-2 py-0.5 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 transition-colors cursor-pointer"
            >
              <Building2 className="w-3 h-3 text-ink-600" />
              <span>{displayOrgName}</span>
              {switching ? (
                <RefreshCw className="w-2.5 h-2.5 animate-spin" />
              ) : (
                <ChevronDown className="w-3 h-3 opacity-60" />
              )}
            </button>

            {orgDropdownOpen && (
              <div className="absolute right-0 mt-1 w-64 bg-paper-0 border-2 border-ink-900 shadow-xl z-50 py-1 font-mono text-[11px]">
                <div className="px-3 py-1.5 border-b border-rule text-[10px] text-ink-500 uppercase tracking-wider font-semibold">
                  Switch Banking Tenant:
                </div>
                {organizations.length > 0 ? (
                  organizations.map((org) => (
                    <button
                      key={org.id}
                      type="button"
                      onClick={() => handleOrgSwitch(org.id)}
                      className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-paper-2 transition-colors ${
                        activeOrg?.id === org.id ? "bg-amber-50 font-bold text-ink-900" : "text-ink-700"
                      }`}
                    >
                      <div className="truncate pr-2">
                        <div className="truncate">{org.name}</div>
                        <div className="text-[9px] text-ink-500">{org.slug}</div>
                      </div>
                      {activeOrg?.id === org.id && (
                        <Check className="w-3.5 h-3.5 text-forensic-green shrink-0" />
                      )}
                    </button>
                  ))
                ) : (
                  <div className="px-3 py-2 text-ink-500 italic">No alternative tenants</div>
                )}
              </div>
            )}
          </div>

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

        {/* Navigation & User Profile / Logout */}
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
          {(user?.role === "ADMIN" || user?.role === "OWNER") && (
            <Link
              href="/settings/api-keys"
              className={`transition-colors hover:text-ink-900 pb-1 border-b-2 ${
                pathname.startsWith("/settings/api-keys")
                  ? "border-ink-900 text-ink-900 font-semibold"
                  : "border-transparent text-ink-500"
              }`}
            >
              API Keys
            </Link>
          )}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-ink-500 hover:text-ink-900 transition-colors hidden sm:inline"
          >
            API Docs ↗
          </a>

          {/* User Profile / Logout Trigger */}
          {isAuthenticated && user ? (
            <div className="flex items-center gap-3 pl-4 border-l border-rule">
              <div className="hidden lg:flex flex-col text-right">
                <span className="text-[11px] font-semibold text-ink-900 lowercase tracking-normal">
                  {user.email}
                </span>
                <span className="text-[9px] text-ink-500 uppercase tracking-wider">
                  [{user.role}]
                </span>
              </div>

              {/* Interactive 2FA Configuration Trigger */}
              <button
                type="button"
                onClick={() => setMfaModalOpen(true)}
                className={`px-2 py-1 border text-[10px] font-mono uppercase font-semibold tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer ${
                  user.mfa_enabled
                    ? "border-emerald-600 text-emerald-700 bg-emerald-50 hover:bg-emerald-100"
                    : "border-rule text-ink-700 bg-paper-1 hover:border-ink-900 hover:bg-paper-2"
                }`}
                title="Manage Real Two-Factor Authentication (2FA) for your account"
              >
                <ShieldCheck className={`w-3 h-3 ${user.mfa_enabled ? "text-emerald-600" : "text-ink-500"}`} />
                <span>{user.mfa_enabled ? "2FA: ENFORCED" : "2FA: SETUP"}</span>
              </button>

              <button
                type="button"
                onClick={handleLogout}
                className="px-2.5 py-1 bg-paper-1 hover:bg-paper-2 border border-rule hover:border-ink-900 text-ink-700 hover:text-ink-900 text-[10px] uppercase font-semibold tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Terminate authenticated session (revokes refresh token)"
              >
                <LogOut className="w-3 h-3" />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="px-3 py-1 bg-ink-900 text-paper-0 hover:bg-black text-[10px] uppercase font-semibold tracking-wider transition-colors"
            >
              Sign In
            </Link>
          )}
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
            ) : documentType === "UTILITY_BILL" ? (
              <>
                <span>UTILITY TARIFF AUDIT: ENFORCED</span>
                <span>•</span>
                <span>K-ELECTRIC / BILLING RECONCILIATION: ACTIVE</span>
              </>
            ) : documentType === "SALARY_SLIP" ? (
              <>
                <span>EMPLOYMENT PAYROLL AUDIT: ENFORCED</span>
                <span>•</span>
                <span>DUAL-COLUMN EARNINGS/DEDUCTIONS: ACTIVE</span>
              </>
            ) : documentType === "TAX_CERTIFICATE" ? (
              <>
                <span>FBR CPR PAYMENT RECEIPT: ENFORCED</span>
                <span>•</span>
                <span>NTN TAX REGISTER: ACTIVE</span>
              </>
            ) : documentType === "IDENTITY_DOCUMENT" ? (
              <>
                <span>NADRA CNIC CREDENTIAL: ENFORCED</span>
                <span>•</span>
                <span>ISO/IEC 7810 ID-1 CARD GEOMETRY: ACTIVE</span>
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

      {/* Two-Factor Authentication Setup Modal */}
      <TwoFactorSetupModal
        isOpen={mfaModalOpen}
        onClose={() => setMfaModalOpen(false)}
      />
    </header>
  );
}
