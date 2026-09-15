"use client";

import React, { useState } from "react";
import { X, Building2, ShieldCheck, AlertCircle, Loader2 } from "lucide-react";
import { updateOrganizationSettings } from "@/lib/api/client";
import { OrganizationDetails } from "@/lib/types/forensics";

interface OrgSettingsModalProps {
  isOpen: boolean;
  org: OrganizationDetails | null;
  onClose: () => void;
  onSuccess: () => void;
}

export function OrgSettingsModal({
  isOpen,
  org,
  onClose,
  onSuccess,
}: OrgSettingsModalProps) {
  const [name, setName] = useState(org?.name || "");
  const [domain, setDomain] = useState(org?.domain || "");
  const [alertThreshold, setAlertThreshold] = useState(
    org?.settings?.alert_threshold_pct ? String(org.settings.alert_threshold_pct) : "80"
  );
  const [complianceEmail, setComplianceEmail] = useState(
    org?.settings?.compliance_email || ""
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !org) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await updateOrganizationSettings({
        name: name.trim() || undefined,
        domain: domain.trim() || undefined,
        settings: {
          ...(org.settings || {}),
          alert_threshold_pct: parseInt(alertThreshold, 10) || 80,
          compliance_email: complianceEmail.trim(),
        },
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to update organization settings.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative">
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
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Tenancy Governance
            </span>
            <h2 className="text-lg font-bold uppercase tracking-wider text-ink-900">
              Organization Settings
            </h2>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-700" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {/* Organization Name */}
          <div className="space-y-1.5">
            <label className="block font-bold uppercase tracking-wider text-ink-800">
              Institutional Entity Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 bg-paper-1 border border-rule focus:border-ink-900 outline-none text-ink-900 font-mono text-xs"
              placeholder="e.g. State Bank of Pakistan — Banking Supervision Directorate"
            />
          </div>

          {/* Dedicated Custom Domain */}
          <div className="space-y-1.5">
            <label className="block font-bold uppercase tracking-wider text-ink-800">
              Custom Whitelabel Domain (Optional)
            </label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full px-3 py-2 bg-paper-1 border border-rule focus:border-ink-900 outline-none text-ink-900 font-mono text-xs"
              placeholder="e.g. forensics.meezanbank.com"
            />
            <span className="text-[10px] text-ink-400 block">
              Configures custom CNAME routing for institutional single sign-on.
            </span>
          </div>

          {/* Quota Alert Threshold */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="block font-bold uppercase tracking-wider text-ink-800">
                Capacity Warning Threshold (%)
              </label>
              <select
                value={alertThreshold}
                onChange={(e) => setAlertThreshold(e.target.value)}
                className="w-full px-3 py-2 bg-paper-1 border border-rule focus:border-ink-900 outline-none text-ink-900 font-mono text-xs cursor-pointer"
              >
                <option value="70">70% Capacity</option>
                <option value="80">80% Capacity (Recommended)</option>
                <option value="90">90% Capacity</option>
                <option value="95">95% Capacity</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="block font-bold uppercase tracking-wider text-ink-800">
                Compliance Alert Email
              </label>
              <input
                type="email"
                value={complianceEmail}
                onChange={(e) => setComplianceEmail(e.target.value)}
                className="w-full px-3 py-2 bg-paper-1 border border-rule focus:border-ink-900 outline-none text-ink-900 font-mono text-xs"
                placeholder="compliance@bank.com.pk"
              />
            </div>
          </div>

          {/* Compliance Disclaimer */}
          <div className="p-3 bg-paper-1 border border-rule flex items-start gap-2 text-[11px] text-ink-600 mt-2">
            <ShieldCheck className="w-4 h-4 text-ink-700 shrink-0 mt-0.5" />
            <span>
              All tenancy setting modifications are recorded in the immutable PostgreSQL compliance
              audit log under SBP BPRD/2020 operational resilience mandates.
            </span>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-rule mt-6">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-700 uppercase font-bold tracking-wider cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-ink-900 hover:bg-black text-paper-0 uppercase font-bold tracking-wider flex items-center gap-2 cursor-pointer shadow-sm"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>{loading ? "Saving Settings..." : "Save Settings"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
