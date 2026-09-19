"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Root error boundary. Catches unhandled React render errors and renders a
 * recovery UI instead of a white screen. Must be a class component because
 * `componentDidCatch` / `getDerivedStateFromError` have no hooks equivalent.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // In production this would send to an error tracking service (e.g. Sentry)
    console.error("[ErrorBoundary] Uncaught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-paper-0 flex flex-col items-center justify-center p-6 font-mono text-ink-900 select-none">
          <div className="max-w-lg w-full border-2 border-ink-900 p-8 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 border-b border-rule pb-3">
              <AlertTriangle className="w-6 h-6 text-forensic-red shrink-0" />
              <div>
                <span className="text-[10px] text-ink-500 uppercase tracking-widest font-bold block">
                  System Fault • Error Boundary Activated
                </span>
                <h2 className="font-serif text-xl font-bold text-ink-900 tracking-tight">
                  Application Error
                </h2>
              </div>
            </div>

            <p className="text-xs text-ink-700 leading-relaxed">
              An unexpected error occurred in the DeepTrace Forensic Platform.
              This incident has been logged. You can try reloading the page to
              recover your session.
            </p>

            {process.env.NODE_ENV === "development" && this.state.error && (
              <pre className="p-3 bg-paper-1 border border-rule text-[11px] text-forensic-red overflow-auto max-h-48 whitespace-pre-wrap font-mono">
                {this.state.error.message}
                {"\n\n"}
                {this.state.error.stack}
              </pre>
            )}

            <button
              onClick={() => window.location.reload()}
              className="w-full px-5 py-2.5 bg-ink-900 hover:bg-black text-paper-0 font-mono text-xs uppercase tracking-widest font-semibold transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
