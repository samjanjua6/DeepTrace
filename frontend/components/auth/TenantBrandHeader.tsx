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
    <div className="border-b-2 border-ink-900 pb-5 mb-6 select-none font-mono">
      {/* Top Enclave Classification Strip */}
      <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-ink-500 mb-2">
        <span className="flex items-center gap-1.5 font-bold text-ink-700">
          <ShieldCheck className="w-3.5 h-3.5 text-forensic-teal" />
          <span>INSTITUTIONAL CLEARANCE GATEWAY</span>
        </span>
        <Badge variant={isCustomTenant ? "inverse" : "neutral"} size="xs">
          {isCustomTenant ? "TENANT RESTRICTED" : "CORE FEDERATION"}
        </Badge>
      </div>

      {/* Primary Brand & Tenant Typography */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl text-ink-900 font-semibold tracking-tight leading-tight">
            DeepTrace Forensics
          </h1>
          <div className="mt-1 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-ink-500 shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-ink-900">
              {tenant?.name || "State Bank of Pakistan Certified Gateway"}
            </span>
          </div>
        </div>

        {/* Tenant Monogram / Seal */}
        <div className="w-12 h-12 bg-paper-1 border-2 border-ink-900 flex items-center justify-center font-bold text-xs text-ink-900 shrink-0 shadow-sm">
          {tenant?.slug
            ? tenant.slug.slice(0, 3).toUpperCase()
            : "DTF"}
        </div>
      </div>

      {/* Tenancy & Protocol Metadata */}
      <div className="mt-3 pt-2.5 border-t border-rule/60 flex items-center justify-between text-[10.5px] text-ink-600">
        <span>
          Clearance Boundary:{" "}
          <strong className="text-ink-900">
            {tenant?.domain || "central.deeptrace.internal"}
          </strong>
        </span>
        <span className="uppercase text-[9.5px] font-semibold text-ink-500">
          {tenant?.tier ? `${tenant.tier} ENCLAVE` : "SBP BPRD COMPLIANT"}
        </span>
      </div>
    </div>
  );
}
