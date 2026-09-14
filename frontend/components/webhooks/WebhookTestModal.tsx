"use client";

import React, { useState } from "react";
import {
  X,
  Play,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Terminal,
  Clock,
  ShieldCheck,
} from "lucide-react";
import { testWebhookEndpoint } from "@/lib/api/client";
import { WebhookEndpointItem, WebhookTestResult } from "@/lib/types/forensics";

interface WebhookTestModalProps {
  endpoint: WebhookEndpointItem | null;
  isOpen: boolean;
  onClose: () => void;
  onTestSuccess: () => void;
}

const TEST_EVENTS = [
  { id: "test.ping", label: "test.ping (Standard Diagnostic Ping)" },
  { id: "investigation.completed", label: "investigation.completed (Docket Finished)" },
  { id: "risk.critical", label: "risk.critical (High Risk Flagged)" },
  { id: "custody.sealed", label: "custody.sealed (RFC 3161 Timestamp Applied)" },
];

export function WebhookTestModal({
  endpoint,
  isOpen,
  onClose,
  onTestSuccess,
}: WebhookTestModalProps) {
  const [eventType, setEventType] = useState("test.ping");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WebhookTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !endpoint) return null;

  const handleRunTest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const testResult = await testWebhookEndpoint(endpoint.id, eventType);
      setResult(testResult);
      onTestSuccess();
    } catch (err: any) {
      setError(err?.message || "Failed to execute webhook test.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-2xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative max-h-[90vh] overflow-y-auto">
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
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-4">
          <div className="p-2 bg-paper-2 border border-ink-900">
            <Play className="w-5 h-5 text-ink-900" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-ink-900">
              Live Webhook Signature & Connectivity Test
            </h2>
            <p className="text-[11px] text-ink-500 truncate max-w-md">
              Target: {endpoint.url}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-900 text-rose-900 text-xs">
            {error}
          </div>
        )}

        {/* Event Selector & Run Button */}
        <div className="p-4 bg-paper-1 border border-rule mb-5 space-y-3">
          <div>
            <label className="block text-[11px] font-bold uppercase text-ink-800 mb-1">
              Select Event Payload Type
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              disabled={loading}
              className="w-full px-3 py-2 text-xs bg-paper-0 border border-ink-900 text-ink-900 focus:outline-none focus:ring-1 focus:ring-ink-900 cursor-pointer"
            >
              {TEST_EVENTS.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[10px] text-ink-500">
              Generates genuine HMAC-SHA256 signature with endpoint secret.
            </span>
            <button
              type="button"
              onClick={handleRunTest}
              disabled={loading}
              className="px-5 py-2 text-xs uppercase font-bold text-paper-0 bg-ink-900 hover:bg-black border border-ink-900 transition-colors flex items-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Dispatching...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>Send Test Ping</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Live Diagnostics Card */}
        {result && (
          <div className="border-2 border-ink-900 bg-paper-0 p-4 space-y-3 mb-5">
            <div className="flex items-center justify-between border-b border-rule pb-2">
              <div className="flex items-center gap-2">
                {result.success ? (
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-900 border border-emerald-800 text-[10px] font-bold uppercase">
                    Delivery Successful (HTTP {result.http_status_code})
                  </span>
                ) : (
                  <span className="px-2 py-0.5 bg-rose-100 text-rose-900 border border-rose-800 text-[10px] font-bold uppercase">
                    Delivery Failed ({result.http_status_code ? `HTTP ${result.http_status_code}` : "Connection Error"})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5 text-xs text-ink-600 tabular-nums">
                <Clock className="w-3.5 h-3.5 text-ink-500" />
                <span>Round-Trip Latency: {result.response_duration_ms}ms</span>
              </div>
            </div>

            {/* Signature Sent */}
            <div>
              <span className="text-[10px] font-bold uppercase text-ink-600 block mb-1">
                Header Dispatched: X-DeepTrace-Signature
              </span>
              <div className="p-2 bg-paper-2 border border-rule text-[11px] font-mono select-all break-all">
                {result.signature_header}
              </div>
            </div>

            {/* Error Message if any */}
            {result.error_message && (
              <div className="p-3 bg-rose-50 border border-rose-900 text-rose-900 text-xs">
                <span className="font-bold block uppercase text-[10px] mb-0.5">
                  Failure Reason:
                </span>
                {result.error_message}
              </div>
            )}

            {/* Response Body Snippet */}
            {result.response_body && (
              <div>
                <span className="text-[10px] font-bold uppercase text-ink-600 block mb-1">
                  Remote Server Response Body:
                </span>
                <div className="p-2.5 bg-zinc-950 text-zinc-200 text-[11px] font-mono overflow-x-auto max-h-32">
                  <pre>{result.response_body}</pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-end pt-3 border-t border-rule">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 text-xs uppercase font-bold text-ink-700 bg-paper-1 hover:bg-paper-2 border border-rule hover:border-ink-900 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
