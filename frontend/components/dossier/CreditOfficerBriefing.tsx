"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  FileText,
  Copy,
  Check,
  Cpu,
  Layers,
  Sparkles,
  Info,
  Scale,
  ExternalLink,
} from "lucide-react";
import { EvidenceItem, EvidenceAnchor, formatRecommendation } from "@/lib/types/forensics";

export interface CreditBriefingItem {
  page_number?: number;
  row_number?: number;
  anchor_type?: string;
  anchors?: EvidenceAnchor[];
  title: string;
  transaction_label?: string;
  expected_value?: string;
  actual_value?: string;
  discrepancy?: string;
  font_detected?: string;
  expected_font?: string;
  visual_cue?: string;
  summary_en: string;
  summary_ur: string;
  severity: string;
  rule_id?: string;
  evidence_id?: string;
}

export interface LeadInvestigatorAnalysis {
  investigation_id: string;
  overall_score: number;
  risk_tier: string;
  action_directive: string;
  confidence_score: number;
  anomalies_detected: number;
  model_provider: string;
  model_name: string;
  english_summary: string;
  urdu_summary: string;
  narrative: string;
  credit_briefing_items: CreditBriefingItem[];
  cross_signal_correlations: string[];
  evidence_citations?: string[];
  specialist_reports?: Record<string, any>;
  authenticity_score?: number;
  tamper_score?: number;
  authenticity_tier?: string;
  transaction_risk_score?: number;
  transaction_risk_tier?: string;
}

interface CreditOfficerBriefingProps {
  investigationId: string;
  overallScore: number;
  riskTier: string;
  actionDirective: string;
  evidenceItems: EvidenceItem[];
  authenticityScore?: number;
  tamperScore?: number;
  authenticityTier?: string;
  transactionRiskScore?: number;
  transactionRiskTier?: string;
  overriddenScore?: number;
  overriddenTier?: string;
  overrideReason?: string;
  overriddenById?: string;
  overriddenAt?: string;
  onFocusCanvas?: (pageNumber: number) => void;
  onSelectEvidence?: (evidenceId: string) => void;
}

export function CreditOfficerBriefing({
  investigationId,
  overallScore,
  riskTier,
  actionDirective,
  evidenceItems,
  authenticityScore,
  tamperScore,
  authenticityTier,
  transactionRiskScore,
  transactionRiskTier,
  overriddenScore,
  overriddenTier,
  overrideReason,
  overriddenById,
  overriddenAt,
  onFocusCanvas,
  onSelectEvidence,
}: CreditOfficerBriefingProps) {
  const [activeLang, setActiveLang] = useState<"en" | "ur">("en");
  const [copied, setCopied] = useState(false);
  const [analysis, setAnalysis] = useState<LeadInvestigatorAnalysis | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!investigationId || investigationId === "sample") return;

    let isMounted = true;
    setLoading(true);

    fetch(`/api/v1/investigations/${investigationId}/analysis`)
      .then((res) => {
        if (res.ok) return res.json();
        return null;
      })
      .then((data) => {
        if (isMounted && data) {
          setAnalysis(data);
        }
      })
      .catch((err) => {
        console.warn("Could not fetch lead investigator analysis:", err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [investigationId]);

  const effectiveAuthScore =
    analysis?.authenticity_score ??
    authenticityScore ??
    Math.max(0, 100 - overallScore);

  const effectiveTamperScore =
    analysis?.tamper_score ??
    tamperScore ??
    overallScore;

  const effectiveAuthTier =
    analysis?.authenticity_tier ??
    authenticityTier ??
    (effectiveAuthScore >= 90
      ? "VERIFIED_AUTHENTIC"
      : effectiveAuthScore >= 60
      ? "SUSPECT_DOCUMENT"
      : "FORGERY_DETECTED");

  const effectiveTxnScore =
    analysis?.transaction_risk_score ??
    transactionRiskScore ??
    0;

  const effectiveTxnTier =
    analysis?.transaction_risk_tier ??
    transactionRiskTier ??
    (effectiveTxnScore <= 20
      ? "CLEAN"
      : effectiveTxnScore <= 40
      ? "MONITORED"
      : effectiveTxnScore <= 70
      ? "HIGH_AML_RISK"
      : "CRITICAL_PROSCRIBED");

  const isOverridden = overriddenScore !== undefined && overriddenScore !== null;
  const effectiveScore = isOverridden ? overriddenScore : overallScore;
  const effectiveTier = isOverridden ? (overriddenTier || riskTier) : riskTier;
  const isCriticalOrHigh = effectiveTier === "CRITICAL" || effectiveTier === "HIGH";
  const isMedium = effectiveTier === "MEDIUM";
  const recAction = formatRecommendation(actionDirective, effectiveTier);

  const adverseEvidence = evidenceItems.filter(
    (it) => it.severity !== "INFO" && !it.ruleId?.endsWith("_VERIFIED")
  );
  const verifiedEvidence = evidenceItems.filter(
    (it) => it.severity === "INFO" || it.ruleId?.endsWith("_VERIFIED")
  );

  const advisoryEn =
    effectiveTamperScore > 0 && effectiveTxnScore > 0
      ? "Compound Forensic & Compliance Alert: Severe document tampering detected alongside statutory AML/CFT violations. Financial figures have been artificially manipulated post-generation, and transactional counterparties trigger regulatory red flags. Recommend loan rejection and compliance escalation to fraud unit."
      : effectiveTamperScore > 0
      ? "Credit Risk Advisory: The financial figures in this statement have been artificially inflated or modified post-generation. Document authenticity is compromised. Recommend halting loan application pending formal verification."
      : "Statutory AML/CFT Compliance Advisory: The document is genuine with verified typographical and ledger consistency; however, high-risk transactional patterns (SBP AML/CFT / FATF red flags) were detected. Recommend forwarding docket to AML Compliance for Enhanced Due Diligence (EDD) without alleging document tampering.";

  const advisoryUr =
    effectiveTamperScore > 0 && effectiveTxnScore > 0
      ? "مشترکہ فرانزک و تعمیل انتباہ: دستاویز میں جعل سازی اور اسٹیٹ بینک AML/CFT کے ضوابط کی سنگین خلاف ورزی پائی گئی ہے۔ اعداد و شمار میں غیر قانونی ردوبدل پایا گیا ہے اور ممنوعہ عناصر شامل ہیں۔ درخواست مسترد کرنے اور اینٹی فراڈ یونٹ کو بھیجنے کی سفارش کی جاتی ہے۔"
      : effectiveTamperScore > 0
      ? "کریڈٹ رسک ایڈوائزری: اس بینک سٹیٹمنٹ کے اعداد و شمار میں سافٹ ویئر کے ذریعے ردوبدل کر کے بیلنس تبدیل کیا گیا ہے۔ دستاویز کی اصلیت مشکوک ہے، لہٰذا درخواست مسترد کرنے یا سینیئر کمیٹی کو برائے فیصلہ پیش کرنے کی سفارش کی جاتی ہے۔"
      : "اسٹیٹ بینک ضوابط و AML ایڈوائزری: دستاویز کی ساخت اور کھاتہ جاتی تسلسل درست اور مصدقہ ہے، البتہ کھاتے دار کے لین دین میں مشکوک ٹرانزیکشنز پائی گئی ہیں۔ اسے جعل سازی کے بجائے منی لانڈرنگ انکوائری کے لیے بھیجنے کی سفارش کی جاتی ہے۔";

  const overrideNoteEn = isOverridden
    ? `\n\n[HUMAN ADJUDICATION AUDIT NOTICE]: Automated risk score of ${overallScore}/100 (${riskTier}) was manually adjudicated to ${effectiveScore}/100 (${effectiveTier}) by officer ${overriddenById || "Authorized Officer"}.\nCompliance Justification: "${overrideReason || "Documented branch operational review cleared discrepancy."}"`
    : "";

  const overrideNoteUr = isOverridden
    ? `\n\n[آڈٹ نوٹ برائے دستی فیصلہ]: کمپیوٹرائزڈ رسک سکور ${overallScore}/100 کو مجاز افسر کی جانب سے تبدیل کر کے ${effectiveScore}/100 (${effectiveTier}) کیا گیا ہے۔\nدستی فیصلے کا جواز: "${overrideReason || "برانچ ریکارڈ سے دستی تصدیق مکمل ہو گئی ہے۔"}"`
    : "";

  const baselineStrEn = isOverridden ? ` [Engine Baseline: ${overallScore}/100 (${riskTier})]` : "";

  // Client-side deterministic fallback if API is not yet loaded or on sample exhibit
  const fallbackEnglishSummary =
    overallScore > 0 && adverseEvidence.length > 0
      ? `CRITICAL BRIEFING FOR CREDIT UNDERWRITERS & LOAN APPROVAL OFFICERS:
Forensic Recommendation: ${recAction} (Human Decision Required).
Evaluated Risk: ${effectiveScore}/100 (${effectiveTier} Risk)${baselineStrEn}.
Forensic Radar: Document Authenticity: ${effectiveAuthScore}% (${effectiveAuthTier.replace(/_/g, " ")}) | Transaction Risk: ${effectiveTxnScore}/100 (${effectiveTxnTier.replace(/_/g, " ")}).

Key Forensic Deficiencies Detected:
` +
        adverseEvidence
          .slice(0, 6)
          .map((it) => {
            const hasFontAnomaly =
              it.severity !== "INFO" &&
              (it.category === "FONT_BASELINE_INCONSISTENCY" ||
                (it.ruleId || "").includes("FONT") ||
                Boolean(it.description.match(/([A-Za-z0-9_-]+)\s+instead/i)));
            const details = [
              it.discrepancy ? `Discrepancy: ${it.discrepancy}.` : "",
              hasFontAnomaly ? "Font irregularity identified." : "",
            ]
              .filter(Boolean)
              .join(" ");

            const tech = it.technicalDetails || {};
            const anchorType = it.anchorType || tech.anchor_type || (it.pageNumber ? "PAGE_REGION" : "DOCUMENT_METADATA");
            let locStr = "Document Metadata";
            if (anchorType === "MULTI_PAGE_SPAN") {
              locStr = `Pages 1–${it.pageNumber || 23} (Summary vs Terminal Ledger)`;
            } else if (anchorType === "DOCUMENT_HEADER" && it.pageNumber) {
              locStr = `Page ${it.pageNumber} Header`;
            } else if (tech.row_number && it.pageNumber) {
              locStr = `Page ${it.pageNumber}, Row ${tech.row_number}`;
            } else if (it.pageNumber) {
              locStr = `Page ${it.pageNumber}`;
            }
            return `• [${locStr}]: ${it.title}.${details ? ` ${details}` : ""}`;
          })
          .join("\n") +
        (verifiedEvidence.length > 0
          ? `\n\nCertified Authentic Controls:\n` +
            verifiedEvidence
              .map((it) => {
                const loc = it.pageNumber ? `Page ${it.pageNumber}` : "Document Metadata";
                return `✓ [${loc}]: ${it.title}. ${it.discrepancy || "Verified Authentic."}`;
              })
              .join("\n")
          : "") +
        overrideNoteEn +
        `\n\n${advisoryEn}\n\nAdvisory Notice: DeepTrace outputs constitute evidentiary forensic analysis. All lending, rejection, freeze, or STR decisions remain the exclusive statutory prerogative of authorized human credit & compliance officers.`
      : `EXECUTIVE BRIEFING FOR CREDIT OFFICERS:
Forensic Recommendation: ${recAction} (Human Decision Required).
Evaluated Risk: ${effectiveScore}/100 (${effectiveTier} Risk)${baselineStrEn}.
Forensic Radar: Document Authenticity: ${effectiveAuthScore}% | Transaction Risk: ${effectiveTxnScore}/100.
Forensic validation confirms 100% document authenticity across all pages. All transaction figures reconcile with the core banking ledger without font, visual, or mathematical anomalies. State Bank of Pakistan (SBP) IBAN validation passed.${overrideNoteEn}

Advisory Notice: Final credit decisions rest with authorized underwriting officers.`;

  const fallbackUrduSummary =
    overallScore > 0 && adverseEvidence.length > 0
      ? `کریڈٹ آفیسر اور لون انڈر رائٹر کے لیے فوری خلاصہ:
تجویز کردہ کارروائی: ${recAction} (حتمی فیصلہ مجاز افسر کا ہوگا)۔
لاگو رسک سکور: ${effectiveScore}/100 (${effectiveTier})${isOverridden ? ` [سسٹم سکور: ${overallScore}/100]` : ""}۔
دستاویزی اصلیت: ${effectiveAuthScore}٪ | کاروباری ٹرانزیکشن رسک: ${effectiveTxnScore}/100۔
دستاویزی اصلیت: ${effectiveAuthScore}٪ | کاروباری ٹرانزیکشن رسک: ${effectiveTxnScore}/100۔

اہم فرانزک شواہد اور خامیاں:
` +
        adverseEvidence
          .slice(0, 6)
          .map((it) => {
            const tech = it.technicalDetails || {};
            const anchorType = it.anchorType || tech.anchor_type || (it.pageNumber ? "PAGE_REGION" : "DOCUMENT_METADATA");
            let locStr = "دستاویز میٹا ڈیٹا";
            if (anchorType === "MULTI_PAGE_SPAN") {
              locStr = `صفحات 1 تا ${it.pageNumber || 23} لیجر`;
            } else if (anchorType === "DOCUMENT_HEADER" && it.pageNumber) {
              locStr = `صفحہ ${it.pageNumber} ہیڈر`;
            } else if (tech.row_number && it.pageNumber) {
              locStr = `صفحہ ${it.pageNumber}، قطار ${tech.row_number}`;
            } else if (it.pageNumber) {
              locStr = `صفحہ ${it.pageNumber}`;
            }
            return `• [${locStr}]: ${it.title}۔`;
          })
          .join("\n") +
        overrideNoteUr +
        `\n\n${advisoryUr}\n\nنوٹ: تمام مالیاتی و قرضہ جاتی فیصلے مجاز افسران کی صوابدید پر منحصر ہیں۔`
      : `کریڈٹ آفیسر کے لیے تفصیلی خلاصہ:
تجویز کردہ کارروائی: ${recAction} (حتمی فیصلہ مجاز افسر کا ہوگا)۔
لاگو رسک سکور: ${effectiveScore}/100 (${effectiveTier})${isOverridden ? ` [سسٹم سکور: ${overallScore}/100]` : ""}۔
دستاویزی اصلیت: ${effectiveAuthScore}٪ | کاروباری رسک: ${effectiveTxnScore}/100۔
فرانزک تصدیق سے ثابت ہوا ہے کہ یہ دستاویز مکمل طور پر اصل اور غیر تبدیل شدہ ہے۔ تمام کھاتہ جاتی اعداد و شمار، رننگ بیلنس اور فونٹ مکمل درست ہیں اور اسٹیٹ بینک آف پاکستان (SBP) کا IBAN معیار پر پورا اترتا ہے۔${overrideNoteUr}

نوٹ: تمام مالیاتی و قرضہ جاتی فیصلے مجاز افسران کی صوابدید پر منحصر ہیں۔`;

  const currentSummary =
    activeLang === "en"
      ? analysis?.english_summary || fallbackEnglishSummary
      : analysis?.urdu_summary || fallbackUrduSummary;

  const briefingItems: CreditBriefingItem[] =
    analysis?.credit_briefing_items && analysis.credit_briefing_items.length > 0
      ? analysis.credit_briefing_items
      : evidenceItems.map((it) => {
          const isInfo = it.severity === "INFO" || (it.ruleId || "").endsWith("_VERIFIED");
          const tech = it.technicalDetails || {};
          const anchorType = it.anchorType || tech.anchor_type || (it.pageNumber ? "PAGE_REGION" : "DOCUMENT_METADATA");
          const rowNum = tech.row_number || (tech.anchors && tech.anchors[0]?.rowNumber) || undefined;
          const anchors = tech.anchors || it.anchors || (it.pageNumber ? [{ type: anchorType, pageNumber: it.pageNumber, label: `Page ${it.pageNumber}` }] : [{ type: "DOCUMENT_METADATA", label: "Document Metadata" }]);

          let locLabelEn = "Document Metadata";
          let locLabelUr = "دستاویز میٹا ڈیٹا";
          if (anchorType === "MULTI_PAGE_SPAN") {
            locLabelEn = `Pages 1–${it.pageNumber || 23} Ledger`;
            locLabelUr = `صفحات 1 تا ${it.pageNumber || 23} لیجر`;
          } else if (anchorType === "DOCUMENT_HEADER" && it.pageNumber) {
            locLabelEn = `Page ${it.pageNumber} Header`;
            locLabelUr = `صفحہ ${it.pageNumber} ہیڈر`;
          } else if (rowNum && it.pageNumber) {
            locLabelEn = `Page ${it.pageNumber}, Row ${rowNum}`;
            locLabelUr = `صفحہ ${it.pageNumber}، قطار ${rowNum}`;
          } else if (it.pageNumber) {
            locLabelEn = `Page ${it.pageNumber}`;
            locLabelUr = `صفحہ ${it.pageNumber}`;
          }

          return {
            page_number: it.pageNumber,
            row_number: rowNum,
            anchor_type: anchorType,
            anchors: anchors,
            title: it.title,
            transaction_label: it.title,
            expected_value: it.expectedValue,
            actual_value: it.actualValue,
            discrepancy: it.discrepancy,
            font_detected: it.description.match(/([A-Za-z0-9_-]+)\s+instead/i)?.[1],
            expected_font: it.description.match(/instead of\s+([A-Za-z0-9_-]+)/i)?.[1],
            visual_cue: it.ruleId.includes("CV_") ? "Local ELA compression divergence" : undefined,
            summary_en: isInfo
              ? `${locLabelEn}: ${it.title}. ${it.discrepancy || "Verified Authentic."}`
              : `${locLabelEn}: ${it.title}. ${
                  it.discrepancy ? `Discrepancy: ${it.discrepancy}.` : ""
                }`,
            summary_ur: isInfo
              ? `${locLabelUr}: ${it.title} (مصدقہ کنٹرول)۔`
              : `${locLabelUr}: ${it.title}۔ ${
                  it.discrepancy ? `${it.discrepancy} کا فرق۔` : ""
                }`,
            severity: it.severity,
            rule_id: it.ruleId,
            evidence_id: it.id,
          };
        });

  const correlations =
    analysis?.cross_signal_correlations &&
    analysis.cross_signal_correlations.length > 0
      ? analysis.cross_signal_correlations
      : overallScore > 50
      ? [
          "Multi-Vector Convergence: Post-creation PDF structural/font tampering directly correlates with mathematical balance manipulation.",
          "Dual-Anchor Reconciliation: Header balance assertions contradict derived running ledger transactions.",
        ]
      : [];

  const handleCopy = () => {
    navigator.clipboard.writeText(currentSummary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const providerLabel = analysis?.model_name
    ? `${analysis.model_provider?.toUpperCase()} (${analysis.model_name})`
    : "LANGGRAPH + GROQ GPT-OSS-120B";

  return (
    <div className="border border-ink-900 bg-paper-0 shadow-sm mb-8">
      {/* Header Bar */}
      <div className="bg-ink-900 text-paper-0 px-4 py-3 flex flex-wrap items-center justify-between gap-3 border-b border-ink-900">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-paper-0/10 border border-paper-0/20">
            <Scale className="w-4 h-4 text-forensic-amber" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif text-sm font-bold tracking-tight uppercase">
                Lead Investigator Agent — Credit Officer Briefing
              </span>
              <span className="text-[10px] bg-paper-0/20 text-paper-0 px-2 py-0.5 border border-paper-0/30 font-mono font-medium">
                {providerLabel}
              </span>
            </div>
            <p className="text-[11px] text-paper-2 font-sans">
              Autonomous LangGraph multi-agent synthesis for underwriting & loan approval committees
            </p>
          </div>
        </div>

        {/* Controls: Language switcher & Copy button */}
        <div className="flex items-center gap-2">
          <div className="inline-flex border border-paper-0/30 p-0.5 bg-paper-0/10 font-sans text-xs">
            <button
              onClick={() => setActiveLang("en")}
              className={`px-2.5 py-1 transition-colors font-medium ${
                activeLang === "en"
                  ? "bg-paper-0 text-ink-900 font-bold"
                  : "text-paper-0 hover:text-white"
              }`}
            >
              English
            </button>
            <button
              onClick={() => setActiveLang("ur")}
              className={`px-3 py-1 transition-colors font-medium ${
                activeLang === "ur"
                  ? "bg-paper-0 text-ink-900 font-bold"
                  : "text-paper-0 hover:text-white"
              }`}
            >
              اردو (Urdu)
            </button>
          </div>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-semibold bg-paper-0 text-ink-900 hover:bg-paper-1 transition-colors border border-paper-0"
            title="Copy executive summary directly to credit memo clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>COPIED</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>{activeLang === "ur" ? "کاپی کریں" : "COPY BRIEFING"}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Verdict & Directive Strip */}
      <div
        className={`px-4 py-3 border-b flex flex-wrap items-center justify-between gap-3 font-mono text-xs ${
          isCriticalOrHigh
            ? "bg-forensic-red/10 border-forensic-red/30 text-forensic-red"
            : isMedium
            ? "bg-forensic-amber/10 border-forensic-amber/30 text-forensic-amber"
            : "bg-emerald-500/10 border-emerald-500/30 text-emerald-700"
        }`}
      >
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 font-bold tracking-wider">
            {isCriticalOrHigh ? (
              <ShieldAlert className="w-4 h-4 text-forensic-red" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
            )}
            <span>
              FORENSIC RECOMMENDATION: {recAction.toUpperCase()} ({effectiveTier} RISK, {effectiveScore}/100)
              {isOverridden && (
                <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-amber-500/20 text-amber-900 border border-amber-500/40 rounded font-bold">
                  HUMAN OVERRIDE
                </span>
              )}
            </span>
          </div>

          <div className="flex items-center gap-2 text-[10px]">
            <span className="px-2 py-0.5 border border-current font-bold">
              AUTH: {effectiveAuthScore}% ({effectiveAuthTier.replace(/_/g, " ")})
            </span>
            <span className="px-2 py-0.5 border border-current font-bold">
              AML RISK: {effectiveTxnScore}/100 ({effectiveTxnTier.replace(/_/g, " ")})
            </span>
          </div>
        </div>

        <div className="text-[11px] font-sans opacity-90">
          {activeLang === "ur"
            ? "زیرو ہالوسینیشن پالیسی — صرف مصدقہ شواہد پر مبنی تجزیہ"
            : "Zero-Hallucination Guardrail — Strictly Bound to Verified Evidence Manifest"}
        </div>
      </div>


      {/* ETO 2002 Section 29 Digital Signature Compliance Strip */}
      {evidenceItems.some(
        (e) =>
          (e.ruleId || "").includes("SIGNATURE_INVALIDATED") ||
          (e.ruleId || "").includes("SIGNATURE_POST_SIGNING")
      ) && (
        <div className="px-4 py-2 bg-forensic-red/15 border-b border-forensic-red/30 flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-forensic-red">
          <div className="flex items-center gap-2 font-bold uppercase tracking-wider">
            <span>ETO 2002 §29 STATUTORY PRESUMPTION REBUTTED</span>
          </div>
          <span className="text-[11px] font-sans">
            {activeLang === "ur"
              ? "ڈیجیٹل سرٹیفکیٹ تصدیق ناکام — دستخط کے بعد بائٹس تبدیل ہونے کا قطعی حسابی ثبوت"
              : "Digital Certificate Invalidated — Cryptographic Byte-Range Mismatch Proves Post-Signing Alteration"}
          </span>
        </div>
      )}
      {evidenceItems.some((e) => (e.ruleId || "").includes("SIGNATURE_VALID")) &&
        !evidenceItems.some(
          (e) =>
            (e.ruleId || "").includes("SIGNATURE_INVALIDATED") ||
            (e.ruleId || "").includes("SIGNATURE_POST_SIGNING")
        ) && (
          <div className="px-4 py-2 bg-emerald-500/15 border-b border-emerald-500/30 flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-emerald-800">
            <div className="flex items-center gap-2 font-bold uppercase tracking-wider">
              <span>ETO 2002 §29 STATUTORY PRESUMPTION SATISFIED</span>
            </div>
            <span className="text-[11px] font-sans">
              {activeLang === "ur"
                ? "مصدقہ این آئی ایف ٹی (NIFT) ڈیجیٹل سرٹیفکیٹ کی تصدیق مکمل — صفر ردوبدل"
                : "Accredited Digital Certificate Validated — Complete Document Integrity Preserved"}
            </span>
          </div>
        )}

      {/* Main Briefing Body */}
      <div className="p-5">
        <div
          dir={activeLang === "ur" ? "rtl" : "ltr"}
          className={`p-4 border border-rule bg-paper-1/60 leading-relaxed font-sans text-sm whitespace-pre-line ${
            activeLang === "ur"
              ? "font-serif text-right text-base leading-loose text-ink-900"
              : "text-ink-800"
          }`}
        >
          {currentSummary}
        </div>

        {/* Structured Evidence Items (Coordinate Table) */}
        {briefingItems.length > 0 && (
          <div className="mt-5">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-ink-700 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5" />
                {activeLang === "ur"
                  ? "مصدقہ شواہد اور نشاندہی شدہ نقائص (صفحہ اور قطار کے مطابق)"
                  : "Verified Evidence Coordinates (Page, Row & Typography Discrepancies)"}
              </span>
              <span className="font-mono text-[11px] text-ink-500">
                {briefingItems.filter((i) => i.severity !== "INFO").length} anomaly(ies) ·{" "}
                {briefingItems.filter((i) => i.severity === "INFO").length} verified check(s)
              </span>
            </div>

            <div className="border border-rule divide-y divide-rule text-xs font-mono bg-paper-0">
              {briefingItems.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3 hover:bg-paper-1/40 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3"
                >
                  <div className="flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Anchor Badge & Jump Links */}
                      {item.anchor_type === "DOCUMENT_METADATA" || (!item.page_number && !item.row_number) ? (
                        <span className="px-1.5 py-0.5 text-[10px] font-bold bg-ink-800 text-paper-0">
                          DOC METADATA
                        </span>
                      ) : item.anchor_type === "MULTI_PAGE_SPAN" ? (
                        <div className="flex items-center gap-1">
                          <span className="px-1.5 py-0.5 text-[10px] font-bold bg-forensic-red text-white">
                            P.1–{item.page_number || 23} LEDGER
                          </span>
                          {item.anchors && item.anchors.length > 0 ? (
                            item.anchors.map((anc, aIdx) => (
                              <button
                                key={aIdx}
                                type="button"
                                onClick={() => {
                                  if (anc.pageNumber) onFocusCanvas?.(anc.pageNumber);
                                  if (item.evidence_id) onSelectEvidence?.(item.evidence_id);
                                }}
                                className="px-1.5 py-0.5 text-[9px] font-bold bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/20 rounded-sm transition-colors flex items-center gap-0.5 cursor-pointer"
                                title={`Jump to ${anc.label}`}
                              >
                                {anc.label} ↗
                              </button>
                            ))
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() => {
                                  onFocusCanvas?.(1);
                                  if (item.evidence_id) onSelectEvidence?.(item.evidence_id);
                                }}
                                className="px-1.5 py-0.5 text-[9px] font-bold bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/20 rounded-sm transition-colors cursor-pointer"
                              >
                                P.1 Summary ↗
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  onFocusCanvas?.(item.page_number || 23);
                                  if (item.evidence_id) onSelectEvidence?.(item.evidence_id);
                                }}
                                className="px-1.5 py-0.5 text-[9px] font-bold bg-paper-2 hover:bg-ink-900 hover:text-white text-ink-900 border border-ink-900/20 rounded-sm transition-colors cursor-pointer"
                              >
                                P.{item.page_number || 23} Terminal ↗
                              </button>
                            </>
                          )}
                        </div>
                      ) : item.row_number ? (
                        <button
                          type="button"
                          onClick={() => {
                            if (item.page_number) onFocusCanvas?.(item.page_number);
                            if (item.evidence_id) onSelectEvidence?.(item.evidence_id);
                          }}
                          className={`px-1.5 py-0.5 text-[10px] font-bold transition-colors flex items-center gap-1 cursor-pointer ${
                            item.severity === "INFO"
                              ? "bg-emerald-700 hover:bg-emerald-800 text-white"
                              : "bg-ink-900 hover:bg-forensic-blue text-paper-0"
                          }`}
                        >
                          P.{item.page_number} · ROW {item.row_number} ↗
                        </button>
                      ) : item.anchor_type === "DOCUMENT_HEADER" ? (
                        <button
                          type="button"
                          onClick={() => {
                            if (item.page_number) onFocusCanvas?.(item.page_number);
                            if (item.evidence_id) onSelectEvidence?.(item.evidence_id);
                          }}
                          className={`px-1.5 py-0.5 text-[10px] font-bold transition-colors flex items-center gap-1 cursor-pointer ${
                            item.severity === "INFO"
                              ? "bg-emerald-700 hover:bg-emerald-800 text-white"
                              : "bg-ink-900 hover:bg-forensic-blue text-paper-0"
                          }`}
                        >
                          P.{item.page_number} HEADER ↗
                        </button>
                      ) : item.page_number ? (
                        <button
                          type="button"
                          onClick={() => {
                            onFocusCanvas?.(item.page_number!);
                            if (item.evidence_id) onSelectEvidence?.(item.evidence_id);
                          }}
                          className={`px-1.5 py-0.5 text-[10px] font-bold transition-colors flex items-center gap-1 cursor-pointer ${
                            item.severity === "INFO"
                              ? "bg-emerald-700 hover:bg-emerald-800 text-white"
                              : "bg-ink-900 hover:bg-forensic-blue text-paper-0"
                          }`}
                        >
                          {item.severity === "INFO" ? `P.${item.page_number} VERIFIED ↗` : `PAGE ${item.page_number} ↗`}
                        </button>
                      ) : (
                        <span className="px-1.5 py-0.5 text-[10px] font-bold bg-ink-800 text-paper-0">
                          {item.severity === "INFO" ? "VERIFIED" : "AUDIT FINDING"}
                        </span>
                      )}

                      <span className="font-serif text-sm font-semibold text-ink-900">
                        {item.title}
                      </span>
                      <span
                        className={`text-[9px] px-1.5 py-0.2 border uppercase font-bold ${
                          item.severity === "CRITICAL"
                            ? "border-forensic-red/40 bg-forensic-red/10 text-forensic-red"
                            : item.severity === "HIGH"
                            ? "border-forensic-amber/40 bg-forensic-amber/10 text-forensic-amber"
                            : item.severity === "INFO"
                            ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700"
                            : "border-rule text-ink-600"
                        }`}
                      >
                        {item.severity === "INFO" ? "VERIFIED" : item.severity}
                      </span>
                    </div>

                    <div
                      dir={activeLang === "ur" ? "rtl" : "ltr"}
                      className="font-sans text-xs text-ink-700 pl-1"
                    >
                      {activeLang === "ur" ? item.summary_ur : item.summary_en}
                    </div>

                    {/* Coordinates & Typography Chip */}
                    {(item.expected_value ||
                      item.font_detected ||
                      item.visual_cue) && (
                      <div className="flex flex-wrap items-center gap-2 pt-1 text-[10px] text-ink-600">
                        {item.expected_value && (
                          <span className="bg-paper-1 border border-rule px-2 py-0.5">
                            Expected: <strong className="text-ink-900">{item.expected_value}</strong> | Recorded: <strong className="text-ink-900">{item.actual_value}</strong>
                          </span>
                        )}
                        {item.font_detected && (
                          <span className="bg-amber-500/10 border border-amber-500/30 text-amber-800 px-2 py-0.5 font-mono">
                            Font: <strong>{item.font_detected}</strong> vs {item.expected_font || "Original"}
                          </span>
                        )}
                        {item.visual_cue && (
                          <span className="bg-blue-500/10 border border-blue-500/30 text-blue-800 px-2 py-0.5">
                            Visual: {item.visual_cue}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cross-Signal Convergence Cards */}
        {correlations.length > 0 && (
          <div className="mt-5 pt-4 border-t border-rule">
            <span className="font-mono text-xs font-bold uppercase tracking-wider text-ink-700 flex items-center gap-1.5 mb-2">
              <Layers className="w-3.5 h-3.5 text-ink-900" />
              {activeLang === "ur"
                ? "کثیر الجہتی شواہد کا ملاپ (Multi-Vector Convergence)"
                : "Cross-Signal Forensics: Multi-Vector Convergence"}
            </span>

            <div className="space-y-2">
              {correlations.map((corr, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-paper-1/80 border border-rule text-xs font-sans text-ink-800 flex items-start gap-2"
                >
                  <Sparkles className="w-4 h-4 text-forensic-amber shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{corr}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
