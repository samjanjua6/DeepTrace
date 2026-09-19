"use client";

import React, { useState, useEffect } from "react";
import { X, ShieldAlert, Shield, Check, AlertCircle, Loader2, UserCheck } from "lucide-react";
import { updateUserRole } from "@/lib/api/client";
import { OrgMemberItem, OrgUserRole } from "@/lib/types/forensics";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { useScrollLock } from "@/lib/hooks/useScrollLock";

interface ChangeRoleModalProps {
  isOpen: boolean;
  member: OrgMemberItem | null;
  currentUserId: string | null;
  onClose: () => void;
  onSuccess: () => void;
}

const ROLE_DEFINITIONS: {
  role: OrgUserRole;
  title: string;
  badge: string;
  description: string;
}[] = [
  {
    role: "OWNER",
    title: "Institutional Sovereign (Owner)",
    badge: "bg-ink-900 text-paper-0",
    description:
      "Full sovereign governance: Subscription & quota management, organization lifecycle, and clearance delegation.",
  },
  {
    role: "ADMIN",
    title: "Institutional Administrator",
    badge: "bg-ink-800 text-paper-0",
    description:
      "Operational control: User onboarding & role assignments, API keys, webhook integrations, and audit trail inspection.",
  },
  {
    role: "ANALYST",
    title: "Forensic Investigator (Analyst)",
    badge: "bg-ink-100 text-ink-900 border border-ink-900/30",
    description:
      "Document processing: Pipeline execution, evidence item inspection, and supervised risk score overrides.",
  },
  {
    role: "VIEWER",
    title: "Auditor / Compliance Observer (Viewer)",
    badge: "bg-paper-2 text-ink-600 border border-ink-900/20",
    description:
      "Read-only visibility: Forensic docket inspection, chain-of-custody verification, and report exports.",
  },
];

export function ChangeRoleModal({
  isOpen,
  member,
  currentUserId,
  onClose,
  onSuccess,
}: ChangeRoleModalProps) {
  const [selectedRole, setSelectedRole] = useState<OrgUserRole>("ANALYST");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useFocusTrap<HTMLDivElement>(isOpen);
  useScrollLock(isOpen);

  useEffect(() => {
    if (member) {
      setSelectedRole(member.role);
      setError(null);
    }
  }, [member]);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen || !member) return null;

  const isSelf = member.id === currentUserId;
  const isDemotingOwner = member.role === "OWNER" && selectedRole !== "OWNER";
  const isUnchanged = selectedRole === member.role;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isUnchanged) {
      onClose();
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await updateUserRole(member.id, selectedRole);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to update member clearance tier.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-label="Modify Clearance Level"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={loading}
          className="absolute top-4 right-4 text-ink-500 hover:text-ink-900 transition-colors p-1 cursor-pointer"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2.5 bg-ink-900 text-paper-0">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Clearance Governance
            </span>
            <h2 className="text-lg font-bold uppercase tracking-wider text-ink-900">
              Modify Clearance Level
            </h2>
          </div>
        </div>

        {/* Target Member Banner */}
        <div className="p-3 bg-paper-1 border border-ink-900/30 mb-4 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-ink-500 block">Personnel</span>
            <span className="font-bold text-sm text-ink-900">
              {member.first_name} {member.last_name}
            </span>
            <span className="text-xs text-ink-600 block">{member.email}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold text-ink-500 block">Current Clearance</span>
            <span className="inline-block px-2 py-0.5 bg-ink-900 text-paper-0 text-[10px] font-bold uppercase tracking-wider">
              {member.role}
            </span>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-700" />
            <span>{error}</span>
          </div>
        )}

        {isDemotingOwner && (
          <div className="p-3 bg-amber-50 border border-amber-300 text-amber-950 text-xs flex items-start gap-2 mb-4">
            <ShieldAlert className="w-4 h-4 shrink-0 text-amber-800 mt-0.5" />
            <div>
              <span className="font-bold uppercase tracking-wider block mb-0.5">Sole Owner Protection</span>
              <span>
                Demoting an Owner will be blocked by the server if this user is the sole institutional owner.
              </span>
            </div>
          </div>
        )}

        {isSelf && (
          <div className="p-3 bg-paper-2 border border-ink-900/40 text-ink-800 text-xs flex items-start gap-2 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0 text-ink-800 mt-0.5" />
            <div>
              <span className="font-bold uppercase tracking-wider block mb-0.5">Self-Modification Notice</span>
              <span>
                You are modifying your own clearance level. Demoting yourself may revoke your administrative access immediately.
              </span>
            </div>
          </div>
        )}

        {/* Role Selection Options */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="space-y-2">
            <label className="block font-bold uppercase tracking-wider text-ink-800">
              Select Target Clearance Level
            </label>

            <div className="space-y-2">
              {ROLE_DEFINITIONS.map((def) => {
                const isCurrent = member.role === def.role;
                const isSelected = selectedRole === def.role;
                return (
                  <label
                    key={def.role}
                    className={`block p-3 border cursor-pointer transition-colors ${
                      isSelected
                        ? "border-ink-900 bg-paper-2"
                        : "border-ink-900/20 bg-paper-1 hover:border-ink-900/40"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="clearance_role"
                          value={def.role}
                          checked={isSelected}
                          onChange={() => setSelectedRole(def.role)}
                          className="text-ink-900 focus:ring-0 cursor-pointer"
                        />
                        <span className="font-bold uppercase tracking-wider text-ink-900">
                          {def.title}
                        </span>
                      </div>
                      {isCurrent && (
                        <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 bg-paper-0 px-2 py-0.5 border border-ink-900/20">
                          Current
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-ink-600 pl-6">{def.description}</p>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-ink-900/10">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-ink-900/30 text-ink-700 hover:bg-paper-2 font-bold uppercase tracking-wider text-xs transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || isUnchanged}
              className="px-5 py-2 bg-ink-900 text-paper-0 hover:bg-ink-800 font-bold uppercase tracking-wider text-xs transition-colors flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Updating Clearance...</span>
                </>
              ) : (
                <>
                  <UserCheck className="w-4 h-4" />
                  <span>Commit Clearance Change</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
