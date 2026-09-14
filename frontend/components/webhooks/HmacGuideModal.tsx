"use client";

import React, { useState } from "react";
import { X, Copy, Check, Terminal, ShieldCheck, AlertCircle } from "lucide-react";

interface HmacGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type TabType = "python" | "node" | "curl";

const PYTHON_SNIPPET = `import hmac
import hashlib
import time
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
WEBHOOK_SECRET = "whsec_your_endpoint_secret_here"
TOLERANCE_SECONDS = 300  # 5-minute replay prevention window

def verify_deeptrace_signature(payload_bytes: bytes, header_val: str, secret: str) -> bool:
    try:
        parts = dict(item.split("=", 1) for item in header_val.split(","))
        timestamp = parts["t"]
        received_sig = parts["v1"]
    except (ValueError, KeyError):
        return False

    # 1. Replay attack guard
    current_time = int(time.time())
    if abs(current_time - int(timestamp)) > TOLERANCE_SECONDS:
        return False

    # 2. Signed payload: "{timestamp}.{raw_payload}"
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    # 3. Constant-time comparison
    return hmac.compare_digest(expected_sig, received_sig)

@app.post("/webhook")
async def receive_webhook(request: Request):
    sig_header = request.headers.get("X-DeepTrace-Signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature header")

    body_bytes = await request.body()
    if not verify_deeptrace_signature(body_bytes, sig_header, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    event = await request.json()
    print(f"Verified event received: {event.get('event')}")
    return {"status": "accepted"}
`;

const NODE_SNIPPET = `import crypto from "crypto";
import express from "express";

const app = express();
const WEBHOOK_SECRET = "whsec_your_endpoint_secret_here";
const TOLERANCE_SECONDS = 300; // 5-minute replay prevention window

// Note: Parse body as raw buffer before JSON parsing
app.post(
  "/webhook",
  express.raw({ type: "application/json" }),
  (req, res) => {
    const sigHeader = req.headers["x-deeptrace-signature"];
    if (!sigHeader || typeof sigHeader !== "string") {
      return res.status(400).send("Missing signature header");
    }

    // Extract t and v1
    const parts = Object.fromEntries(
      sigHeader.split(",").map((kv) => kv.split("=", 2))
    );
    const timestamp = parts.t;
    const receivedSig = parts.v1;

    if (!timestamp || !receivedSig) {
      return res.status(400).send("Malformed signature header");
    }

    // 1. Replay attack guard
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parseInt(timestamp, 10)) > TOLERANCE_SECONDS) {
      return res.status(401).send("Timestamp outside tolerance window");
    }

    // 2. Signed payload: "{timestamp}.{raw_payload}"
    const signedPayload = \`\${timestamp}.\${req.body.toString("utf-8")}\`;
    const expectedSig = crypto
      .createHmac("sha256", WEBHOOK_SECRET)
      .update(signedPayload)
      .digest("hex");

    // 3. Constant-time comparison
    const sigBufferA = Buffer.from(receivedSig, "utf-8");
    const sigBufferB = Buffer.from(expectedSig, "utf-8");

    if (
      sigBufferA.length !== sigBufferB.length ||
      !crypto.timingSafeEqual(sigBufferA, sigBufferB)
    ) {
      return res.status(401).send("Invalid HMAC signature");
    }

    const payload = JSON.parse(req.body.toString("utf-8"));
    console.log("Verified event received:", payload.event);
    return res.status(200).json({ status: "accepted" });
  }
);
`;

const CURL_SNIPPET = `# Verify local test dispatch via OpenSSL CLI
TIMESTAMP=$(date +%s)
SECRET="whsec_your_endpoint_secret_here"
BODY='{"event":"test.ping","payload":{"diagnostic":"verification"}}'

# Signed payload format: {timestamp}.{raw_body}
SIGNED_PAYLOAD="\${TIMESTAMP}.\${BODY}"
SIGNATURE=$(echo -n "\${SIGNED_PAYLOAD}" | openssl dgst -sha256 -hmac "\${SECRET}" | awk '{print $NF}')

curl -X POST https://your-server.domain.com/webhook \\
  -H "Content-Type: application/json" \\
  -H "X-DeepTrace-Signature: t=\${TIMESTAMP},v1=\${SIGNATURE}" \\
  -d "\${BODY}"
`;

export function HmacGuideModal({ isOpen, onClose }: HmacGuideModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>("python");
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const currentSnippet =
    activeTab === "python"
      ? PYTHON_SNIPPET
      : activeTab === "node"
      ? NODE_SNIPPET
      : CURL_SNIPPET;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(currentSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

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

        {/* Modal Header */}
        <div className="flex items-center gap-3 border-b-2 border-ink-900 pb-4 mb-5">
          <div className="p-2.5 bg-ink-900 text-paper-0">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <span className="text-[10px] font-bold uppercase tracking-widest text-ink-500 block">
              Cryptographic Integration Standard
            </span>
            <h2 className="text-lg font-bold uppercase tracking-wider text-ink-900">
              HMAC-SHA256 Signature Verification
            </h2>
          </div>
        </div>

        {/* Protocol Overview */}
        <div className="space-y-4 text-xs text-ink-700 leading-relaxed mb-6">
          <p>
            DeepTrace signs all outbound webhook deliveries using institutional HMAC-SHA256
            signatures complying with NIST SP 800-86 and SBP BPRD/2020 operational resilience
            guidelines. Receiving endpoints must verify the signature to prevent tampering and
            spoofing.
          </p>

          <div className="p-3 bg-paper-2 border border-rule space-y-2">
            <div className="font-bold text-ink-900 uppercase text-[11px]">
              Signature Header Specification:
            </div>
            <div className="bg-paper-0 p-2 border border-rule font-mono text-[11px] text-ink-900 select-all">
              X-DeepTrace-Signature: t=1726353912,v1=a1b2c3d4e5f6...
            </div>
            <ul className="list-disc pl-4 space-y-1 text-[11px] text-ink-600">
              <li>
                <span className="font-semibold text-ink-800">t</span>: Unix timestamp (seconds)
                indicating when the delivery was dispatched.
              </li>
              <li>
                <span className="font-semibold text-ink-800">v1</span>: Hex-encoded HMAC-SHA256
                digest computed over <code className="text-ink-900 font-bold">{"{t}.{raw_json_body}"}</code> using your endpoint secret.
              </li>
            </ul>
          </div>

          <div className="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-300 text-amber-900 text-[11px]">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-700" />
            <div>
              <span className="font-bold uppercase tracking-wider">Replay Attack Mitigation:</span>{" "}
              Reject any request where the absolute difference between your server clock and timestamp{" "}
              <code className="font-bold">t</code> exceeds 300 seconds (5 minutes). Always compare
              signatures using constant-time string comparison.
            </div>
          </div>
        </div>

        {/* Code Snippets Section */}
        <div className="border border-rule bg-paper-1">
          <div className="flex items-center justify-between border-b border-rule px-3 py-2 bg-paper-2">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-ink-600" />
              <div className="flex gap-1">
                {(["python", "node", "curl"] as TabType[]).map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setActiveTab(tab)}
                    className={`px-3 py-1 text-[11px] uppercase font-bold tracking-wider transition-colors cursor-pointer ${
                      activeTab === tab
                        ? "bg-ink-900 text-paper-0"
                        : "bg-paper-0 text-ink-600 hover:text-ink-900 border border-rule"
                    }`}
                  >
                    {tab === "python" ? "Python (FastAPI)" : tab === "node" ? "Node.js (Express)" : "cURL / Bash"}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={handleCopy}
              className="px-2.5 py-1 bg-paper-0 border border-rule hover:border-ink-900 text-ink-700 hover:text-ink-900 text-[10px] uppercase font-semibold tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-600" />
                  <span className="text-emerald-700 font-bold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 text-ink-500" />
                  <span>Copy Code</span>
                </>
              )}
            </button>
          </div>

          <pre className="p-4 text-[11px] text-ink-900 font-mono overflow-x-auto max-h-72 leading-relaxed bg-paper-0">
            <code>{currentSnippet}</code>
          </pre>
        </div>

        {/* Modal Actions */}
        <div className="flex justify-end pt-5 mt-6 border-t border-rule">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 bg-ink-900 hover:bg-black text-paper-0 text-xs uppercase font-bold tracking-wider transition-colors cursor-pointer"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
}
