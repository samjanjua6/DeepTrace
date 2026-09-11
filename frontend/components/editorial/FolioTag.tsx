import React from "react";

interface FolioTagProps {
  section: string;
  label: string;
  className?: string;
}

export function FolioTag({ section, label, className = "" }: FolioTagProps) {
  return (
    <div
      className={`font-mono text-[10px] tracking-[0.15em] uppercase text-ink-500 flex items-center gap-2 ${className}`}
    >
      <span className="text-ink-900 font-semibold">{section}</span>
      <span className="text-ink-300">/</span>
      <span>{label}</span>
    </div>
  );
}
