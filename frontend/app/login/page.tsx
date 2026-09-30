"use client";

import React, { useState, useEffect, useRef, useMemo, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { TenantBrandHeader, TenantIdentity } from "@/components/auth/TenantBrandHeader";
import { SsoFederationModal } from "@/components/auth/SsoFederationModal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  ShieldCheck,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  KeyRound,
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

const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

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
      name: "DeepTrace Forensic Platform",
      slug: "platform-default",
      domain: "central.deeptrace.internal",
      tier: "CENTRAL",
    };
  }, [tenantParam, email]);

  const handlePreset = (type: "analyst" | "admin") => {
    setError(null);
    setIsMfaRequired(false);
    setTempToken(null);
    setMfaCode(["", "", "", "", "", ""]);

    if (type === "analyst") {
      setEmail("analyst@meezan.pk");
      setPassword("Analyst@12345");
      setPresetNotice("Loaded Meezan Analyst");
    } else if (type === "admin") {
      setEmail("admin@deeptrace.test");
      setPassword("Admin@12345");
      setPresetNotice("Loaded Platform Admin");
    }
    setTimeout(() => setPresetNotice(null), 3000);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !EMAIL_REGEX.test(email.trim())) {
      setError("Please provide a valid institutional email address.");
      return;
    }
    if (!password) {
      setError("Please enter your password.");
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
      setError(err.message || "Authentication failed. Please verify credentials.");
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
    <div className="min-h-[100dvh] bg-paper-0 text-ink-900 flex flex-col font-mono selection:bg-forensic-red selection:text-white">
      {/* Top Compliance Folio */}
      <div className="w-full border-b border-rule bg-paper-0">
        <div className="flex items-center justify-between px-6 py-2 text-[11px] font-mono text-ink-500">
          <div className="flex items-center gap-3">
            <span className="font-bold text-ink-900 tracking-wider">
              DEEPTRACE FORENSICS
            </span>
            <span className="text-rule-dark">|</span>
            <span className="hidden sm:inline">SBP BPRD ALIGNED ACCESS GATEWAY</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline text-ink-600">PKT TIME</span>
            <span className="tabular-nums font-semibold text-ink-900">
              {timeStr || "—"}
            </span>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6">
        <div className="w-full max-w-md border border-ink-900/30 bg-paper-0 p-6 sm:p-8 shadow-sm">
          {/* Institutional Logo & Dynamic Tenant Identification */}
          <TenantBrandHeader tenant={detectedTenant} />

          {/* Quick Presets */}
          <div className="mb-5">
            <div className="flex items-center justify-between text-[11px] mb-1.5 font-mono">
              <span className="text-ink-500 font-medium">Quick Presets:</span>
              {presetNotice && (
                <span className="text-forensic-green font-semibold">
                  {presetNotice}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              <button
                type="button"
                onClick={() => handlePreset("analyst")}
                className={`py-1.5 px-3 border text-center transition-colors cursor-pointer select-none ${
                  email === "analyst@meezan.pk"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Meezan Analyst
              </button>
              <button
                type="button"
                onClick={() => handlePreset("admin")}
                className={`py-1.5 px-3 border text-center transition-colors cursor-pointer select-none ${
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
            <div className="mb-4 p-3 bg-red-50 border border-forensic-red font-mono text-xs text-red-950 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-forensic-red shrink-0 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          {/* Conditional Form: Login Credentials or 2FA Challenge */}
          {!isMfaRequired ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4 font-mono text-xs">
              {/* Institutional Email Field */}
              <div>
                <label
                  htmlFor="login-email"
                  className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider mb-1"
                >
                  Institutional Email
                </label>
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@meezan.pk"
                />
              </div>

              {/* Password Field */}
              <div>
                <label
                  htmlFor="login-password"
                  className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider mb-1"
                >
                  Password
                </label>
                <Input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                />
              </div>

              {/* Remember Device Toggle */}
              <div className="pt-0.5">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberDevice}
                    onChange={(e) => setRememberDevice(e.target.checked)}
                    className="w-4 h-4 rounded-none accent-ink-900 cursor-pointer"
                  />
                  <span className="text-xs text-ink-600 font-sans">
                    Remember this device for 30 days
                  </span>
                </label>
              </div>

              {/* Submit Button */}
              <div className="pt-1">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isLoading={loading}
                  className="w-full text-xs font-mono uppercase tracking-wider"
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                >
                  Sign In
                </Button>
              </div>

              {/* Enterprise SSO Divider & Button */}
              <div className="pt-4 border-t border-rule space-y-3">
                <div className="relative flex items-center justify-center">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-rule" />
                  </div>
                  <span className="relative bg-paper-0 px-2 text-[10px] uppercase tracking-widest text-ink-400 font-mono">
                    or
                  </span>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  onClick={() => setIsSsoModalOpen(true)}
                  className="w-full flex items-center justify-center gap-2 py-2 text-xs font-mono"
                  aria-label="Sign in with Institutional SSO"
                >
                  <KeyRound className="w-3.5 h-3.5 text-ink-600 shrink-0" />
                  <span>Institutional SSO (SAML / Azure AD)</span>
                </Button>
              </div>
            </form>
          ) : (
            /* RFC 6238 Two-Factor Challenge Form */
            <form onSubmit={handleMfaSubmit} className="space-y-4 font-mono text-xs select-none">
              <div className="p-3 bg-paper-1 border border-rule text-ink-700 space-y-1">
                <div className="flex items-center gap-2 font-bold text-ink-900 text-xs uppercase">
                  <ShieldCheck className="w-4 h-4 text-forensic-green" />
                  <span>Two-Factor Authentication</span>
                </div>
                <p className="text-[11px] text-ink-600 leading-relaxed font-sans">
                  Enter the 6-digit verification code from your authenticator app (Google Authenticator, Microsoft Authenticator, or security token).
                </p>
              </div>

              {/* Segmented 6-digit input */}
              <div className="py-2">
                <label
                  htmlFor="mfa-digit-0"
                  className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider mb-2.5 text-center"
                >
                  6-Digit Authenticator Code
                </label>
                <div className="flex justify-center gap-2">
                  {mfaCode.map((digit, idx) => (
                    <input
                      key={idx}
                      id={idx === 0 ? "mfa-digit-0" : undefined}
                      ref={(el) => {
                        digitRefs.current[idx] = el;
                      }}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      aria-label={`Digit ${idx + 1} of 6`}
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
                    className="text-[11px] text-ink-600 hover:text-ink-900 underline decoration-dotted font-mono cursor-pointer"
                  >
                    [Auto-Fill Demo TOTP Token]
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
                  className="w-full text-xs font-mono uppercase tracking-wider"
                  rightIcon={<CheckCircle2 className="w-4 h-4" />}
                >
                  Verify &amp; Continue
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
                  className="w-full text-xs"
                >
                  ← Back to Email &amp; Password
                </Button>
              </div>
            </form>
          )}

          {/* Footer Notice */}
          <div className="border-t border-rule mt-5 pt-3 text-[11px] font-mono text-ink-400 text-center leading-normal">
            Protected under State Bank of Pakistan Cybersecurity Framework
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
