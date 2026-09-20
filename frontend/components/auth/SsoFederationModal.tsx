"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { initiateSso, SsoInitiateResponse } from "@/lib/api/client";
import { ExternalLink, KeyRound, CheckCircle2 } from "lucide-react";

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
  const [domain, setDomain] = useState<string>(defaultDomain);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [ssoResult, setSsoResult] = useState<SsoInitiateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const providers = [
    {
      id: "azure_ad",
      name: "Microsoft Entra ID (Azure AD)",
      protocol: "SAML 2.0 / WS-FED",
      recommended: true,
      description:
        "Direct SAML 2.0 & OIDC federation with enterprise Azure Active Directory tenants for Pakistani core banks.",
    },
    {
      id: "okta",
      name: "Okta Identity Cloud",
      protocol: "OIDC / SAML 2.0",
      recommended: false,
      description:
        "Automated SCIM user provisioning and hardware security token authentication (FIDO2 / WebAuthn).",
    },
    {
      id: "saml",
      name: "Institutional SAML 2.0 / ADFS",
      protocol: "SAML 2.0 (ETO 2002)",
      recommended: false,
      description:
        "On-premise Active Directory Federation Services (ADFS) or Shibboleth IdP connector.",
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
      // In production, redirects to the institutional IdP
      window.location.href = ssoResult.sso_url;
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      category="ENTERPRISE WORKFORCE FEDERATION"
      title="Single Sign-On (SSO) Directory Gateway"
      maxWidth="xl"
    >
      {!ssoResult ? (
        <form onSubmit={handleInitiateSso} className="space-y-4 font-mono text-xs select-none">
          <p className="text-xs text-ink-700 leading-relaxed">
            Federate your institutional session using SAML 2.0, Active Directory, or Okta Identity Cloud in compliance with SBP Enterprise Cyber Security Framework.
          </p>

          {/* Provider Selection */}
          <div className="space-y-2">
            <label className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider">
              Select Enterprise Identity Provider:
            </label>
            <div className="space-y-2">
              {providers.map((p) => {
                const isSelected = selectedProvider === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedProvider(p.id)}
                    className={`p-3 border-2 transition-all cursor-pointer ${
                      isSelected
                        ? "border-ink-900 bg-paper-1 shadow-sm"
                        : "border-rule bg-paper-0 hover:bg-paper-1/60"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <KeyRound className="w-3.5 h-3.5 text-ink-900 shrink-0" />
                        <span className="font-bold text-ink-900 text-xs uppercase">
                          {p.name}
                        </span>
                      </div>
                      <Badge variant={isSelected ? "inverse" : "neutral"} size="xs">
                        {p.protocol}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-ink-600 leading-snug">
                      {p.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Institutional Domain Input */}
          <div>
            <label htmlFor="sso-domain" className="block text-[11px] font-bold text-ink-700 uppercase tracking-wider mb-1">
              Institutional Email Domain (Optional for Auto-Routing):
            </label>
            <Input
              id="sso-domain"
              type="text"
              placeholder="e.g. meezanbank.com, hbl.com, ubl.com.pk"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            />
            <span className="text-[11px] text-ink-500 mt-1 block">
              Directs SAML AuthnRequest to your bank&apos;s dedicated single sign-on realm.
            </span>
          </div>

          {error && (
            <div className="p-2.5 bg-forensic-red/10 border border-forensic-red/40 text-forensic-red text-[11px]">
              {error}
            </div>
          )}

          <div className="pt-3 border-t border-rule flex items-center justify-end gap-3">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={isLoading}
              rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
            >
              Initiate SSO Handshake
            </Button>
          </div>
        </form>
      ) : (
        <div className="space-y-4 font-mono text-xs select-none">
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-900 space-y-1">
            <div className="flex items-center gap-2 font-bold text-xs uppercase">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>SAML 2.0 / OAuth2 Handshake Ready</span>
            </div>
            <p className="text-[11px] text-emerald-800 leading-relaxed">
              {ssoResult.message}
            </p>
          </div>

          <div className="bg-paper-1 border border-rule p-3 space-y-2 text-[11px]">
            <div className="flex justify-between">
              <span className="text-ink-500 uppercase text-[11px]">Identity Provider:</span>
              <strong className="text-ink-900 uppercase">{ssoResult.provider}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-500 uppercase text-[11px]">Protocol:</span>
              <strong className="text-ink-900">{ssoResult.protocol}</strong>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-ink-500 uppercase text-[11px]">Service Provider Entity ID:</span>
              <span className="text-ink-900 font-bold break-all bg-paper-0 p-1 border border-rule text-[11px]">
                {ssoResult.entity_id}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-ink-500 uppercase text-[11px]">Target IdP Authorization URL:</span>
              <span className="text-ink-900 font-bold break-all bg-paper-0 p-1 border border-rule text-[11px]">
                {ssoResult.sso_url}
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
              ← Choose Different Provider
            </Button>
            <div className="flex items-center gap-2">
              <Button type="button" variant="secondary" onClick={onClose}>
                Close
              </Button>
              <Button
                type="button"
                variant="primary"
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
