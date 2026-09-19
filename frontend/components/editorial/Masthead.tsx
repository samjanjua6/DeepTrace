"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  ChevronDown,
  Building2,
  LogOut,
  Check,
  RefreshCw,
  ShieldCheck,
  Menu,
  X,
} from "lucide-react";
import { TwoFactorSetupModal } from "@/components/auth/TwoFactorSetupModal";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const drawerRef = useFocusTrap<HTMLDivElement>(mobileMenuOpen);

  // Clock ticker
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

  // Close org dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOrgDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Body scroll lock when mobile drawer is open
  useEffect(() => {
    document.body.style.overflow = mobileMenuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileMenuOpen]);

  // Escape key closes mobile drawer
  useEffect(() => {
    if (!mobileMenuOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [mobileMenuOpen]);

  const handleOrgSwitch = async (orgId: string) => {
    if (activeOrg?.id === orgId) {
      setOrgDropdownOpen(false);
      return;
    }
    setSwitching(true);
    try {
      await switchOrg(orgId);
      setOrgDropdownOpen(false);
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

  // Shared nav link class helper
  const navLinkClass = (active: boolean) =>
    `transition-colors hover:text-ink-900 pb-1 border-b-2 ${
      active
        ? "border-ink-900 text-ink-900 font-semibold"
        : "border-transparent text-ink-500"
    }`;

  return (
    <header className="w-full border-b border-rule bg-paper-0">
      {/* Top micro-bar */}
      <div className="flex items-center justify-between px-6 py-1.5 border-b border-rule/60 text-[11px] font-mono text-ink-500">
        <div className="flex items-center gap-4">
          <span className="font-semibold text-ink-900 tracking-wider">
            DEEPTRACE INSTITUTIONAL
          </span>
          <span className="text-ink-300">|</span>
          <span className="hidden sm:inline">NIST SP 800-86 &amp; ETO 2002 STANDARDS</span>
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
              <span className="hidden sm:inline">{displayOrgName}</span>
              <span className="sm:hidden">Org</span>
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

          <span className="text-ink-300 hidden sm:inline">|</span>
          <span
            suppressHydrationWarning
            className="tabular-nums font-semibold text-ink-900 hidden sm:inline"
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
            Document Forensics &amp; Verification API
          </span>
        </div>

        {/* Desktop Navigation */}
        <nav
          aria-label="Main navigation"
          className="hidden md:flex items-center gap-6 font-mono text-xs uppercase tracking-wider"
        >
          <Link
            href={isAuthenticated ? "/dashboard" : "/login?redirect=/dashboard"}
            className={navLinkClass(pathname === "/dashboard")}
          >
            Dashboard
          </Link>
          <Link
            href={isAuthenticated ? "/investigations" : "/login?redirect=/investigations"}
            className={navLinkClass(
              pathname.startsWith("/investigations") && !pathname.includes("/new")
            )}
          >
            Case Docket
          </Link>
          <Link
            href={isAuthenticated ? "/investigations/new" : "/login?redirect=/investigations/new"}
            className={navLinkClass(pathname === "/investigations/new")}
          >
            + New Intake
          </Link>
          {(user?.role === "ADMIN" || user?.role === "OWNER") && (
            <>
              <Link href="/settings/users" className={navLinkClass(pathname.startsWith("/settings/users"))}>
                Users
              </Link>
              <Link href="/settings/api-keys" className={navLinkClass(pathname.startsWith("/settings/api-keys"))}>
                API Keys
              </Link>
              <Link href="/settings/webhooks" className={navLinkClass(pathname.startsWith("/settings/webhooks"))}>
                Webhooks
              </Link>
              <Link href="/settings/billing" className={navLinkClass(pathname.startsWith("/settings/billing"))}>
                Billing
              </Link>
            </>
          )}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-ink-500 hover:text-ink-900 transition-colors"
          >
            API Docs ↗
          </a>

          {/* User Profile / Logout */}
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

              <button
                type="button"
                onClick={() => setMfaModalOpen(true)}
                className={`px-2 py-1 border text-[10px] font-mono uppercase font-semibold tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer ${
                  user.mfa_enabled
                    ? "border-emerald-600 text-emerald-700 bg-emerald-50 hover:bg-emerald-100"
                    : "border-rule text-ink-700 bg-paper-1 hover:border-ink-900 hover:bg-paper-2"
                }`}
                title="Manage Two-Factor Authentication (2FA) for your account"
              >
                <ShieldCheck className={`w-3 h-3 ${user.mfa_enabled ? "text-emerald-600" : "text-ink-500"}`} />
                <span>{user.mfa_enabled ? "2FA: ENFORCED" : "2FA: SETUP"}</span>
              </button>

              <button
                type="button"
                onClick={handleLogout}
                className="px-2.5 py-1 bg-paper-1 hover:bg-paper-2 border border-rule hover:border-ink-900 text-ink-700 hover:text-ink-900 text-[10px] uppercase font-semibold tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Terminate authenticated session"
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

        {/* Mobile hamburger button — visible below md breakpoint */}
        <button
          type="button"
          className="md:hidden p-2 text-ink-700 hover:text-ink-900 hover:bg-paper-1 border border-transparent hover:border-rule transition-colors"
          onClick={() => setMobileMenuOpen(true)}
          aria-label="Open navigation menu"
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-nav-drawer"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile Slide-out Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60"
            aria-hidden="true"
            onClick={() => setMobileMenuOpen(false)}
          />

          {/* Drawer panel */}
          <div
            id="mobile-nav-drawer"
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            className="absolute inset-y-0 right-0 w-72 bg-paper-0 border-l-2 border-ink-900 shadow-2xl flex flex-col overflow-y-auto"
          >
            {/* Drawer header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-rule">
              <span className="font-serif text-xl text-ink-900 font-normal">DeepTrace</span>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="p-1 text-ink-500 hover:text-ink-900 transition-colors"
                aria-label="Close navigation menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Nav links */}
            <nav aria-label="Mobile navigation" className="flex flex-col font-mono text-xs uppercase tracking-wider py-4">
              <Link
                href={isAuthenticated ? "/dashboard" : "/login?redirect=/dashboard"}
                className={`px-5 py-3 border-l-4 hover:bg-paper-1 transition-colors ${
                  pathname === "/dashboard"
                    ? "border-ink-900 text-ink-900 font-semibold bg-paper-1"
                    : "border-transparent text-ink-600"
                }`}
              >
                Dashboard
              </Link>
              <Link
                href={isAuthenticated ? "/investigations" : "/login?redirect=/investigations"}
                className={`px-5 py-3 border-l-4 hover:bg-paper-1 transition-colors ${
                  pathname.startsWith("/investigations") && !pathname.includes("/new")
                    ? "border-ink-900 text-ink-900 font-semibold bg-paper-1"
                    : "border-transparent text-ink-600"
                }`}
              >
                Case Docket
              </Link>
              <Link
                href={isAuthenticated ? "/investigations/new" : "/login?redirect=/investigations/new"}
                className={`px-5 py-3 border-l-4 hover:bg-paper-1 transition-colors ${
                  pathname === "/investigations/new"
                    ? "border-ink-900 text-ink-900 font-semibold bg-paper-1"
                    : "border-transparent text-ink-600"
                }`}
              >
                + New Intake
              </Link>

              {(user?.role === "ADMIN" || user?.role === "OWNER") && (
                <>
                  <div className="px-5 pt-3 pb-1 text-[10px] text-ink-400 uppercase tracking-widest border-t border-rule mt-2">
                    Administration
                  </div>
                  <Link
                    href="/settings/users"
                    className={`px-5 py-3 border-l-4 hover:bg-paper-1 transition-colors ${
                      pathname.startsWith("/settings/users")
                        ? "border-ink-900 text-ink-900 font-semibold bg-paper-1"
                        : "border-transparent text-ink-600"
                    }`}
                  >
                    Users
                  </Link>
                  <Link
                    href="/settings/api-keys"
                    className={`px-5 py-3 border-l-4 hover:bg-paper-1 transition-colors ${
                      pathname.startsWith("/settings/api-keys")
                        ? "border-ink-900 text-ink-900 font-semibold bg-paper-1"
                        : "border-transparent text-ink-600"
                    }`}
                  >
                    API Keys
                  </Link>
                  <Link
                    href="/settings/webhooks"
                    className={`px-5 py-3 border-l-4 hover:bg-paper-1 transition-colors ${
                      pathname.startsWith("/settings/webhooks")
                        ? "border-ink-900 text-ink-900 font-semibold bg-paper-1"
                        : "border-transparent text-ink-600"
                    }`}
                  >
                    Webhooks
                  </Link>
                  <Link
                    href="/settings/billing"
                    className={`px-5 py-3 border-l-4 hover:bg-paper-1 transition-colors ${
                      pathname.startsWith("/settings/billing")
                        ? "border-ink-900 text-ink-900 font-semibold bg-paper-1"
                        : "border-transparent text-ink-600"
                    }`}
                  >
                    Billing
                  </Link>
                </>
              )}

              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                className="px-5 py-3 border-l-4 border-transparent text-ink-600 hover:bg-paper-1 transition-colors"
              >
                API Docs ↗
              </a>
            </nav>

            {/* User info & actions */}
            {isAuthenticated && user && (
              <div className="mt-auto border-t border-rule p-5 space-y-3">
                <div className="font-mono text-[11px]">
                  <div className="font-semibold text-ink-900 lowercase">{user.email}</div>
                  <div className="text-[9px] text-ink-500 uppercase tracking-wider mt-0.5">[{user.role}]</div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    setMfaModalOpen(true);
                  }}
                  className={`w-full px-3 py-2 border text-[10px] font-mono uppercase font-semibold tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer ${
                    user.mfa_enabled
                      ? "border-emerald-600 text-emerald-700 bg-emerald-50"
                      : "border-rule text-ink-700 bg-paper-1 hover:border-ink-900"
                  }`}
                >
                  <ShieldCheck className={`w-3 h-3 ${user.mfa_enabled ? "text-emerald-600" : "text-ink-500"}`} />
                  <span>{user.mfa_enabled ? "2FA: ENFORCED" : "2FA: SETUP"}</span>
                </button>

                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full px-3 py-2 bg-paper-1 hover:bg-paper-2 border border-rule hover:border-ink-900 text-ink-700 hover:text-ink-900 text-[10px] uppercase font-semibold tracking-wider flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                >
                  <LogOut className="w-3 h-3" />
                  <span>Logout</span>
                </button>
              </div>
            )}

            {!isAuthenticated && (
              <div className="mt-auto border-t border-rule p-5">
                <Link
                  href="/login"
                  className="block w-full text-center px-3 py-2 bg-ink-900 text-paper-0 hover:bg-black text-[10px] uppercase font-semibold tracking-wider transition-colors font-mono"
                >
                  Sign In
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

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
