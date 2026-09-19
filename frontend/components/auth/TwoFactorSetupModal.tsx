"use client";

import React, { useState, useEffect } from "react";
import { QRCodeSVG } from "qrcode.react";
import { useAuth } from "@/context/AuthContext";
import { setupMfa, enableMfa, disableMfa } from "@/lib/api/client";
import {
  ShieldCheck,
  ShieldAlert,
  X,
  Copy,
  Check,
  RefreshCw,
  KeyRound,
  Lock,
  AlertTriangle,
  Smartphone,
} from "lucide-react";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { useScrollLock } from "@/lib/hooks/useScrollLock";

interface TwoFactorSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TwoFactorSetupModal({ isOpen, onClose }: TwoFactorSetupModalProps) {
  const { user, refreshProfile } = useAuth();

  const [step, setStep] = useState<"initial" | "enroll" | "disable">("initial");
  const [setupData, setSetupData] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [confirmationCode, setConfirmationCode] = useState<string>("");
  const [disablePassword, setDisablePassword] = useState<string>("");
  const [disableCode, setDisableCode] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      setStep("initial");
      setError(null);
      setSuccess(null);
      setConfirmationCode("");
      setDisablePassword("");
      setDisableCode("");
      setSetupData(null);
    }
  }, [isOpen]);

  const containerRef = useFocusTrap<HTMLDivElement>(isOpen);
  useScrollLock(isOpen);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen || !user) return null;

  const isEnabled = user.mfa_enabled;

  const handleStartEnrollment = async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await setupMfa();
      setSetupData(data);
      setStep("enroll");
    } catch (err: any) {
      setError(err.message || "Failed to initialize 2FA pairing.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopySecret = () => {
    if (!setupData) return;
    navigator.clipboard.writeText(setupData.secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!setupData || confirmationCode.length !== 6) {
      setError("Please enter the 6-digit verification code from your phone.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await enableMfa(setupData.secret, confirmationCode);
      await refreshProfile();
      setSuccess("Two-Factor Authentication is now active on your account.");
      setStep("initial");
    } catch (err: any) {
      setError(err.message || "Invalid authenticator code. Please check your phone app.");
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disablePassword || disableCode.length !== 6) {
      setError("Both clearance password and current 6-digit code are required.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await disableMfa(disablePassword, disableCode);
      await refreshProfile();
      setSuccess("Two-Factor Authentication has been removed from your account.");
      setStep("initial");
    } catch (err: any) {
      setError(err.message || "Failed to disable 2FA. Verify password and current code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-label="Two-Factor Authentication"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 sm:p-8 font-sans"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-rule pb-4 mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2 border border-ink-900 bg-paper-1">
              <KeyRound className="w-5 h-5 text-ink-900" />
            </div>
            <div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-ink-500">
                Institutional Security Protocol
              </div>
              <h2 className="font-serif text-2xl text-ink-900 font-normal">
                Two-Factor Authentication (2FA)
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 border border-rule hover:border-ink-900 text-ink-600 hover:text-ink-900 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border-l-4 border-forensic-red font-mono text-xs text-red-900 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-forensic-red shrink-0 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-emerald-50 border-l-4 border-forensic-green font-mono text-xs text-emerald-900 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-forensic-green shrink-0 mt-0.5" />
            <div>{success}</div>
          </div>
        )}

        {/* View 1: Status Screen */}
        {step === "initial" && (
          <div className="space-y-5">
            <div className="p-4 border border-rule bg-paper-1 flex items-start justify-between gap-4">
              <div>
                <div className="font-mono text-xs font-semibold uppercase tracking-wider text-ink-500 mb-1">
                  Current Status
                </div>
                <div className="flex items-center gap-2">
                  {isEnabled ? (
                    <>
                      <span className="w-2.5 h-2.5 rounded-full bg-forensic-green inline-block animate-pulse" />
                      <span className="font-mono text-sm font-bold text-forensic-green tracking-wider uppercase">
                        Active & Enforced (RFC 6238)
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
                      <span className="font-mono text-sm font-bold text-ink-700 tracking-wider uppercase">
                        Disabled (Single Factor Only)
                      </span>
                    </>
                  )}
                </div>
                <p className="text-xs text-ink-600 mt-2 font-sans">
                  {isEnabled
                    ? "Your analyst account is protected by hardware/software authenticator verification conforming to State Bank of Pakistan cybersecurity guidelines."
                    : "Protect your case dockets and documents with an authenticator app (Google Authenticator, Microsoft Authenticator, or 1Password)."}
                </p>
              </div>
            </div>

            <div className="pt-2 flex items-center gap-3">
              {!isEnabled ? (
                <button
                  type="button"
                  onClick={handleStartEnrollment}
                  disabled={loading}
                  className="px-5 py-2.5 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Preparing Key...</span>
                    </>
                  ) : (
                    <>
                      <Smartphone className="w-3.5 h-3.5" />
                      <span>Setup 2FA with Phone</span>
                    </>
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setStep("disable")}
                  className="px-4 py-2 border border-rule hover:border-forensic-red text-ink-700 hover:text-forensic-red font-mono text-xs uppercase tracking-wider transition-colors cursor-pointer"
                >
                  Disable 2FA
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-ink-600 hover:text-ink-900 font-mono text-xs uppercase tracking-wider transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}

        {/* View 2: QR Enrollment Screen */}
        {step === "enroll" && setupData && (
          <form onSubmit={handleActivate} className="space-y-5">
            <div className="text-xs text-ink-700 leading-relaxed font-sans">
              Scan this QR code with your authenticator app (Google Authenticator, Microsoft Authenticator, 1Password, or Apple Passwords):
            </div>

            {/* QR Display */}
            <div className="flex flex-col sm:flex-row items-center gap-6 p-4 bg-paper-1 border border-rule">
              <div className="bg-white p-3 border border-ink-900 shrink-0">
                <QRCodeSVG
                  value={setupData.otpauth_uri}
                  size={160}
                  level="M"
                  includeMargin={false}
                />
              </div>
              <div className="space-y-3 font-mono text-xs">
                <div>
                  <span className="text-[10px] text-ink-500 uppercase tracking-wider block">
                    Account Identity:
                  </span>
                  <span className="font-semibold text-ink-900">{user.email}</span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-500 uppercase tracking-wider block">
                    Manual Base32 Secret Key:
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    <code className="px-2 py-1 bg-paper-0 border border-rule text-ink-900 font-bold tracking-widest text-[11px] select-all">
                      {setupData.secret}
                    </code>
                    <button
                      type="button"
                      onClick={handleCopySecret}
                      className="p-1 border border-rule hover:border-ink-900 text-ink-600 hover:text-ink-900 transition-colors"
                      title="Copy secret key"
                    >
                      {copied ? (
                        <Check className="w-3.5 h-3.5 text-forensic-green" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Confirmation input */}
            <div>
              <label className="block text-[11px] font-mono font-semibold text-ink-700 uppercase tracking-wider mb-1.5">
                Confirmation: Enter 6-digit code from phone
              </label>
              <input
                type="text"
                required
                inputMode="numeric"
                maxLength={6}
                value={confirmationCode}
                onChange={(e) => setConfirmationCode(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                className="w-full bg-paper-0 border border-ink-900 px-3 py-2 text-center text-lg font-mono font-bold tracking-widest text-ink-900 focus:outline-none focus:bg-amber-50"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                disabled={loading || confirmationCode.length !== 6}
                className="px-6 py-2.5 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Activating...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Verify & Activate 2FA</span>
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={() => setStep("initial")}
                className="px-4 py-2 border border-rule hover:border-ink-900 text-ink-600 hover:text-ink-900 font-mono text-xs uppercase tracking-wider transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* View 3: Disable Screen */}
        {step === "disable" && (
          <form onSubmit={handleDisable} className="space-y-4">
            <div className="p-3 bg-red-50 border-l-4 border-forensic-red font-mono text-xs text-red-900">
              Disabling 2FA will lower your workstation compliance status to single factor. Password confirmation is required.
            </div>

            <div>
              <label className="block text-[11px] font-mono font-semibold text-ink-700 uppercase tracking-wider mb-1">
                Account Password
              </label>
              <input
                type="password"
                required
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-paper-0 border border-ink-900 px-3 py-2 text-xs font-mono text-ink-900 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono font-semibold text-ink-700 uppercase tracking-wider mb-1">
                Current 6-Digit Authenticator Code
              </label>
              <input
                type="text"
                required
                inputMode="numeric"
                maxLength={6}
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                className="w-full bg-paper-0 border border-ink-900 px-3 py-2 text-center text-base font-mono font-bold tracking-widest text-ink-900 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                disabled={loading || !disablePassword || disableCode.length !== 6}
                className="px-5 py-2.5 bg-forensic-red hover:bg-red-800 text-white font-mono text-xs uppercase tracking-widest font-semibold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
              >
                {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldAlert className="w-3.5 h-3.5" />}
                <span>Confirm & Disable 2FA</span>
              </button>
              <button
                type="button"
                onClick={() => setStep("initial")}
                className="px-4 py-2 border border-rule text-ink-600 hover:text-ink-900 font-mono text-xs uppercase tracking-wider transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
