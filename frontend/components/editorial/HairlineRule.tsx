import React from "react";

interface HairlineRuleProps {
  label?: string;
  className?: string;
}

export function HairlineRule({ label, className = "" }: HairlineRuleProps) {
  if (!label) {
    return <hr className={`border-t border-rule my-4 ${className}`} />;
  }

  return (
    <div className={`relative flex items-center my-6 ${className}`}>
      <div className="flex-grow border-t border-rule" />
      <span className="flex-shrink mx-4 font-mono text-[10px] tracking-[0.2em] uppercase text-ink-500 bg-paper-0 px-2">
        {label}
      </span>
      <div className="flex-grow border-t border-rule" />
    </div>
  );
}
