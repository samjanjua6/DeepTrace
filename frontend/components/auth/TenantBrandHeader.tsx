"use client";

import React from "react";
import { Building2 } from "lucide-react";

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
    <div className="pb-4 mb-4 border-b border-rule select-none">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-serif text-2xl font-bold tracking-tight text-ink-900 leading-none">
              DeepTrace
            </h1>
            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 bg-paper-1 border border-rule text-ink-600 font-semibold tracking-wider">
              Forensics
            </span>
          </div>
          <div className="mt-1.5 flex items-center gap-1.5 text-xs text-ink-500 font-mono">
            {isCustomTenant ? (
              <>
                <Building2 className="w-3.5 h-3.5 text-ink-500 shrink-0" />
                <span className="font-semibold text-ink-800">{tenant.name}</span>
                <span className="text-ink-400">•</span>
                <span>Institutional Portal</span>
              </>
            ) : (
              <span>Institutional Verification Gateway</span>
            )}
          </div>
        </div>

        {isCustomTenant && tenant?.slug && (
          <div className="h-8 px-2.5 bg-paper-1 border border-rule flex items-center justify-center font-mono font-bold text-xs text-ink-700 tracking-wider shrink-0">
            {tenant.slug.slice(0, 3).toUpperCase()}
          </div>
        )}
      </div>
    </div>
  );
}
