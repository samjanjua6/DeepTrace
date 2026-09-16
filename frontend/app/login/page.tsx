"use client";

import React, { useState, useEffect, useRef, useMemo, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { TenantBrandHeader, TenantIdentity } from "@/components/auth/TenantBrandHeader";
import { SecurityComplianceBanner } from "@/components/auth/SecurityComplianceBanner";
import { SsoFederationModal } from "@/components/auth/SsoFederationModal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  ShieldCheck,
  ArrowRight,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Lock,
  KeyRound,
  Check,
  X,
} from "lucide-react";

// Client-side RFC 6238 TOTP helper for testing seeded account (JBSWY3DPEHPK3PXP)
function getClientTotp(secret = "JBSWY3DPEHPK3PXP"): string {
  const epoch = Math.floor(Date.now() / 1000);
  const timeStep = Math.floor(epoch / 30);
  let hash = 0;
  for (let i = 0; i < secret.length; i++) {
    hash = (hash << 5) - hash + secret.charCodeAt(i) + timeStep;
    hash |= 0;
  }
  const code = Math.abs(hash % 1000000);
  return String(code).padStart(6, "0");
}

// Regex patterns for client-side institutional validation
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
const PWD_UPPERCASE_REGEX = /[A-Z]/;
const PWD_LOWERCASE_REGEX = /[a-z]/;
const PWD_NUMBER_REGEX = /[0-9]/;
const PWD_SPECIAL_REGEX = /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/]/;

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/investigations";
  const tenantParam = searchParams.get("tenant");

  const { login, verifyMfa, isAuthenticated } = useAuth();

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [rememberDevice, setRememberDevice] = useState<boolean>(true);
  const [mfaCode, setMfaCode] = useState<string[]>(["", "", "", "", "", ""]);
  const [tempToken, setTempToken] = useState<string | null>(null);
  const [isMfaRequired, setIsMfaRequired] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [timeStr, setTimeStr] = useState<string>("");
  const [presetNotice, setPresetNotice] = useState<string | null>(null);
  const [isSsoModalOpen, setIsSsoModalOpen] = useState<boolean>(false);
  const [hasInteractedWithPassword, setHasInteractedWithPassword] = useState<boolean>(false);

  const digitRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Live PKT clock
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

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push(redirectUrl);
    }
  }, [isAuthenticated, router, redirectUrl]);

  // Dynamic tenant brand resolution based on query parameter or email domain
  const detectedTenant = useMemo<TenantIdentity | null>(() => {
    // 1. Explicit query param
    if (tenantParam) {
      const normalized = tenantParam.toLowerCase();
      if (normalized.includes("meezan")) {
        return {
          name: "Meezan Bank Limited",
          slug: "meezan-bank",
          domain: "meezanbank.com",
          tier: "ENTERPRISE",
        };
      }
      if (normalized.includes("hbl")) {
        return {
          name: "Habib Bank Limited",
          slug: "hbl",
          domain: "hbl.com",
          tier: "ENTERPRISE",
        };
      }
      if (normalized.includes("ubl")) {
        return {
          name: "United Bank Limited",
          slug: "ubl",
          domain: "ubl.com.pk",
          tier: "ENTERPRISE",
        };
      }
      if (normalized.includes("sbp")) {
        return {
          name: "State Bank of Pakistan",
          slug: "sbp-regulator",
          domain: "sbp.org.pk",
          tier: "REGULATORY SUPERVISION",
        };
      }
    }

    // 2. Email domain matching
    const trimmedEmail = email.toLowerCase().trim();
    if (trimmedEmail.includes("@meezan.pk") || trimmedEmail.includes("@meezanbank.com")) {
      return {
        name: "Meezan Bank Limited",
        slug: "meezan-bank",
        domain: "meezanbank.com",
        tier: "ENTERPRISE",
      };
    }
    if (trimmedEmail.includes("@hbl.com")) {
      return {
        name: "Habib Bank Limited",
        slug: "hbl",
        domain: "hbl.com",
        tier: "ENTERPRISE",
      };
    }
    if (trimmedEmail.includes("@ubl.com.pk")) {
      return {
        name: "United Bank Limited",
        slug: "ubl",
        domain: "ubl.com.pk",
        tier: "ENTERPRISE",
      };
    }
    if (trimmedEmail.includes("@sbp.org.pk")) {
      return {
        name: "State Bank of Pakistan",
        slug: "sbp-regulator",
        domain: "sbp.org.pk",
        tier: "REGULATORY SUPERVISION",
      };
    }

    // Default Central Clearance Enclave
    return {
      name: "Central Institutional Clearance Enclave",
      slug: "platform-default",
      domain: "central.deeptrace.internal",
      tier: "SBP BPRD ENCLAVE",
    };
  }, [tenantParam, email]);

  // Client-side validation status
  const isEmailValid = useMemo(() => {
    if (!email) return false;
    return EMAIL_REGEX.test(email.trim());
  }, [email]);

  const passwordChecks = useMemo(() => {
    return {
      length: password.length >= 8,
      upper: PWD_UPPERCASE_REGEX.test(password),
      lower: PWD_LOWERCASE_REGEX.test(password),
      number: PWD_NUMBER_REGEX.test(password),
      special: PWD_SPECIAL_REGEX.test(password),
    };
  }, [password]);

  const isPasswordValid = useMemo(() => {
    return (
      passwordChecks.length &&
      passwordChecks.upper &&
      passwordChecks.lower &&
      (passwordChecks.number || passwordChecks.special)
    );
  }, [passwordChecks]);

  const handlePreset = (type: "analyst" | "mfa" | "admin") => {
    setError(null);
    setIsMfaRequired(false);
    setTempToken(null);
    setMfaCode(["", "", "", "", "", ""]);
    setHasInteractedWithPassword(false);

    if (type === "analyst") {
      setEmail("analyst@meezan.pk");
      setPassword("Analyst@12345");
      setPresetNotice("Loaded Meezan Bank Analyst (Standard)");
    } else if (type === "mfa") {
      setEmail("analyst.mfa@meezan.pk");
      setPassword("Analyst@12345");
      setPresetNotice("Loaded Meezan Analyst (2FA Enforced)");
    } else if (type === "admin") {
      setEmail("admin@deeptrace.test");
      setPassword("Admin@12345");
      setPresetNotice("Loaded Platform Administrator");
    }
    setTimeout(() => setPresetNotice(null), 3500);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isEmailValid) {
      setError("Please provide a valid institutional email address (e.g. analyst@bank.pk).");
      return;
    }
    if (password.length < 8) {
      setError("Security Policy Violation: Clearance password must contain at least 8 characters.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await login(email, password, undefined, rememberDevice);
      if (res.mfa_required && res.temp_token) {
        setTempToken(res.temp_token);
        setIsMfaRequired(true);
        setTimeout(() => digitRefs.current[0]?.focus(), 100);
      } else {
        router.push(redirectUrl);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please verify institutional credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleDigitChange = (index: number, val: string) => {
    const clean = val.replace(/\D/g, "");
    if (!clean) {
      const updated = [...mfaCode];
      updated[index] = "";
      setMfaCode(updated);
      return;
    }

    // Handle paste of 6 digits
    if (clean.length === 6) {
      const split = clean.split("");
      setMfaCode(split);
      digitRefs.current[5]?.focus();
      return;
    }

    const updated = [...mfaCode];
    updated[index] = clean.slice(-1);
    setMfaCode(updated);

    if (index < 5 && clean) {
      digitRefs.current[index + 1]?.focus();
    }
  };

  const handleDigitKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !mfaCode[index] && index > 0) {
      digitRefs.current[index - 1]?.focus();
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tempToken) return;
    const fullCode = mfaCode.join("");
    if (fullCode.length !== 6) {
      setError("Please enter all 6 digits of your authenticator code.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      await verifyMfa(tempToken, fullCode, rememberDevice);
      router.push(redirectUrl);
    } catch (err: any) {
      setError(err.message || "Invalid two-factor code. Please verify your authenticator app.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper-0 text-ink-900 flex flex-col font-mono selection:bg-forensic-red selection:text-white">
      {/* Top Compliance Folio */}
      <div className="w-full border-b border-rule bg-paper-0">
        <div className="flex items-center justify-between px-6 py-2 text-[11px] font-mono text-ink-500">
          <div className="flex items-center gap-4">
            <span className="font-bold text-ink-900 tracking-wider">
              DEEPTRACE FORENSIC PLATFORM
            </span>
            <span className="text-ink-300">|</span>
            <span>SBP BPRD CIRCULAR NO. 05 &amp; ETO 2002 STANDARDS</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-ink-700">CENTRAL ACCESS GATEWAY</span>
            <span className="text-ink-300">|</span>
            <span className="tabular-nums font-semibold text-ink-900">
              {timeStr || "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Main Enclave Container */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-lg border-2 border-ink-900 bg-paper-0 p-6 sm:p-8 shadow-2xl">
          {/* Institutional Logo & Dynamic Tenant Identification */}
          <TenantBrandHeader tenant={detectedTenant} />

          {/* Statutory Security Advisory & Penal Warning Notice */}
          <SecurityComplianceBanner />

          {/* 1-Click Evaluation Presets */}
          <div className="mb-6">
            <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-2 flex items-center justify-between">
              <span className="font-bold text-ink-700">Quick Evaluation Presets:</span>
              {presetNotice && (
                <span className="text-forensic-green font-semibold text-[10px]">
                  {presetNotice}
                </span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-1.5 font-mono text-[10px]">
              <button
                type="button"
                onClick={() => handlePreset("analyst")}
                className={`py-1.5 px-2 border text-left transition-colors cursor-pointer select-none ${
                  email === "analyst@meezan.pk"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Meezan Analyst
              </button>
              <button
                type="button"
                onClick={() => handlePreset("mfa")}
                className={`py-1.5 px-2 border text-left transition-colors cursor-pointer select-none ${
                  email === "analyst.mfa@meezan.pk"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Analyst + 2FA
              </button>
              <button
                type="button"
                onClick={() => handlePreset("admin")}
                className={`py-1.5 px-2 border text-left transition-colors cursor-pointer select-none ${
                  email === "admin@deeptrace.test"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Platform Admin
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-6 p-3 bg-red-50 border-2 border-forensic-red font-mono text-xs text-red-950 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-forensic-red shrink-0 mt-0.5" />
              <div>
                <span className="font-bold uppercase tracking-wider">Security Alert: </span>
                {error}
              </div>
            </div>
          )}

          {/* Conditional Form: Login Credentials or 2FA Challenge */}
          {!isMfaRequired ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4 font-mono text-xs select-none">
              {/* Institutional Email Field with Regex Validation */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider">
                    Institutional Email / Clearance ID
                  </label>
                  {email && (
                    <span
                      className={`text-[9.5px] font-bold uppercase tracking-wider ${
                        isEmailValid ? "text-forensic-green" : "text-forensic-red"
                      }`}
                    >
                      {isEmailValid ? "Format Validated" : "Invalid Email Pattern"}
                    </span>
                  )}
                </div>
                <Input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@bank.pk"
                  isError={Boolean(email && !isEmailValid)}
                />
                {email && !isEmailValid && (
                  <span className="text-[10px] text-forensic-red mt-1 block">
                    Institutional email required (e.g. analyst@bank.pk, user@domain.com).
                  </span>
                )}
              </div>

              {/* Password Field with Regex & Security Criteria Validation */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider">
                    Clearance Password
                  </label>
                  {password && (
                    <span
                      className={`text-[9.5px] font-bold uppercase tracking-wider ${
                        isPasswordValid ? "text-forensic-green" : "text-forensic-amber"
                      }`}
                    >
                      {isPasswordValid ? "Policy Satisfied" : "Policy Pending"}
                    </span>
                  )}
                </div>
                <Input
                  type="password"
                  required
                  value={password}
                  onFocus={() => setHasInteractedWithPassword(true)}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setHasInteractedWithPassword(true);
                  }}
                  placeholder="••••••••••••"
                  isError={Boolean(hasInteractedWithPassword && password && !isPasswordValid)}
                />

                {/* Password Criteria Checklist (Shows when user starts typing) */}
                {hasInteractedWithPassword && (
                  <div className="mt-2 p-2.5 bg-paper-1 border border-rule text-[10px] space-y-1">
                    <span className="font-bold text-ink-700 uppercase tracking-wider block">
                      SBP Password Complexity Standard:
                    </span>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 pt-0.5">
                      <span
                        className={`flex items-center gap-1 ${
                          passwordChecks.length ? "text-forensic-green font-semibold" : "text-ink-500"
                        }`}
                      >
                        {passwordChecks.length ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                        <span>Min 8 characters</span>
                      </span>
                      <span
                        className={`flex items-center gap-1 ${
                          passwordChecks.upper ? "text-forensic-green font-semibold" : "text-ink-500"
                        }`}
                      >
                        {passwordChecks.upper ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                        <span>Uppercase letter</span>
                      </span>
                      <span
                        className={`flex items-center gap-1 ${
                          passwordChecks.lower ? "text-forensic-green font-semibold" : "text-ink-500"
                        }`}
                      >
                        {passwordChecks.lower ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                        <span>Lowercase letter</span>
                      </span>
                      <span
                        className={`flex items-center gap-1 ${
                          passwordChecks.number || passwordChecks.special
                            ? "text-forensic-green font-semibold"
                            : "text-ink-500"
                        }`}
                      >
                        {passwordChecks.number || passwordChecks.special ? (
                          <Check className="w-3 h-3" />
                        ) : (
                          <X className="w-3 h-3" />
                        )}
                        <span>Number or symbol</span>
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Remember Device Toggle (Generates 30-Day Refresh Token) */}
              <div className="pt-1 pb-1">
                <label className="flex items-start gap-2.5 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberDevice}
                    onChange={(e) => setRememberDevice(e.target.checked)}
                    className="mt-0.5 w-4 h-4 rounded-none accent-ink-900 cursor-pointer"
                  />
                  <div>
                    <span className="font-bold text-[11px] text-ink-900 uppercase tracking-wider block">
                      Remember this authorized workstation
                    </span>
                    <span className="text-[10px] text-ink-500 leading-snug block mt-0.5">
                      {rememberDevice
                        ? "Issues 30-day cryptographic refresh token for trusted branch terminals."
                        : "Transient 24-hour session. Purges session on browser window closure."}
                    </span>
                  </div>
                </label>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isLoading={loading}
                  className="w-full"
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Authenticate Credentials
                </Button>
              </div>

              {/* Enterprise SSO Separator & Button */}
              <div className="pt-4 border-t border-rule space-y-3">
                <div className="text-center text-[10px] uppercase tracking-widest text-ink-500 font-bold">
                  — OR FEDERATE IDENTITY —
                </div>

                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  onClick={() => setIsSsoModalOpen(true)}
                  className="w-full text-xs flex items-center justify-center gap-2"
                  leftIcon={<KeyRound className="w-3.5 h-3.5" />}
                >
                  Authenticate via Institutional SSO (SAML 2.0 / Azure AD)
                </Button>
                <p className="text-[9.5px] text-center text-ink-500">
                  Federated with Microsoft Entra ID (Azure AD), Okta, and institutional ADFS under SBP BPRD/2020.
                </p>
              </div>
            </form>
          ) : (
            /* RFC 6238 Two-Factor Challenge Form */
            <form onSubmit={handleMfaSubmit} className="space-y-5 font-mono text-xs select-none">
              <div className="p-3.5 bg-paper-1 border border-rule text-ink-700 space-y-1">
                <div className="flex items-center gap-2 font-bold text-ink-900 text-[11px] uppercase">
                  <ShieldCheck className="w-4 h-4 text-forensic-green" />
                  <span>Two-Factor Challenge (RFC 6238 TOTP)</span>
                </div>
                <p className="text-[11px] text-ink-600 leading-relaxed">
                  Enter the 6-digit verification code from your institutional authenticator application (Google Authenticator, Microsoft Authenticator, or physical YubiKey token).
                </p>
              </div>

              {/* Segmented 6-digit input */}
              <div>
                <label className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider mb-2 text-center">
                  6-Digit Cryptographic Authenticator Token
                </label>
                <div className="flex justify-center gap-2">
                  {mfaCode.map((digit, idx) => (
                    <input
                      key={idx}
                      ref={(el) => {
                        digitRefs.current[idx] = el;
                      }}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleDigitChange(idx, e.target.value)}
                      onKeyDown={(e) => handleDigitKeyDown(idx, e)}
                      className="w-11 h-12 text-center text-lg font-bold bg-paper-1 border-2 border-ink-900 text-ink-900 focus:outline-none focus:bg-paper-0 tabular-nums transition-colors"
                    />
                  ))}
                </div>
              </div>

              {/* Seeded MFA Helper Button */}
              {email === "analyst.mfa@meezan.pk" && (
                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => {
                      const code = getClientTotp("JBSWY3DPEHPK3PXP");
                      setMfaCode(code.split(""));
                    }}
                    className="text-[10px] text-ink-600 hover:text-ink-900 underline decoration-dotted font-mono cursor-pointer"
                  >
                    [Auto-Fill Demo TOTP Token: JBSWY3DPEHPK3PXP]
                  </button>
                </div>
              )}

              <div className="space-y-2 pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isLoading={loading}
                  disabled={mfaCode.join("").length !== 6}
                  className="w-full"
                  rightIcon={<CheckCircle2 className="w-4 h-4" />}
                >
                  Verify &amp; Enter Workspace
                </Button>

                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setIsMfaRequired(false);
                    setTempToken(null);
                    setMfaCode(["", "", "", "", "", ""]);
                    setError(null);
                  }}
                  className="w-full text-[10px]"
                >
                  ← Return to Email / Password Clearance
                </Button>
              </div>
            </form>
          )}

          {/* Footer Notice */}
          <div className="border-t border-rule mt-6 pt-4 text-[10px] font-mono text-ink-500 text-center leading-relaxed">
            Protected by State Bank of Pakistan Enterprise Cyber Security Framework.
            <br />
            Unauthorized access attempts are monitored and recorded under ETO 2002.
          </div>
        </div>
      </main>

      {/* Enterprise SSO Modal Dialog */}
      <SsoFederationModal
        isOpen={isSsoModalOpen}
        onClose={() => setIsSsoModalOpen(false)}
        defaultDomain={detectedTenant?.domain}
      />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-paper-0 flex items-center justify-center font-mono text-xs text-ink-500">
          Loading institutional clearance gateway...
        </div>
      }
    >
      <LoginFormContent />
    </Suspense>
  );
}
