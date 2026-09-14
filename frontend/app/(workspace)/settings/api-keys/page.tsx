"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Key,
  Plus,
  Trash2,
  Shield,
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Loader2,
  ArrowLeft,
  ExternalLink,
} from "lucide-react";
import { getApiKeys } from "@/lib/api/client";
import { ApiKeyItem, ApiKeyCreatedResponse } from "@/lib/types/forensics";
import { CreateKeyModal } from "@/components/admin/CreateKeyModal";
import { KeyRevealModal } from "@/components/admin/KeyRevealModal";
import { RevokeKeyModal } from "@/components/admin/RevokeKeyModal";

type FilterTab = "active" | "revoked";

export default function ApiKeysSettingsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [activeTab, setActiveTab] = useState<FilterTab>("active");
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createdKeyData, setCreatedKeyData] = useState<ApiKeyCreatedResponse | null>(null);
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKeyItem | null>(null);

  const isAdmin = user?.role === "ADMIN" || user?.role === "OWNER";

  const fetchKeys = async () => {
    if (!isAdmin) return;
    setLoading(true);
    setError(null);
    try {
      // Fetch both active and revoked to populate metrics and tabs
      const data = await getApiKeys(true);
      setKeys(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load API keys.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && isAdmin) {
      fetchKeys();
    }
  }, [authLoading, isAdmin]);

  // Derived metrics
  const activeKeys = useMemo(() => keys.filter((k) => k.is_active), [keys]);
  const revokedKeys = useMemo(() => keys.filter((k) => !k.is_active), [keys]);

  const expiringSoonCount = useMemo(() => {
    const fourteenDaysMs = 14 * 24 * 60 * 60 * 1000;
    const now = Date.now();
    return activeKeys.filter((k) => {
      if (!k.expires_at) return false;
      const exp = new Date(k.expires_at).getTime();
      return exp > now && exp - now <= fourteenDaysMs;
    }).length;
  }, [activeKeys]);

  const displayedKeys = activeTab === "active" ? activeKeys : revokedKeys;

  // ── Authentication & RBAC Gatekeeper ─────────────────────────────────────
  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-8 font-mono">
        <Loader2 className="w-8 h-8 animate-spin text-ink-900 mb-3" />
        <span className="text-xs uppercase tracking-widest text-ink-600">
          Verifying Institutional Clearance...
        </span>
      </div>
    );
  }

  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-6 font-mono">
        <div className="bg-paper-0 border-2 border-rose-900 shadow-2xl p-8">
          <div className="flex items-center gap-3 border-b-2 border-rose-900 pb-4 mb-6">
            <div className="p-2.5 bg-rose-100 border border-rose-900 text-rose-900">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-rose-700 block">
                Access Denied [HTTP 403]
              </span>
              <h1 className="text-lg font-bold uppercase tracking-wider text-rose-950">
                Institutional Administrator Clearance Required
              </h1>
            </div>
          </div>

          <div className="space-y-3 text-xs text-ink-700 leading-relaxed mb-8">
            <p>
              Access to Machine-to-Machine Credential Governance is strictly restricted to
              designated Institutional Compliance Officers and System Administrators (
              <span className="font-bold text-ink-900">ADMIN</span> or{" "}
              <span className="font-bold text-ink-900">OWNER</span> roles).
            </p>
            <p>
              Your active session is authenticated as{" "}
              <span className="font-bold text-ink-900">{user?.email || "Unknown User"}</span> with
              assigned role{" "}
              <span className="font-bold text-rose-900">[{user?.role || "UNAUTHORIZED"}]</span>.
            </p>
            <div className="p-3 bg-paper-2 border border-rule text-[11px] text-ink-600">
              Under SBP Cybersecurity Guidelines (BPRD/2020), unauthorized attempts to inspect or
              generate machine-level keys are recorded in the central compliance audit trail.
            </div>
          </div>

          <div className="flex items-center gap-4 pt-4 border-t border-rule">
            <Link
              href="/investigations"
              className="px-5 py-2.5 bg-ink-900 text-paper-0 hover:bg-black text-xs uppercase font-bold tracking-wider transition-colors inline-flex items-center gap-2"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Return to Case Docket</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Admin API Key Governance View ─────────────────────────────────────────
  return (
    <div className="max-w-7xl mx-auto py-8 px-6 font-mono space-y-6">
      {/* Page Header */}
      <div className="border-b-2 border-ink-900 pb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-ink-500 mb-1">
              <span>Administration</span>
              <span>/</span>
              <span>Settings</span>
              <span>/</span>
              <span className="text-ink-900 font-bold">API Keys</span>
            </div>
            <h1 className="text-2xl font-serif text-ink-900 tracking-tight">
              API Key Management
            </h1>
            <p className="text-xs text-ink-600 mt-1 max-w-2xl">
              Cryptographic machine-to-machine credentials for automated document ingestion,
              core banking middleware, and institutional pipeline triggers.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={fetchKeys}
              disabled={loading}
              className="p-2 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-700 transition-colors cursor-pointer"
              title="Refresh Registry"
            >
              <RotateCcw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              type="button"
              onClick={() => setCreateModalOpen(true)}
              className="px-4 py-2 bg-ink-900 hover:bg-black text-paper-0 text-xs uppercase font-bold tracking-wider transition-colors flex items-center gap-2 border border-ink-900 cursor-pointer shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Issue New Key</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            Active Credentials
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink-900 tabular-nums">
              {activeKeys.length}
            </span>
            <span className="text-[10px] text-emerald-700 uppercase font-semibold">
              Operational
            </span>
          </div>
        </div>

        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            Expiring Soon (14 Days)
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink-900 tabular-nums">
              {expiringSoonCount}
            </span>
            {expiringSoonCount > 0 && (
              <span className="text-[10px] text-amber-700 uppercase font-semibold">
                Rotation Required
              </span>
            )}
          </div>
        </div>

        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            Revocation Registry
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-ink-900 tabular-nums">
              {revokedKeys.length}
            </span>
            <span className="text-[10px] text-ink-500 uppercase font-semibold">
              Historical Records
            </span>
          </div>
        </div>

        <div className="p-4 bg-paper-0 border-2 border-ink-900 shadow-sm">
          <span className="text-[10px] uppercase font-bold text-ink-500 tracking-wider block mb-1">
            Compliance Standard
          </span>
          <div className="text-xs font-bold text-ink-900 mt-1">
            SBP BPRD / NIST SP 800-86
          </div>
          <span className="text-[10px] text-ink-500 block mt-0.5">
            HMAC / SHA-256 Hashed
          </span>
        </div>
      </div>

      {/* Tabs & Table Container */}
      <div className="bg-paper-0 border-2 border-ink-900 shadow-sm">
        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b-2 border-ink-900 px-4 bg-paper-1">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("active")}
              className={`px-4 py-3 text-xs uppercase font-bold tracking-wider border-b-2 transition-colors cursor-pointer ${
                activeTab === "active"
                  ? "border-ink-900 text-ink-900 bg-paper-0"
                  : "border-transparent text-ink-500 hover:text-ink-900"
              }`}
            >
              Active Credentials ({activeKeys.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("revoked")}
              className={`px-4 py-3 text-xs uppercase font-bold tracking-wider border-b-2 transition-colors cursor-pointer ${
                activeTab === "revoked"
                  ? "border-ink-900 text-ink-900 bg-paper-0"
                  : "border-transparent text-ink-500 hover:text-ink-900"
              }`}
            >
              Revocation Registry ({revokedKeys.length})
            </button>
          </div>

          <span className="text-[10px] text-ink-500 uppercase tracking-wider hidden sm:inline">
            Tenant: {user?.organization_name || user?.organization_id}
          </span>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-rose-50 border-b border-rose-900 text-rose-900 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading Indicator */}
        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center text-ink-500 text-xs">
            <Loader2 className="w-6 h-6 animate-spin mb-2 text-ink-900" />
            <span>Loading Cryptographic Key Registry...</span>
          </div>
        ) : displayedKeys.length === 0 ? (
          /* Empty State */
          <div className="p-12 text-center text-ink-500">
            <Key className="w-8 h-8 mx-auto mb-3 opacity-30 text-ink-900" />
            <p className="text-xs uppercase font-bold text-ink-800">
              {activeTab === "active"
                ? "No Active Machine-to-Machine Credentials"
                : "No Revoked Keys in Historical Registry"}
            </p>
            <p className="text-[11px] text-ink-500 mt-1 max-w-sm mx-auto">
              {activeTab === "active"
                ? "Generate an API key to allow external banking middleware or ingestion scripts to interact with DeepTrace."
                : "All previously issued keys remain active or no keys have been revoked."}
            </p>
            {activeTab === "active" && (
              <button
                type="button"
                onClick={() => setCreateModalOpen(true)}
                className="mt-4 px-4 py-2 bg-ink-900 text-paper-0 hover:bg-black text-xs uppercase font-bold tracking-wider inline-flex items-center gap-2 transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Issue First Key</span>
              </button>
            )}
          </div>
        ) : (
          /* Credentials Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="border-b border-rule bg-paper-2 text-[10px] text-ink-600 uppercase tracking-wider">
                  <th className="py-2.5 px-4 font-semibold">Consumer Identifier</th>
                  <th className="py-2.5 px-4 font-semibold">Prefix</th>
                  <th className="py-2.5 px-4 font-semibold">Authorized Scopes</th>
                  <th className="py-2.5 px-4 font-semibold">Issued</th>
                  <th className="py-2.5 px-4 font-semibold">Status / Expiry</th>
                  <th className="py-2.5 px-4 font-semibold">Last Used</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {displayedKeys.map((key) => {
                  const isExpiringSoon =
                    key.is_active &&
                    key.expires_at &&
                    new Date(key.expires_at).getTime() - Date.now() <= 14 * 24 * 60 * 60 * 1000 &&
                    new Date(key.expires_at).getTime() > Date.now();

                  return (
                    <tr key={key.id} className="hover:bg-paper-1 transition-colors">
                      {/* Name */}
                      <td className="py-3 px-4 font-bold text-ink-900">
                        {key.name}
                      </td>

                      {/* Prefix */}
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 bg-paper-2 border border-rule text-[11px] font-mono font-bold text-ink-800">
                          {key.key_prefix}...
                        </span>
                      </td>

                      {/* Scopes */}
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {key.scopes.map((scope) => (
                            <span
                              key={scope}
                              className="px-1.5 py-0.5 text-[9px] bg-paper-2 border border-rule text-ink-700"
                            >
                              {scope}
                            </span>
                          ))}
                        </div>
                      </td>

                      {/* Issued Date */}
                      <td className="py-3 px-4 text-ink-600 text-[11px] tabular-nums">
                        {new Date(key.created_at).toLocaleDateString("en-PK", {
                          year: "numeric",
                          month: "short",
                          day: "2-digit",
                        })}
                      </td>

                      {/* Status / Expiry */}
                      <td className="py-3 px-4 text-[11px]">
                        {!key.is_active ? (
                          <span className="inline-flex items-center gap-1 text-rose-900 font-bold uppercase text-[10px]">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-900" />
                            Revoked
                          </span>
                        ) : key.is_expired ? (
                          <span className="inline-flex items-center gap-1 text-amber-900 font-bold uppercase text-[10px]">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-900" />
                            Expired
                          </span>
                        ) : isExpiringSoon ? (
                          <div className="space-y-0.5">
                            <span className="inline-flex items-center gap-1 text-amber-800 font-bold uppercase text-[10px]">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-pulse" />
                              Expiring Soon
                            </span>
                            <div className="text-[10px] text-ink-500 tabular-nums">
                              {new Date(key.expires_at!).toLocaleDateString("en-PK", {
                                month: "short",
                                day: "2-digit",
                              })}
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-0.5">
                            <span className="inline-flex items-center gap-1 text-emerald-800 font-bold uppercase text-[10px]">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                              Active
                            </span>
                            {key.expires_at ? (
                              <div className="text-[10px] text-ink-500 tabular-nums">
                                Expires:{" "}
                                {new Date(key.expires_at).toLocaleDateString("en-PK", {
                                  year: "numeric",
                                  month: "short",
                                  day: "2-digit",
                                })}
                              </div>
                            ) : (
                              <div className="text-[10px] text-ink-400">Never Expires</div>
                            )}
                          </div>
                        )}
                      </td>

                      {/* Last Used */}
                      <td className="py-3 px-4 text-ink-600 text-[11px] tabular-nums">
                        {key.last_used_at
                          ? new Date(key.last_used_at).toLocaleDateString("en-PK", {
                              month: "short",
                              day: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "Never"}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        {key.is_active ? (
                          <button
                            type="button"
                            onClick={() => setKeyToRevoke(key)}
                            className="px-2.5 py-1 text-[10px] uppercase font-bold text-rose-900 hover:text-white bg-paper-1 hover:bg-rose-900 border border-rose-900 transition-colors cursor-pointer inline-flex items-center gap-1"
                            title="Revoke programmatic access"
                          >
                            <Trash2 className="w-3 h-3" />
                            <span>Revoke</span>
                          </button>
                        ) : (
                          <span className="text-[10px] text-ink-400 uppercase italic">
                            Inactive
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* SBP Regulatory Footer Documentation */}
      <div className="p-4 bg-paper-1 border-2 border-rule text-xs space-y-2">
        <div className="flex items-center gap-2 font-bold uppercase text-ink-900 text-[11px]">
          <Shield className="w-4 h-4 text-ink-800" />
          <span>SBP Framework for Machine-to-Machine Ingestion Security</span>
        </div>
        <p className="text-[11px] text-ink-600 leading-relaxed">
          In compliance with the State Bank of Pakistan Cybersecurity Framework Section 4.2.3,
          all API keys issued within DeepTrace operate on the Principle of Least Privilege.
          Keys are stored via irreversible cryptographic hashing (SHA-256 with tenant salting).
          Each transaction authenticated through an API key generates an immutable entry in the
          institutional audit registry containing the key prefix, IP address, and operation payload.
        </p>
      </div>

      {/* Modals */}
      <CreateKeyModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={(newKey) => {
          setCreatedKeyData(newKey);
          fetchKeys();
        }}
      />

      <KeyRevealModal
        apiKeyData={createdKeyData}
        onClose={() => setCreatedKeyData(null)}
      />

      <RevokeKeyModal
        apiKey={keyToRevoke}
        isOpen={Boolean(keyToRevoke)}
        onClose={() => setKeyToRevoke(null)}
        onSuccess={() => {
          fetchKeys();
        }}
      />
    </div>
  );
}
