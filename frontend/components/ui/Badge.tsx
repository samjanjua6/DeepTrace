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
    critical: "border-rose-700/80 bg-rose-100 text-rose-950 border",
    high: "border-amber-700/80 bg-amber-100 text-amber-950 border",
    low: "border-emerald-700/80 bg-emerald-100 text-emerald-950 border",
    neutral: "border-rule-dark bg-paper-1 text-ink-900 border",
    outline: "border-ink-900 text-ink-900 bg-transparent border",
    inverse: "bg-ink-900 text-paper-0 border border-ink-900",
    amber: "bg-amber-100 text-amber-950 border border-amber-600",
  };

  const sizeStyles: Record<NonNullable<BadgeProps["size"]>, string> = {
    xs: "text-[11px] px-2 py-0.5",
    sm: "text-xs px-2.5 py-0.5",
    md: "text-xs px-3 py-1 font-bold",
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
