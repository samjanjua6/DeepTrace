import React, { useEffect, useId } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { useScrollLock } from "@/lib/hooks/useScrollLock";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  category?: string;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl";
  children: React.ReactNode;
  className?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  category,
  maxWidth = "lg",
  children,
  className,
}: ModalProps) {
  const titleId = useId();
  const containerRef = useFocusTrap<HTMLDivElement>(isOpen);
  useScrollLock(isOpen);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidthStyles: Record<NonNullable<ModalProps["maxWidth"]>, string> = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-xl",
    "2xl": "max-w-2xl",
    "3xl": "max-w-3xl",
    "4xl": "max-w-4xl",
  };

  return (
    /* Backdrop — clicking it closes the modal */
    <div
      ref={containerRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 font-mono select-none"
      onClick={onClose}
    >
      {/* Inner panel — stop clicks propagating to backdrop */}
      <div
        className={cn(
          "bg-paper-0 border-2 border-ink-900 shadow-2xl w-full p-6 relative",
          maxWidthStyles[maxWidth],
          className
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {(title || category) && (
          <div className="flex items-start justify-between border-b border-rule pb-3 mb-4">
            <div>
              {category && (
                <span className="text-[10px] text-ink-500 uppercase tracking-widest block font-semibold">
                  {category}
                </span>
              )}
              {title && (
                <h2
                  id={titleId}
                  className="font-serif text-xl text-ink-900 font-semibold tracking-tight"
                >
                  {title}
                </h2>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-ink-500 hover:text-ink-900 p-1 transition-colors leading-none"
              aria-label="Close dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
