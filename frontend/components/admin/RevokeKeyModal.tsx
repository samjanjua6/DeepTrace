"use client";

import React, { useState } from "react";
import { AlertOctagon, Loader2, X } from "lucide-react";
import { revokeApiKey } from "@/lib/api/client";
import { ApiKeyItem } from "@/lib/types/forensics";

interface RevokeKeyModalProps {
  apiKey: ApiKeyItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function RevokeKeyModal({ apiKey, isOpen, onClose, onSuccess }: RevokeKeyModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !apiKey) return null;

  const handleRevoke = async () => {
    setLoading(true);
    setError(null);
    try {
      await revokeApiKey(apiKey.id);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to revoke API key.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-lg bg-paper-0 border-2 border-rose-900 shadow-2xl p-6 relative">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={loading}
          className="absolute top-4 right-4 text-ink-500 hover:text-ink-900 transition-colors p-1"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b-2 border-rose-900 pb-4 mb-4">
          <div className="p-2 bg-rose-100 border border-rose-900 text-rose-900">
            <AlertOctagon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-rose-950">
              Revoke Machine-to-Machine Credential
            </h2>
            <p className="text-[11px] text-ink-500">
              Permanent Deactivation & Immediate Session Termination
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-900 text-rose-900 text-xs">
            {error}
          </div>
        )}

        {/* Key Target Info */}
        <div className="p-3 bg-paper-2 border border-rule mb-4 space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-ink-500 uppercase text-[10px]">Key Identifier:</span>
            <span className="font-bold text-ink-900">{apiKey.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-500 uppercase text-[10px]">Key Prefix:</span>
            <span className="font-mono text-ink-900">{apiKey.key_prefix}...</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-500 uppercase text-[10px]">Active Scopes:</span>
            <span className="font-mono text-ink-700">{apiKey.scopes.join(", ")}</span>
          </div>
        </div>

        {/* Warning Text */}
        <div className="p-3 bg-rose-50 border border-rose-300 text-rose-950 text-xs leading-relaxed mb-5">
          <p className="font-bold uppercase text-[11px] mb-1">
            Immediate Invalidation Directive
          </p>
          <p className="text-[11px]">
            Revocation is permanent and cannot be undone. Any core banking service, document ingestion
            job, or external API client using this key will immediately receive HTTP 401 Unauthorized.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-rule">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-xs uppercase font-semibold text-ink-700 bg-paper-1 hover:bg-paper-2 border border-rule hover:border-ink-900 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleRevoke}
            disabled={loading}
            className="px-5 py-2 text-xs uppercase font-bold text-white bg-rose-900 hover:bg-black border border-rose-900 transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Revoking...</span>
              </>
            ) : (
              <span>Confirm Revocation</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
