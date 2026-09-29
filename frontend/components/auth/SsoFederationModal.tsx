"use client";

import React, { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { initiateSso, SsoInitiateResponse } from "@/lib/api/client";
import { ExternalLink, CheckCircle2 } from "lucide-react";

interface SsoFederationModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultDomain?: string;
}

export function SsoFederationModal({
  isOpen,
  onClose,
  defaultDomain = "",
}: SsoFederationModalProps) {
  const [selectedProvider, setSelectedProvider] = useState<string>("azure_ad");
  const [domain, setDomain] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [ssoResult, setSsoResult] = useState<SsoInitiateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sync domain only if a genuine enterprise domain is passed
  useEffect(() => {
    if (defaultDomain && !defaultDomain.includes("internal") && !defaultDomain.includes("platform")) {
      setDomain(defaultDomain);
    } else {
      setDomain("");
    }
  }, [defaultDomain, isOpen]);

  const providers = [
    {
      id: "azure_ad",
      name: "Microsoft Entra ID (Azure AD)",
      protocol: "SAML 2.0",
      description: "Direct SAML & OIDC federation for enterprise bank directories.",
    },
    {
      id: "okta",
      name: "Okta Identity Cloud",
      protocol: "OIDC",
      description: "Cloud identity and multi-factor hardware token authentication.",
    },
    {
      id: "saml",
      name: "Institutional SAML / ADFS",
      protocol: "SAML 2.0",
      description: "On-premise Active Directory Federation Services or Shibboleth.",
    },
  ];

  const handleInitiateSso = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await initiateSso({
        provider: selectedProvider,
        tenant_domain: domain.trim() || undefined,
        redirect_uri: "/investigations",
      });
      setSsoResult(res);
    } catch (err: any) {
      setError(err?.message || "Failed to initiate institutional SSO federation.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleProceedRedirect = () => {
    if (ssoResult?.sso_url) {
      window.location.href = ssoResult.sso_url;
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      category="Enterprise Authentication"
      title="Single Sign-On (SSO)"
      maxWidth="lg"
    >
      {!ssoResult ? (
        <form onSubmit={handleInitiateSso} className="space-y-4 font-sans text-xs select-none">
          <p className="text-xs text-ink-600 leading-relaxed">
            Sign in using your organization&apos;s identity provider.
          </p>

          {/* Provider Selection */}
          <div className="space-y-2">
            <label className="block text-[11px] font-mono font-bold text-ink-700 uppercase tracking-wider">
              Identity Provider
            </label>
            <div className="space-y-2">
              {providers.map((p) => {
                const isSelected = selectedProvider === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedProvider(p.id)}
                    className={`p-3 border transition-colors cursor-pointer flex items-center justify-between gap-3 ${
                      isSelected
                        ? "border-ink-900 bg-paper-1"
                        : "border-rule bg-paper-0 hover:bg-paper-1/60"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 ${
                          isSelected ? "border-ink-900" : "border-ink-300"
                        }`}
                      >
                        {isSelected && <div className="w-2 h-2 rounded-full bg-ink-900" />}
                      </div>
                      <div>
                        <div className="font-semibold text-ink-900 text-xs">
                          {p.name}
                        </div>
                        <p className="text-[11px] text-ink-500 mt-0.5">
                          {p.description}
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 border border-rule text-ink-600 bg-paper-0 shrink-0">
                      {p.protocol}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Institutional Domain Input */}
          <div>
            <label
              htmlFor="sso-domain"
              className="block text-[11px] font-mono font-bold text-ink-700 uppercase tracking-wider mb-1"
            >
              Organization Domain (Optional)
            </label>
            <Input
              id="sso-domain"
              type="text"
              placeholder="e.g. meezanbank.com, hbl.com"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            />
            <span className="text-[11px] text-ink-500 mt-1 block">
              Auto-routes authentication to your organization&apos;s dedicated realm.
            </span>
          </div>

          {error && (
            <div className="p-2.5 bg-forensic-red/10 border border-forensic-red/40 text-forensic-red text-xs font-mono">
              {error}
            </div>
          )}

          <div className="pt-3 border-t border-rule flex items-center justify-end gap-2.5">
            <Button type="button" variant="secondary" size="md" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
            >
              Continue with SSO
            </Button>
          </div>
        </form>
      ) : (
        <div className="space-y-4 font-mono text-xs select-none">
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-900 space-y-1 font-sans">
            <div className="flex items-center gap-2 font-bold text-xs uppercase">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>Identity Provider Handshake Ready</span>
            </div>
            <p className="text-[11px] text-emerald-800 leading-relaxed">
              {ssoResult.message}
            </p>
          </div>

          <div className="bg-paper-1 border border-rule p-3 space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-ink-500 uppercase">Provider:</span>
              <strong className="text-ink-900 uppercase">{ssoResult.provider}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-500 uppercase">Protocol:</span>
              <strong className="text-ink-900">{ssoResult.protocol}</strong>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-ink-500 uppercase">Entity ID:</span>
              <span className="text-ink-900 font-bold break-all bg-paper-0 p-1 border border-rule">
                {ssoResult.entity_id}
              </span>
            </div>
          </div>

          <div className="pt-3 border-t border-rule flex items-center justify-between">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setSsoResult(null)}
            >
              ← Back
            </Button>
            <div className="flex items-center gap-2">
              <Button type="button" variant="secondary" size="sm" onClick={onClose}>
                Close
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={handleProceedRedirect}
                rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
              >
                Proceed to IdP Login
              </Button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
