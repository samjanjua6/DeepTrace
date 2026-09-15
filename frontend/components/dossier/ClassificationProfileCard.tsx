"use client";

import React from "react";

interface ClassificationProfileCardProps {
  classifier: any;
  documentType: string;
}

export function ClassificationProfileCard({
  classifier,
  documentType,
}: ClassificationProfileCardProps) {
  if (!classifier) return null;
  const primaryDoc = classifier.documents?.[0];

  return (
    <div className="bg-paper-1 border border-rule p-3 font-mono text-xs space-y-1.5 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-ink-500 uppercase tracking-widest font-semibold">
          STAGE 0 MULTI-MODAL CLASSIFIER
        </span>
        <span className="bg-ink-900 text-paper-0 text-[10px] px-2 py-0.5 font-bold">
          {Math.round((primaryDoc?.confidence ?? 0.95) * 100)}% CONFIDENCE
        </span>
      </div>
      <div className="flex items-baseline justify-between pt-0.5">
        <span className="font-serif text-sm font-semibold text-ink-900">
          {primaryDoc?.subtype?.replace(/_/g, " ") || documentType}
        </span>
        <span className="text-[11px] text-ink-600 uppercase">
          CATEGORY: {documentType}
        </span>
      </div>
      {primaryDoc?.decision_rationale && (
        <p className="text-[10px] text-ink-600 italic pt-0.5 leading-snug">
          {primaryDoc.decision_rationale}
        </p>
      )}
    </div>
  );
}
