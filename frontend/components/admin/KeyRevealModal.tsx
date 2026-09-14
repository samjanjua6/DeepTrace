"use client";

import React, { useState } from "react";
import { Check, Copy, Key, ShieldAlert, Terminal } from "lucide-react";
import { ApiKeyCreatedResponse } from "@/lib/types/forensics";

interface KeyRevealModalProps {
  apiKeyData: ApiKeyCreatedResponse | null;
  onClose: () => void;
}

type TabType = "curl" | "python" | "node";

export function KeyRevealModal({ apiKeyData, onClose }: KeyRevealModalProps) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>("curl");

  if (!apiKeyData) return null;

  const plaintext = apiKeyData.plaintext_key;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(plaintext);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textArea = document.createElement("textarea");
      textArea.value = plaintext;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getQuickstartCode = (tab: TabType) => {
    switch (tab) {
      case "curl":
        return `# Verify Institutional Connectivity
curl -X GET "https://api.deeptrace.meezanbank.com/api/v1/investigations" \\
  -H "X-API-Key: ${plaintext}" \\
  -H "Accept: application/json"`;

      case "python":
        return `import httpx

client = httpx.Client(
    base_url="https://api.deeptrace.meezanbank.com/api/v1",
    headers={
        "X-API-Key": "${plaintext}",
        "Accept": "application/json",
    },
    timeout=30.0,
)

# Fetch Active Forensic Dockets
response = client.get("/investigations")
print("HTTP Status:", response.status_code)
dockets = response.json()
print("Retrieved dockets:", len(dockets))`;

      case "node":
        return `// Node.js 18+ Native Fetch Integration
const response = await fetch("https://api.deeptrace.meezanbank.com/api/v1/investigations", {
  method: "GET",
  headers: {
    "X-API-Key": "${plaintext}",
    "Accept": "application/json",
  },
});

if (!response.ok) {
  throw new Error(\`DeepTrace Error: \${response.statusText}\`);
}

const dockets = await response.json();
console.log("Active Forensic Dockets:", dockets.length);`;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono">
      <div className="w-full max-w-2xl bg-paper-0 border-2 border-ink-900 shadow-2xl p-6 relative max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2 bg-paper-2 border border-ink-900">
            <Key className="w-5 h-5 text-ink-900" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-ink-900">
              API Key Issued Successfully
            </h2>
            <p className="text-[11px] text-ink-500">
              Identifier: {apiKeyData.name} ({apiKeyData.key_prefix}...)
            </p>
          </div>
        </div>

        {/* Security Warning Banner */}
        <div className="mb-5 p-4 bg-amber-50 border-2 border-amber-900 text-amber-950 text-xs flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-amber-900 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold uppercase tracking-wider block mb-1">
              One-Time Plaintext Credential Reveal
            </span>
            <p className="leading-relaxed text-[11px]">
              Store this secret key now in your institutional secrets manager (e.g. HashiCorp Vault,
              AWS Secrets Manager). Under State Bank of Pakistan cryptographic compliance, DeepTrace
              only stores a salted SHA-256 hash. This secret cannot be recovered after this modal is
              closed.
            </p>
          </div>
        </div>

        {/* Key Display & Copy */}
        <div className="mb-5">
          <label className="block text-[11px] font-bold uppercase text-ink-800 mb-1">
            Plaintext API Key
          </label>
          <div className="flex items-center gap-2">
            <div className="flex-1 p-2.5 bg-paper-2 border-2 border-ink-900 font-mono text-xs text-ink-900 select-all overflow-x-auto break-all font-bold">
              {plaintext}
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

        {/* Quickstart Integration Tabs */}
        <div className="mb-5 border border-ink-900 bg-paper-1">
          <div className="flex items-center justify-between border-b border-ink-900 px-3 py-2 bg-paper-2">
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-ink-900">
              <Terminal className="w-3.5 h-3.5" />
              <span>Integration Quickstart</span>
            </div>
            <div className="flex items-center gap-1">
              {(["curl", "python", "node"] as TabType[]).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
                  className={`px-2.5 py-0.5 text-[10px] uppercase font-bold tracking-wider border transition-colors ${
                    activeTab === tab
                      ? "bg-ink-900 text-paper-0 border-ink-900"
                      : "bg-paper-0 text-ink-700 border-rule hover:border-ink-900"
                  }`}
                >
                  {tab === "node" ? "Node.js" : tab.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div className="p-3 bg-zinc-950 text-zinc-100 text-[11px] leading-relaxed overflow-x-auto font-mono selection:bg-zinc-800">
            <pre>{getQuickstartCode(activeTab)}</pre>
          </div>
        </div>

        {/* Dismissal Button */}
        <div className="flex items-center justify-end pt-3 border-t border-rule">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-6 py-2.5 text-xs uppercase font-bold text-paper-0 bg-ink-900 hover:bg-black border border-ink-900 transition-colors"
          >
            I Have Securely Saved This Credential
          </button>
        </div>
      </div>
    </div>
  );
}
