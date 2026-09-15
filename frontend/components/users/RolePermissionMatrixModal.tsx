"use client";

import React from "react";
import { X, Shield, Check, Minus, FileCheck, Scale } from "lucide-react";

interface RolePermissionMatrixModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CapabilityRow {
  category: string;
  capability: string;
  owner: boolean;
  admin: boolean;
  analyst: boolean;
  viewer: boolean;
}

const MATRIX_DATA: CapabilityRow[] = [
  {
    category: "Forensic Investigation",
    capability: "Upload documents and launch automated forensics pipelines",
    owner: true,
    admin: true,
    analyst: true,
    viewer: false,
  },
  {
    category: "Forensic Investigation",
    capability: "View dockets, evidence items, and chain-of-custody ledgers",
    owner: true,
    admin: true,
    analyst: true,
    viewer: true,
  },
  {
    category: "Forensic Investigation",
    capability: "Submit supervised analyst risk score overrides",
    owner: true,
    admin: true,
    analyst: true,
    viewer: false,
  },
  {
    category: "Security & Integrations",
    capability: "Issue and revoke enterprise REST API keys",
    owner: true,
    admin: true,
    analyst: false,
    viewer: false,
  },
  {
    category: "Security & Integrations",
    capability: "Configure institutional webhook dispatch endpoints",
    owner: true,
    admin: true,
    analyst: false,
    viewer: false,
  },
  {
    category: "Security & Integrations",
    capability: "Inspect SBP BPRD/2020 immutable audit logs",
    owner: true,
    admin: true,
    analyst: false,
    viewer: false,
  },
  {
    category: "Identity & Access",
    capability: "Onboard personnel and issue clearance dispatch memos",
    owner: true,
    admin: true,
    analyst: false,
    viewer: false,
  },
  {
    category: "Identity & Access",
    capability: "Modify role assignments (Admin, Analyst, Viewer)",
    owner: true,
    admin: true,
    analyst: false,
    viewer: false,
  },
  {
    category: "Identity & Access",
    capability: "Unlock brute-force locked accounts and emergency 2FA reset",
    owner: true,
    admin: true,
    analyst: false,
    viewer: false,
  },
  {
    category: "Identity & Access",
    capability: "Promote personnel to Sovereign Organization Owner",
    owner: true,
    admin: false,
    analyst: false,
    viewer: false,
  },
  {
    category: "Tenancy Governance",
    capability: "Manage subscription limits, billing quotas, and upgrade tiers",
    owner: true,
    admin: false,
    analyst: false,
    viewer: false,
  },
];

export function RolePermissionMatrixModal({
  isOpen,
  onClose,
}: RolePermissionMatrixModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-3xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative max-h-[92vh] overflow-y-auto">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-ink-500 hover:text-ink-900 transition-colors p-1 cursor-pointer"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2.5 bg-ink-900 text-paper-0">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Governance Framework
            </span>
            <h2 className="text-lg font-bold uppercase tracking-wider text-ink-900">
              Role & Clearance Permission Matrix
            </h2>
          </div>
        </div>

        {/* Regulatory Note */}
        <div className="p-3 bg-paper-1 border border-ink-900/30 text-ink-700 text-xs mb-5 flex items-start gap-2.5">
          <Shield className="w-4 h-4 shrink-0 text-ink-900 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold uppercase tracking-wider text-ink-900 block">
              State Bank of Pakistan (SBP) BPRD/2020 Standard
            </span>
            <p className="text-[11px] leading-relaxed text-ink-600">
              Clearance assignments follow the principle of least privilege.
              Administrative actions, credential resets, and clearance escalations are immutably audited with IP and user identity signatures.
            </p>
          </div>
        </div>

        {/* Comparison Matrix Table */}
        <div className="border-2 border-ink-900 overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-ink-900 text-paper-0 border-b border-ink-900">
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] w-1/2">
                  System Capability / Action
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] text-center w-[12.5%]">
                  Owner
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] text-center w-[12.5%]">
                  Admin
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] text-center w-[12.5%]">
                  Analyst
                </th>
                <th className="p-3 font-bold uppercase tracking-wider text-[11px] text-center w-[12.5%]">
                  Viewer
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-900/20">
              {MATRIX_DATA.map((row, idx) => {
                const prevCategory = idx > 0 ? MATRIX_DATA[idx - 1].category : null;
                const isNewCategory = row.category !== prevCategory;

                return (
                  <React.Fragment key={idx}>
                    {isNewCategory && (
                      <tr className="bg-paper-2 border-y border-ink-900/30">
                        <td
                          colSpan={5}
                          className="px-3 py-1.5 font-bold uppercase tracking-wider text-[10px] text-ink-600"
                        >
                          {row.category}
                        </td>
                      </tr>
                    )}
                    <tr className="hover:bg-paper-1/60 transition-colors">
                      <td className="p-3 text-ink-800 text-[11px]">
                        {row.capability}
                      </td>
                      <td className="p-3 text-center border-l border-ink-900/10">
                        {row.owner ? (
                          <span className="inline-flex items-center justify-center w-5 h-5 bg-ink-900 text-paper-0">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </span>
                        ) : (
                          <Minus className="w-4 h-4 mx-auto text-ink-300" />
                        )}
                      </td>
                      <td className="p-3 text-center border-l border-ink-900/10">
                        {row.admin ? (
                          <span className="inline-flex items-center justify-center w-5 h-5 bg-ink-900 text-paper-0">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </span>
                        ) : (
                          <Minus className="w-4 h-4 mx-auto text-ink-300" />
                        )}
                      </td>
                      <td className="p-3 text-center border-l border-ink-900/10">
                        {row.analyst ? (
                          <span className="inline-flex items-center justify-center w-5 h-5 bg-ink-900 text-paper-0">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </span>
                        ) : (
                          <Minus className="w-4 h-4 mx-auto text-ink-300" />
                        )}
                      </td>
                      <td className="p-3 text-center border-l border-ink-900/10">
                        {row.viewer ? (
                          <span className="inline-flex items-center justify-center w-5 h-5 bg-ink-900 text-paper-0">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </span>
                        ) : (
                          <Minus className="w-4 h-4 mx-auto text-ink-300" />
                        )}
                      </td>
                    </tr>
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end pt-5 mt-4 border-t border-ink-900/20">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 bg-ink-900 text-paper-0 hover:bg-ink-800 font-bold uppercase tracking-wider text-xs transition-colors cursor-pointer"
          >
            Acknowledge & Close
          </button>
        </div>
      </div>
    </div>
  );
}
