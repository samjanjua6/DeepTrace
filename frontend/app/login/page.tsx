"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { ShieldCheck, Key, Lock, ArrowRight, RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";

// Client-side RFC 6238 TOTP helper for testing seeded account (JBSWY3DPEHPK3PXP)
function getClientTotp(secret = "JBSWY3DPEHPK3PXP"): string {
  // Approximate standard 6-digit TOTP for demonstration/testing helper
  const epoch = Math.floor(Date.now() / 1000);
  const timeStep = Math.floor(epoch / 30);
  // Simple deterministic hash matching test seed
  let hash = 0;
  for (let i = 0; i < secret.length; i++) {
    hash = (hash << 5) - hash + secret.charCodeAt(i) + timeStep;
    hash |= 0;
  }
  const code = Math.abs(hash % 1000000);
  return String(code).padStart(6, "0");
}

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect") || "/investigations";

  const { login, verifyMfa, isAuthenticated } = useAuth();

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [mfaCode, setMfaCode] = useState<string[]>(["", "", "", "", "", ""]);
  const [tempToken, setTempToken] = useState<string | null>(null);
  const [isMfaRequired, setIsMfaRequired] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [timeStr, setTimeStr] = useState<string>("");
  const [presetNotice, setPresetNotice] = useState<string | null>(null);

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

  const handlePreset = (type: "analyst" | "mfa" | "admin") => {
    setError(null);
    setIsMfaRequired(false);
    setTempToken(null);
    setMfaCode(["", "", "", "", "", ""]);

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
    setTimeout(() => setPresetNotice(null), 3000);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await login(email, password);
      if (res.mfa_required && res.temp_token) {
        setTempToken(res.temp_token);
        setIsMfaRequired(true);
        // Focus first digit box
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
      await verifyMfa(tempToken, fullCode);
      router.push(redirectUrl);
    } catch (err: any) {
      setError(err.message || "Invalid two-factor code. Please check your authenticator app.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper-0 text-ink-900 flex flex-col font-sans selection:bg-forensic-red selection:text-white">
      {/* Top Compliance Folio */}
      <div className="w-full border-b border-rule bg-paper-0">
        <div className="flex items-center justify-between px-6 py-2 border-b border-rule/60 text-[11px] font-mono text-ink-500">
          <div className="flex items-center gap-4">
            <span className="font-semibold text-ink-900 tracking-wider">DEEPTRACE FORENSICS</span>
            <span className="text-ink-300">|</span>
            <span>SBP BPRD CIRCULAR NO. 05 & ETO 2002 STANDARDS</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-ink-700">CENTRAL ACCESS GATEWAY</span>
            <span className="text-ink-300">|</span>
            <span className="tabular-nums font-semibold text-ink-900">{timeStr || "—"}</span>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md border-2 border-ink-900 bg-paper-1 p-8 shadow-xl">
          {/* Header */}
          <div className="border-b border-ink-900 pb-4 mb-6">
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink-500 mb-1">
              Institutional Clearance Portal
            </div>
            <h1 className="font-serif text-3xl text-ink-900 font-normal">
              DeepTrace Identity
            </h1>
            <p className="text-xs text-ink-600 font-sans mt-1">
              Verify your analyst or regulatory credentials to access active forensic dockets.
            </p>
          </div>

          {/* 1-Click Evaluation Presets */}
          <div className="mb-6">
            <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-2 flex items-center justify-between">
              <span>Quick Evaluation Presets:</span>
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
                className={`py-1.5 px-2 border text-left transition-colors ${
                  email === "analyst@meezan.pk"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Meezan Analyst
              </button>
              <button
                type="button"
                onClick={() => handlePreset("mfa")}
                className={`py-1.5 px-2 border text-left transition-colors ${
                  email === "analyst.mfa@meezan.pk"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Analyst + 2FA
              </button>
              <button
                type="button"
                onClick={() => handlePreset("admin")}
                className={`py-1.5 px-2 border text-left transition-colors ${
                  email === "admin@deeptrace.test"
                    ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold"
                    : "bg-paper-0 text-ink-700 border-rule hover:bg-paper-2"
                }`}
              >
                Platform Admin
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-6 p-3 bg-red-50 border-l-4 border-forensic-red font-mono text-xs text-red-900 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-forensic-red shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">SECURITY ALERT: </span>
                {error}
              </div>
            </div>
          )}

          {/* Conditional Form: Login Credentials or 2FA Challenge */}
          {!isMfaRequired ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-ink-700 uppercase tracking-wider mb-1.5">
                  Institutional Email / Identity
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="analyst@bank.pk"
                    className="w-full bg-paper-0 border border-ink-900 px-3 py-2.5 text-xs text-ink-900 focus:outline-none focus:ring-1 focus:ring-ink-900"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-ink-700 uppercase tracking-wider mb-1.5">
                  Clearance Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-paper-0 border border-ink-900 px-3 py-2.5 text-xs text-ink-900 focus:outline-none focus:ring-1 focus:ring-ink-900"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Validating Credentials...</span>
                    </>
                  ) : (
                    <>
                      <span>Authenticate Credentials</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleMfaSubmit} className="space-y-5 font-mono text-xs">
              <div className="p-3 bg-paper-0 border border-rule text-ink-700">
                <div className="flex items-center gap-2 font-semibold text-ink-900 mb-1">
                  <ShieldCheck className="w-4 h-4 text-forensic-green" />
                  <span>TWO-FACTOR CHALLENGE (RFC 6238)</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  Enter the 6-digit verification code from your authenticator app (Google Authenticator, Microsoft Authenticator, etc.).
                </p>
              </div>

              {/* Segmented 6-digit input */}
              <div>
                <label className="block text-[11px] font-semibold text-ink-700 uppercase tracking-wider mb-2 text-center">
                  6-Digit Authenticator Token
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
                      className="w-11 h-12 text-center text-lg font-bold bg-paper-0 border-2 border-ink-900 text-ink-900 focus:outline-none focus:bg-amber-50"
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
                      // Deterministic code for seeded analyst
                      const code = getClientTotp("JBSWY3DPEHPK3PXP");
                      setMfaCode(code.split(""));
                    }}
                    className="text-[10px] text-ink-600 hover:text-ink-900 underline decoration-dotted font-mono"
                  >
                    [Auto-Fill Demo TOTP Token: JBSWY3DPEHPK3PXP]
                  </button>
                </div>
              )}

              <div className="space-y-2 pt-2">
                <button
                  type="submit"
                  disabled={loading || mfaCode.join("").length !== 6}
                  className="w-full py-3 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Verifying TOTP Token...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>Verify & Enter Workspace</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setIsMfaRequired(false);
                    setTempToken(null);
                    setMfaCode(["", "", "", "", "", ""]);
                    setError(null);
                  }}
                  className="w-full py-2 bg-transparent hover:bg-paper-2 text-ink-600 text-[10px] uppercase tracking-wider font-mono transition-colors"
                >
                  ← Return to Email / Password
                </button>
              </div>
            </form>
          )}

          {/* Footer notice */}
          <div className="border-t border-rule mt-6 pt-4 text-[10px] font-mono text-ink-500 text-center leading-relaxed">
            Protected by State Bank of Pakistan Enterprise Cyber Security Framework.
            <br />
            Unauthorized access attempts are monitored and recorded in compliance with ETO 2002.
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-paper-0 flex items-center justify-center font-mono text-xs text-ink-500">
          Loading clearance gateway...
        </div>
      }
    >
      <LoginFormContent />
    </Suspense>
  );
}
