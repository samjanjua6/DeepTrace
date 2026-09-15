import React from "react";
import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export function Tabs({ tabs, activeTab, onChange, className }: TabsProps) {
  return (
    <div
      role="tablist"
      className={cn("flex flex-wrap gap-2 font-mono text-xs", className)}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              "px-3 py-1 border transition-colors uppercase flex items-center gap-1.5 select-none focus:outline-none focus:ring-1 focus:ring-ink-900",
              isActive
                ? "bg-ink-900 text-paper-0 border-ink-900 font-semibold shadow-sm"
                : "bg-paper-1 text-ink-700 border-rule hover:bg-paper-2"
            )}
          >
            {tab.icon && <span className="shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>
            {typeof tab.count === "number" && (
              <span
                className={cn(
                  "ml-1 px-1.5 py-0.2 text-[9px] font-bold tabular-nums",
                  isActive
                    ? "bg-paper-0 text-ink-900"
                    : "bg-paper-2 text-ink-700"
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
