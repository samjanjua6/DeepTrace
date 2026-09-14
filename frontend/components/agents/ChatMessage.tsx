"use client";

import React, { useState } from "react";
import { Copy, Check, Sparkles, User, ExternalLink, ShieldAlert } from "lucide-react";
import { formatDatePKT } from "@/lib/formatters";

interface ChatMessageProps {
  id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  tokensIn?: number;
  tokensOut?: number;
  sequenceOrder?: number;
  createdAt?: string;
  evidenceReferences?: string[];
  isStreaming?: boolean;
  onCitationClick?: (citationId: string) => void;
}

export function ChatMessage({
  role,
  content,
  tokensOut,
  createdAt,
  evidenceReferences = [],
  isStreaming = false,
  onCitationClick,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const isUser = role === "USER";
  const isUrdu = /[\u0600-\u06FF]/.test(content);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore clipboard error
    }
  };

  // Render markdown-like blocks cleanly
  const renderFormattedContent = (text: string) => {
    // Split into paragraphs / lines
    const lines = text.split("\n");

    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return <div key={idx} className="h-2" />;
      }

      // Check for headings
      if (trimmed.startsWith("### ")) {
        return (
          <h4 key={idx} className="font-mono font-bold text-ink-900 text-sm mt-2 mb-1 tracking-wide uppercase">
            {trimmed.replace(/^###\s*/, "")}
          </h4>
        );
      }
      if (trimmed.startsWith("## ")) {
        return (
          <h3 key={idx} className="font-mono font-bold text-ink-900 text-base mt-3 mb-1 border-b border-rule pb-1 tracking-wide uppercase">
            {trimmed.replace(/^##\s*/, "")}
          </h3>
        );
      }

      // Check for bullet lists
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        const bulletText = trimmed.replace(/^[-*]\s*/, "");
        return (
          <div key={idx} className="flex items-start gap-2 my-1 text-xs pl-2">
            <span className="text-ink-500 font-mono select-none">-</span>
            <div className="flex-1 leading-relaxed">{renderInlineMarkup(bulletText)}</div>
          </div>
        );
      }

      // Normal paragraph line
      return (
        <p key={idx} className="my-1 leading-relaxed text-xs">
          {renderInlineMarkup(line)}
        </p>
      );
    });
  };

  // Render bolding and citations inline
  const renderInlineMarkup = (text: string) => {
    // Regex matches **bold**, `code`, and citations like [RULE_...] or RULE_...
    const parts = text.split(/(\*\*.*?\*\*|`.*?`|\[(?:RULE_[A-Z0-9_]+|ev-[a-z0-9\-]+)\]|\bRULE_[A-Z0-9_]+)/g);

    return parts.map((part, i) => {
      if (!part) return null;

      // Bold text **bold**
      if (part.startsWith("**") && part.endsWith("**")) {
        const inner = part.slice(2, -2);
        return (
          <strong key={i} className="font-semibold text-ink-900">
            {inner}
          </strong>
        );
      }

      // Monospace code `code`
      if (part.startsWith("`") && part.endsWith("`")) {
        const inner = part.slice(1, -1);
        return (
          <code key={i} className="bg-paper-2 text-ink-900 px-1 py-0.5 font-mono text-[11px] border border-rule">
            {inner}
          </code>
        );
      }

      // Citations [RULE_...] or RULE_...
      const citationMatch = part.match(/^\[?(RULE_[A-Z0-9_]+|ev-[a-z0-9\-]+)\]?$/);
      if (citationMatch) {
        const citationId = citationMatch[1];
        return (
          <button
            key={i}
            onClick={() => onCitationClick?.(citationId)}
            className="inline-flex items-center gap-1 mx-1 px-1.5 py-0.2 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 font-mono text-[10px] font-bold transition-colors cursor-pointer"
            title={`Jump to verified exhibit: ${citationId}`}
          >
            <ShieldAlert className="w-2.5 h-2.5 text-amber-700" />
            <span>{citationId}</span>
            <ExternalLink className="w-2.5 h-2.5 opacity-60" />
          </button>
        );
      }

      return <span key={i}>{part}</span>;
    });
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[85%] md:max-w-[75%] border border-ink-900 bg-paper-0 p-3 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]">
          <div className="flex items-center justify-between gap-3 border-b border-rule pb-1.5 mb-2 font-mono text-[10px] uppercase text-ink-600">
            <div className="flex items-center gap-1.5 font-bold text-ink-900">
              <User className="w-3 h-3 text-ink-700" />
              <span>ANALYST INQUIRY</span>
            </div>
            {createdAt && <span>{formatDatePKT(createdAt)}</span>}
          </div>
          <div className="font-mono text-xs text-ink-900 whitespace-pre-wrap leading-relaxed">
            {content}
          </div>
        </div>
      </div>
    );
  }

  // Assistant Lead Investigator Message
  return (
    <div className="mb-5 border border-ink-900 bg-paper-1 shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] border-l-4 border-l-ink-900">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule px-3 py-2 bg-paper-2 font-mono text-[11px]">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 bg-ink-900 text-paper-0 px-2 py-0.5 font-bold uppercase tracking-wider text-[10px]">
            <Sparkles className="w-3 h-3 text-amber-400" />
            AGENT 4: LEAD INVESTIGATOR
          </span>
          <span className="text-ink-600 text-[10px] hidden sm:inline">
            LangGraph Multi-Vector Synthesis
          </span>
        </div>

        <div className="flex items-center gap-3">
          {tokensOut !== undefined && tokensOut > 0 && (
            <span className="text-[10px] text-ink-500 font-mono">
              {tokensOut} tokens
            </span>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono border border-rule bg-paper-0 hover:bg-paper-2 text-ink-700 transition-colors cursor-pointer"
            title="Copy response markdown"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-600" />
                <span className="text-emerald-700 font-semibold">COPIED</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>COPY</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Narrative Body */}
      <div
        className={`p-4 text-ink-900 ${
          isUrdu
            ? "font-serif text-sm md:text-base leading-loose text-right text-ink-950"
            : "font-serif text-xs md:text-sm leading-relaxed"
        }`}
        dir={isUrdu ? "rtl" : "ltr"}
      >
        {renderFormattedContent(content)}

        {isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-ink-900 animate-pulse align-middle" />
        )}
      </div>

      {/* Cited Exhibits Footer (if present) */}
      {evidenceReferences.length > 0 && (
        <div className="px-4 py-2 border-t border-rule bg-paper-0 flex flex-wrap items-center gap-2 font-mono text-[11px]">
          <span className="font-bold text-ink-700 uppercase tracking-wider text-[10px]">
            VERIFIED CITATIONS:
          </span>
          {evidenceReferences.map((refId) => (
            <button
              key={refId}
              onClick={() => onCitationClick?.(refId)}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-300 font-bold text-[10px] transition-colors cursor-pointer"
            >
              <ShieldAlert className="w-2.5 h-2.5 text-amber-700" />
              <span>{refId}</span>
              <ExternalLink className="w-2.5 h-2.5 opacity-60" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
