"use client";

import React, { useState } from "react";
import { X, UserPlus, Key, Copy, Check, ShieldCheck, AlertCircle, Loader2, FileText, Lock } from "lucide-react";
import { inviteOrgUser } from "@/lib/api/client";
import { InviteUserResponse, OrgUserRole } from "@/lib/types/forensics";

interface InviteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function InviteUserModal({ isOpen, onClose, onSuccess }: InviteUserModalProps) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrgUserRole>("ANALYST");
  const [tempPassword, setTempPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Result state after successful invitation
  const [inviteResult, setInviteResult] = useState<InviteUserResponse | null>(null);
  const [copiedMemo, setCopiedMemo] = useState(false);
  const [copiedPassword, setCopiedPassword] = useState(false);

  if (!isOpen) return null;

  const generateSecurePassword = () => {
    const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%&*";
    let pwd = "DT-";
    for (let i = 0; i < 12; i++) {
      pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setTempPassword(pwd);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await inviteOrgUser({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim().toLowerCase(),
        role,
        temp_password: tempPassword.trim() || undefined,
      });
      setInviteResult(res);
      onSuccess();
    } catch (err: any) {
      setError(err?.message || "Failed to onboard analyst. Please verify inputs.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMemo = async () => {
    if (!inviteResult) return;
    try {
      await navigator.clipboard.writeText(inviteResult.dispatch_memo);
      setCopiedMemo(true);
      setTimeout(() => setCopiedMemo(false), 2000);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = inviteResult.dispatch_memo;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopiedMemo(true);
      setTimeout(() => setCopiedMemo(false), 2000);
    }
  };

  const handleCopyPassword = async () => {
    if (!inviteResult) return;
    try {
      await navigator.clipboard.writeText(inviteResult.temp_password);
      setCopiedPassword(true);
      setTimeout(() => setCopiedPassword(false), 2000);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = inviteResult.temp_password;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopiedPassword(true);
      setTimeout(() => setCopiedPassword(false), 2000);
    }
  };

  const handleClose = () => {
    setFirstName("");
    setLastName("");
    setEmail("");
    setRole("ANALYST");
    setTempPassword("");
    setInviteResult(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-2xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative max-h-[92vh] overflow-y-auto">
        {/* Close Button */}
        <button
          type="button"
          onClick={handleClose}
          disabled={loading}
          className="absolute top-4 right-4 text-ink-500 hover:text-ink-900 transition-colors p-1 cursor-pointer"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2.5 bg-ink-900 text-paper-0">
            <UserPlus className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Identity & Access Management
            </span>
            <h2 className="text-lg font-bold uppercase tracking-wider text-ink-900">
              {inviteResult ? "Credential Dispatch Memo Issued" : "Onboard Personnel / Issue Clearance"}
            </h2>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-700" />
            <span>{error}</span>
          </div>
        )}

        {!inviteResult ? (
          /* Onboarding Form */
          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block font-bold uppercase tracking-wider text-ink-800">
                  First Name <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="e.g. Tariq"
                  className="w-full px-3 py-2 bg-paper-1 border border-ink-900/30 text-ink-900 focus:outline-none focus:border-ink-900 text-xs placeholder:text-ink-400"
                />
              </div>

              <div className="space-y-1.5">
                <label className="block font-bold uppercase tracking-wider text-ink-800">
                  Last Name <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="e.g. Mahmood"
                  className="w-full px-3 py-2 bg-paper-1 border border-ink-900/30 text-ink-900 focus:outline-none focus:border-ink-900 text-xs placeholder:text-ink-400"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block font-bold uppercase tracking-wider text-ink-800">
                Institutional Email Address <span className="text-rose-600">*</span>
              </label>
              <input
                type="text"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@meezanbank.com"
                className="w-full px-3 py-2 bg-paper-1 border border-ink-900/30 text-ink-900 focus:outline-none focus:border-ink-900 text-xs placeholder:text-ink-400"
              />
              <span className="text-[10px] text-ink-500 block">
                Must be an authorized enterprise domain. System generates an audit log entry for this issuance.
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="block font-bold uppercase tracking-wider text-ink-800">
                Clearance Tier / Role <span className="text-rose-600">*</span>
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as OrgUserRole)}
                className="w-full px-3 py-2 bg-paper-1 border border-ink-900/30 text-ink-900 focus:outline-none focus:border-ink-900 text-xs font-mono"
              >
                <option value="ANALYST">ANALYST - Case Investigation & Forensic Assessment</option>
                <option value="VIEWER">VIEWER - Read-Only Dossier Inspection</option>
                <option value="ADMIN">ADMIN - Full Personnel & Integration Administration</option>
              </select>
            </div>

            <div className="space-y-1.5 pt-1">
              <div className="flex items-center justify-between">
                <label className="block font-bold uppercase tracking-wider text-ink-800">
                  Temporary Access Credential (Optional)
                </label>
                <button
                  type="button"
                  onClick={generateSecurePassword}
                  className="text-[10px] text-ink-700 hover:text-ink-900 underline font-bold cursor-pointer"
                >
                  Generate Strong Key
                </button>
              </div>
              <input
                type="text"
                value={tempPassword}
                onChange={(e) => setTempPassword(e.target.value)}
                placeholder="Leave blank to automatically auto-generate institutional key"
                className="w-full px-3 py-2 bg-paper-1 border border-ink-900/30 text-ink-900 focus:outline-none focus:border-ink-900 text-xs placeholder:text-ink-400"
              />
              <span className="text-[10px] text-ink-500 block">
                If omitted, an entropy-evaluated 14-character cryptographic passcode is provisioned.
              </span>
            </div>

            {/* Compliance Banner */}
            <div className="p-3 bg-paper-1 border border-ink-900/20 text-ink-700 text-[11px] flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 shrink-0 text-ink-900 mt-0.5" />
              <div>
                <span className="font-bold uppercase tracking-wider text-ink-900 block mb-0.5">
                  SBP BPRD/2020 Compliance Protocol
                </span>
                <span>
                  The onboarding event is permanently recorded in the institutional audit log with your Administrator fingerprint.
                  The personnel member will be required to configure 2FA upon initial authentication.
                </span>
              </div>
            </div>

            {/* Form Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-ink-900/10">
              <button
                type="button"
                onClick={handleClose}
                disabled={loading}
                className="px-4 py-2 border border-ink-900/30 text-ink-700 hover:bg-paper-2 font-bold uppercase tracking-wider text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2 bg-ink-900 text-paper-0 hover:bg-ink-800 font-bold uppercase tracking-wider text-xs transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Issuing Clearance...</span>
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    <span>Issue Clearance</span>
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          /* Dispatch Memo Result */
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-950 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0" />
                <span>
                  Personnel <strong>{inviteResult.user.first_name} {inviteResult.user.last_name}</strong> ({inviteResult.user.email}) clearance created.
                </span>
              </div>
              <span className="px-2 py-0.5 bg-emerald-700 text-white font-mono text-[10px] font-bold">
                {inviteResult.user.role}
              </span>
            </div>

            {/* Key Grid */}
            <div className="p-4 bg-paper-1 border border-ink-900 space-y-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block mb-1">
                  Temporary Password
                </span>
                <div className="flex items-center justify-between bg-paper-0 border border-ink-900/30 px-3 py-2">
                  <span className="font-mono font-bold text-sm tracking-widest text-ink-900 select-all">
                    {inviteResult.temp_password}
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyPassword}
                    className="p-1.5 text-ink-700 hover:text-ink-900 transition-colors flex items-center gap-1 cursor-pointer"
                    title="Copy Password"
                  >
                    {copiedPassword ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    <span className="text-[10px] uppercase font-bold">{copiedPassword ? "Copied" : "Copy"}</span>
                  </button>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block mb-1">
                  Portal Login URL
                </span>
                <div className="bg-paper-0 border border-ink-900/30 px-3 py-2 font-mono text-[11px] text-ink-700 select-all">
                  {inviteResult.login_url}
                </div>
              </div>
            </div>

            {/* Formatted Dispatch Memo */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold uppercase tracking-wider text-ink-800 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-ink-600" />
                  Institutional Dispatch Memo
                </span>
                <button
                  type="button"
                  onClick={handleCopyMemo}
                  className="px-3 py-1 bg-ink-900 text-paper-0 text-[10px] font-bold uppercase tracking-wider hover:bg-ink-800 transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  {copiedMemo ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedMemo ? "Memo Copied" : "Copy Dispatch Memo"}</span>
                </button>
              </div>
              <pre className="p-3 bg-paper-2 border border-ink-900/40 text-[10px] text-ink-800 whitespace-pre-wrap font-mono select-all overflow-x-auto">
                {inviteResult.dispatch_memo}
              </pre>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-300 text-amber-950 text-[11px] flex items-start gap-2">
              <Lock className="w-4 h-4 shrink-0 text-amber-800 mt-0.5" />
              <span>
                <strong>Confidential Dispatch:</strong> Send this memo through your organization's approved secure channel.
                The temporary password will not be displayed again in plaintext.
              </span>
            </div>

            {/* Completion Action */}
            <div className="flex justify-end pt-3 border-t border-ink-900/10">
              <button
                type="button"
                onClick={handleClose}
                className="px-5 py-2 bg-ink-900 text-paper-0 hover:bg-ink-800 font-bold uppercase tracking-wider text-xs transition-colors cursor-pointer"
              >
                Acknowledge & Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
