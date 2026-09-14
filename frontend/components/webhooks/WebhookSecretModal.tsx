"use client";

import React, { useState } from "react";
import { Check, Copy, KeyRound, ShieldAlert, X } from "lucide-react";
import { WebhookEndpointItem } from "@/lib/types/forensics";

interface WebhookSecretModalProps {
  endpoint: WebhookEndpointItem | null;
  secret: string | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenGuide: () => void;
}

export function WebhookSecretModal({
  endpoint,
  secret,
  isOpen,
  onClose,
  onOpenGuide,
}: WebhookSecretModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !endpoint || !secret) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textArea = document.createElement("textarea");
      textArea.value = secret;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-ink-500 hover:text-ink-900 transition-colors p-1"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2 bg-paper-2 border border-ink-900">
            <KeyRound className="w-5 h-5 text-ink-900" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-ink-900">
              Webhook HMAC Signing Secret
            </h2>
            <p className="text-[11px] text-ink-500">
              Cryptographic Key for Endpoint Verification ({endpoint.url})
            </p>
          </div>
        </div>

        {/* Security Warning */}
        <div className="mb-5 p-4 bg-amber-50 border-2 border-amber-900 text-amber-950 text-xs flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-amber-900 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold uppercase tracking-wider block mb-1">
              Confidential Signing Secret
            </span>
            <p className="leading-relaxed text-[11px]">
              Configure this secret in your receiving service environment. Every webhook payload
              is signed using HMAC-SHA256 with this key. Never expose this secret in client-side code.
            </p>
          </div>
        </div>

        {/* Secret Display & Copy */}
        <div className="mb-5">
          <label className="block text-[11px] font-bold uppercase text-ink-800 mb-1">
            HMAC Secret (32-byte Hexadecimal)
          </label>
          <div className="flex items-center gap-2">
            <div className="flex-1 p-2.5 bg-paper-2 border-2 border-ink-900 font-mono text-xs text-ink-900 select-all overflow-x-auto break-all font-bold">
              {secret}
            </div>
            <button
              type="button"
              onClick={handleCopy}
              className={`px-4 py-2.5 border-2 border-ink-900 text-xs uppercase font-bold tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer shrink-0 ${
                copied
                  ? "bg-emerald-700 text-white border-emerald-900"
                  : "bg-ink-900 text-paper-0 hover:bg-black"
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-3 border-t border-rule">
          <button
            type="button"
            onClick={onOpenGuide}
            className="text-xs uppercase font-bold text-ink-900 underline hover:text-black cursor-pointer"
          >
            View Verification Guide ↗
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 text-xs uppercase font-bold text-paper-0 bg-ink-900 hover:bg-black border border-ink-900 transition-colors"
          >
            I Have Saved This Secret
          </button>
        </div>
      </div>
    </div>
  );
}
