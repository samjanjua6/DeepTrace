import React, { forwardRef } from "react";
import { cn } from "@/lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  isError?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, isError = false, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          "w-full bg-paper-1 border px-3 py-2 text-ink-900 font-mono text-xs focus:outline-none focus:bg-paper-0 transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
          isError
            ? "border-forensic-red focus:border-forensic-red"
            : "border-rule focus:border-ink-900",
          className
        )}
        {...props}
      >
        {children}
      </select>
    );
  }
);

Select.displayName = "Select";
