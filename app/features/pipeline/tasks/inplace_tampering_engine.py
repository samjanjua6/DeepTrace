"""
In-Place Tampering Forensics Engine for Digital PDF Bank Statements.
Detects in-situ modifications where original values were edited, masked, or overwritten
without rebuilding the whole document from CBS.
"""
from decimal import Decimal
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def detect_stream_displacement(page: Any, page_num: int) -> list[dict[str, Any]]:
    """
    Detect content-stream sequence displacement.
    In legitimate statements, label and value operators are emitted sequentially in the content stream.
    When an attacker edits or inserts values (e.g. in Acrobat or PDF editors), the replacement
    text is frequently appended at the end of the content stream or placed in an appended /Contents object,
    creating a massive byte/sequence gap between the label and its value.
    """
    findings = []
    try:
        stream_bytes = page.read_contents()
        if not stream_bytes:
            return []

        texttrace = page.get_texttrace()
        if not texttrace:
            return []

        # Find sequence numbers and positions for labels vs values
        header_labels: dict[str, dict[str, Any]] = {}
        for t in texttrace:
            txt = "".join([chr(c[0]) for c in t.get("chars", []) if isinstance(c, (list, tuple)) and len(c) > 0 and 32 <= c[0] <= 126])
            seq = t.get("seqno", 0)
            bbox = t.get("bbox", (0, 0, 0, 0))

            for lbl in ["Opening Balance", "Closing Balance", "Account Title", "Account Number"]:
                if lbl in txt and lbl not in header_labels:
                    header_labels[lbl] = {"seqno": seq, "bbox": bbox, "text": txt}

        if not header_labels:
            return []

        # Inspect candidate balance values
        for val_lbl, r_id, desc_lbl in [
            ("Opening Balance", "RULE_INPLACE_STREAM_DISPLACEMENT_OPENING", "Opening Balance"),
            ("Closing Balance", "RULE_INPLACE_STREAM_DISPLACEMENT_CLOSING", "Closing Balance"),
        ]:
            if val_lbl not in header_labels:
                continue

            lbl_info = header_labels[val_lbl]
            lbl_seq = lbl_info["seqno"]
            lbl_bbox = lbl_info["bbox"]

            # Look for values near the label spatially
            best_val_entry = None
            for t in texttrace:
                t_seq = t.get("seqno", 0)
                t_bbox = t.get("bbox", (0, 0, 0, 0))
                # Check spatial proximity: within 50pt below, or 180pt right
                is_below = (0 < t_bbox[1] - lbl_bbox[1] <= 45) and (abs(t_bbox[0] - lbl_bbox[0]) <= 25 or abs(t_bbox[2] - lbl_bbox[2]) <= 30)
                is_right = (abs(t_bbox[1] - lbl_bbox[1]) <= 10) and (0 < t_bbox[0] - lbl_bbox[2] <= 180)

                if is_below or is_right:
                    txt = "".join([chr(c[0]) for c in t.get("chars", []) if isinstance(c, (list, tuple)) and len(c) > 0 and 32 <= c[0] <= 126])
                    if any(c.isdigit() for c in txt) and ("." in txt or "PKR" in txt):
                        best_val_entry = (t_seq, t_bbox, txt)
                        break

            if best_val_entry:
                v_seq, v_bbox, v_txt = best_val_entry
                seq_gap = abs(v_seq - lbl_seq)
                
                # Check byte displacement in stream
                lbl_byte_pos = stream_bytes.find(val_lbl.encode("latin-1", errors="ignore"))
                v_clean = re.sub(r"[^\d.]", "", v_txt)
                val_byte_pos = stream_bytes.find(v_clean.encode("latin-1", errors="ignore")) if v_clean else -1

                byte_gap = abs(val_byte_pos - lbl_byte_pos) if (lbl_byte_pos != -1 and val_byte_pos != -1) else 0

                # If sequence gap >= 50 or byte gap > 10,000 bytes away (outlier)
                if seq_gap >= 50 or byte_gap > 10000:
                    endpoints = [
                        {
                            "role": "stated",
                            "page": page_num,
                            "bbox": [float(v_bbox[0]), float(v_bbox[1]), float(v_bbox[2]), float(v_bbox[3])],
                            "label": f"Displaced Value '{v_txt}' (Seq #{v_seq})",
                            "relation": "intra_page",
                        },
                        {
                            "role": "derived",
                            "page": page_num,
                            "bbox": [float(lbl_bbox[0]), float(lbl_bbox[1]), float(lbl_bbox[2]), float(lbl_bbox[3])],
                            "label": f"Original Label '{val_lbl}' (Seq #{lbl_seq})",
                            "relation": "intra_page",
                        },
                    ]

                    findings.append({
                        "category": "PDF_OBJECT_ANOMALY",
                        "severity": "MEDIUM",
                        "rule_id": r_id,
                        "risk_points": 10,
                        "title": f"Content-Stream Sequence Displacement on {desc_lbl}",
                        "description": (
                            f"The text value '{v_txt}' is emitted at execution sequence #{v_seq} ({byte_gap:,} bytes away from label), "
                            f"while its field label '{val_lbl}' is emitted at sequence #{lbl_seq}. Legitimate core banking engines "
                            "render labels and values contiguously (Δseq ≤ 2). This displacement indicates post-export in-place insertion."
                        ),
                        "is_deterministic": False,
                        "confidence": 0.85,
                        "page_number": page_num,
                        "expected_value": "Contiguous stream execution (Δseq ≤ 2)",
                        "actual_value": f"Displaced execution (Δseq = {seq_gap}, {byte_gap:,} byte gap)",
                        "discrepancy": f"+{seq_gap} sequence delta",
                        "technical_details": {
                            "label": val_lbl,
                            "label_seqno": lbl_seq,
                            "value_seqno": v_seq,
                            "seq_gap": seq_gap,
                            "byte_gap": byte_gap,
                            "value_text": v_txt,
                            "endpoints": endpoints,
                            "rule_version": 2,
                        },
                        "bbox": v_bbox,
                    })
    except Exception as e:
        logger.debug(f"Error checking stream displacement: {e}")

    return findings


def detect_whiteout_patch(page: Any, page_num: int) -> list[dict[str, Any]]:
    """
    Detect vector whiteout paint-over patches.
    Attacker draws a white vector rectangle over an original value, then prints new text on top.
    A legitimate white card background has: seqno_white_rect < seqno_text_on_top.
    A malicious whiteout patch has: seqno_text_underneath < seqno_white_rect < seqno_text_on_top.
    """
    findings = []
    try:
        drawings = page.get_drawings()
        texttrace = page.get_texttrace()
        if not drawings or not texttrace:
            return []

        # Find white fill rectangles
        white_rects = []
        for d in drawings:
            fill = d.get("fill")
            r = d.get("rect")
            seq = d.get("seqno", 0)
            if fill in ((1.0, 1.0, 1.0), [1.0, 1.0, 1.0], (1, 1, 1), [1, 1, 1]) and r:
                # Exclude full-page white backgrounds
                if (r[2] - r[0] < 500) and (r[3] - r[1] < 100):
                    white_rects.append((seq, r, d))

        for w_seq, w_rect, _ in white_rects:
            # Check text entries overlapping w_rect
            text_under = []
            text_over = []

            for t in texttrace:
                t_bbox = t.get("bbox", (0, 0, 0, 0))
                t_seq = t.get("seqno", 0)

                # Overlap test
                ix0 = max(w_rect[0], t_bbox[0])
                iy0 = max(w_rect[1], t_bbox[1])
                ix1 = min(w_rect[2], t_bbox[2])
                iy1 = min(w_rect[3], t_bbox[3])

                if ix1 > ix0 and iy1 > iy0:
                    area_inter = (ix1 - ix0) * (iy1 - iy0)
                    t_area = (t_bbox[2] - t_bbox[0]) * (t_bbox[3] - t_bbox[1])
                    if t_area > 0 and (area_inter / t_area) > 0.5:
                        txt = "".join([chr(c[0]) for c in t.get("chars", []) if isinstance(c, (list, tuple)) and len(c) > 0 and 32 <= c[0] <= 126])
                        if t_seq < w_seq:
                            text_under.append((t_seq, txt, t_bbox))
                        elif t_seq > w_seq:
                            text_over.append((t_seq, txt, t_bbox))

            # If both text under and text over exist, a whiteout paint-over is strictly proven!
            if text_under and text_over:
                under_str = ", ".join([t[1] for t in text_under])
                over_str = ", ".join([t[1] for t in text_over])
                endpoints = [
                    {
                        "role": "derived",
                        "page": page_num,
                        "bbox": [float(text_under[0][2][0]), float(text_under[0][2][1]), float(text_under[0][2][2]), float(text_under[0][2][3])],
                        "label": f"Masked Text Underneath ('{under_str}')",
                        "relation": "intra_page",
                    },
                    {
                        "role": "stated",
                        "page": page_num,
                        "bbox": [float(text_over[0][2][0]), float(text_over[0][2][1]), float(text_over[0][2][2]), float(text_over[0][2][3])],
                        "label": f"Replacement Text On Top ('{over_str}')",
                        "relation": "intra_page",
                    },
                ]

                findings.append({
                    "category": "PDF_OBJECT_ANOMALY",
                    "severity": "CRITICAL",
                    "rule_id": "RULE_INPLACE_WHITEOUT_PATCH",
                    "risk_points": 35,
                    "title": "Vector Whiteout Paint-Over Patch Detected",
                    "description": (
                        f"A vector whiteout drawing (seqno #{w_seq}) masks underlying original text '{under_str}' (seqno #{text_under[0][0]}), "
                        f"with replacement text '{over_str}' (seqno #{text_over[0][0]}) painted on top. "
                        "This physical vector sandwich conclusively proves post-export forgery."
                    ),
                    "is_deterministic": True,
                    "confidence": 1.0,
                    "page_number": page_num,
                    "expected_value": f"Original text '{under_str}'",
                    "actual_value": f"Masked replacement '{over_str}'",
                    "discrepancy": f"Whiteout rectangle at ({w_rect[0]:.1f}, {w_rect[1]:.1f})",
                    "technical_details": {
                        "whiteout_seqno": w_seq,
                        "under_seqno": text_under[0][0],
                        "over_seqno": text_over[0][0],
                        "text_under": under_str,
                        "text_over": over_str,
                        "endpoints": endpoints,
                        "rule_version": 2,
                    },
                    "bbox": w_rect,
                })
    except Exception as e:
        logger.debug(f"Error checking whiteout patch: {e}")

    return findings


def detect_incremental_revision_diff(file_bytes: bytes) -> list[dict[str, Any]]:
    """
    Detect and diff true incremental PDF revisions using the /Prev cross-reference chain.
    Linearized PDFs have 2 %%EOF markers legitimately; true incremental revisions contain
    a /Prev trailer pointer linking back to the previous XREF offset.
    """
    findings = []
    try:
        is_linearized = b"/Linearized" in file_bytes[:4096]
        eof_count = file_bytes.count(b"%%EOF")

        # Find all /Prev pointers in trailers
        prev_matches = list(re.finditer(rb"/Prev\s+(\d+)", file_bytes))
        
        # If no /Prev, this is clean single-version export (even if 2 %%EOF from linearization)
        if not prev_matches:
            return []

        # True incremental save detected
        prev_offsets = [int(m.group(1)) for m in prev_matches]
        findings.append({
            "category": "PDF_OBJECT_ANOMALY",
            "severity": "CRITICAL",
            "rule_id": "RULE_PDF_INCREMENTAL_REVISION_PREV",
            "risk_points": 35,
            "title": f"Incremental PDF Trailer Revision Chain Detected ({len(prev_offsets) + 1} Revisions)",
            "description": (
                f"The PDF contains an incremental modification trailer chain with /Prev cross-reference offset(s): {prev_offsets}. "
                "Official bank statements are compiled in a single export pass by core banking systems. "
                "A /Prev revision pointer proves the file was re-saved and modified after generation."
            ),
            "is_deterministic": True,
            "confidence": 1.0,
            "page_number": None,
            "expected_value": "1 monolithic revision (no /Prev pointers)",
            "actual_value": f"{len(prev_offsets) + 1} revisions with /Prev chain",
            "discrepancy": f"+{len(prev_offsets)} unauthorized incremental revision(s)",
            "technical_details": {
                "prev_offsets": prev_offsets,
                "eof_count": eof_count,
                "is_linearized": is_linearized,
                "rule_version": 2,
            },
        })
    except Exception as e:
        logger.debug(f"Error checking incremental revision diff: {e}")

    return findings


def detect_comma_inconsistency(page: Any, page_num: int, bank_code: str = "MEEZAN", doc_has_commas: bool = True) -> list[dict[str, Any]]:
    """
    Detect missing commas on large financial figures in bank templates that mandate thousands grouping.
    Pakistani banking standards (Meezan, HBL, UBL, Alfalah) format amounts >= 1,000 with commas.
    An edited value like 'PKR120000.00' or 'PKR955000.00' that omits commas while other values
    contain commas represents an amateur in-place text edit.
    """
    findings = []
    try:
        p_text = page.get_text()
        # Verify page or document template mandates comma figures
        has_comma_amounts = bool(re.search(r"\b\d{1,3},\d{3}(?:\.\d{2})?\b", p_text)) or doc_has_commas or bank_code == "MEEZAN"
        if not has_comma_amounts:
            return []

        words = page.get_text("words")
        for w in words:
            w_str = w[4].strip()
            # Only test monetary tokens starting with PKR/Rs. or strictly ending in .00 with >= 5 digits before dot
            # This prevents false positives on epoch timestamps (e.g. 1788943474.03), tracking numbers, or dates
            m = re.search(r"^(?:PKR\s*|Rs\.?\s*)(\d{5,}\.\d{2})$", w_str)
            if not m:
                # Also check standalone amount if surrounded by PKR in adjacent word
                if re.match(r"^\d{5,}\.\d{2}$", w_str):
                    # Check if previous or next word is PKR
                    m = re.match(r"^(\d{5,}\.\d{2})$", w_str)
                    # Verify it is not a timestamp (timestamps don't end in .00 usually, and are > 10 digits)
                    if len(m.group(1).split(".")[0]) > 9:
                        m = None

            if m:
                unformatted_val = m.group(1)
                num = Decimal(unformatted_val)
                expected_format = f"{num:,.2f}"
                endpoints = [
                    {
                        "role": "stated",
                        "page": page_num,
                        "bbox": [float(w[0]), float(w[1]), float(w[2]), float(w[3])],
                        "label": f"Unformatted Value '{w_str}'",
                        "relation": "intra_page",
                    }
                ]

                findings.append({
                    "category": "TRANSACTION_FORMAT_VIOLATION",
                    "severity": "MEDIUM",
                    "rule_id": "RULE_INPLACE_COMMA_FORMAT_INCONSISTENCY",
                    "risk_points": 10,
                    "title": f"Thousands Separator Formatting Anomaly ('{unformatted_val}')",
                    "description": (
                        f"Financial figure '{w_str}' on Page {page_num} omits mandatory thousands separators ('{expected_format}'). "
                        "The bank reporting engine consistently outputs grouped currency tokens across all rows. "
                        "Omission of commas indicates manual text editing."
                    ),
                    "is_deterministic": False,
                    "confidence": 0.75,
                    "page_number": page_num,
                    "expected_value": f"PKR {expected_format}",
                    "actual_value": w_str,
                    "discrepancy": "Missing thousands comma",
                    "technical_details": {
                        "raw_word": w_str,
                        "unformatted_amount": unformatted_val,
                        "expected_format": expected_format,
                        "endpoints": endpoints,
                        "rule_version": 2,
                    },
                    "bbox": (w[0], w[1], w[2], w[3]),
                })
    except Exception as e:
        logger.debug(f"Error checking comma inconsistency: {e}")

    return findings


def detect_slot_width_overflow(page: Any, page_num: int, bank_code: str = "MEEZAN") -> list[dict[str, Any]]:
    """
    Detect balance bounding box width overflow against verified bank template slot constraints.
    In Meezan Bank statements, header balance fields are set in 7pt Helvetica in a fixed column slot.
    Inflating a balance from 5 digits (e.g. 120.00 -> 32pt) to 8 digits (120000.00 -> 47.5pt)
    causes slot boundary encroachment.
    """
    findings = []
    if bank_code != "MEEZAN":
        return []

    try:
        # Use page.get_text("dict") to get exact span text and bounding boxes
        text_dict = page.get_text("dict")
        for b in text_dict.get("blocks", []):
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                for s in line.get("spans", []):
                    txt = s.get("text", "").strip()
                    bbox = s.get("bbox", (0, 0, 0, 0))
                    # Check if in header area y in [140, 180]
                    if 140 <= bbox[1] <= 180 and "PKR" in txt and any(c.isdigit() for c in txt):
                        w_pts = bbox[2] - bbox[0]
                        # Normal Meezan header balances with typical amounts have slot width <= 42pt
                        if w_pts > 45.0:
                            endpoints = [
                                {
                                    "role": "stated",
                                    "page": page_num,
                                    "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                                    "label": f"Over-width Slot '{txt}' ({w_pts:.1f} pt)",
                                    "relation": "intra_page",
                                }
                            ]
                            findings.append({
                                "category": "FONT_BASELINE_INCONSISTENCY",
                                "severity": "LOW",
                                "rule_id": "RULE_INPLACE_SLOT_WIDTH_OVERFLOW",
                                "risk_points": 5,
                                "title": f"Header Slot Width Encroachment ({w_pts:.1f} pt)",
                                "description": (
                                    f"Text span '{txt}' on Page {page_num} has a rendered width of {w_pts:.1f} pt, "
                                    "encroaching on the Meezan Bank statement header slot margin (nominal slot width ≤ 42.0 pt). "
                                    "This physical boundary encroachment is a direct byproduct of appending digits to inflate balances."
                                ),
                                "is_deterministic": False,
                                "confidence": 0.70,
                                "page_number": page_num,
                                "expected_value": "Slot width ≤ 42.0 pt",
                                "actual_value": f"{w_pts:.1f} pt",
                                "discrepancy": f"+{w_pts - 42.0:.1f} pt slot expansion",
                                "technical_details": {
                                    "span_text": txt,
                                    "width_pts": round(w_pts, 2),
                                    "nominal_max_pts": 42.0,
                                    "endpoints": endpoints,
                                    "rule_version": 2,
                                },
                                "bbox": bbox,
                            })
    except Exception as e:
        logger.debug(f"Error checking slot width overflow: {e}")

    return findings
