import React, { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "primary"
    | "secondary"
    | "destructive"
    | "outline"
    | "ghost"
    | "accent";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const variantStyles: Record<NonNullable<ButtonProps["variant"]>, string> = {
      primary:
        "bg-ink-900 text-paper-0 hover:bg-black border border-ink-900 shadow-sm disabled:bg-ink-900/50",
      secondary:
        "bg-paper-1 hover:bg-paper-2 text-ink-900 border border-rule disabled:bg-paper-1/50",
      destructive:
        "bg-forensic-red text-paper-0 hover:bg-rose-900 border border-forensic-red disabled:bg-forensic-red/50",
      outline:
        "bg-paper-0 hover:bg-paper-1 text-ink-900 border border-ink-900 disabled:opacity-50",
      ghost:
        "text-ink-700 hover:text-ink-900 hover:bg-paper-1 border border-transparent disabled:opacity-50",
      accent:
        "bg-amber-100 hover:bg-amber-200 text-ink-900 border border-ink-900 disabled:opacity-50",
    };

    const sizeStyles: Record<NonNullable<ButtonProps["size"]>, string> = {
      sm: "px-2.5 py-1 text-[10px]",
      md: "px-3.5 py-1.5 text-xs",
      lg: "px-5 py-2 text-sm",
      icon: "p-1.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center font-mono font-bold uppercase tracking-wider transition-colors select-none focus:outline-none focus:ring-1 focus:ring-ink-900 disabled:cursor-not-allowed whitespace-nowrap",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <>
            <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin shrink-0" />
            <span>Loading...</span>
          </>
        ) : (
          <>
            {leftIcon && <span className="mr-1.5 shrink-0">{leftIcon}</span>}
            {children}
            {rightIcon && <span className="ml-1.5 shrink-0">{rightIcon}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
