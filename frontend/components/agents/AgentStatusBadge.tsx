"use client";

import React, { useState } from "react";
import {
  Cpu,
  Eye,
  FileSearch,
  Scale,
  CheckCircle2,
  Loader2,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AgentStatusBadgeProps {
  isStreaming?: boolean;
  activeModel?: string;
  totalTokens?: number;
  className?: string;
  defaultCollapsed?: boolean;
}

export function AgentStatusBadge({
  isStreaming = false,
  activeModel = "Groq LLaMA-3.3 / Lead Investigator v1",
  totalTokens = 0,
  className = "",
  defaultCollapsed = false,
}: AgentStatusBadgeProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  const agents = [
    {
      id: "A1",
      name: "Agent 1",
      role: "Forensic Vision",
      detail: "ELA & Copy-Move",
      icon: Eye,
      status: "synced",
    },
    {
      id: "A2",
      name: "Agent 2",
      role: "Typography & Custody",
      detail: "Baseline & PDF Metadata",
      icon: FileSearch,
      status: "synced",
    },
    {
      id: "A3",
      name: "Agent 3",
      role: "Pakistani Rules",
      detail: "SBP, NADRA & FBR",
      icon: Scale,
      status: "synced",
    },
    {
      id: "A4",
      name: "Agent 4",
      role: "Lead Investigator",
      detail: isStreaming ? "Reasoning & Synthesizing..." : "Active Swarm Coordinator",
      icon: Cpu,
      status: isStreaming ? "active" : "standby",
    },
  ];

  // Minimized compact state: single-line bar saving over 90px of vertical space
  if (isCollapsed) {
    return (
      <div
        className={cn(
          "border border-ink-900 bg-paper-1 px-3 py-1.5 font-mono text-xs",
          className
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-ink-900 text-paper-0 font-bold uppercase tracking-wider text-[10px]">
              <Sparkles className="w-2.5 h-2.5 text-amber-400" />
              SWARM
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-ink-700">
              <span className="inline-flex items-center gap-1 text-emerald-800 font-medium">
                <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />
                A1-A3 SYNCED
              </span>
              <span className="text-rule">|</span>
              <span
                className={cn(
                  "inline-flex items-center gap-1 font-semibold",
                  isStreaming ? "text-amber-800" : "text-ink-800"
                )}
              >
                {isStreaming ? (
                  <>
                    <Loader2 className="w-2.5 h-2.5 animate-spin text-amber-600" />
                    A4 SYNTHESIZING
                  </>
                ) : (
                  <>
                    <Cpu className="w-2.5 h-2.5 text-ink-600" />
                    A4 READY
                  </>
                )}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-[10px]">
            {totalTokens > 0 && (
              <span className="text-ink-600 hidden sm:inline">
                Tokens:{" "}
                <strong className="text-ink-900 font-semibold">
                  {totalTokens.toLocaleString()}
                </strong>
              </span>
            )}
            <span className="bg-paper-2 border border-rule px-1.5 py-0.5 text-ink-700 font-medium hidden md:inline text-[9px]">
              {activeModel}
            </span>
            <button
              type="button"
              onClick={() => setIsCollapsed(false)}
              className="flex items-center gap-1 px-1.5 py-0.5 hover:bg-paper-2 border border-rule text-ink-700 hover:text-ink-900 font-bold uppercase text-[9px] transition-colors cursor-pointer"
              title="Expand full specialist telemetry grid"
            >
              <span>Details</span>
              <ChevronDown className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Expanded state: full telemetry with minimize toggle
  return (
    <div className={cn("border border-ink-900 bg-paper-1 p-3 font-mono text-xs", className)}>
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-2 mb-3">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-ink-900 text-paper-0 font-bold uppercase tracking-wider text-[11px]">
            <Sparkles className="w-3 h-3 text-amber-400" />
            SWARM TELEMETRY
          </div>
          <span className="text-ink-600 text-[11px] hidden sm:inline">
            Zero-Hallucination Policy Active
          </span>
        </div>

        <div className="flex items-center gap-2 text-[11px]">
          {totalTokens > 0 && (
            <span className="text-ink-600">
              Tokens:{" "}
              <strong className="text-ink-900 font-semibold">
                {totalTokens.toLocaleString()}
              </strong>
            </span>
          )}
          <span className="bg-paper-2 border border-rule px-2 py-0.5 text-ink-700 font-medium">
            {activeModel}
          </span>
          <button
            type="button"
            onClick={() => setIsCollapsed(true)}
            className="flex items-center gap-1 px-1.5 py-0.5 hover:bg-paper-2 border border-rule text-ink-700 hover:text-ink-900 font-bold uppercase text-[9px] transition-colors cursor-pointer ml-1"
            title="Minimize telemetry to expand chat area"
          >
            <span>Minimize</span>
            <ChevronUp className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* 4 Agent Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {agents.map((agent) => {
          const Icon = agent.icon;
          const isActive = agent.status === "active";
          return (
            <div
              key={agent.id}
              className={`p-2 border transition-all ${
                isActive
                  ? "border-ink-900 bg-paper-0 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ring-1 ring-ink-900"
                  : "border-rule bg-paper-0/60"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-[10px] tracking-wider text-ink-900">
                  {agent.id}: {agent.name.toUpperCase()}
                </span>
                {isActive ? (
                  <span className="flex items-center gap-1 text-[10px] text-amber-700 font-bold uppercase">
                    <Loader2 className="w-2.5 h-2.5 animate-spin" />
                    LIVE
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-[10px] text-emerald-700 font-medium">
                    <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />
                    SYNCED
                  </span>
                )}
              </div>
              <div className="text-[11px] font-semibold text-ink-800 truncate">{agent.role}</div>
              <div className="text-[10px] text-ink-500 truncate">{agent.detail}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
