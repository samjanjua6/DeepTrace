"use client";

import React, { useState, useEffect } from "react";
import { X, Globe, Shield, AlertTriangle, Loader2 } from "lucide-react";
import { createWebhook } from "@/lib/api/client";
import { WebhookEndpointCreated } from "@/lib/types/forensics";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { useScrollLock } from "@/lib/hooks/useScrollLock";

interface CreateWebhookModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (createdEndpoint: WebhookEndpointCreated) => void;
}

const AVAILABLE_EVENTS = [
  {
    id: "investigation.completed",
    label: "investigation.completed",
    description: "Triggered immediately when forensic docket finishes all 6 pipeline stages.",
    defaultChecked: true,
  },
  {
    id: "risk.critical",
    label: "risk.critical",
    description: "Triggered when composite forensic risk score exceeds institutional threshold.",
    defaultChecked: true,
  },
  {
    id: "custody.sealed",
    label: "custody.sealed",
    description: "Triggered when a document receives an RFC 3161 cryptographic timestamp seal.",
    defaultChecked: false,
  },
  {
    id: "*",
    label: "* (Wildcard - All Events)",
    description: "Receive all system events including intake, pipeline transitions, and risk updates.",
    defaultChecked: false,
  },
];

export function CreateWebhookModal({ isOpen, onClose, onSuccess }: CreateWebhookModalProps) {
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([
    "investigation.completed",
    "risk.critical",
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useFocusTrap<HTMLDivElement>(isOpen);
  useScrollLock(isOpen);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleToggleEvent = (eventId: string) => {
    setSelectedEvents((prev) => {
      if (eventId === "*") {
        return prev.includes("*") ? [] : ["*"];
      }
      const withoutWildcard = prev.filter((e) => e !== "*");
      if (withoutWildcard.includes(eventId)) {
        return withoutWildcard.filter((e) => e !== eventId);
      } else {
        return [...withoutWildcard, eventId];
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) {
      setError("Destination URL is required.");
      return;
    }
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      setError("Destination URL must start with https:// (or http:// for testing).");
      return;
    }
    if (selectedEvents.length === 0) {
      setError("At least one event trigger must be selected.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        url: url.trim(),
        events: selectedEvents,
        description: description.trim() || undefined,
      };
      const created = await createWebhook(payload);
      onSuccess(created);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to register webhook endpoint.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-label="Register Webhook Endpoint"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 font-mono"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative"
        onClick={(e) => e.stopPropagation()}
      >
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
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2 bg-paper-2 border border-ink-900">
            <Globe className="w-5 h-5 text-ink-900" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-ink-900">
              Register Webhook Endpoint
            </h2>
            <p className="text-[11px] text-ink-500">
              Automated HTTP Callback with Timestamped HMAC-SHA256 Signatures
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-900 text-rose-900 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* URL Input */}
          <div>
            <label htmlFor="webhook-url" className="block text-[11px] font-bold uppercase text-ink-800 mb-1">
              Destination URL (HTTPS Enforced in Production)
            </label>
            <input
              id="webhook-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://core-banking.meezanbank.com/api/v1/webhooks/deeptrace"
              className="w-full px-3 py-2 text-xs bg-paper-1 border border-ink-900 text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-1 focus:ring-ink-900"
              disabled={loading}
              autoFocus
            />
          </div>

          {/* Description Input */}
          <div>
            <label htmlFor="webhook-description" className="block text-[11px] font-bold uppercase text-ink-800 mb-1">
              Endpoint Description / Consumer System
            </label>
            <input
              id="webhook-description"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Meezan Core Banking Middleware / T24 Event Ingestion"
              className="w-full px-3 py-2 text-xs bg-paper-1 border border-ink-900 text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-1 focus:ring-ink-900"
              disabled={loading}
            />
          </div>

          {/* Event Triggers */}
          <div>
            <label className="block text-[11px] font-bold uppercase text-ink-800 mb-1.5">
              Subscribed Event Triggers
            </label>
            <div className="space-y-2 border border-rule bg-paper-1 p-3">
              {AVAILABLE_EVENTS.map((ev) => {
                const checked = selectedEvents.includes(ev.id);
                return (
                  <label
                    key={ev.id}
                    className="flex items-start gap-2.5 cursor-pointer select-none hover:bg-paper-2 p-1 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleToggleEvent(ev.id)}
                      disabled={loading}
                      className="mt-0.5 rounded-none border-ink-900 text-ink-900 focus:ring-0 cursor-pointer"
                    />
                    <div className="text-xs">
                      <span className="font-bold text-ink-900">{ev.label}</span>
                      <p className="text-[11px] text-ink-600 leading-tight mt-0.5">
                        {ev.description}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* SBP Compliance Notice */}
          <div className="p-3 bg-paper-2 border border-rule text-[10px] text-ink-600 leading-relaxed flex items-start gap-2.5">
            <Shield className="w-4 h-4 text-ink-800 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold uppercase tracking-wider text-ink-900 block mb-0.5">
                SBP Cybersecurity Framework Directive
              </span>
              All dispatched HTTP requests carry timestamped HMAC-SHA256 signatures in the{" "}
              <code className="bg-paper-0 px-1 border border-rule font-bold">X-DeepTrace-Signature</code>{" "}
              header. Receiver systems must verify this signature before processing payloads.
            </div>
          </div>

          {/* Actions */}
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
              type="submit"
              disabled={loading}
              className="px-5 py-2 text-xs uppercase font-bold text-paper-0 bg-ink-900 hover:bg-black border border-ink-900 transition-colors flex items-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Registering...</span>
                </>
              ) : (
                <span>Register Endpoint</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
