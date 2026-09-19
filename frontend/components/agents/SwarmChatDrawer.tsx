"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  X,
  Sparkles,
  Download,
  Trash2,
  RefreshCw,
  Loader2,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { AgentMessage, AskResponse } from "@/lib/types/forensics";
import {
  askAgentStream,
  getAgentChatHistory,
} from "@/lib/api/client";
import { AgentStatusBadge } from "./AgentStatusBadge";
import { ChatMessage } from "./ChatMessage";
import { SuggestedPrompts } from "./SuggestedPrompts";

interface SwarmChatDrawerProps {
  investigationId: string;
  isOpen?: boolean;
  onClose?: () => void;
  mode?: "drawer" | "tab";
  onCitationClick?: (citationId: string) => void;
}

export function SwarmChatDrawer({
  investigationId,
  isOpen = true,
  onClose,
  mode = "drawer",
  onCitationClick,
}: SwarmChatDrawerProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [totalTokens, setTotalTokens] = useState(0);
  const [activeModel, setActiveModel] = useState("Groq LLaMA-3.3 / Lead Investigator v1");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 1. Fetch initial chat history
  useEffect(() => {
    let isMounted = true;
    if (!investigationId) return;

    async function loadHistory() {
      setIsLoadingHistory(true);
      try {
        const hist = await getAgentChatHistory(investigationId);
        if (!isMounted) return;
        if (hist.messages && hist.messages.length > 0) {
          setMessages(hist.messages);
          const totalOut = hist.messages.reduce((acc, m) => acc + (m.tokensOut || 0), 0);
          setTotalTokens(totalOut);
        }
        if (hist.modelName) {
          setActiveModel(`${hist.modelProvider?.toUpperCase() || "AI"} (${hist.modelName})`);
        }
      } catch (err) {
        console.warn("Could not load agent chat history:", err);
      } finally {
        if (isMounted) setIsLoadingHistory(false);
      }
    }

    loadHistory();

    return () => {
      isMounted = false;
    };
  }, [investigationId]);

  // 2. Auto-scroll to bottom on new messages or streaming tokens
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // 3. Send query to Lead Investigator
  const handleSendMessage = async (queryText?: string) => {
    const textToSend = (queryText || inputQuery).trim();
    if (!textToSend || isStreaming) return;

    setError(null);
    setInputQuery("");

    // Create optimistic user message
    const userMsg: AgentMessage = {
      id: `usr-${Date.now()}`,
      role: "USER",
      content: textToSend,
      sequenceOrder: messages.length + 1,
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsStreaming(true);
    setStreamingContent("");

    let accumulatedAnswer = "";

    try {
      const response: AskResponse = await askAgentStream(
        investigationId,
        textToSend,
        (chunk) => {
          accumulatedAnswer += chunk;
          setStreamingContent(accumulatedAnswer);
        }
      );

      // Finalize assistant turn
      const assistantMsg: AgentMessage = {
        id: `ast-${Date.now()}`,
        role: "ASSISTANT",
        content: response.answer || accumulatedAnswer,
        tokensOut: response.tokensUsed,
        evidenceReferences: response.evidenceReferences || [],
        sequenceOrder: messages.length + 2,
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setStreamingContent("");
      setTotalTokens((prev) => prev + (response.tokensUsed || 0));
    } catch (err: any) {
      console.error("Swarm query failed:", err);
      setError(err.message || "Failed to contact Lead Investigator Agent.");
      // If we got partial response before failing, save it
      if (accumulatedAnswer) {
        setMessages((prev) => [
          ...prev,
          {
            id: `ast-${Date.now()}`,
            role: "ASSISTANT",
            content: accumulatedAnswer,
            sequenceOrder: messages.length + 2,
            createdAt: new Date().toISOString(),
          },
        ]);
        setStreamingContent("");
      }
    } finally {
      setIsStreaming(false);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleExportTranscript = () => {
    if (messages.length === 0) return;

    const transcriptLines = [
      `================================================================================`,
      `DEEPTRACE FORENSIC AGENT SWARM TRANSCRIPT`,
      `Investigation ID: ${investigationId}`,
      `Exported: ${new Date().toISOString()}`,
      `Evidentiary Compliance: PECA 2016 / SBP BPRD / ETO 2002`,
      `Zero-Hallucination Verified Evidence Grounding: ACTIVE`,
      `================================================================================\n`,
    ];

    messages.forEach((m, idx) => {
      transcriptLines.push(
        `[TURN ${idx + 1}] [${m.role}] [${m.createdAt}]`
      );
      if (m.evidenceReferences && m.evidenceReferences.length > 0) {
        transcriptLines.push(`Verified Citations: ${m.evidenceReferences.join(", ")}`);
      }
      transcriptLines.push(`--------------------------------------------------------------------------------`);
      transcriptLines.push(m.content);
      transcriptLines.push(`\n`);
    });

    const blob = new Blob([transcriptLines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `DeepTrace-AgentSwarm-${investigationId}-${Date.now()}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleClearChat = () => {
    if (window.confirm("Clear active chat transcript from this view? (Database session remains recorded for SBP audit)")) {
      setMessages([]);
      setStreamingContent("");
      setError(null);
    }
  };

  // If used as drawer and closed, return null
  if (mode === "drawer" && !isOpen) return null;

  const containerClasses =
    mode === "drawer"
      ? "fixed inset-y-0 right-0 z-50 w-full sm:w-[580px] md:w-[680px] lg:w-[740px] bg-paper-0 border-l border-ink-900 shadow-[-8px_0px_0px_0px_rgba(0,0,0,1)] flex flex-col transition-transform duration-200 ease-in-out"
      : "w-full border border-ink-900 bg-paper-0 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] flex flex-col";

  return (
    <div className={containerClasses}>
      {/* Top Banner & Controls */}
      <div className="flex items-center justify-between px-4 py-3 bg-ink-900 text-paper-0 font-mono text-xs border-b border-ink-900 shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span className="font-bold tracking-wider uppercase text-sm">
            INTERACTIVE AGENT SWARM
          </span>
          <span className="bg-ink-700 text-paper-1 px-2 py-0.2 text-[10px] hidden sm:inline">
            AGENT 4 / LEAD INVESTIGATOR
          </span>
        </div>

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <>
              <button
                onClick={handleExportTranscript}
                className="flex items-center gap-1 px-2 py-1 bg-ink-800 hover:bg-ink-700 text-paper-0 border border-ink-700 text-[11px] transition-colors cursor-pointer"
                title="Export evidential Q&A transcript"
              >
                <Download className="w-3 h-3" />
                <span className="hidden sm:inline">EXPORT</span>
              </button>
              <button
                onClick={handleClearChat}
                className="p-1 hover:bg-ink-800 text-paper-2 transition-colors cursor-pointer"
                title="Clear current view"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          {mode === "drawer" && onClose && (
            <button
              onClick={onClose}
              className="p-1 bg-ink-800 hover:bg-scarlet-600 text-paper-0 transition-colors cursor-pointer ml-1"
              title="Close panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Live Swarm Telemetry Ribbon */}
      <div className="p-2.5 bg-paper-1 border-b border-rule shrink-0">
        <AgentStatusBadge
          isStreaming={isStreaming}
          activeModel={activeModel}
          totalTokens={totalTokens}
          defaultCollapsed={messages.length > 0}
        />
      </div>

      {/* Chat Messages Stream */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-3 bg-paper-0">
        {isLoadingHistory ? (
          <div className="flex flex-col items-center justify-center h-48 font-mono text-xs text-ink-600 gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-ink-900" />
            <span>Synchronizing agent session manifest...</span>
          </div>
        ) : messages.length === 0 && !isStreaming ? (
          /* Empty State / Briefing */
          <div className="border border-rule bg-paper-1 p-6 font-mono text-xs my-auto">
            <div className="flex items-center gap-2 text-ink-900 font-bold uppercase tracking-wider mb-2">
              <HelpCircle className="w-4 h-4 text-amber-600" />
              <span>FORENSIC SWARM READY FOR INQUIRY</span>
            </div>
            <p className="font-serif text-sm text-ink-700 leading-relaxed mb-4">
              You are connected to the <strong>Lead Investigator Agent (Agent 4)</strong>. Agent 4 is
              grounded strictly in this docket's verified evidence items and incorporates findings
              from the Visual, Typographical, and Semantic Pakistani Regulatory specialists.
            </p>
            <div className="border-t border-rule pt-3">
              <SuggestedPrompts
                onSelectPrompt={(p) => handleSendMessage(p)}
                disabled={isStreaming}
                variant="card"
              />
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                id={msg.id}
                role={msg.role}
                content={msg.content}
                tokensOut={msg.tokensOut}
                sequenceOrder={msg.sequenceOrder}
                createdAt={msg.createdAt}
                evidenceReferences={msg.evidenceReferences}
                onCitationClick={onCitationClick}
              />
            ))}

            {/* Currently Streaming Response */}
            {isStreaming && (
              <ChatMessage
                id="streaming-turn"
                role="ASSISTANT"
                content={streamingContent || "Consulting swarm specialist evidence items..."}
                isStreaming={true}
                onCitationClick={onCitationClick}
              />
            )}
          </>
        )}

        {/* Error notification */}
        {error && (
          <div className="flex items-start gap-2 p-3 bg-scarlet-50 border border-scarlet-300 text-scarlet-900 font-mono text-xs">
            <AlertCircle className="w-4 h-4 text-scarlet-600 shrink-0 mt-0.5" />
            <div>
              <strong className="font-bold uppercase tracking-wider">SWARM CONSULTATION ERROR:</strong>
              <div className="mt-0.5">{error}</div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts Pill Tray (when chat has messages) */}
      {messages.length > 0 && !isStreaming && (
        <div className="px-3 py-1.5 bg-paper-1 border-t border-rule shrink-0">
          <SuggestedPrompts
            onSelectPrompt={(p) => handleSendMessage(p)}
            disabled={isStreaming}
            variant="tray"
          />
        </div>
      )}

      {/* Input Form Footer */}
      <div className="p-3 bg-paper-1 border-t border-ink-900 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex flex-col gap-2"
        >
          <div className="relative">
            <textarea
              ref={textareaRef}
              rows={2}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isStreaming}
              placeholder="Ask a forensic question in English or Urdu... (Enter to send, Shift+Enter for newline)"
              className="w-full p-2.5 bg-paper-0 border border-ink-900 text-ink-900 placeholder:text-ink-500 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-ink-900 resize-none rounded-none"
            />
          </div>

          <div className="flex items-center justify-between font-mono text-[11px] text-ink-600">
            <span className="hidden sm:inline">
              Press <kbd className="px-1 py-0.5 bg-paper-2 border border-rule text-ink-800">Enter</kbd> to submit
            </span>

            <button
              type="submit"
              disabled={!inputQuery.trim() || isStreaming}
              className="flex items-center gap-1.5 px-4 py-2 bg-ink-900 hover:bg-ink-800 text-paper-0 font-bold uppercase tracking-wider transition-all disabled:opacity-40 cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
            >
              {isStreaming ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
                  <span>SYNTHESIZING...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>DISPATCH QUERY</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
