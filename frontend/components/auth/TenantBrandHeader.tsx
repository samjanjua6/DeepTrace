"use client";

import React from "react";
import { ShieldCheck, Building2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export interface TenantIdentity {
  name: string;
  slug: string;
  domain?: string;
  tier?: string;
  category?: string;
}

interface TenantBrandHeaderProps {
  tenant: TenantIdentity | null;
}

export function TenantBrandHeader({ tenant }: TenantBrandHeaderProps) {
  const isCustomTenant = tenant && tenant.slug !== "platform-default";

  return (
    <div className="border-b-2 border-ink-900 pb-2.5 mb-2.5 select-none font-mono">
      {/* Top Enclave Classification Strip */}
      <div className="flex items-center justify-between text-[11px] uppercase tracking-widest text-ink-500 mb-1.5">
        <span className="flex items-center gap-1.5 font-bold text-ink-700">
          <ShieldCheck className="w-3.5 h-3.5 text-forensic-teal" />
          <span>INSTITUTIONAL CLEARANCE GATEWAY</span>
        </span>
        <Badge
          variant={isCustomTenant ? "inverse" : "neutral"}
          size="sm"
          className="text-[11px] px-1.5 py-0.5"
        >
          {isCustomTenant ? "TENANT RESTRICTED" : "CORE FEDERATION"}
        </Badge>
      </div>

      {/* Primary Brand & Tenant Typography */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl text-ink-900 font-semibold tracking-tight leading-tight">
            DeepTrace Forensics
          </h1>
          <div className="mt-0.5 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-ink-500 shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-ink-900">
              {tenant?.name || "State Bank of Pakistan Certified Gateway"}
            </span>
          </div>
        </div>

        {/* Tenant Monogram / Seal */}
        <div className="w-10 h-10 bg-paper-1 border-2 border-ink-900 flex items-center justify-center font-bold text-xs text-ink-900 shrink-0 shadow-sm">
          {tenant?.slug
            ? tenant.slug.slice(0, 3).toUpperCase()
            : "DTF"}
        </div>
      </div>

      {/* Tenancy & Protocol Metadata */}
      <div className="mt-2 pt-1.5 border-t border-rule/60 flex items-center justify-between text-[11px] text-ink-600">
        <span>
          Clearance Boundary:{" "}
          <strong className="text-ink-900">
            {tenant?.domain || "central.deeptrace.internal"}
          </strong>
        </span>
        <span className="uppercase text-[11px] font-semibold text-ink-500">
          {tenant?.tier
            ? tenant.tier.trim().toUpperCase().endsWith("ENCLAVE")
              ? tenant.tier.trim()
              : `${tenant.tier.trim()} ENCLAVE`
            : "SBP BPRD COMPLIANT"}
        </span>
      </div>
    </div>
  );
}
