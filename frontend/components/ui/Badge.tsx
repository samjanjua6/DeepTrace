import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | "critical"
    | "high"
    | "low"
    | "neutral"
    | "outline"
    | "inverse"
    | "amber";
  size?: "xs" | "sm" | "md";
}

export function Badge({
  className,
  variant = "neutral",
  size = "sm",
  children,
  ...props
}: BadgeProps) {
  const variantStyles: Record<NonNullable<BadgeProps["variant"]>, string> = {
    critical: "border-forensic-red/50 bg-forensic-red/5 text-forensic-red border",
    high: "border-forensic-amber/50 bg-forensic-amber/5 text-forensic-amber border",
    low: "border-forensic-green/50 bg-forensic-green/5 text-forensic-green border",
    neutral: "border-rule bg-paper-1 text-ink-700 border",
    outline: "border-ink-900 text-ink-900 bg-transparent border",
    inverse: "bg-ink-900 text-paper-0 border border-ink-900",
    amber: "bg-amber-100 text-amber-900 border border-amber-300",
  };

  const sizeStyles: Record<NonNullable<BadgeProps["size"]>, string> = {
    xs: "text-[9px] px-1.5 py-0.2",
    sm: "text-[10px] px-2 py-0.5",
    md: "text-[11px] px-2.5 py-1",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-mono font-bold uppercase tracking-wider select-none shrink-0",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
