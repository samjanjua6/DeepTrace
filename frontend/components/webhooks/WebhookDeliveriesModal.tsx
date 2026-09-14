"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  History,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { getWebhookDeliveries } from "@/lib/api/client";
import { WebhookEndpointItem, WebhookDeliveryLog } from "@/lib/types/forensics";

interface WebhookDeliveriesModalProps {
  endpoint: WebhookEndpointItem | null;
  isOpen: boolean;
  onClose: () => void;
}

export function WebhookDeliveriesModal({
  endpoint,
  isOpen,
  onClose,
}: WebhookDeliveriesModalProps) {
  const [deliveries, setDeliveries] = useState<WebhookDeliveryLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchDeliveries = async () => {
    if (!endpoint) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getWebhookDeliveries(endpoint.id);
      setDeliveries(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load delivery history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && endpoint) {
      fetchDeliveries();
    }
  }, [isOpen, endpoint]);

  if (!isOpen || !endpoint) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-4xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative max-h-[90vh] flex flex-col">
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
        <div className="flex items-center justify-between border-b-2 border-ink-900 pb-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-paper-2 border border-ink-900">
              <History className="w-5 h-5 text-ink-900" />
            </div>
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-ink-900">
                Webhook Delivery History
              </h2>
              <p className="text-[11px] text-ink-500 truncate max-w-lg">
                Target: {endpoint.url}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={fetchDeliveries}
            disabled={loading}
            className="p-1.5 border border-rule hover:border-ink-900 bg-paper-1 hover:bg-paper-2 text-ink-700 transition-colors cursor-pointer mr-8"
            title="Refresh Deliveries"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-900 text-rose-900 text-xs">
            {error}
          </div>
        )}

        {/* Table Content */}
        <div className="flex-1 overflow-y-auto border border-rule">
          {loading ? (
            <div className="p-12 flex flex-col items-center justify-center text-ink-500 text-xs">
              <Loader2 className="w-6 h-6 animate-spin mb-2 text-ink-900" />
              <span>Loading delivery logs...</span>
            </div>
          ) : deliveries.length === 0 ? (
            <div className="p-12 text-center text-ink-500">
              <History className="w-8 h-8 mx-auto mb-2 opacity-30 text-ink-900" />
              <p className="text-xs uppercase font-bold text-ink-800">No Deliveries Recorded</p>
              <p className="text-[11px] text-ink-500 mt-1">
                No webhook events have been dispatched to this endpoint yet.
              </p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="border-b border-rule bg-paper-2 text-[10px] text-ink-600 uppercase tracking-wider sticky top-0">
                  <th className="py-2.5 px-3 font-semibold">Event</th>
                  <th className="py-2.5 px-3 font-semibold">Status Code</th>
                  <th className="py-2.5 px-3 font-semibold">Duration</th>
                  <th className="py-2.5 px-3 font-semibold">Attempt</th>
                  <th className="py-2.5 px-3 font-semibold">Timestamp</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {deliveries.map((deliv) => {
                  const isSuccess =
                    deliv.http_status_code !== null &&
                    deliv.http_status_code >= 200 &&
                    deliv.http_status_code < 300;
                  const isExpanded = expandedId === deliv.id;

                  return (
                    <React.Fragment key={deliv.id}>
                      <tr
                        className={`hover:bg-paper-1 transition-colors cursor-pointer ${
                          isExpanded ? "bg-paper-1" : ""
                        }`}
                        onClick={() => setExpandedId(isExpanded ? null : deliv.id)}
                      >
                        <td className="py-2.5 px-3 font-bold text-ink-900">
                          <span className="px-1.5 py-0.5 text-[9px] bg-paper-2 border border-rule">
                            {deliv.event_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          {isSuccess ? (
                            <span className="inline-flex items-center gap-1 text-emerald-800 font-bold text-[10px]">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                              HTTP {deliv.http_status_code} OK
                            </span>
                          ) : deliv.http_status_code ? (
                            <span className="inline-flex items-center gap-1 text-rose-900 font-bold text-[10px]">
                              <span className="w-1.5 h-1.5 rounded-full bg-rose-900" />
                              HTTP {deliv.http_status_code} Error
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-rose-900 font-bold text-[10px]">
                              <span className="w-1.5 h-1.5 rounded-full bg-rose-900" />
                              Connection Failed
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 tabular-nums text-ink-600 text-[11px]">
                          {deliv.response_duration_ms !== null
                            ? `${deliv.response_duration_ms}ms`
                            : "—"}
                        </td>
                        <td className="py-2.5 px-3 tabular-nums text-ink-600 text-[11px]">
                          Attempt {deliv.attempt}
                        </td>
                        <td className="py-2.5 px-3 tabular-nums text-ink-600 text-[11px]">
                          {new Date(deliv.created_at).toLocaleDateString("en-PK", {
                            month: "short",
                            day: "2-digit",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            type="button"
                            className="text-ink-600 hover:text-ink-900 p-1"
                          >
                            {isExpanded ? (
                              <ChevronUp className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Details Row */}
                      {isExpanded && (
                        <tr className="bg-paper-2 border-b border-rule">
                          <td colSpan={6} className="p-4 space-y-2 text-xs">
                            {deliv.error_message && (
                              <div className="p-2 bg-rose-50 border border-rose-900 text-rose-900 text-[11px]">
                                <span className="font-bold block uppercase text-[10px]">
                                  Error Diagnostic:
                                </span>
                                {deliv.error_message}
                              </div>
                            )}

                            {deliv.response_body && (
                              <div>
                                <span className="text-[10px] font-bold uppercase text-ink-600 block mb-1">
                                  Remote Server Response Body:
                                </span>
                                <div className="p-2 bg-zinc-950 text-zinc-200 text-[11px] font-mono overflow-x-auto max-h-36">
                                  <pre>{deliv.response_body}</pre>
                                </div>
                              </div>
                            )}

                            <div className="flex items-center justify-between text-[10px] text-ink-500 pt-1">
                              <span>Delivery ID: {deliv.id}</span>
                              {deliv.delivered_at && (
                                <span>Delivered: {new Date(deliv.delivered_at).toISOString()}</span>
                              )}
                              {deliv.failed_at && (
                                <span>Failed: {new Date(deliv.failed_at).toISOString()}</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-rule mt-4">
          <span className="text-[10px] text-ink-500">
            Showing latest {deliveries.length} delivery attempts.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs uppercase font-bold text-paper-0 bg-ink-900 hover:bg-black border border-ink-900 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
