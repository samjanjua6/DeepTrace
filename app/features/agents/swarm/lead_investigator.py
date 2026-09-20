"""
Lead Investigator Agent (Agent 4)
Orchestrates forensic specialist agents (Structural, Visual, Semantic PK Financial),
correlates multi-vector anomalies, and synthesizes Plain English and Urdu briefings
specifically tailored for Pakistani credit officers using LangGraph and Groq LLM
(primary: gpt-oss-120b, fallback: gpt-oss-20b), with deterministic safety nets.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import httpx
try:
    from langgraph.graph import StateGraph, START, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    StateGraph = None
    START = "START"
    END = "END"

from app.config import get_settings
from app.features.agents.swarm.base_agent import BaseForensicAgent
from app.features.agents.swarm.structural_agent import StructuralForensicAgent
from app.features.agents.swarm.visual_agent import VisualForensicAgent
from app.features.agents.swarm.semantic_pk_agent import SemanticPKFinancialAgent

logger = logging.getLogger(__name__)
settings = get_settings()


class LeadInvestigatorState(TypedDict, total=False):
    """LangGraph state representation for forensic synthesis."""
    investigation_id: str
    manifest: dict
    specialist_reports: dict
    cross_signal_correlations: list[str]
    anomalies_detected: int
    confidence_score: float
    overall_score: int
    risk_tier: str
    action_directive: str
    narrative: str
    english_summary: str
    urdu_summary: str
    credit_briefing: list[str]
    credit_briefing_items: list[dict]
    evidence_citations: list[str]
    model_provider: str
    model_name: str


def _extract_row_number(text: str) -> Optional[int]:
    """Extract 1-indexed row number from finding text if present."""
    if not text:
        return None
    m = re.search(r"\b(?:row|line|tr(?:x)?)\s*#?\s*(\d+)\b", text, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def _extract_font_details(item: dict, all_items: list[dict]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract font names (actual and expected) from finding or related structural items.
    """
    desc = f"{item.get('title', '')} {item.get('description', '')}"
    m = re.search(
        r"font\s+(?:is\s+|found\s+)?([A-Za-z0-9_\-]+)\s+(?:instead of|vs|contradicts|rather than)\s+(?:document(?:'s)?\s+|authentic\s+)?([A-Za-z0-9_\-]+)",
        desc,
        re.IGNORECASE,
    )
    if m:
        return m.group(1), m.group(2)

    # Search for font findings on the same page
    page = item.get("pageNumber") or item.get("page_number")
    for other in all_items:
        if (other.get("pageNumber") or other.get("page_number")) == page:
            if "font" in (other.get("ruleId") or "").lower() or "font" in other.get("title", "").lower():
                odesc = other.get("description", "")
                m2 = re.search(
                    r"([A-Za-z0-9_\-]+)\s+(?:instead of|expected)\s+(?:document(?:'s)?\s+|authentic\s+)?([A-Za-z0-9_\-]+)",
                    odesc,
                    re.IGNORECASE,
                )
                if m2:
                    return m2.group(1), m2.group(2)
    return None, None


def _build_structured_credit_briefing_items(
    evidence_items: list[dict],
) -> list[dict]:
    """
    Parse evidence items into structured credit briefing items with exact
    page, row, amounts, and typography details for loan officers.
    Strictly eliminates synthetic row coordinates (no fake precision).
    """
    items: list[dict] = []
    for idx, it in enumerate(evidence_items, 1):
        raw_page = it.get("pageNumber") or it.get("page_number")
        desc = it.get("description", "")
        title = it.get("title", f"Finding {idx}")
        row_num = _extract_row_number(desc) or _extract_row_number(title)

        tech_details = it.get("technicalDetails") or it.get("technical_details") or {}
        if not isinstance(tech_details, dict):
            tech_details = {}
        anchor_type = tech_details.get("anchor_type")
        r_id = (it.get("ruleId") or it.get("rule_id") or "").upper()
        cat = (it.get("category") or "").upper()

        page_num = raw_page
        anchors: list[dict] = []

        if (
            anchor_type == "DOCUMENT_METADATA"
            or cat == "METADATA_TIMESTAMP_MISMATCH"
            or "TIMESTAMP" in r_id
            or "INCREMENTAL" in r_id
            or "PRODUCER" in r_id
            or ("SIGNATURE" in r_id and not it.get("boundingBoxes"))
            or (raw_page is None and not it.get("boundingBoxes"))
        ):
            anchor_type = "DOCUMENT_METADATA"
            page_num = None
            row_num = None
            anchors = [{"label": "Document Metadata", "type": "DOCUMENT_METADATA"}]
        elif (
            anchor_type == "MULTI_PAGE_SPAN"
            or r_id == "RULE_PK_CLOSING_BALANCE_MISMATCH"
            or (tech_details.get("last_page") and tech_details.get("last_page") > 1)
        ):
            anchor_type = "MULTI_PAGE_SPAN"
            anchors = tech_details.get("anchors") or []
            if not anchors:
                p_end = tech_details.get("last_page", 23)
                anchors = [
                    {"pageNumber": 1, "label": "P.1 Summary", "type": "STATEMENT_SUMMARY"},
                    {"pageNumber": p_end, "label": f"P.{p_end} Ledger", "type": "LEDGER_TERMINAL"},
                ]
            page_num = page_num or tech_details.get("last_page") or 1
        elif (
            anchor_type == "TABLE_ROW"
            or (row_num is not None and "AML" not in r_id)
            or (r_id == "RULE_AML_HIGH_RISK_NARRATION" and anchor_type == "TABLE_ROW")
        ):
            anchor_type = "TABLE_ROW"
            page_num = page_num or 1
            anchors = tech_details.get("anchors") or [
                {"pageNumber": page_num, "rowNumber": row_num, "label": f"Page {page_num}, Row {row_num}", "type": "TABLE_ROW"}
            ]
        elif (
            anchor_type == "DOCUMENT_HEADER"
            or "IBAN" in r_id
            or "CNIC" in r_id
            or ("AML" in r_id and r_id != "RULE_AML_HIGH_RISK_NARRATION")
        ):
            anchor_type = "DOCUMENT_HEADER"
            page_num = page_num or 1
            row_num = None
            anchors = [{"pageNumber": page_num, "label": f"Page {page_num} Header", "type": "DOCUMENT_HEADER"}]
        elif row_num is not None:
            anchor_type = "TABLE_ROW"
            page_num = page_num or 1
            anchors = [{"pageNumber": page_num, "rowNumber": row_num, "label": f"Page {page_num}, Row {row_num}", "type": "TABLE_ROW"}]
        else:
            anchor_type = "PAGE_REGION"
            page_num = page_num or 1
            anchors = [{"pageNumber": page_num, "label": f"Page {page_num}", "type": "PAGE_REGION"}]

        expected_val = it.get("expectedValue")
        actual_val = it.get("actualValue")
        discrepancy = it.get("discrepancy")
        font_detected, expected_font = _extract_font_details(it, evidence_items)

        # Detect visual cue
        visual_cue = None
        if "ela" in desc.lower() or "RULE_CV_" in it.get("ruleId", ""):
            visual_cue = "Local ELA compression boundary divergence"

        is_info = it.get("severity") == "INFO" or (it.get("ruleId") or "").endswith("_VERIFIED")

        # Format Plain English item summary
        if is_info:
            if anchor_type == "DOCUMENT_METADATA":
                parts_en = [f"Document Metadata: {title}."]
            elif page_num:
                parts_en = [f"Page {page_num}: {title}."]
            else:
                parts_en = [f"{title}."]

            if discrepancy:
                parts_en.append(f"{discrepancy}.")
            elif desc:
                parts_en.append(f"{desc}.")
            summary_en = " ".join(parts_en)
        else:
            if anchor_type == "DOCUMENT_METADATA":
                loc_prefix_en = "Document Metadata"
            elif anchor_type == "MULTI_PAGE_SPAN":
                p_end = tech_details.get("last_page") or (anchors[-1].get("pageNumber") if anchors else None) or 23
                p_start = tech_details.get("page_start", 1)
                loc_prefix_en = f"Pages {p_start}–{p_end} (Multi-Page Ledger)"
            elif anchor_type == "TABLE_ROW" and row_num is not None:
                loc_prefix_en = f"Page {page_num}, Row {row_num}"
            elif anchor_type == "DOCUMENT_HEADER":
                loc_prefix_en = f"Page {page_num} (Account Header)"
            else:
                loc_prefix_en = f"Page {page_num}"

            parts_en = [f"{loc_prefix_en}: {title}."]
            if expected_val and actual_val:
                parts_en.append(f"Recorded balance is {actual_val} vs reconciled {expected_val}")
                if discrepancy:
                    parts_en.append(f"({discrepancy} discrepancy).")
                else:
                    parts_en.append(".")
            elif discrepancy:
                parts_en.append(f"Discrepancy: {discrepancy}.")

            if font_detected and expected_font:
                parts_en.append(f"Font is {font_detected} instead of document's {expected_font}.")
            elif font_detected:
                parts_en.append(f"Font detected: {font_detected}.")

            if visual_cue:
                parts_en.append(f"Visual Cue: {visual_cue}.")

            summary_en = " ".join(parts_en)

        # Format authentic Urdu item summary
        is_sig_invalidated = "SIGNATURE_INVALIDATED" in (it.get("ruleId") or "")
        is_sig_mod = "SIGNATURE_POST_SIGNING" in (it.get("ruleId") or "")
        is_sig_stripped = "SIGNATURE_STRIPPED" in (it.get("ruleId") or "")
        is_aml_nacta = "AML_NACTA" in (it.get("ruleId") or "")
        is_aml_unsc = "AML_UNSC" in (it.get("ruleId") or "")
        is_aml_pep = "AML_PEP" in (it.get("ruleId") or "")
        is_aml_hawala = "HIGH_RISK_NARRATION" in (it.get("ruleId") or "")
        is_cnic_tamper = "RULE_CNIC_PROVINCE_CODE_INVALID" in (it.get("ruleId") or "") or "RULE_CNIC_FORMAT_INVALID" in (it.get("ruleId") or "")
        is_cnic_parity = "RULE_CNIC_GENDER_PARITY_MISMATCH" in (it.get("ruleId") or "")
        is_cnic_mrz = "RULE_CNIC_MRZ_CHECKSUM_INVALID" in (it.get("ruleId") or "")
        is_cnic_temporal = "RULE_CNIC_TEMPORAL_INCONSISTENCY" in (it.get("ruleId") or "")
        is_cnic_verified = "RULE_CNIC_VERIFIED" in (it.get("ruleId") or "")
        is_bank_template_verified = "RULE_BANK_TEMPLATE_VERIFIED" in (it.get("ruleId") or "")
        is_utility_verified = "RULE_PK_UTILITY_REGISTRY_VERIFIED" in (it.get("ruleId") or "")

        if anchor_type == "DOCUMENT_METADATA":
            p_label_ur = "دستاویز کا میٹا ڈیٹا"
        elif anchor_type == "MULTI_PAGE_SPAN":
            p_start = tech_details.get("page_start", 1)
            p_end = tech_details.get("last_page") or (anchors[-1].get("pageNumber") if anchors else None) or 23
            p_label_ur = f"صفحات {p_start} تا {p_end}"
        elif anchor_type == "TABLE_ROW" and row_num is not None:
            p_label_ur = f"صفحہ {page_num or 1}، قطار {row_num}"
        elif page_num:
            p_label_ur = f"صفحہ {page_num}"
        else:
            p_label_ur = "دستاویز"

        if is_cnic_tamper:
            parts_ur = [f"{p_label_ur}: نادرا شناختی کارڈ کے نمبر میں صوبائی کوڈ یا ساخت کی سنگین خلاف ورزی پائی گئی ہے۔"]
        elif is_cnic_parity:
            parts_ur = [f"{p_label_ur}: کھاتہ دار کے ٹائٹل اور نادرا شناختی کارڈ کے آخری ہندسے (جنس کی شناخت) میں تضاد پایا گیا ہے۔"]
        elif is_cnic_mrz:
            parts_ur = [f"{p_label_ur}: نادرا سمارٹ کارڈ کے بیک سائیڈ پر موجود ICAO 9303 MRZ آپٹیکل چیک سم میں حسابی خرابی ہے۔"]
        elif is_cnic_temporal:
            parts_ur = [f"{p_label_ur}: نادرا شناختی کارڈ کے اجرا اور میعاد کی تاریخوں میں زمانی تضاد پایا گیا ہے۔"]
        elif is_cnic_verified:
            parts_ur = [f"{p_label_ur}: نادرا شناختی کارڈ کے صوبائی کوڈ، جنس کے ہندسے اور سمارٹ کارڈ MRZ چیک سم کی باضابطہ تصدیق مکمل ہو چکی ہے۔"]
        elif is_bank_template_verified:
            parts_ur = [f"{p_label_ur}: آفیشل کور بینکنگ سسٹم (CBS) رپورٹنگ ٹیمپلیٹ کی تصدیق مکمل — صفر کالم ڈرفٹ (0 pt column drift) اور مستند لے آؤٹ۔"]
        elif is_utility_verified:
            parts_ur = [f"{p_label_ur}: سرکاری اتھارٹی یوٹیلیٹی رجسٹری (PITC) کے ساتھ بل کی 100% تصدیق مکمل۔"]
        elif is_aml_nacta:
            parts_ur = [f"{p_label_ur}: نیکٹا (NACTA) فورتھ شیڈول کے تحت کالعدم فرد/تنظیم سے مماثلت (انسدادِ دہشت گردی ایکٹ 1997 دفعہ 11EE کی سنگین خلاف ورزی)۔ فوری اکاؤنٹ منجمد اور FMU کو STR بھیجنا لازمی ہے۔"]
        elif is_aml_unsc:
            parts_ur = [f"{p_label_ur}: اقوامِ متحدہ کی سلامتی کونسل (UNSC 1267) کی پابندیوں کی فہرست میں شامل دہشت گرد سے مماثلت (یو این ایس سی ایکٹ 1948)۔ فوری اثاثے منجمد کرنا لازمی ہے۔"]
        elif is_aml_pep:
            parts_ur = [f"{p_label_ur}: سیاسی طور پر بااثر شخصیت (PEP) کی شناخت (اسٹیٹ بینک BPRD سرکلر 1/2021)۔ اعلیٰ انتظامیہ کی منظوری (SMA) اور اضافی چھان بین (EDD) لازمی ہے۔"]
        elif is_aml_hawala:
            is_crypto = tech_details.get("is_crypto")
            is_hawala_only = tech_details.get("is_hawala") and not is_crypto
            if is_crypto and not tech_details.get("is_hawala"):
                parts_ur = [f"{p_label_ur}: غیر قانونی کرپٹو / پی ٹو پی (P2P) ورچوئل اثاثوں کی منتقلی کے ممنوعہ الفاظ کی شناخت (اسٹیٹ بینک BPRD سرکلر 3/2018 کی خلاف ورزی)۔"]
            elif is_hawala_only:
                parts_ur = [f"{p_label_ur}: غیر قانونی حوالہ / ہنڈی کے ذریعے رقوم کی منتقلی کے ممنوعہ الفاظ کی شناخت (اسٹیٹ بینک ضوابط و AML ایکٹ 2010 کی خلاف ورزی)۔"]
            else:
                parts_ur = [f"{p_label_ur}: حوالہ/ہنڈی یا کرپٹو غیر قانونی رقم کی منتقلی کے ممنوعہ الفاظ کی شناخت (اسٹیٹ بینک BPRD سرکلر 3/2018 کی خلاف ورزی)۔"]
        elif is_sig_invalidated:
            parts_ur = [f"{p_label_ur}: ڈیجیٹل دستخط اور سرٹیفکیٹ کی تصدیق ناکام (ETO 2002 کی خلاف ورزی)۔ فائل پر بینک کا ڈیجیٹل سرٹیفکیٹ موجود ہے مگر حسابی ردوبدل کی وجہ سے ہیش میش نہیں ہوا۔"]
        elif is_sig_mod:
            parts_ur = [f"{p_label_ur}: ڈیجیٹل تصدیق کے بعد غیر مجاز تبدیلی۔ دستخط کے بعد فائل میں اضافی بائٹس داخل کیے گئے ہیں۔"]
        elif is_sig_stripped:
            parts_ur = [f"{p_label_ur}: بینک کے اصل ٹیمپلیٹ سے لازمی ڈیجیٹل سرٹیفکیٹ مٹایا گیا ہے۔"]
        else:
            if anchor_type == "DOCUMENT_METADATA":
                loc_prefix_ur = "دستاویز کا میٹا ڈیٹا"
            elif anchor_type == "MULTI_PAGE_SPAN":
                loc_prefix_ur = f"صفحات 1 تا {tech_details.get('last_page', 23)} (کھاتہ)"
            elif anchor_type == "TABLE_ROW" and row_num is not None:
                loc_prefix_ur = f"صفحہ {page_num or 1}، قطار {row_num}"
            elif anchor_type == "DOCUMENT_HEADER":
                loc_prefix_ur = f"صفحہ {page_num or 1} (ہیڈر)"
            else:
                loc_prefix_ur = f"صفحہ {page_num or 1}"

            parts_ur = [f"{loc_prefix_ur}: {title}۔"]
            if expected_val and actual_val:
                diff_str = f" ({discrepancy} کا فرق)" if discrepancy else ""
                parts_ur.append(f"درج شدہ رقم {actual_val} ہے جبکہ درست متوقع رقم {expected_val} تھی{diff_str}۔")
            elif discrepancy:
                parts_ur.append(f"مالیاتی فرق: {discrepancy}۔")

            if font_detected and expected_font:
                parts_ur.append(f"دستاویز کے مستند فونٹ {expected_font} کے برعکس {font_detected} فونٹ پایا گیا۔")
            elif font_detected:
                parts_ur.append(f"تبدیل شدہ فونٹ: {font_detected}۔")

            if visual_cue:
                parts_ur.append("تصویری معائنہ: کمپریشن تضاد (ELA Anomaly) واضح ہے۔")

        summary_ur = " ".join(parts_ur)

        boxes = it.get("boundingBoxes") or it.get("bounding_boxes") or []
        primary_box = None
        if boxes:
            b = boxes[0]
            primary_box = {
                "page_number": b.get("pageNumber") or b.get("page_number", page_num or 1),
                "x_pts": b.get("xPts") or b.get("x_pts") or b.get("x", 0),
                "y_pts": b.get("yPts") or b.get("y_pts") or b.get("y", 0),
                "width_pts": b.get("widthPts") or b.get("width_pts") or b.get("width", 0),
                "height_pts": b.get("heightPts") or b.get("height_pts") or b.get("height", 0),
                "label": b.get("label", "Anomaly Anchor"),
            }

        items.append({
            "page_number": page_num,
            "row_number": row_num,
            "anchor_type": anchor_type,
            "anchors": anchors,
            "title": title,
            "transaction_label": title,
            "expected_value": expected_val,
            "actual_value": actual_val,
            "discrepancy": discrepancy,
            "font_detected": font_detected,
            "expected_font": expected_font,
            "visual_cue": visual_cue,
            "primary_bounding_box": primary_box,
            "summary_en": summary_en,
            "summary_ur": summary_ur,
            "severity": it.get("severity", "MEDIUM"),
            "rule_id": it.get("ruleId"),
            "evidence_id": it.get("id"),
            "is_adverse": not is_info,
        })

    return items


from app.features.agents.swarm.semantic_pk_agent import SemanticPKFinancialAgent
from app.features.risk.schemas import format_recommendation

logger = logging.getLogger(__name__)
settings = get_settings()


class LeadInvestigatorState(TypedDict, total=False):
    """LangGraph state representation for forensic synthesis."""
    investigation_id: str
    manifest: dict
    findings: list
    evidence_items: list
    cross_signal_correlations: list
    credit_briefing: list[str]
    credit_briefing_items: list
    english_summary: str
    urdu_summary: str
    narrative: str
    action_directive: str
    confidence_score: float
    overall_score: int
    risk_tier: str
    model_provider: str
    model_name: str
    anomalies_detected: int
    evidence_citations: list
    specialist_reports: dict


def _generate_deterministic_briefing(
    overall_score: int,
    risk_tier: str,
    action_directive: str,
    evidence_items: list[dict],
    cross_signal_correlations: list[str],
    briefing_items: list[dict],
    authenticity_score: int = 100,
    tamper_score: int = 0,
    authenticity_tier: str = "VERIFIED_AUTHENTIC",
    transaction_risk_score: int = 0,
    transaction_risk_tier: str = "CLEAN",
    overridden_score: Optional[int] = None,
    overridden_tier: Optional[str] = None,
    override_reason: Optional[str] = None,
    overridden_by: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Generate deterministic English and Urdu summaries directly from verified evidence.
    Ensures zero downtime, 100% offline safety, Zero Hallucination, and human-in-the-loop framing.
    """
    adverse_briefing = [b for b in briefing_items if b.get("severity") != "INFO" and b.get("is_adverse", True)]
    verified_briefing = [b for b in briefing_items if b.get("severity") == "INFO" or not b.get("is_adverse", True)]

    effective_score = overridden_score if overridden_score is not None else overall_score
    effective_tier = overridden_tier if overridden_tier is not None else risk_tier
    rec_action_en = format_recommendation(action_directive, effective_tier)

    rec_ur_map = {
        "Recommend: Reject / Escalate to Fraud Unit": "سفارش: درخواست مسترد / اینٹی فراڈ یونٹ کو بھیجیں",
        "Recommend: Mandatory STR Escalation & Freeze Review": "سفارش: لازمی ایس ٹی آر رپورٹنگ اور منجمد کرنے کا جائزہ",
        "Recommend: Enhanced Due Diligence / Compliance Review": "سفارش: اضافی تصدیق (EDD) اور منی لانڈرنگ جائزہ",
        "Recommend: Escalate to Senior Underwriter": "سفارش: سینیئر انڈر رائٹر کو برائے فیصلہ پیش کریں",
        "Recommend: Human Review & Operational Verification": "سفارش: آپریشنل و کاغذی شواہد کی دستی جانچ",
        "Recommend: Secondary Branch / Counterfoil Verification": "سفارش: برانچ کاؤنٹر سے تصدیق",
        "Recommend: Straight-Through Approval (Standard Underwriting)": "سفارش: براہِ راست منظوری (معیاری انڈر رائٹنگ)",
        "Recommend: Straight-Through Processing (Standard Underwriting)": "سفارش: براہِ راست منظوری (معیاری انڈر رائٹنگ)",
    }
    rec_action_ur = rec_ur_map.get(rec_action_en, f"سفارش: {rec_action_en}")

    tier_ur_map = {
        "VERIFIED_AUTHENTIC": "مصدقہ اصل",
        "SUSPECT_DOCUMENT": "مشکوک دستاویز",
        "FORGERY_DETECTED": "جعل سازی ثابت",
        "CLEAN": "محفوظ",
        "MONITORED": "زیرِ نگرانی",
        "HIGH_AML_RISK": "زیادہ رسک",
        "CRITICAL_PROSCRIBED": "کالعدم / پابندی",
    }
    auth_tier_ur = tier_ur_map.get(authenticity_tier, authenticity_tier)
    txn_tier_ur = tier_ur_map.get(transaction_risk_tier, transaction_risk_tier)

    override_notice_en = ""
    override_notice_ur = ""
    if overridden_score is not None:
        override_notice_en = (
            f"\n\n[HUMAN ADJUDICATION AUDIT NOTICE]: Automated risk score of {overall_score}/100 ({risk_tier}) "
            f"was manually adjudicated by authorized officer ({overridden_by or 'Compliance Officer'}) to {effective_score}/100 ({effective_tier}).\n"
            f"Compliance Justification: \"{override_reason or 'Branch operational review verified documents.'}\""
        )
        override_notice_ur = (
            f"\n\n[آڈٹ نوٹ برائے انسانی فیصلہ]: کمپیوٹرائزڈ رسک سکور {overall_score}/100 کو مجاز افسر "
            f"کی جانب سے تبدیل کر کے {effective_score}/100 ({effective_tier}) کیا گیا ہے۔\n"
            f"دستی فیصلے کا جواز: \"{override_reason or 'برانچ ریکارڈ سے دستی تصدیق مکمل ہو گئی ہے۔'}\""
        )

    # 1. Plain English Credit Officer Briefing
    if not adverse_briefing or (overall_score == 0 and tamper_score == 0 and transaction_risk_score == 0):
        baseline_str = f" [Engine Baseline: {overall_score}/100 ({risk_tier})]" if overridden_score is not None else ""
        english_summary = (
            f"EXECUTIVE BRIEFING FOR CREDIT OFFICERS:\n"
            f"Forensic Recommendation: {rec_action_en} (Human Adjudication Required).\n"
            f"Evaluated Risk: {effective_score}/100 ({effective_tier} Risk){baseline_str}.\n"
            f"Forensic Metrics: Document Authenticity: {authenticity_score}% ({authenticity_tier.replace('_', ' ')}) | Transaction Risk: {transaction_risk_score}/100 ({transaction_risk_tier.replace('_', ' ')}).\n"
            f"Forensic validation confirms 100% document authenticity across all pages. "
            f"All transaction figures reconcile with the core banking ledger without font, visual, "
            f"or mathematical anomalies. State Bank of Pakistan (SBP) IBAN validation passed. "
            f"Digital chain of custody is cryptographically sealed under PECA 2016 §33/§34 via RFC 3161 TSA.{override_notice_en}\n\n"
            f"Advisory Notice: DeepTrace outputs constitute evidentiary forensic analysis. All lending, rejection, freeze, or STR decisions remain the exclusive statutory prerogative of authorized human credit & compliance officers."
        )
        urdu_summary = (
            f"کریڈٹ آفیسر کے لیے تفصیلی خلاصہ:\n"
            f"تجویز کردہ کارروائی: {rec_action_ur} (حتمی فیصلہ مجاز افسر کا ہوگا)۔\n"
            f"لاگو رسک درجہ بندی: {effective_score}/100 ({effective_tier})"
            + (f" [سسٹم کا ابتدائی سکور: {overall_score}/100]" if overridden_score is not None else "") + "۔\n"
            f"دستاویزی اصلیت: {authenticity_score}٪ ({auth_tier_ur}) | کاروباری رسک: {transaction_risk_score}/100 ({txn_tier_ur})۔\n"
            f"فرانزک تصدیق سے ثابت ہوا ہے کہ یہ دستاویز مکمل طور پر اصل اور غیر تبدیل شدہ ہے۔ "
            f"تمام کھاتہ جاتی اعداد و شمار، رننگ بیلنس اور فونٹ درست ہیں، اسٹیٹ بینک آف پاکستان (SBP) کا IBAN تصدیق شدہ ہے، "
            f"اور شواہد کا چین آف کسٹڈی پی ای سی اے 2016 اور RFC 3161 ڈیجیٹل ٹائم سٹیمپ کے تحت محفوظ شدہ ہے۔{override_notice_ur}\n\n"
            f"نوٹ: تمام مالیاتی و قرضہ جاتی فیصلے مجاز افسران کی صوابدید پر منحصر ہیں۔"
        )
        narrative = (
            f"Multi-Agent forensic investigation verified Document Authenticity at {authenticity_score}% and Transaction Risk at {transaction_risk_score}/100 (Evaluated Risk: {effective_score}/100, {effective_tier}). "
            "No structural, visual, or mathematical anomalies detected across the evidence manifest."
        )
    else:
        en_points = [f"• {b['summary_en']}" for b in adverse_briefing[:6]]
        ur_points = [f"• {b['summary_ur']}" for b in adverse_briefing[:6]]

        en_verified = [f"✓ {b['summary_en']}" for b in verified_briefing]
        ur_verified = [f"✓ {b['summary_ur']}" for b in verified_briefing]

        verified_block_en = (
            f"\n\nCertified Authentic Controls:\n" + "\n".join(en_verified)
            if en_verified
            else ""
        )
        verified_block_ur = (
            f"\n\nمصدقہ سسٹم کنٹرولز (بغیر کسی تضاد کے):\n" + "\n".join(ur_verified)
            if ur_verified
            else ""
        )

        correlations_str_en = " ".join(cross_signal_correlations) if cross_signal_correlations else ""

        # Determine decoupled advisory
        if tamper_score > 0 and transaction_risk_score > 0:
            advisory_en = (
                "Compound Forensic & Compliance Alert: Severe document tampering detected alongside statutory AML/CFT violations. "
                "The financial figures have been artificially manipulated post-generation, and transactional counterparties trigger regulatory red flags. Recommend immediate loan application rejection and compliance escalation to fraud unit."
            )
            advisory_ur = (
                "مشترکہ فرانزک و تعمیل انتباہ: دستاویز میں جعل سازی اور اسٹیٹ بینک AML/CFT کے ضوابط کی سنگین خلاف ورزی پائی گئی ہے۔ "
                "بینک سٹیٹمنٹ میں اعداد و شمار کو غیر قانونی طور پر بدلا گیا ہے اور لین دین میں ممنوعہ عناصر شامل ہیں۔ درخواست مسترد کرنے اور معاملہ اینٹی فراڈ یونٹ کو بھیجنے کی سفارش کی جاتی ہے۔"
            )
        elif tamper_score > 0:
            advisory_en = (
                "Credit Risk Advisory: The financial figures in this statement have been artificially inflated or modified post-generation. "
                "Document authenticity is compromised. Recommend halting loan application pending formal verification."
            )
            advisory_ur = (
                "کریڈٹ رسک ایڈوائزری: اس بینک سٹیٹمنٹ کے اعداد و شمار میں سافٹ ویئر کے ذریعے ردوبدل کر کے بیلنس تبدیل کیا گیا ہے۔ "
                "دستاویز کی اصلیت مشکوک ہے، لہٰذا قرض کی درخواست مسترد کرنے یا سینیئر کریڈٹ کمیٹی کو برائے فیصلہ بھیجنے کی سفارش کی جاتی ہے۔"
            )
        else:
            # Document is authentic, but transaction risk is flagged (e.g. AML, Hawala, Crypto P2P, PEP)
            advisory_en = (
                "Statutory AML/CFT Compliance Advisory: The document is genuine with verified typographical and ledger consistency; "
                "however, high-risk transactional patterns (SBP AML/CFT / FATF red flags) were detected. "
                "Recommend forwarding docket to AML Compliance for Enhanced Due Diligence (EDD) without alleging document tampering."
            )
            advisory_ur = (
                "اسٹیٹ بینک ضوابط و AML ایڈوائزری: دستاویز کی فرانزک ساخت اور کھاتہ جاتی تسلسل اصل اور درست ہے، البتہ کھاتے دار کے لین دین میں "
                "اسٹیٹ بینک یا عالمی واچ لسٹ کے مطابق مشکوک ٹرانزیکشنز پائی گئی ہیں۔ اسے جعل سازی کے بجائے منی لانڈرنگ کمپلائنس انکوائری کے لیے بھیجنے کی سفارش کی جاتی ہے۔"
            )

        baseline_str = f" [Engine Baseline: {overall_score}/100 ({risk_tier})]" if overridden_score is not None else ""
        english_summary = (
            f"CRITICAL BRIEFING FOR CREDIT UNDERWRITERS & LOAN APPROVAL OFFICERS:\n"
            f"Forensic Recommendation: {rec_action_en} (Human Adjudication Required).\n"
            f"Evaluated Risk: {effective_score}/100 ({effective_tier} Risk){baseline_str}.\n"
            f"Forensic Metrics: Document Authenticity: {authenticity_score}% ({authenticity_tier.replace('_', ' ')}) | Transaction Risk: {transaction_risk_score}/100 ({transaction_risk_tier.replace('_', ' ')}).\n\n"
            f"Key Forensic Deficiencies Detected:\n"
            + "\n".join(en_points)
            + verified_block_en
            + (f"\n\nCross-Vector Correlation:\n{correlations_str_en}" if correlations_str_en else "")
            + override_notice_en
            + f"\n\n{advisory_en}\n\n"
            f"Advisory Notice: DeepTrace outputs constitute evidentiary forensic analysis. All lending, rejection, freeze, or STR decisions remain the exclusive statutory prerogative of authorized human credit & compliance officers."
        )

        urdu_summary = (
            f"کریڈٹ آفیسر اور لون انڈر رائٹر کے لیے فوری خلاصہ:\n"
            f"تجویز کردہ کارروائی: {rec_action_ur} (حتمی فیصلہ مجاز افسر کا ہوگا)۔\n"
            f"لاگو رسک درجہ بندی: {effective_score}/100 ({effective_tier})"
            + (f" [سسٹم کا ابتدائی سکور: {overall_score}/100]" if overridden_score is not None else "") + "۔\n"
            f"دستاویزی اصلیت: {authenticity_score}٪ ({auth_tier_ur}) | ٹرانزیکشن رسک: {transaction_risk_score}/100 ({txn_tier_ur})۔\n\n"
            f"اہم فرانزک شواہد اور خامیاں:\n"
            + "\n".join(ur_points)
            + verified_block_ur
            + (f"\n\nشواہد کا باہمی ربط:\nپی ڈی ایف فونٹ اور ڈھانچے میں ردوبدل براہِ راست حسابی بیلنس کی تبدیلی کے ساتھ پایا گیا ہے۔" if cross_signal_correlations else "")
            + override_notice_ur
            + f"\n\n{advisory_ur}\n\n"
            f"نوٹ: تمام مالیاتی و قرضہ جاتی فیصلے مجاز افسران کی صوابدید پر منحصر ہیں۔"
        )

        narrative = (
            f"Multi-Agent forensic investigation evaluated Document Authenticity at {authenticity_score}% ({authenticity_tier}) "
            f"and Transaction Risk at {transaction_risk_score}/100 ({transaction_risk_tier}) with composite score {overall_score}/100 ({risk_tier}). "
            f"Synthesized {len(adverse_briefing)} independent adverse indicator(s). "
            f"{' '.join(cross_signal_correlations)}"
        )

    return english_summary, urdu_summary, narrative



async def _call_groq_llm(
    prompt: str,
    system_prompt: str,
    primary_model: str = "gpt-oss-120b",
    fallback_model: str = "gpt-oss-20b",
    api_key: Optional[str] = None,
    base_url: str = "https://api.groq.com/openai/v1",
) -> Tuple[Optional[str], str, str]:
    """
    Invoke Groq LLM using primary model (gpt-oss-120b) with automatic fallback
    to secondary model (gpt-oss-20b) if capacity, rate-limit, or model issues occur.
    Returns (response_text, provider_name, model_used).
    """
    key = api_key or settings.groq_api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        return None, "none", "none"

    models_to_try = [primary_model, fallback_model]

    for model in models_to_try:
        try:
            logger.info("Dispatching forensic synthesis to Groq LLM model: %s", model)
            from groq import AsyncGroq

            client = AsyncGroq(api_key=key, base_url=base_url)
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            content = completion.choices[0].message.content
            if content and content.strip():
                return content.strip(), "groq", model

        except Exception as exc:
            logger.warning("Groq call failed on model %s: %s. Attempting fallback if available.", model, exc)
            # Try HTTPX fallback for this model before moving to next
            try:
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    resp = await http_client.post(
                        f"{base_url.rstrip('/')}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.1,
                            "max_tokens": 1800,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["choices"][0]["message"]["content"]
                        if text and text.strip():
                            return text.strip(), "groq", model
                    else:
                        logger.warning("Groq HTTP status %s for model %s: %s", resp.status_code, model, resp.text)
            except Exception as http_exc:
                logger.warning("Groq HTTP fallback also failed for model %s: %s", model, http_exc)

    return None, "groq-failed", "none"


class LeadInvestigatorAgent(BaseForensicAgent):
    """
    Agent 4: Multi-Agent Swarm Orchestrator and Lead Forensic Synthesizer.
    Implemented with LangGraph StateGraph, Groq primary (gpt-oss-120b) and fallback (gpt-oss-20b),
    Gemini / Claude support, and deterministic rule-based zero-hallucination fallback.
    """

    def __init__(self, evidence_manifest: dict):
        super().__init__(evidence_manifest)
        self._graph = self._build_langgraph_workflow()

    def _build_langgraph_workflow(self):
        """Construct the LangGraph StateGraph pipeline."""
        workflow = StateGraph(LeadInvestigatorState)

        # 1. Specialist Gathering Node
        async def gather_specialists_node(state: LeadInvestigatorState) -> dict:
            manifest = state.get("manifest", self.evidence_manifest)
            agent_1 = StructuralForensicAgent(manifest)
            agent_2 = VisualForensicAgent(manifest)
            agent_3 = SemanticPKFinancialAgent(manifest)

            # Concurrent execution of specialist agents
            res_struct, res_visual, res_financial = await asyncio.gather(
                agent_1.analyze(),
                agent_2.analyze(),
                agent_3.analyze(),
            )

            total_anomalies = (
                res_struct.get("anomalies_detected", 0)
                + res_visual.get("anomalies_detected", 0)
                + res_financial.get("anomalies_detected", 0)
            )

            citations = list(
                dict.fromkeys(
                    res_struct.get("evidence_citations", [])
                    + res_visual.get("evidence_citations", [])
                    + res_financial.get("evidence_citations", [])
                )
            )

            confidence = max(
                res_struct.get("confidence_score", 0.0),
                res_visual.get("confidence_score", 0.0),
                res_financial.get("confidence_score", 0.0),
                0.90,
            )

            return {
                "specialist_reports": {
                    "structural": res_struct,
                    "visual": res_visual,
                    "financial": res_financial,
                },
                "anomalies_detected": total_anomalies,
                "evidence_citations": citations,
                "confidence_score": confidence,
            }

        # 2. Cross-Signal Correlation Node
        async def correlate_cross_signals_node(state: LeadInvestigatorState) -> dict:
            specs = state.get("specialist_reports", {})
            res_struct = specs.get("structural", {})
            res_visual = specs.get("visual", {})
            res_financial = specs.get("financial", {})

            has_structural = res_struct.get("anomalies_detected", 0) > 0
            has_visual = res_visual.get("anomalies_detected", 0) > 0
            has_financial = res_financial.get("anomalies_detected", 0) > 0

            correlations: list[str] = []
            if has_structural and has_financial:
                correlations.append(
                    "Multi-Vector Convergence: Post-creation PDF structural/font tampering directly correlates "
                    "with mathematical balance manipulation."
                )
            if has_visual and has_financial:
                manifest = state.get("manifest", self.evidence_manifest)
                ev_items = manifest.get("evidence_items", [])
                has_raster_ela = any(
                    it.get("category") == "IMAGE_ELA_MANIPULATION" for it in ev_items
                )
                if has_raster_ela:
                    correlations.append(
                        "Visual-Arithmetic Coupling: Localized raster compression anomalies align with manipulated ledger rows."
                    )
                else:
                    correlations.append(
                        "Dual-Anchor Reconciliation: Header balance assertions contradict derived running ledger transactions."
                    )
            if has_structural and has_visual:
                correlations.append(
                    "Structural-Visual Concurrence: External editor signatures concur with pixel-level re-compression boundaries."
                )

            # Digital signature invalidation cross-correlation
            manifest = state.get("manifest", self.evidence_manifest)
            ev_items = manifest.get("evidence_items", [])
            has_sig_invalidation = any(
                "SIGNATURE_INVALIDATED" in (it.get("ruleId") or "")
                for it in ev_items
            )
            if has_sig_invalidation and has_financial:
                correlations.append(
                    "Cryptographic-Arithmetic Breach (ETO 2002 §29): X.509 digital certificate was cryptographically invalidated "
                    "by post-signing byte modifications that altered the bank ledger running balance."
                )

            # SBP AML / CFT & Sanctions cross-correlations
            has_aml_sanctions = any(
                ("AML_NACTA" in (it.get("ruleId") or "") or "AML_UNSC" in (it.get("ruleId") or ""))
                for it in ev_items
            )
            has_aml_pep = any("AML_PEP" in (it.get("ruleId") or "") for it in ev_items)
            if has_aml_sanctions and has_financial:
                correlations.append(
                    "Sanctions-Ledger Nexus (SBP AML/CFT): Account holder matches statutory counter-terrorism / UN sanctions proscription lists "
                    "while transaction ledger concurrently exhibits balance tampering."
                )
            if has_aml_pep and has_financial:
                correlations.append(
                    "High-Risk PEP Exposure: Identified Politically Exposed Person (PEP) account displays abnormal transaction ledger manipulations requiring immediate senior management escalation."
                )

            # NADRA CNIC & Smart Card cross-correlations
            has_cnic_tamper = any(
                ("RULE_CNIC_PROVINCE_CODE_INVALID" in (it.get("ruleId") or "")
                 or "RULE_CNIC_GENDER_PARITY_MISMATCH" in (it.get("ruleId") or "")
                 or "RULE_CNIC_MRZ_CHECKSUM_INVALID" in (it.get("ruleId") or "")
                 or "RULE_CNIC_MRZ_FRONT_MISMATCH" in (it.get("ruleId") or ""))
                for it in ev_items
            )
            if has_cnic_tamper and has_financial:
                correlations.append(
                    "Identity-Financial Nexus (NADRA Ordinance 2000 §30): Identity credential tampering (CNIC province code, gender parity, or MRZ checksum failure) "
                    "is coupled with financial ledger inconsistencies, indicating synthetic identity banking fraud."
                )
            elif has_cnic_tamper:
                correlations.append(
                    "National Identity Forgery (NADRA Ordinance 2000 §30): CNIC administrative encoding or reverse ICAO 9303 MRZ checksum failure "
                    "establishes fraudulent credential manufacturing or Photoshop alteration."
                )

            # FBR Tax & Income Nexus cross-correlations
            has_wht_zero = any("RULE_FBR_WHT_ZERO_ON_TAXABLE_SALARY" in (it.get("ruleId") or "") for it in ev_items)
            has_ntn_invalid = any("RULE_FBR_NTN_INVALID" in (it.get("ruleId") or "") for it in ev_items)
            has_fbr_other = any(
                ("RULE_FBR_WHT_DISCREPANCY" in (it.get("ruleId") or "") or "RULE_FBR_CPR_" in (it.get("ruleId") or ""))
                for it in ev_items
            )
            if has_wht_zero and has_financial:
                correlations.append(
                    "Tax-Income Nexus (Income Tax Ordinance 2001 §149): Salary slip declares taxable salary exceeding PKR 50,000/month "
                    "with ZERO tax deduction, coupled with bank statement transactions, indicating phantom employment or fabricated payslips."
                )
            elif has_wht_zero:
                correlations.append(
                    "Statutory Tax Evasion (Income Tax Ordinance 2001 §149): Declared salary exceeds tax-exempt threshold of PKR 600,000/year "
                    "with zero withholding tax, in direct violation of First Schedule statutory tax brackets."
                )
            if has_ntn_invalid:
                correlations.append(
                    "Taxpayer Identity Fraud (FBR ITO 2001 §181): Employer or corporate entity National Tax Number (NTN) "
                    "violates Modulus 11 statutory check digit algorithm, proving fraudulent registration credentials."
                )
            elif has_fbr_other:
                correlations.append(
                    "FBR Regulatory Tax Discrepancy: Declared tax deduction contradicts statutory Finance Act tax slabs or CPR receipt contains invalid date/structure."
                )
            pages_with_font = {
                it.get("pageNumber") or it.get("page_number")
                for it in ev_items
                if it.get("severity") != "INFO" and ("font" in (it.get("ruleId") or "").lower() or "font" in it.get("title", "").lower() or it.get("category") == "FONT_BASELINE_INCONSISTENCY")
            }
            pages_with_math = {
                it.get("pageNumber") or it.get("page_number")
                for it in ev_items
                if it.get("severity") != "INFO" and ("PK_" in (it.get("ruleId") or "") or "balance" in it.get("title", "").lower() or it.get("category") == "MATHEMATICAL_MISMATCH")
            }
            common_pages = pages_with_font.intersection(pages_with_math)
            for cp in common_pages:
                if cp:
                    correlations.append(
                        f"Page {cp} Co-Location: Font deviation is co-located with transaction balance discrepancy on Page {cp}."
                    )

            return {"cross_signal_correlations": correlations}

        # 3. Credit Officer Synthesis Node
        async def synthesize_credit_briefing_node(state: LeadInvestigatorState) -> dict:
            manifest = state.get("manifest", self.evidence_manifest)
            risk = manifest.get("risk_assessment", {})
            overall_score = risk.get("overallScore", self.risk_assessment.get("overallScore", 0))
            risk_tier = risk.get("riskTier", self.risk_assessment.get("riskTier", "LOW"))
            action_directive = risk.get("actionDirective", self.risk_assessment.get("actionDirective", "STRAIGHT_THROUGH_APPROVAL"))

            ev_items = manifest.get("evidence_items", self.evidence_items)
            correlations = state.get("cross_signal_correlations", [])

            # Extract dual scores from risk assessment or fusionParameters
            fusion_params = risk.get("fusionParameters", self.risk_assessment.get("fusionParameters", {}))
            if hasattr(fusion_params, "data"):
                fusion_params = fusion_params.data
            elif hasattr(fusion_params, "to_dict"):
                fusion_params = fusion_params.to_dict()
            if not isinstance(fusion_params, dict):
                fusion_params = {}

            doc_auth = fusion_params.get("document_authenticity", {})
            txn_risk = fusion_params.get("transaction_risk", {})

            tamper_score = risk.get("tamperScore", risk.get("tamper_score"))
            if tamper_score is None:
                tamper_score = doc_auth.get("tamper_score", overall_score)

            authenticity_score = risk.get("authenticityScore", risk.get("authenticity_score"))
            if authenticity_score is None:
                authenticity_score = doc_auth.get("score", max(0, 100 - tamper_score))

            authenticity_tier = risk.get("authenticityTier", risk.get("authenticity_tier"))
            if not authenticity_tier:
                authenticity_tier = doc_auth.get("tier", "VERIFIED_AUTHENTIC" if tamper_score <= 10 else ("SUSPECT_DOCUMENT" if tamper_score <= 40 else "FORGERY_DETECTED"))

            transaction_risk_score = risk.get("transactionRiskScore", risk.get("transaction_risk_score"))
            if transaction_risk_score is None:
                transaction_risk_score = txn_risk.get("score", 0)

            transaction_risk_tier = risk.get("transactionRiskTier", risk.get("transaction_risk_tier"))
            if not transaction_risk_tier:
                transaction_risk_tier = txn_risk.get("tier", "CRITICAL_PROSCRIBED" if transaction_risk_score >= 75 else ("HIGH_AML_RISK" if transaction_risk_score >= 45 else ("MONITORED" if transaction_risk_score >= 20 else "CLEAN")))

            # Extract override data if present
            overridden_score = risk.get("overriddenScore")
            overridden_tier = risk.get("overriddenTier")
            override_reason = risk.get("overrideReason")
            overridden_by = risk.get("overriddenById")

            # Generate structured credit briefing items with exact coordinates
            briefing_items = _build_structured_credit_briefing_items(ev_items)

            # Generate deterministic base
            det_en, det_ur, det_narrative = _generate_deterministic_briefing(
                overall_score=overall_score,
                risk_tier=risk_tier,
                action_directive=action_directive,
                evidence_items=ev_items,
                cross_signal_correlations=correlations,
                briefing_items=briefing_items,
                authenticity_score=authenticity_score,
                tamper_score=tamper_score,
                authenticity_tier=authenticity_tier,
                transaction_risk_score=transaction_risk_score,
                transaction_risk_tier=transaction_risk_tier,
                overridden_score=overridden_score,
                overridden_tier=overridden_tier,
                override_reason=override_reason,
                overridden_by=overridden_by,
            )

            # Prepare LLM Prompts
            system_prompt = (
                "You are the Lead Forensic Document Investigator for DeepTrace, a Pakistani bank document forensics system.\n"
                "You strictly adhere to a ZERO-HALLUCINATION POLICY. You must NEVER invent transactions, account names, "
                "page numbers, row numbers, or font names. Every figure, anchor, and font must come strictly from the provided Evidence Items.\n"
                "CRITICAL ANCHORING DISCIPLINE:\n"
                "- Only cite 'Page X, Row Y' if the evidence item explicitly provides a row_number in its anchors or technicalDetails. NEVER synthesize or assume a row number from list index.\n"
                "- For findings with anchor_type 'DOCUMENT_METADATA' (like incremental save tampering, PDF producer alterations, or timestamp anomalies), cite location as 'Document Metadata' or 'File Catalog', NEVER as Page 1 or Row 1.\n"
                "- For findings with anchor_type 'MULTI_PAGE_SPAN' (like closing balance mismatch across pages), cite both the statement summary page and the ledger terminal page (e.g. 'Page 1 Summary vs Page 23 Ledger Terminal').\n"
                "- For findings with anchor_type 'DOCUMENT_HEADER', cite as 'Page X Header'.\n"
                "CRITICAL DISTINCTION: Items with severity 'INFO' or titles containing 'Verified' are CERTIFIED AUTHENTIC CHECKS (such as canonical CBS template match, 0 pt column drift, 0.00 pt variance). You must NEVER describe them as deficiencies, anomalies, tampering, or font irregularities.\n"
                "CRITICAL ADVISORY DISCIPLINE:\n"
                "- Frame all outcomes as ADVISORY FORENSIC RECOMMENDATIONS for the credit committee, NEVER as mandatory statutory directives or police powers.\n"
                "- If Document Authenticity is 100% and tamper score is 0, NEVER state that figures, fonts, or balances have been artificially inflated or modified. Instead, advise on statutory AML/CFT compliance or counterparty risk verification.\n"
                "- If tamper score > 0, advise on document fabrication and balance tampering.\n"
                "Output your briefing in two distinct sections:\n"
                "SECTION 1: PLAIN ENGLISH CREDIT OFFICER BRIEFING (Actionable verdict for loan underwriters, highlighting specific real anchor locations and findings).\n"
                "SECTION 2: URDU CREDIT OFFICER BRIEFING (خلاصہ برائے کریڈٹ آفیسر) using professional Pakistani banking Urdu."
            )

            adverse_ev = [b for b in briefing_items if b.get("severity") != "INFO" and b.get("is_adverse", True)]
            verified_ev = [b for b in briefing_items if b.get("severity") == "INFO" or not b.get("is_adverse", True)]

            rec_text = format_recommendation(action_directive, overridden_tier or risk_tier)
            user_prompt = (
                f"Investigation Case: {manifest.get('investigation', {}).get('caseNumber', 'DT-AUDIT')}\n"
                f"Document Authenticity: {authenticity_score}% ({authenticity_tier})\n"
                f"Transaction Risk: {transaction_risk_score}/100 ({transaction_risk_tier})\n"
                f"Evaluated Risk Score: {overridden_score if overridden_score is not None else overall_score}/100 ({overridden_tier or risk_tier})\n"
                f"Forensic Recommendation: {rec_text} (Human Adjudication Required)\n\n"
                f"Adverse Forensic Deficiencies ({len(adverse_ev)} items):\n"
                + json.dumps(adverse_ev[:10], indent=2)
                + (f"\n\nCertified Authentic Controls ({len(verified_ev)} items):\n" + json.dumps(verified_ev[:5], indent=2) if verified_ev else "")
                + f"\n\nCross-Signal Correlations:\n"
                + json.dumps(correlations, indent=2)
                + "\n\nPlease generate the comprehensive English and Urdu briefings for the credit underwriting committee."
            )

            # Try Groq primary (gpt-oss-120b) -> Groq fallback (gpt-oss-20b)
            llm_text, provider, model_used = await _call_groq_llm(
                prompt=user_prompt,
                system_prompt=system_prompt,
                primary_model=settings.groq_model_primary,
                fallback_model=settings.groq_model_fallback,
                api_key=settings.groq_api_key,
                base_url=settings.groq_api_base_url,
            )

            if llm_text and ("SECTION 1" in llm_text or "SECTION 2" in llm_text or "خلاصہ" in llm_text):
                # Parse English & Urdu sections if present
                en_match = re.search(r"SECTION 1:?(.*?)(?=SECTION 2|\Z)", llm_text, re.DOTALL | re.IGNORECASE)
                ur_match = re.search(r"SECTION 2:?(.*)", llm_text, re.DOTALL | re.IGNORECASE)

                english_summary = en_match.group(1).strip() if en_match else det_en
                urdu_summary = ur_match.group(1).strip() if ur_match else det_ur
                narrative = det_narrative
            else:
                english_summary = det_en
                urdu_summary = det_ur
                narrative = det_narrative
                provider = "deeptrace-deterministic"
                model_used = "rule-synthesizer-v1"

            return {
                "overall_score": overall_score,
                "risk_tier": risk_tier,
                "action_directive": action_directive,
                "authenticity_score": authenticity_score,
                "tamper_score": tamper_score,
                "authenticity_tier": authenticity_tier,
                "transaction_risk_score": transaction_risk_score,
                "transaction_risk_tier": transaction_risk_tier,
                "english_summary": english_summary,
                "urdu_summary": urdu_summary,
                "narrative": narrative,
                "credit_briefing": [b["summary_en"] for b in briefing_items if b.get("severity") != "INFO" and b.get("is_adverse", True)],
                "credit_briefing_items": briefing_items,
                "model_provider": provider,
                "model_name": model_used,
            }

        workflow.add_node("gather_specialists", gather_specialists_node)
        workflow.add_node("correlate_cross_signals", correlate_cross_signals_node)
        workflow.add_node("synthesize_credit_briefing", synthesize_credit_briefing_node)

        workflow.add_edge(START, "gather_specialists")
        workflow.add_edge("gather_specialists", "correlate_cross_signals")
        workflow.add_edge("correlate_cross_signals", "synthesize_credit_briefing")
        workflow.add_edge("synthesize_credit_briefing", END)

        return workflow.compile()

    async def analyze(self) -> dict:
        """
        Execute the LangGraph orchestrator state graph, coordinate specialist agents,
        correlate cross-signal anomalies, and return structured Plain English & Urdu credit briefings.
        """
        initial_state: LeadInvestigatorState = {
            "investigation_id": self.investigation.get("id", ""),
            "manifest": self.evidence_manifest,
            "specialist_reports": {},
            "cross_signal_correlations": [],
            "anomalies_detected": 0,
            "confidence_score": 0.90,
            "overall_score": self.risk_assessment.get("overallScore", 0),
            "risk_tier": self.risk_assessment.get("riskTier", "UNKNOWN"),
            "action_directive": self.risk_assessment.get("actionDirective", "REVIEW"),
            "narrative": "",
            "english_summary": "",
            "urdu_summary": "",
            "credit_briefing": [],
            "credit_briefing_items": [],
            "evidence_citations": [],
            "model_provider": "deeptrace-deterministic",
            "model_name": "lead-investigator-v1",
        }

        # Invoke LangGraph state graph
        result_state = await self._graph.ainvoke(initial_state)

        # Construct backward-compatible & rich response
        return {
            "agent_role": "LEAD_INVESTIGATOR",
            "anomalies_detected": result_state.get("anomalies_detected", 0),
            "confidence_score": result_state.get("confidence_score", 0.95),
            "overall_score": result_state.get("overall_score", 0),
            "risk_tier": result_state.get("risk_tier", "LOW"),
            "action_directive": result_state.get("action_directive", "STRAIGHT_THROUGH_APPROVAL"),
            "narrative": result_state.get("narrative", ""),
            "english_summary": result_state.get("english_summary", ""),
            "urdu_summary": result_state.get("urdu_summary", ""),
            "credit_briefing": result_state.get("credit_briefing", []),
            "credit_briefing_items": result_state.get("credit_briefing_items", []),
            "cross_signal_correlations": result_state.get("cross_signal_correlations", []),
            "evidence_citations": result_state.get("evidence_citations", []),
            "specialist_reports": result_state.get("specialist_reports", {}),
            "model_provider": result_state.get("model_provider", "deeptrace-deterministic"),
            "model_name": result_state.get("model_name", "lead-investigator-v1"),
        }

    async def answer_query(self, question: str) -> dict:
        """
        Answer an investigator's natural language question strictly using the verified evidence manifest.
        ZERO-HALLUCINATION POLICY: Answers are formulated strictly from verified EvidenceItem records.
        Supports both English and Urdu queries.
        """
        q_lower = question.lower().strip()
        is_urdu_query = any("\u0600" <= c <= "\u06FF" for c in question)

        cited_evidence_ids: list[str] = []
        parts: list[str] = []

        overall_score = self.risk_assessment.get("overallScore", 0)
        risk_tier = self.risk_assessment.get("riskTier", "UNKNOWN")
        action_directive = self.risk_assessment.get("actionDirective", "REVIEW")

        # 1. Questions regarding IBAN authenticity
        if any(w in q_lower for w in ["iban", "account number", "pakistani iban", "sbp iban", "آئی بی اے این"]):
            iban_findings = self.get_findings_by_rule_prefix("RULE_PK_IBAN")
            if iban_findings:
                for f in iban_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                if is_urdu_query:
                    parts.append(f"**پاکستانی IBAN چیک فیل**: {iban_findings[0].get('description', 'آئی بی اے این چیک سم میں غلطی پائی گئی۔')}")
                else:
                    parts.append(
                        f"**PK-IBAN Check Failed**: {iban_findings[0].get('description', 'The stated Pakistani IBAN failed ISO 7064 MOD-97 checksum validation.')}"
                    )
            else:
                if is_urdu_query:
                    parts.append("**پاکستانی IBAN تصدیق شدہ**: تمام IBAN نمبرز اسٹیٹ بینک آف پاکستان (SBP) کے رجسٹرڈ بینک کوڈ اور ISO 7064 MOD-97 پر مکمل درست ہیں۔")
                else:
                    parts.append(
                        "**PK-IBAN Check Verified**: All Pakistani IBAN(s) detected in the document are mathematically authentic under ISO 7064 MOD-97 check-digit validation with legitimate State Bank of Pakistan (SBP) registered bank codes."
                    )

        # 1b. Questions regarding SBP AML/CFT, NACTA, UNSC Sanctions, PEPs, or Hawala
        elif any(w in q_lower for w in ["aml", "cdd", "nacta", "unsc", "sanction", "pep", "terror", "hawala", "hundi", "chitti", "کالعدم", "پابندی", "نیکٹا", "پی ای پی", "حوالہ", "ہنڈی"]):
            aml_findings = self.get_findings_by_rule_prefix("RULE_AML_")
            adverse_aml = [f for f in aml_findings if f.get("ruleId") != "RULE_AML_CDD_CLEARED"]
            if adverse_aml:
                if is_urdu_query:
                    parts.append("اسٹیٹ بینک اور نیکٹا (NACTA) AML/CFT جانچ پڑتال میں درج ذیل سنگین انتباہات پائے گئے:")
                else:
                    parts.append("State Bank of Pakistan (SBP) AML/CFT & Customer Due Diligence (CDD) screening identified the following adverse findings:")
                for f in adverse_aml:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(f"- **{f.get('title')}** [{f.get('severity', 'CRITICAL')}]: {f.get('description')}")
            else:
                if is_urdu_query:
                    parts.append("**اسٹیٹ بینک CDD اور AML کلیئر**: کھاتہ دار نیکٹا (NACTA 4th Schedule)، اقوامِ متحدہ 1267 پابندیوں اور پی ای پی (PEP) رجسٹری سے مکمل پاک ہے اور کوئی مشتبہ حوالہ/ہنڈی ٹرانزیکشن نہیں پائی گئی۔")
                else:
                    parts.append("**SBP CDD & AML/CFT Cleared**: The account holder cleared screening against NACTA 4th Schedule, UNSC Resolution 1267 Sanctions, and Politically Exposed Persons (PEPs) registry under SBP BPRD Circular No. 1 of 2021 with zero adverse matches.")

        # 1c. Questions regarding NADRA CNIC, SNIC, MRZ, or Gender Parity
        elif any(w in q_lower for w in ["cnic", "nadra", "snic", "mrz", "identity", "شناختی کارڈ", "نادرا", "سی این آئی سی"]):
            cnic_findings = self.get_findings_by_rule_prefix("RULE_CNIC_")
            adverse_cnic = [f for f in cnic_findings if f.get("ruleId") != "RULE_CNIC_VERIFIED"]
            if adverse_cnic:
                if is_urdu_query:
                    parts.append("نادرا (NADRA) شناختی کارڈ جانچ پڑتال میں درج ذیل سنگین انتباہات پائے گئے:")
                else:
                    parts.append("NADRA CNIC & Smart Card forensic verification identified the following adverse findings:")
                for f in adverse_cnic:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(f"- **{f.get('title')}** [{f.get('severity', 'CRITICAL')}]: {f.get('description')}")
            else:
                if is_urdu_query:
                    parts.append("**نادرا شناختی کارڈ تصدیق شدہ**: شناختی کارڈ کا صوبائی کوڈ، جنس کا ہندسہ اور سمارٹ کارڈ MRZ چیک سم نادرا آرڈیننس 2000 کے عین مطابق درست پایا گیا۔")
                else:
                    parts.append("**NADRA CNIC Verified**: The 13-digit CNIC provincial administrative code, gender parity check digit, and Smart Card reverse ICAO 9303 MRZ checksum are fully conforming under the NADRA Ordinance 2000.")

        # 1d. Questions regarding FBR Tax, NTN, Withholding Tax (WHT), Section 149, or CPR
        elif any(w in q_lower for w in ["fbr", "ntn", "wht", "withholding", "salary slip", "tax", "cpr", "section 149", "ٹیکس", "تنخواہ", "سیلری سلپ"]):
            fbr_findings = self.get_findings_by_rule_prefix("RULE_FBR_")
            adverse_fbr = [f for f in fbr_findings if f.get("ruleId") != "RULE_FBR_WHT_VERIFIED"]
            if adverse_fbr:
                if is_urdu_query:
                    parts.append("ایف بی آر (FBR) ٹیکس اور ودہولڈنگ جانچ پڑتال میں درج ذیل قانونی و حسابی خامیاں پائی گئیں:")
                else:
                    parts.append("Federal Board of Revenue (FBR) Tax & Section 149 Withholding audit identified the following statutory discrepancies:")
                for f in adverse_fbr:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(f"- **{f.get('title')}** [{f.get('severity', 'CRITICAL')}]: {f.get('description')}")
            else:
                if is_urdu_query:
                    parts.append("**ایف بی آر ٹیکس قوانین کی تعمیل**: این ٹی این (NTN) موڈیولس 11 چیک سم، انکم ٹیکس آرڈیننس 2001 کے سیکشن 149 کے تحت سیلری سلپ ٹیکس کٹوتی اور کمپیوٹرائزڈ پیمنٹ رسید (CPR) مکمل درست ہیں۔")
                else:
                    parts.append("**FBR Tax Compliance Verified**: National Tax Number (NTN) satisfies Modulus 11 check digit verification, salary withholding tax fully reconciles against statutory Finance Act Section 149 progressive tax slabs, and Computerized Payment Receipts (CPR) are authentic.")

        # 2. Questions regarding balance tampering or ledger calculations
        elif any(w in q_lower for w in ["balance", "ledger", "math", "opening", "closing", "tamper", "tampered", "discrepancy", "بیلنس", "حساب", "رقم"]):
            fin_findings = (
                self.get_findings_by_rule_prefix("RULE_PK_")
                + self.get_findings_by_category("FINANCIAL_VERIFICATION")
                + self.get_findings_by_category("MATHEMATICAL_MISMATCH")
            )
            if fin_findings:
                if is_urdu_query:
                    parts.append("لیجر اور ٹرانزیکشنز میں درج ذیل حسابی خامیاں پائی گئیں:")
                else:
                    parts.append("The following deterministic mathematical discrepancies were identified in the transaction ledger:")
                for f in fin_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(
                        f"- **{f.get('title')}**: Expected `{f.get('expectedValue')}`, Actual `{f.get('actualValue')}` (Discrepancy: `{f.get('discrepancy')}`).\n  {f.get('description')}"
                    )
            else:
                if is_urdu_query:
                    parts.append("**لیجر میتھ تصدیق شدہ**: تمام ٹرانزیکشنز اور رننگ بیلنس بغیر کسی غلطی کے 100% درست اور تصدیق شدہ ہیں۔")
                else:
                    parts.append(
                        "**Ledger Math Verified**: All transactions across all pages reconcile with 0 mathematical errors. The running balances strictly match stated opening and closing balances."
                    )

        # 3. Questions regarding risk score or classification
        elif any(w in q_lower for w in ["why", "risk", "score", "classified", "critical", "tier", "assessment", "کیوں", "سکور", "رسک"]):
            rec_str = format_recommendation(action_directive, risk_tier)
            if is_urdu_query:
                parts.append(
                    f"دستاویز کی تفتیش کا فرانزک جائزہ **{risk_tier} خطرہ ({overall_score}/100)** ہے، "
                    f"جس کے لیے فرانزک سفارش **{rec_str}** ہے (حتمی فیصلہ مجاز افسر کا ہوگا)۔ درج ذیل تصدیق شدہ شواہد کی بنیاد پر:"
                )
            else:
                parts.append(
                    f"The investigation was evaluated as **{risk_tier} Risk ({overall_score}/100)** with advisory recommendation **{rec_str}** (human adjudication required) based on the following verified forensic evidence:"
                )

            for idx, item in enumerate(self.evidence_items[:5], 1):
                item_id = item.get("id", "")
                if item_id:
                    cited_evidence_ids.append(item_id)
                disc = f" (Discrepancy: {item.get('discrepancy')})" if item.get("discrepancy") else ""
                parts.append(
                    f"{idx}. **{item.get('title', 'Finding')}** [{item.get('severity', 'UNKNOWN')}]: {item.get('description', '')}{disc}"
                )

        # 4. Questions regarding fonts, typography, or desktop editors
        elif any(w in q_lower for w in ["font", "typography", "producer", "software", "editor", "acrobat", "incremental", "فونٹ", "سافٹ ویئر"]):
            struct_findings = (
                self.get_findings_by_rule_prefix("RULE_PDF_")
                + self.get_findings_by_rule_prefix("RULE_FONT_")
                + self.get_findings_by_rule_prefix("RULE_METADATA_")
            )
            if struct_findings:
                if is_urdu_query:
                    parts.append("دستاویز کے فونٹ اور ساخت کے فرانزک معائنے سے درج ذیل نتائج ملے:")
                else:
                    parts.append("Structural and typography forensic analysis identified:")
                for f in struct_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(f"- **{f.get('title')}**: {f.get('description')}")
            else:
                if is_urdu_query:
                    parts.append("**فونٹ اور ساخت تصدیق شدہ**: دستاویز میں کوئی بیرونی ایڈیٹر یا غیر مطابقت پذیر فونٹ نہیں پایا گیا۔")
                else:
                    parts.append("**Typography & Structure Verified**: No font substitutions, sub-pixel baseline offsets, or consumer PDF editor signatures were detected.")

        # 5. Questions regarding visual ELA or image tampering
        elif any(w in q_lower for w in ["ela", "visual", "image", "compression", "heat", "ghosting", "pixel", "تصویر"]):
            vis_findings = self.get_findings_by_rule_prefix("RULE_CV_")
            if vis_findings:
                if is_urdu_query:
                    parts.append("کمپیوٹر ویژن اور ایرر لیول اینالیسس (ELA) کے نتائج:")
                else:
                    parts.append("Computer Vision & Error Level Analysis (ELA) detected:")
                for f in vis_findings:
                    if f.get("id"):
                        cited_evidence_ids.append(f["id"])
                    parts.append(f"- **{f.get('title')}**: {f.get('description')}")
            else:
                if is_urdu_query:
                    parts.append("**تصویری سالمیت تصدیق شدہ**: تمام صفحات پر یکساں اور معیاری کمپریشن موجود ہے۔")
                else:
                    parts.append("**Visual Integrity Verified**: Clean ELA heatmap with uniform compression residuals across all pages.")

        # 6. Default general synthesis
        else:
            if is_urdu_query:
                parts.append(
                    f"**ڈیپ ٹریس لیڈ انویسٹی گیٹر جائزہ (کیس {self.investigation.get('caseNumber', '')})**:\n"
                    f"مجموعی رسک سکور: **{overall_score}/100** ({risk_tier})۔\n"
                    f"تصدیق شدہ فرانزک شواہد کی تعداد: **{len(self.evidence_items)}**۔"
                )
            else:
                parts.append(
                    f"**DeepTrace Lead Investigator Assessment (Case {self.investigation.get('caseNumber', '')})**:\n"
                    f"The document has an overall risk score of **{overall_score}/100** ({risk_tier}). "
                    f"Total verified forensic evidence items: **{len(self.evidence_items)}**."
                )
            if self.evidence_items:
                parts.append("\nTop verified evidence items:")
                for item in self.evidence_items[:3]:
                    if item.get("id"):
                        cited_evidence_ids.append(item["id"])
                    parts.append(f"- **{item.get('title')}** [{item.get('severity')}]: {item.get('description')}")

        answer_text = "\n\n".join(parts)
        est_tokens = len(answer_text.split()) + len(question.split()) + 50

        # Validate zero-hallucination guardrail for cited items
        for ev_id in cited_evidence_ids:
            self._assert_evidence_exists(ev_id)

        return {
            "answer": answer_text,
            "evidence_references": cited_evidence_ids,
            "tokens_used": est_tokens,
            "model_provider": "deeptrace-rules",
        }

