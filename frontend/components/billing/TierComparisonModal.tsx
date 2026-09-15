"use client";

import React, { useState } from "react";
import { X, Check, ShieldCheck, AlertCircle, Loader2, Sparkles, Building2 } from "lucide-react";
import { upgradeSubscriptionTier } from "@/lib/api/client";

interface TierComparisonModalProps {
  isOpen: boolean;
  currentTier: string;
  isAdmin: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface TierDefinition {
  id: "FREE" | "FINTECH_GROWTH" | "BUSINESS_SCALE" | "ENTERPRISE";
  title: string;
  volume: string;
  priceNote: string;
  features: string[];
  bestFor: string;
}

const TIERS: TierDefinition[] = [
  {
    id: "FREE",
    title: "Community Sandbox",
    volume: "100 Documents / mo",
    priceNote: "Free Community",
    bestFor: "Local testing and prototype evaluations",
    features: [
      "100 document monthly allowance",
      "Standard OCR & PDF layout analysis",
      "7-day evidence retention",
      "Single tenancy workspace",
    ],
  },
  {
    id: "FINTECH_GROWTH",
    title: "Fintech Growth",
    volume: "2,000 Documents / mo",
    priceNote: "Institutional Tier 1",
    bestFor: "Regional banks and digital micro-lenders",
    features: [
      "2,000 document monthly allowance",
      "RFC 3161 cryptographic timestamping",
      "Outbound Webhooks event delivery",
      "90-day custody retention",
      "Multi-tenant switching",
    ],
  },
  {
    id: "BUSINESS_SCALE",
    title: "Business Scale",
    volume: "15,000 Documents / mo",
    priceNote: "High Throughput",
    bestFor: "Commercial banking clearing houses & audit firms",
    features: [
      "15,000 document monthly allowance",
      "Priority GPU hardware acceleration",
      "Full Forensic Swarm LLM & Urdu briefings",
      "Granular API Key management",
      "1-year custody audit preservation",
    ],
  },
  {
    id: "ENTERPRISE",
    title: "Enterprise Sovereign",
    volume: "100,000+ Documents / mo",
    priceNote: "Custom State SLA",
    bestFor: "State Bank of Pakistan (SBP) & Federal Regulators",
    features: [
      "100,000+ custom document throughput",
      "Dedicated Hardware Security Module (HSM)",
      "Air-gapped / on-premises SBP deployment",
      "Perpetual ETO 2002 chain-of-custody",
      "24/7 dedicated cybersecurity hotline",
    ],
  },
];

export function TierComparisonModal({
  isOpen,
  currentTier,
  isAdmin,
  onClose,
  onSuccess,
}: TierComparisonModalProps) {
  const [loadingTier, setLoadingTier] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const activeKey = currentTier?.toUpperCase() || "FREE";

  const handleApplyTier = async (targetTier: string) => {
    if (!isAdmin) return;
    setLoadingTier(targetTier);
    setError(null);

    try {
      await upgradeSubscriptionTier(targetTier);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to upgrade subscription tier.");
    } finally {
      setLoadingTier(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-5xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative max-h-[92vh] overflow-y-auto">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={loadingTier !== null}
          className="absolute top-4 right-4 text-ink-500 hover:text-ink-900 transition-colors p-1 cursor-pointer"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-6">
          <div className="p-2.5 bg-ink-900 text-paper-0">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Capacity Governance
            </span>
            <h2 className="text-lg font-bold uppercase tracking-wider text-ink-900">
              Institutional Subscription Tiers
            </h2>
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-700" />
            <span>{error}</span>
          </div>
        )}

        {/* SBP Regulatory Notice */}
        <div className="p-3 bg-paper-1 border border-rule text-xs text-ink-700 mb-6 flex items-start gap-2">
          <ShieldCheck className="w-4 h-4 shrink-0 text-ink-800 mt-0.5" />
          <div>
            Under the State Bank of Pakistan (SBP) Framework for Risk Management in Outsourcing
            (BPRD/2020), document processing volume changes are recorded in the central compliance
            audit trail with immediate tenancy quota recalibration.
          </div>
        </div>

        {/* 4 Tiers Comparison Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {TIERS.map((tier) => {
            const isActive = activeKey === tier.id;
            const isLoadingThis = loadingTier === tier.id;

            return (
              <div
                key={tier.id}
                className={`p-4 border flex flex-col justify-between space-y-4 transition-colors ${
                  isActive
                    ? "border-2 border-ink-900 bg-paper-1 shadow-sm"
                    : "border-rule bg-paper-0 hover:border-ink-600"
                }`}
              >
                <div className="space-y-3">
                  {/* Top Badge */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-ink-500">
                      {tier.priceNote}
                    </span>
                    {isActive && (
                      <span className="px-2 py-0.5 bg-emerald-700 text-paper-0 text-[9px] font-bold uppercase tracking-wider">
                        Active Plan
                      </span>
                    )}
                  </div>

                  <div>
                    <h3 className="text-base font-bold font-serif text-ink-900">
                      {tier.title}
                    </h3>
                    <div className="text-sm font-bold text-ink-900 font-mono mt-1">
                      {tier.volume}
                    </div>
                    <p className="text-[11px] text-ink-500 mt-1 leading-relaxed">
                      {tier.bestFor}
                    </p>
                  </div>

                  {/* Feature Bullets */}
                  <div className="space-y-1.5 pt-3 border-t border-rule">
                    {tier.features.map((feat, idx) => (
                      <div key={idx} className="flex items-start gap-1.5 text-[11px] text-ink-800">
                        <Check className="w-3 h-3 text-emerald-600 shrink-0 mt-0.5" />
                        <span>{feat}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Tier Selection Button */}
                <div className="pt-3 border-t border-rule">
                  {isActive ? (
                    <div className="w-full py-2 bg-paper-2 border border-rule text-ink-500 text-center text-xs uppercase font-bold tracking-wider cursor-default">
                      Active Plan
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleApplyTier(tier.id)}
                      disabled={!isAdmin || loadingTier !== null}
                      className={`w-full py-2 text-xs uppercase font-bold tracking-wider flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
                        isAdmin
                          ? "bg-ink-900 hover:bg-black text-paper-0"
                          : "bg-paper-2 text-ink-400 border border-rule cursor-not-allowed"
                      }`}
                    >
                      {isLoadingThis ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="w-3.5 h-3.5" />
                      )}
                      <span>
                        {isLoadingThis
                          ? "Applying..."
                          : isAdmin
                          ? "Apply Tier"
                          : "Admin Only"}
                      </span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Modal Actions */}
        <div className="flex justify-end pt-6 mt-6 border-t border-rule">
          <button
            type="button"
            onClick={onClose}
            disabled={loadingTier !== null}
            className="px-5 py-2 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-700 text-xs uppercase font-bold tracking-wider transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
