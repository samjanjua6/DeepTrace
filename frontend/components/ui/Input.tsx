import React, { forwardRef } from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  isError?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", isError = false, ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          "w-full bg-paper-1 border px-3 py-2 text-ink-900 placeholder:text-ink-500 font-mono text-xs focus:outline-none focus:bg-paper-0 transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
          isError
            ? "border-forensic-red focus:border-forensic-red"
            : "border-rule focus:border-ink-900",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
