"use client";

import React, { useState } from "react";
import { X, Key, Shield, AlertTriangle, Loader2 } from "lucide-react";
import { createApiKey } from "@/lib/api/client";
import { ApiKeyCreatedResponse } from "@/lib/types/forensics";

interface CreateKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (keyData: ApiKeyCreatedResponse) => void;
}

const AVAILABLE_SCOPES = [
  {
    id: "investigations:read",
    label: "investigations:read",
    description: "Read access to case dockets, forensic signals, and custody chains.",
    defaultChecked: true,
  },
  {
    id: "investigations:write",
    label: "investigations:write",
    description: "Create cases, upload loan documents, and trigger forensic analysis pipelines.",
    defaultChecked: true,
  },
  {
    id: "custody:read",
    label: "custody:read",
    description: "Inspect RFC 3161 cryptographic seals and immutable chain-of-custody manifests.",
    defaultChecked: false,
  },
  {
    id: "agents:ask",
    label: "agents:ask",
    description: "Query the autonomous Lead Investigator Agent swarm for forensic interrogation.",
    defaultChecked: false,
  },
];

const EXPIRATION_OPTIONS = [
  { value: 30, label: "30 Days (Recommended for Core Banking)" },
  { value: 90, label: "90 Days (Quarterly Rotation)" },
  { value: 180, label: "180 Days (Semi-Annual)" },
  { value: 365, label: "365 Days (Annual Review)" },
  { value: 0, label: "No Expiration (Permanent Institutional Service Account)" },
];

export function CreateKeyModal({ isOpen, onClose, onSuccess }: CreateKeyModalProps) {
  const [name, setName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>([
    "investigations:read",
    "investigations:write",
  ]);
  const [expirationDays, setExpirationDays] = useState<number>(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleToggleScope = (scopeId: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scopeId)
        ? prev.filter((s) => s !== scopeId)
        : [...prev, scopeId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Credential identifier / system name is required.");
      return;
    }
    if (selectedScopes.length === 0) {
      setError("At least one permission scope must be selected.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        scopes: selectedScopes,
        expires_in_days: expirationDays > 0 ? expirationDays : null,
      };
      const createdKey = await createApiKey(payload);
      onSuccess(createdKey);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to create API key.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={loading}
          className="absolute top-4 right-4 text-ink-500 hover:text-ink-900 transition-colors p-1"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2 bg-paper-2 border border-ink-900">
            <Key className="w-5 h-5 text-ink-900" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-ink-900">
              Issue Machine-to-Machine API Key
            </h2>
            <p className="text-[11px] text-ink-500">
              Institutional Clearance for Automated Ingestion & Verification
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-900 text-rose-900 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Key Identifier */}
          <div>
            <label className="block text-[11px] font-bold uppercase text-ink-800 mb-1">
              Credential Identifier / Consumer System
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Meezan Core Banking Middleware / T24 Integration"
              className="w-full px-3 py-2 text-xs bg-paper-1 border border-ink-900 text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-1 focus:ring-ink-900"
              disabled={loading}
              autoFocus
            />
          </div>

          {/* Expiration Policy */}
          <div>
            <label className="block text-[11px] font-bold uppercase text-ink-800 mb-1">
              Cryptographic Expiration Policy
            </label>
            <select
              value={expirationDays}
              onChange={(e) => setExpirationDays(Number(e.target.value))}
              disabled={loading}
              className="w-full px-3 py-2 text-xs bg-paper-1 border border-ink-900 text-ink-900 focus:outline-none focus:ring-1 focus:ring-ink-900 cursor-pointer"
            >
              {EXPIRATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Granular Scope Selection */}
          <div>
            <label className="block text-[11px] font-bold uppercase text-ink-800 mb-1.5">
              Granular Permission Scopes (Least Privilege Enforcement)
            </label>
            <div className="space-y-2 border border-rule bg-paper-1 p-3">
              {AVAILABLE_SCOPES.map((scope) => {
                const checked = selectedScopes.includes(scope.id);
                return (
                  <label
                    key={scope.id}
                    className="flex items-start gap-2.5 cursor-pointer select-none hover:bg-paper-2 p-1 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleToggleScope(scope.id)}
                      disabled={loading}
                      className="mt-0.5 rounded-none border-ink-900 text-ink-900 focus:ring-0 cursor-pointer"
                    />
                    <div className="text-xs">
                      <span className="font-bold text-ink-900">{scope.label}</span>
                      <p className="text-[11px] text-ink-600 leading-tight mt-0.5">
                        {scope.description}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* SBP Compliance Notice */}
          <div className="p-3 bg-paper-2 border border-rule text-[10px] text-ink-600 leading-relaxed flex items-start gap-2.5">
            <Shield className="w-4 h-4 text-ink-800 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold uppercase tracking-wider text-ink-900 block mb-0.5">
                SBP Cybersecurity Framework Notice (BPRD/2020)
              </span>
              Machine-to-machine keys carry direct institutional execution authority. Key creation
              is immutably recorded in the PostgreSQL audit log alongside administrator identity,
              IP address, and timestamp.
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-rule">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-xs uppercase font-semibold text-ink-700 bg-paper-1 hover:bg-paper-2 border border-rule hover:border-ink-900 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 text-xs uppercase font-bold text-paper-0 bg-ink-900 hover:bg-black border border-ink-900 transition-colors flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Issuing...</span>
                </>
              ) : (
                <span>Issue Key</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
