"use client";

import React from "react";
import { Sparkles, ArrowUpRight, ShieldCheck, Check, Database, Zap } from "lucide-react";

interface SubscriptionTierCardProps {
  currentTier: string;
  monthlyLimit: number;
  isAdmin: boolean;
  onOpenUpgrade: () => void;
}

const TIER_DESCRIPTIONS: Record<string, { label: string; tag: string; description: string; highlights: string[] }> = {
  FREE: {
    label: "Community Sandbox",
    tag: "Evaluation Tier",
    description: "Ideal for local verification, unit tests, and proof-of-concept document forensic reviews.",
    highlights: [
      "100 Documents / Month",
      "Standard Optical Character Recognition",
      "7-Day Evidence Retention",
      "Community GitHub Support",
    ],
  },
  FINTECH_GROWTH: {
    label: "Fintech Growth",
    tag: "Production Banking",
    description: "Built for regional banks, microfinance institutions, and digital lending verification teams.",
    highlights: [
      "2,000 Documents / Month",
      "RFC 3161 Legal Evidence Custody Seals",
      "Outbound Webhook Event Dispatcher",
      "90-Day Evidence Retention & Audit Trails",
    ],
  },
  BUSINESS_SCALE: {
    label: "Business Scale",
    tag: "High-Throughput Institutional",
    description: "Designed for commercial clearing houses, national credit bureaus, and automated loan pipelines.",
    highlights: [
      "15,000 Documents / Month",
      "Priority GPU Pipeline Acceleration",
      "Full Forensic Swarm LLM & Urdu Briefings",
      "Multi-Tenant Tenant Switching & API Keys",
    ],
  },
  ENTERPRISE: {
    label: "State / Enterprise Sovereign",
    tag: "Regulatory Framework Sovereign",
    description: "Tailored for the State Bank of Pakistan (SBP), federal law enforcement, and Tier-1 banking consortia.",
    highlights: [
      "100,000+ Custom Document Intake Capacity",
      "Dedicated Hardware Security Module (HSM)",
      "On-Premises / Air-Gapped SBP Deployment",
      "24/7 Dedicated Security Operations SLA",
    ],
  },
};

export function SubscriptionTierCard({
  currentTier,
  monthlyLimit,
  isAdmin,
  onOpenUpgrade,
}: SubscriptionTierCardProps) {
  const tierKey = currentTier?.toUpperCase() || "FREE";
  const tierInfo = TIER_DESCRIPTIONS[tierKey] || TIER_DESCRIPTIONS.FREE;

  return (
    <div className="bg-paper-0 border-2 border-ink-900 p-6 font-mono shadow-sm flex flex-col justify-between space-y-6">
      {/* Top Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500">
            Licensed Tenancy
          </span>
          <span className="px-2 py-0.5 bg-ink-900 text-paper-0 text-[10px] font-bold uppercase tracking-wider">
            {tierInfo.tag}
          </span>
        </div>

        <div>
          <h3 className="text-xl font-bold font-serif text-ink-900 tracking-tight">
            {tierInfo.label}
          </h3>
          <p className="text-xs text-ink-600 mt-1 leading-relaxed">
            {tierInfo.description}
          </p>
        </div>

        {/* Feature List */}
        <div className="space-y-2 pt-2 border-t border-rule">
          {tierInfo.highlights.map((feature, idx) => (
            <div key={idx} className="flex items-start gap-2 text-xs text-ink-800">
              <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
              <span>{feature}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Action Footer */}
      <div className="pt-4 border-t border-rule space-y-2">
        <button
          type="button"
          onClick={onOpenUpgrade}
          className="w-full py-2.5 bg-ink-900 hover:bg-black text-paper-0 text-xs uppercase font-bold tracking-wider transition-colors flex items-center justify-center gap-2 cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>{isAdmin ? "Change Subscription Tier" : "Inspect Tier Offerings"}</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
        {!isAdmin && (
          <span className="text-[10px] text-ink-400 text-center block">
            Institutional Admin or Owner role required to apply plan upgrades.
          </span>
        )}
      </div>
    </div>
  );
}
