"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  Gauge,
  Building2,
  Receipt,
  Sparkles,
  RotateCcw,
  Loader2,
  ShieldCheck,
  AlertTriangle,
  ArrowLeft,
  Settings,
  Layers,
  ArrowUpRight,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { getOrganization, getOrganizationUsage } from "@/lib/api/client";
import { OrganizationDetails, OrganizationUsageStats } from "@/lib/types/forensics";
import { QuotaUsageMeter } from "@/components/billing/QuotaUsageMeter";
import { SubscriptionTierCard } from "@/components/billing/SubscriptionTierCard";
import { TierComparisonModal } from "@/components/billing/TierComparisonModal";
import { DocumentBreakdownCard } from "@/components/billing/DocumentBreakdownCard";
import { BillingHistoryTable } from "@/components/billing/BillingHistoryTable";
import { OrgSettingsModal } from "@/components/billing/OrgSettingsModal";

type ActiveTab = "overview" | "plans" | "history" | "settings";

export default function OrganizationBillingPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [org, setOrg] = useState<OrganizationDetails | null>(null);
  const [usage, setUsage] = useState<OrganizationUsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");

  // Modals
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  const isAdmin = user?.role === "ADMIN" || user?.role === "OWNER";

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [orgData, usageData] = await Promise.all([
        getOrganization(),
        getOrganizationUsage(),
      ]);
      setOrg(orgData);
      setUsage(usageData);
    } catch (err: any) {
      setError(err?.message || "Failed to load organization quota and billing data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchData();
    }
  }, [authLoading, isAuthenticated]);

  // Derived metrics
  const used = usage?.monthly_doc_used ?? org?.monthly_doc_used ?? 0;
  const limit = usage?.monthly_doc_limit ?? org?.monthly_doc_limit ?? 100;
  const remaining = usage?.remaining ?? org?.remaining_docs ?? 0;
  const usagePercentage = usage?.usage_percentage ?? org?.usage_percentage ?? 0;
  const daysUntilRenewal = usage?.days_until_renewal ?? org?.days_until_renewal ?? 30;
  const tier = usage?.subscription_tier ?? org?.subscription_tier ?? "FREE";

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-8 font-mono">
        <Loader2 className="w-8 h-8 animate-spin text-ink-900 mb-3" />
        <span className="text-xs uppercase tracking-widest text-ink-600">
          Loading Institutional Tenancy Metrics...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-6 font-mono">
        <div className="bg-paper-0 border-2 border-rose-900 p-8 shadow-2xl space-y-4">
          <div className="flex items-center gap-3 border-b border-rose-900 pb-4 text-rose-950">
            <AlertTriangle className="w-6 h-6 text-rose-700" />
            <h2 className="text-base font-bold uppercase tracking-wider">
              Authentication Required
            </h2>
          </div>
          <p className="text-xs text-ink-700 leading-relaxed">
            You must be authenticated within an institutional banking session to access organization
            quotas and billing records.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 px-4 py-2 bg-ink-900 text-paper-0 text-xs uppercase font-bold tracking-wider"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Proceed to Login</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-6 font-mono space-y-6">
      {/* Header */}
      <div className="border-b-2 border-ink-900 pb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-ink-500 mb-1">
              <span>Administration</span>
              <span>/</span>
              <span>Settings</span>
              <span>/</span>
              <span className="text-ink-900 font-bold">Quotas & Billing</span>
            </div>
            <h1 className="text-2xl font-serif text-ink-900 tracking-tight">
              Organization Quotas & Billing
            </h1>
            <p className="text-xs text-ink-600 mt-1 max-w-2xl">
              Licensed document intake capacity, real-time quota metering, and SBP regulatory
              usage auditing for <span className="font-bold text-ink-900">{org?.name || "Active Organization"}</span>.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={fetchData}
              disabled={loading}
              className="p-2 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-700 transition-colors cursor-pointer"
              title="Refresh Quota Metrics"
            >
              <RotateCcw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>

            {isAdmin && (
              <button
                type="button"
                onClick={() => setSettingsModalOpen(true)}
                className="px-3.5 py-2 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-800 text-xs uppercase font-bold tracking-wider transition-colors flex items-center gap-2 cursor-pointer"
              >
                <Settings className="w-3.5 h-3.5 text-ink-600" />
                <span>Settings</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => setUpgradeModalOpen(true)}
              className="px-4 py-2 bg-ink-900 hover:bg-black text-paper-0 text-xs uppercase font-bold tracking-wider transition-colors flex items-center gap-2 border border-ink-900 cursor-pointer shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isAdmin ? "Upgrade Tier" : "Inspect Plans"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-paper-0 border border-rule p-4">
          <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
            Ingested (This Cycle)
          </span>
          <div className="text-2xl font-bold text-ink-900 mt-1 font-mono">
            {used.toLocaleString()}
          </div>
          <span className="text-[10px] text-ink-400 mt-0.5 block">
            Documents processed
          </span>
        </div>

        <div className="bg-paper-0 border border-rule p-4">
          <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
            Remaining Allowance
          </span>
          <div className="text-2xl font-bold text-emerald-700 mt-1 font-mono">
            {remaining.toLocaleString()}
          </div>
          <span className="text-[10px] text-ink-400 mt-0.5 block">
            Of {limit.toLocaleString()} monthly quota
          </span>
        </div>

        <div className="bg-paper-0 border border-rule p-4">
          <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
            Capacity Utilization
          </span>
          <div
            className={`text-2xl font-bold mt-1 font-mono ${
              usagePercentage >= 90
                ? "text-rose-700"
                : usagePercentage >= 70
                ? "text-amber-700"
                : "text-ink-900"
            }`}
          >
            {usagePercentage}%
          </div>
          <span className="text-[10px] text-ink-400 mt-0.5 block">
            {usagePercentage >= 90 ? "Threshold limit reached" : "Intake rate healthy"}
          </span>
        </div>

        <div className="bg-paper-0 border border-rule p-4">
          <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
            Active Plan Tier
          </span>
          <div className="text-sm font-bold text-ink-900 mt-2 flex items-center gap-1.5 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>{tier}</span>
          </div>
          <span className="text-[10px] text-ink-400 mt-0.5 block">
            Renews in {daysUntilRenewal} days
          </span>
        </div>
      </div>

      {/* SBP Framework Compliance Banner */}
      <div className="p-3 bg-paper-1 border border-rule flex items-center justify-between text-xs text-ink-600">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-ink-700 shrink-0" />
          <span>
            Under the State Bank of Pakistan (SBP) Framework for Risk Management in Outsourcing
            (BPRD/2020), document intake quotas and custody storage are isolated and metered per
            licensed institutional tenancy.
          </span>
        </div>
        <button
          type="button"
          onClick={() => setUpgradeModalOpen(true)}
          className="text-ink-900 underline hover:text-black shrink-0 font-bold ml-4 cursor-pointer"
        >
          View Tiers
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-rule pb-2">
          <div className="flex items-center gap-2">
            {(
              [
                { id: "overview", label: "Quota & Consumption" },
                { id: "plans", label: "Subscription Tiers" },
                { id: "history", label: "Billing History & Statements" },
                { id: "settings", label: "Tenancy Settings" },
              ] as { id: ActiveTab; label: string }[]
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`px-3.5 py-1 text-xs uppercase font-bold tracking-wider transition-colors cursor-pointer ${
                  activeTab === tab.id
                    ? "bg-ink-900 text-paper-0"
                    : "bg-paper-1 text-ink-600 hover:text-ink-900 border border-rule"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-3">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-700" />
            <span>{error}</span>
          </div>
        )}

        {/* Tab 1: Overview & Quota */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <QuotaUsageMeter
              used={used}
              limit={limit}
              remaining={remaining}
              usagePercentage={usagePercentage}
              daysUntilRenewal={daysUntilRenewal}
              billingCycleStart={usage?.billing_cycle_start || org?.billing_cycle_start}
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SubscriptionTierCard
                currentTier={tier}
                monthlyLimit={limit}
                isAdmin={isAdmin}
                onOpenUpgrade={() => setUpgradeModalOpen(true)}
              />

              <DocumentBreakdownCard
                breakdown={usage?.document_type_breakdown || {}}
                totalUsed={used}
              />
            </div>
          </div>
        )}

        {/* Tab 2: Subscription Plans */}
        {activeTab === "plans" && (
          <div className="space-y-4">
            <div className="bg-paper-0 border-2 border-ink-900 p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-rule pb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
                    Institutional Matrix
                  </span>
                  <h3 className="text-base font-bold uppercase tracking-wider text-ink-900">
                    Subscription Tiers & Throughput Limits
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setUpgradeModalOpen(true)}
                  className="px-4 py-2 bg-ink-900 hover:bg-black text-paper-0 text-xs uppercase font-bold tracking-wider transition-colors inline-flex items-center gap-2 cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isAdmin ? "Manage Tier Upgrade" : "Inspect Tier Details"}</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
                {[
                  {
                    name: "Community Sandbox",
                    code: "FREE",
                    limit: "100 Docs / mo",
                    desc: "Prototype evaluation and local verification.",
                    badge: "Free",
                  },
                  {
                    name: "Fintech Growth",
                    code: "FINTECH_GROWTH",
                    limit: "2,000 Docs / mo",
                    desc: "Regional banking and digital micro-lending pipelines.",
                    badge: "Tier 1",
                  },
                  {
                    name: "Business Scale",
                    code: "BUSINESS_SCALE",
                    limit: "15,000 Docs / mo",
                    desc: "Commercial clearing houses with priority GPU pipelines.",
                    badge: "Tier 2",
                  },
                  {
                    name: "Enterprise Sovereign",
                    code: "ENTERPRISE",
                    limit: "100,000+ Docs / mo",
                    desc: "SBP Central Bank and sovereign national consortia.",
                    badge: "Sovereign",
                  },
                ].map((item) => {
                  const isActive = tier === item.code;
                  return (
                    <div
                      key={item.code}
                      className={`p-4 border space-y-3 ${
                        isActive
                          ? "border-2 border-ink-900 bg-paper-1 shadow-sm"
                          : "border-rule bg-paper-0"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] uppercase tracking-wider text-ink-500 font-bold">
                          {item.badge}
                        </span>
                        {isActive && (
                          <span className="px-2 py-0.5 bg-emerald-700 text-paper-0 text-[9px] font-bold uppercase tracking-wider">
                            Active
                          </span>
                        )}
                      </div>
                      <div>
                        <h4 className="font-bold text-ink-900 text-sm">{item.name}</h4>
                        <div className="text-xs font-bold text-ink-900 font-mono mt-0.5">
                          {item.limit}
                        </div>
                        <p className="text-[11px] text-ink-500 mt-1 leading-relaxed">
                          {item.desc}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Billing History & Statements */}
        {activeTab === "history" && (
          <BillingHistoryTable
            currentTier={tier}
            monthlyLimit={limit}
            monthlyUsed={used}
            billingCycleStart={usage?.billing_cycle_start || org?.billing_cycle_start}
          />
        )}

        {/* Tab 4: Tenancy Settings */}
        {activeTab === "settings" && (
          <div className="bg-paper-0 border-2 border-ink-900 p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-rule pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-ink-900 text-paper-0">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
                    Tenancy Profile
                  </span>
                  <h3 className="text-base font-bold uppercase tracking-wider text-ink-900">
                    Institutional Entity Governance
                  </h3>
                </div>
              </div>

              {isAdmin && (
                <button
                  type="button"
                  onClick={() => setSettingsModalOpen(true)}
                  className="px-4 py-2 bg-ink-900 hover:bg-black text-paper-0 text-xs uppercase font-bold tracking-wider transition-colors inline-flex items-center gap-2 cursor-pointer"
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>Edit Settings</span>
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
              <div className="space-y-1 p-4 bg-paper-1 border border-rule">
                <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
                  Institutional Name
                </span>
                <span className="font-bold text-ink-900 text-sm block">
                  {org?.name || "Not Specified"}
                </span>
              </div>

              <div className="space-y-1 p-4 bg-paper-1 border border-rule">
                <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
                  Tenancy Slug
                </span>
                <span className="font-bold text-ink-900 text-sm block font-mono">
                  {org?.slug || "default-org"}
                </span>
              </div>

              <div className="space-y-1 p-4 bg-paper-1 border border-rule">
                <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
                  Custom Domain Routing
                </span>
                <span className="font-bold text-ink-900 text-sm block font-mono">
                  {org?.domain || "None (Default Multi-Tenant Routing)"}
                </span>
              </div>

              <div className="space-y-1 p-4 bg-paper-1 border border-rule">
                <span className="text-[10px] uppercase tracking-wider text-ink-500 block">
                  Quota Warning Threshold
                </span>
                <span className="font-bold text-ink-900 text-sm block">
                  {org?.settings?.alert_threshold_pct || 80}% Capacity
                </span>
              </div>
            </div>

            {!isAdmin && (
              <div className="p-3 bg-paper-2 border border-rule text-[11px] text-ink-500">
                You are currently signed in with role [{user?.role}]. Only institutional administrators
                (ADMIN or OWNER) can modify tenancy settings.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      <TierComparisonModal
        isOpen={upgradeModalOpen}
        currentTier={tier}
        isAdmin={isAdmin}
        onClose={() => setUpgradeModalOpen(false)}
        onSuccess={() => {
          fetchData();
        }}
      />

      <OrgSettingsModal
        isOpen={settingsModalOpen}
        org={org}
        onClose={() => setSettingsModalOpen(false)}
        onSuccess={() => {
          fetchData();
        }}
      />
    </div>
  );
}
