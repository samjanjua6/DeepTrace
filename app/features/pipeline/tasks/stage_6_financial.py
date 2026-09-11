"""
Stage 6: Deterministic Pakistani Financial Ledger & SBP IBAN Verification — Celery Task & Async Processor
NIST SP 800-86 Compliant Mathematical Proof, Lakh/Crore Reconciliation, and ISO 7064 MOD-97 Validation.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
import time
from typing import Any

import pymupdf
from prisma import Json

from app.config import get_settings
from app.core.celery_app import celery_app
from app.core.storage import storage
from app.db.client import db, set_org_context

settings = get_settings()

# State Bank of Pakistan (SBP) Authorized Bank Clearing Codes
SBP_BANK_CODES = {
    "MEZN": "Meezan Bank Limited",
    "HABB": "Habib Bank Limited (HBL)",
    "UNIL": "United Bank Limited (UBL)",
    "MUCB": "MCB Bank Limited",
    "MCIB": "MCB Islamic Bank",
    "ABPA": "Allied Bank Limited (ABL)",
    "ALFH": "Bank Alfalah Limited",
    "SCBL": "Standard Chartered Bank (Pakistan)",
    "FAYS": "Faysal Bank Limited",
    "BAHL": "Bank AL Habib Limited",
    "BIPL": "BankIslami Pakistan Limited",
    "JSBL": "JS Bank Limited",
    "SONA": "Samba Bank Limited",
    "SIND": "Sindh Bank Limited",
    "BOPK": "The Bank of Punjab (BOP)",
    "BOKP": "The Bank of Khyber",
    "DIBK": "Dubai Islamic Bank Pakistan",
    "ASKA": "Askari Bank Limited",
    "FWBL": "First Women Bank Limited",
    "ZTBL": "Zarai Taraqiati Bank Limited",
}

# Regex to detect Pakistani IBAN (24 alphanumeric characters starting with PK)
PK_IBAN_REGEX = re.compile(r"\b(PK\s*\d{2}\s*[A-Z]{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4})\b", re.IGNORECASE)

# Regex to match transaction date formats (e.g. 12/04/2024, 12-04-2024, 12-Apr-2024, 12/Apr/24, 11 Jun 2026)
DATE_REGEX = re.compile(
    r"\b(\d{1,2}[\/\-\.\s](?:\d{1,2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\/\-\.\s]\d{2,4})\b",
    re.IGNORECASE,
)

# Regex to extract amount strings (handles both Western 1,234,567.89 and South Asian 12,34,567.89)
AMOUNT_REGEX = re.compile(
    r"(?:PKR|Rs\.?|₨)?\s*\(?([\d]{1,3}(?:[,\s]\d{2,3})*(?:\.\d{1,2})?)\)?",
    re.IGNORECASE,
)


def parse_pakistani_amount(raw_str: str) -> Decimal | None:
    """
    Parse monetary amounts formatted in Western or South Asian (Lakh/Crore) notation.
    Handles currency prefixes without requiring word boundary (e.g. 'PKR120.00', 'PKR0.00'),
    signed indicators (+, -, ()), commas, and spaces.
    Examples:
        '1,50,000.00'   -> Decimal('150000.00')  (1.5 Lakh)
        '10,00,000.00'  -> Decimal('1000000.00') (10 Lakh / 1 Million)
        '1,00,00,000.00'-> Decimal('10000000.00')(1 Crore)
        '(25,000.50)'   -> Decimal('-25000.50')  (Negative)
        '+ PKR3,000.00' -> Decimal('3000.00')
        '- PKR120.00'   -> Decimal('-120.00')
    """
    if not raw_str or not isinstance(raw_str, str):
        return None

    cleaned = raw_str.strip()
    is_negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1].strip()
    elif cleaned.startswith("-") or cleaned.endswith("-"):
        is_negative = True
        cleaned = cleaned.replace("-", "").strip()
    elif cleaned.startswith("+"):
        cleaned = cleaned.lstrip("+").strip()

    # Remove currency text (with or without space/boundary)
    cleaned = re.sub(r"(?i)(?:PKR|Rs\.?|₨|USD|EUR)\s*", "", cleaned).strip()
    # Remove commas and spaces
    cleaned = cleaned.replace(",", "").replace(" ", "")

    try:
        val = Decimal(cleaned)
        return -val if is_negative else val
    except (InvalidOperation, ValueError):
        return None


def merge_line_words(words: list[Any]) -> list[Any]:
    """
    Merge standalone sign tokens ('-' or '+') with adjacent monetary words if separated by <= 15 pt.
    E.g. ('-', ...) at x=390.2 and ('PKR120.00', ...) at x=395.1 -> ('-PKR120.00', ...)
    """
    merged = []
    i = 0
    while i < len(words):
        w = words[i]
        if w[4] in ("-", "+") and i + 1 < len(words):
            next_w = words[i + 1]
            if next_w[0] - w[2] <= 15.0:
                combined_word = w[4] + next_w[4]
                combined_bbox = (w[0], min(w[1], next_w[1]), next_w[2], max(w[3], next_w[3]))
                merged.append((combined_bbox[0], combined_bbox[1], combined_bbox[2], combined_bbox[3], combined_word))
                i += 2
                continue
        merged.append(w)
        i += 1
    return merged



SUMMARY_PATTERNS = {
    "opening_balance": re.compile(
        r"\b(?:Opening\s+Balance|Start(?:ing)?\s+Balance|Op\.?\s*Bal\.?)\b",
        re.IGNORECASE,
    ),
    "closing_balance": re.compile(
        r"\b(?:Closing\s+Balance|Ending\s+Balance|Cl\.?\s*Bal\.?)\b",
        re.IGNORECASE,
    ),
    "total_credits": re.compile(
        r"\b(?:Total\s+Credits?(?:\s+Amount)?|Credits?\s+Total|Total\s+Deposits?(?:\s+Amount)?|Deposits?\s+Total)\b",
        re.IGNORECASE,
    ),
    "total_debits": re.compile(
        r"\b(?:Total\s+Debits?(?:\s+Amount)?|Debits?\s+Total|Total\s+Withdrawals?(?:\s+Amount)?|Withdrawals?\s+Total)\b",
        re.IGNORECASE,
    ),
}

BROUGHT_FORWARD_REGEX = re.compile(
    r"\b(?:Balance\s+Brought\s+Forward|Brought\s+Forward|Balance\s+B\/F|Total\s+B\/F|B\/F)\b",
    re.IGNORECASE,
)

CARRIED_FORWARD_REGEX = re.compile(
    r"\b(?:Balance\s+Carried\s+Forward|Carried\s+Forward|Balance\s+C\/F|Total\s+C\/F|C\/F)\b",
    re.IGNORECASE,
)

OPENING_ROW_REGEX = re.compile(
    r"\b(?:Opening\s+Balance|Start(?:ing)?\s+Balance|Op\.?\s*Bal\.?)\b",
    re.IGNORECASE,
)


def extract_financial_summary(text: str) -> dict[str, Decimal | None]:
    """
    Extract stated Opening Balance, Closing Balance, Total Credits, and Total Debits
    from Pakistani bank statement summary headers and key-value sections.
    """
    result: dict[str, Decimal | None] = {
        "opening_balance": None,
        "closing_balance": None,
        "total_credits": None,
        "total_debits": None,
    }
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Pass 1: Direct key-value matching on line
    for key, rx in SUMMARY_PATTERNS.items():
        for i, line in enumerate(lines):
            m = rx.search(line)
            if not m:
                continue
            remainder = line[m.end():]
            cleaned = re.sub(r"\b\d{1,2}[\/\-\.](?:\d{1,2}|[A-Za-z]{3,})[\/\-\.]\d{2,4}\b", " ", remainder)
            cleaned = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " ", cleaned)
            cleaned = re.sub(r"\(PKR\)", " ", cleaned, flags=re.IGNORECASE)
            amt_matches = re.findall(
                r"(?:PKR|Rs\.?|₨)?\s*\(?([0-9]{1,3}(?:[,\s][0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\)?",
                cleaned,
                re.IGNORECASE,
            )
            valid_amts = []
            for a in amt_matches:
                ca = a.replace(",", "").replace(" ", "")
                try:
                    valid_amts.append(Decimal(ca))
                except Exception:
                    pass
            if valid_amts:
                result[key] = valid_amts[0]
                break

            # Lookahead: next line if current line only had label
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_cleaned = re.sub(r"\b\d{1,2}[\/\-\.](?:\d{1,2}|[A-Za-z]{3,})[\/\-\.]\d{2,4}\b", " ", next_line)
                next_amts = re.findall(
                    r"(?:PKR|Rs\.?|₨)?\s*\(?([0-9]{1,3}(?:[,\s][0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\)?",
                    next_cleaned,
                    re.IGNORECASE,
                )
                valid_next = []
                for a in next_amts:
                    ca = a.replace(",", "").replace(" ", "")
                    try:
                        valid_next.append(Decimal(ca))
                    except Exception:
                        pass
                if len(valid_next) == 1:
                    result[key] = valid_next[0]
                    break

    # Pass 2: Tabular multi-column summary
    if not all(result.values()):
        for i, line in enumerate(lines):
            matches_in_line = []
            for key, rx in SUMMARY_PATTERNS.items():
                m = rx.search(line)
                if m:
                    matches_in_line.append((m.start(), key))
            if len(matches_in_line) >= 2 and i + 1 < len(lines):
                matches_in_line.sort(key=lambda x: x[0])
                next_line = lines[i + 1]
                next_cleaned = re.sub(r"\b\d{1,2}[\/\-\.](?:\d{1,2}|[A-Za-z]{3,})[\/\-\.]\d{2,4}\b", " ", next_line)
                next_amts = re.findall(
                    r"(?:PKR|Rs\.?|₨)?\s*\(?([0-9]{1,3}(?:[,\s][0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)\)?",
                    next_cleaned,
                    re.IGNORECASE,
                )
                parsed_amts = []
                for a in next_amts:
                    ca = a.replace(",", "").replace(" ", "")
                    try:
                        parsed_amts.append(Decimal(ca))
                    except Exception:
                        pass
                if len(parsed_amts) == len(matches_in_line):
                    for idx, (_, k) in enumerate(matches_in_line):
                        if result[k] is None:
                            result[k] = parsed_amts[idx]

    return result


def cluster_words_into_lines(words: list[Any]) -> list[tuple[float, list[Any]]]:
    """
    Cluster word bounding boxes into distinct lines using adaptive vertical overlap.
    Solves font size scaling, multi-line narrations, and slight document skew.
    Returns list of (line_y, sorted_words).
    """
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w[1], w[0]))
    lines: list[list[Any]] = []
    for w in sorted_words:
        w_y0, w_y1 = w[1], w[3]
        w_h = max(1.0, w_y1 - w_y0)

        best_line_idx = None
        best_overlap_ratio = 0.0

        for idx, line in enumerate(lines):
            line_y0 = min(lw[1] for lw in line)
            line_y1 = max(lw[3] for lw in line)
            line_h = max(1.0, line_y1 - line_y0)

            inter_y0 = max(w_y0, line_y0)
            inter_y1 = min(w_y1, line_y1)
            if inter_y1 > inter_y0:
                overlap = inter_y1 - inter_y0
                min_h = min(w_h, line_h)
                ratio = overlap / min_h
                if ratio >= 0.40 and ratio > best_overlap_ratio:
                    best_overlap_ratio = ratio
                    best_line_idx = idx

        if best_line_idx is not None:
            lines[best_line_idx].append(w)
        else:
            lines.append([w])

    result: list[tuple[float, list[Any]]] = []
    for line in lines:
        line.sort(key=lambda w: w[0])
        med_y = float(sum(w[1] for w in line) / len(line))
        result.append((med_y, line))

    result.sort(key=lambda item: item[0])
    return result


def read_structured_table_from_page(page_meta: Any) -> list[dict] | None:
    """
    Reads structured table cells from page_meta.extractedTables (persisted by Stage 5 OCR).
    Returns a list of structured table rows, or None if no structured table exists.
    Each row contains:
      - 'row_idx': int
      - 'date': str
      - 'date_bbox': tuple | None
      - 'narration': str
      - 'cheque': str | None
      - 'debit': Decimal | None
      - 'credit': Decimal | None
      - 'balance': Decimal | None
      - 'balance_bbox': tuple | None
      - 'words': list of word tuples [x0, y0, x1, y1, text, 0, 0, 0] for line processing
    """
    if not page_meta:
        return None
    extracted = getattr(page_meta, "extractedTables", None)
    if not extracted:
        return None
    if isinstance(extracted, str):
        import json
        try:
            extracted = json.loads(extracted)
        except Exception:
            return None

    tables = extracted.get("tables", []) if isinstance(extracted, dict) else []
    if not tables:
        return None

    for tbl in tables:
        cells = tbl.get("cells", [])
        if not cells:
            continue

        # Group cells by row index
        rows_by_idx: dict[int, dict[int, dict]] = {}
        for c in cells:
            r = c.get("row", 0)
            col = c.get("col", 0)
            rows_by_idx.setdefault(r, {})[col] = c

        if not rows_by_idx:
            continue

        # Detect header row
        header_col_map: dict[str, int] = {}
        header_row_idx = None
        for r_idx in sorted(rows_by_idx.keys()):
            row_cells = rows_by_idx[r_idx]
            row_text = " ".join(c.get("text", "").lower() for c in row_cells.values())
            if any(k in row_text for k in ["date", "trans date", "txn date", "booking date", "value date"]) and any(
                k in row_text for k in ["debit", "credit", "withdrawal", "deposit", "dr", "cr", "balance"]
            ):
                header_row_idx = r_idx
                for col_idx, c in row_cells.items():
                    txt = c.get("text", "").lower()
                    if any(k in txt for k in ["trans date", "txn date", "value date", "booking date", "date"]):
                        header_col_map.setdefault("date", col_idx)
                    elif any(k in txt for k in ["description", "narration", "particulars"]):
                        header_col_map.setdefault("narration", col_idx)
                    elif any(k in txt for k in ["cheque", "chq", "ref", "instrument"]):
                        header_col_map.setdefault("cheque", col_idx)
                    elif any(k in txt for k in ["debit", "withdrawal", "dr"]):
                        header_col_map.setdefault("debit", col_idx)
                    elif any(k in txt for k in ["credit", "deposit", "cr"]):
                        header_col_map.setdefault("credit", col_idx)
                    elif "balance" in txt:
                        header_col_map.setdefault("balance", col_idx)
                break

        if header_row_idx is None:
            continue

        parsed_rows: list[dict] = []
        for r_idx in sorted(rows_by_idx.keys()):
            if r_idx <= header_row_idx:
                continue
            row_cells = rows_by_idx[r_idx]

            date_cell = row_cells.get(header_col_map.get("date", -1), {})
            narr_cell = row_cells.get(header_col_map.get("narration", -1), {})
            chq_cell = row_cells.get(header_col_map.get("cheque", -1), {})
            debit_cell = row_cells.get(header_col_map.get("debit", -1), {})
            credit_cell = row_cells.get(header_col_map.get("credit", -1), {})
            bal_cell = row_cells.get(header_col_map.get("balance", -1), {})

            date_str = date_cell.get("text", "").strip()
            bal_val = parse_pakistani_amount(bal_cell.get("text", ""))
            deb_val = parse_pakistani_amount(debit_cell.get("text", ""))
            cred_val = parse_pakistani_amount(credit_cell.get("text", ""))

            words_for_row = []
            for col_idx in sorted(row_cells.keys()):
                cell_dict = row_cells[col_idx]
                txt = cell_dict.get("text", "").strip()
                if txt:
                    bb = cell_dict.get("bbox", [0, 0, 0, 0])
                    words_for_row.append([bb[0], bb[1], bb[2], bb[3], txt, 0, r_idx, col_idx])

            parsed_rows.append({
                "row_idx": r_idx,
                "date": date_str,
                "date_bbox": date_cell.get("bbox"),
                "narration": narr_cell.get("text", "").strip(),
                "cheque": chq_cell.get("text", "").strip() if chq_cell else None,
                "debit": deb_val,
                "credit": cred_val,
                "balance": bal_val,
                "balance_bbox": bal_cell.get("bbox"),
                "words": words_for_row,
            })

        if parsed_rows:
            return parsed_rows

    return None



def extract_spatial_summary(page: Any) -> dict[str, dict[str, Any]]:
    """
    Extract stated financial metrics using 2D physical spatial proximity.
    Solves PDF editor stream displacement where edited values are placed at the end
    of the content stream rather than adjacent to their labels.
    Returns dict mapping metric name -> {"amount": Decimal, "bbox": (x0, y0, x1, y1), "raw_text": str}
    """
    words = page.get_text("words")
    if not words:
        return {}

    results: dict[str, dict[str, Any]] = {}
    for i in range(len(words)):
        for k in range(1, 4):
            if i + k <= len(words):
                combo_words = words[i : i + k]
                combo_text = " ".join([cw[4] for cw in combo_words])
                combo_box = (
                    min(cw[0] for cw in combo_words),
                    min(cw[1] for cw in combo_words),
                    max(cw[2] for cw in combo_words),
                    max(cw[3] for cw in combo_words),
                )

                for metric, pattern in SUMMARY_PATTERNS.items():
                    if metric in results:
                        continue
                    if pattern.search(combo_text):
                        best_candidate = None
                        min_dist = 999999.0

                        for candidate_w in words:
                            if candidate_w in combo_words:
                                continue
                            amt = parse_pakistani_amount(candidate_w[4])
                            if amt is None:
                                continue
                            # Skip isolated year tokens like 2024, 2025, 2026
                            if "." not in candidate_w[4] and amt in (2024, 2025, 2026):
                                continue

                            cx0, cy0, cx1, cy1 = candidate_w[0], candidate_w[1], candidate_w[2], candidate_w[3]
                            # Vertical candidate directly underneath
                            is_below = (0 < cy0 - combo_box[1] <= 35) and (
                                abs(cx0 - combo_box[0]) <= 25
                                or abs(cx1 - combo_box[2]) <= 25
                                or (cx0 >= combo_box[0] - 10 and cx1 <= combo_box[2] + 20)
                            )
                            # Horizontal candidate directly to right
                            is_right = (abs(cy0 - combo_box[1]) <= 8) and (0 < cx0 - combo_box[2] <= 180)

                            if is_below or is_right:
                                dist = ((cx0 - combo_box[0]) ** 2 + (cy0 - combo_box[1]) ** 2) ** 0.5
                                if dist < min_dist:
                                    min_dist = dist
                                    best_candidate = (amt, (cx0, cy0, cx1, cy1), candidate_w[4])

                        if best_candidate:
                            results[metric] = {
                                "amount": best_candidate[0],
                                "bbox": best_candidate[1],
                                "raw_text": best_candidate[2],
                                "label_bbox": combo_box,
                            }
    return results



def validate_pk_iban(iban_str: str) -> tuple[bool, str, str | None]:
    """
    Validate a Pakistani IBAN using the ISO 7064 MOD-97 checksum algorithm.
    Returns: (is_valid, reason, detected_bank_name)
    """
    cleaned = re.sub(r"\s+", "", iban_str).upper()
    if len(cleaned) != 24:
        return False, f"Invalid IBAN length: expected 24 characters, got {len(cleaned)}", None

    if not cleaned.startswith("PK"):
        return False, "Not a Pakistani IBAN: must begin with country code 'PK'", None

    bank_code = cleaned[4:8]
    bank_name = SBP_BANK_CODES.get(bank_code, f"Unknown/Unregistered Bank ({bank_code})")

    # ISO 7064 MOD-97: Move first 4 chars to the end
    rearranged = cleaned[4:] + cleaned[:4]

    # Convert letters to digits (A=10, B=11, ... Z=35)
    numeric_str = ""
    for char in rearranged:
        if char.isdigit():
            numeric_str += char
        elif char.isalpha():
            numeric_str += str(ord(char) - ord("A") + 10)
        else:
            return False, f"Invalid character '{char}' in IBAN", bank_name

    try:
        mod = int(numeric_str) % 97
        if mod == 1:
            return True, "Valid ISO 7064 MOD-97 Checksum", bank_name
        else:
            return False, f"MOD-97 checksum failed (remainder = {mod}, expected 1)", bank_name
    except Exception as exc:
        return False, f"Checksum calculation error: {exc}", bank_name


async def process_financial(
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute Stage 6: Deterministic Financial Verification.
    Reconciles transaction ledger running balances, performs total arithmetic checks,
    and validates SBP clearing codes with ISO 7064 MOD-97.
    """
    start_time = time.perf_counter()

    async with set_org_context(org_id) as tx:
        await tx.pipelinestage.update(
            where={"id": pipeline_stage_id},
            data={"status": "RUNNING", "startedAt": datetime.now(timezone.utc)},
        )

        try:
            where_doc: dict[str, Any] = {"investigationId": investigation_id}
            if document_id:
                where_doc["id"] = document_id

            documents = await tx.document.find_many(
                where=where_doc,
                include={"pages": True},
            )
            if not documents:
                raise ValueError(f"No documents found for investigation '{investigation_id}'")

            stage_findings = []

            for doc in documents:
                if doc.mimeType != "application/pdf":
                    continue

                file_bytes = storage.get_file(settings.s3_bucket_documents, doc.storagePath)
                if not file_bytes:
                    continue

                pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")
                page_meta_map = {p.pageNumber: p for p in (doc.pages or [])}

                # ─────────────────────────────────────────────────────────────
                # 1. Full Document Text Extraction for IBAN & Header Metrics
                # ─────────────────────────────────────────────────────────────
                all_text = ""
                for page in pdf_doc:
                    all_text += page.get_text("text") + "\n"

                # Scanned / raster fallback: read OCR text produced by Stage 5
                if len(all_text.strip()) < 30:
                    all_text = "\n".join([(pm.ocrText or "") for pm in page_meta_map.values() if pm])

                # Check IBANs
                primary_iban_info: dict[str, Any] | None = None
                iban_matches = PK_IBAN_REGEX.findall(all_text)
                for raw_iban in set(iban_matches):
                    is_valid, reason, bank_name = validate_pk_iban(raw_iban)
                    if not primary_iban_info:
                        primary_iban_info = {
                            "raw_iban": raw_iban,
                            "formatted_iban": " ".join([raw_iban[i:i+4] for i in range(0, len(raw_iban), 4)]),
                            "bank_name": bank_name or "Unknown Financial Institution",
                            "bank_code": raw_iban[4:8] if len(raw_iban) >= 8 else "",
                            "account_number": raw_iban[8:] if len(raw_iban) >= 8 else "",
                            "check_digits": raw_iban[2:4] if len(raw_iban) >= 4 else "",
                            "country": raw_iban[:2] if len(raw_iban) >= 2 else "PK",
                            "is_valid": is_valid,
                            "validation_reason": reason,
                        }
                    if not is_valid:
                        finding = await tx.evidenceitem.create(
                            data={
                                "document": {"connect": {"id": doc.id}},
                                "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                "category": "IBAN_CHECKSUM_FAILURE",
                                "severity": "HIGH",
                                "ruleId": "RULE_PK_IBAN_CHECKSUM_INVALID",
                                "riskPoints": 30,
                                "title": f"Invalid Pakistani IBAN Checksum: {raw_iban}",
                                "description": (
                                    f"The document states Pakistani IBAN '{raw_iban}' ({bank_name or 'Unrecognized'}), "
                                    f"which fails ISO 7064 MOD-97 validation: {reason}. Legitimate bank accounts always "
                                    "satisfy remainder = 1. A failed checksum indicates fabricated account credentials."
                                ),
                                "isDeterministic": True,
                                "pageNumber": 1,
                                "expectedValue": "Valid ISO 7064 Checksum (Remainder = 1)",
                                "actualValue": reason,
                                "discrepancy": "Failed MOD-97 Checksum",
                                "technicalDetails": Json({
                                    "raw_iban": raw_iban,
                                    "bank_name": bank_name,
                                    "validation_reason": reason,
                                }),
                            }
                        )
                        stage_findings.append({
                            "id": finding.id,
                            "rule_id": "RULE_PK_IBAN_CHECKSUM_INVALID",
                            "severity": finding.severity,
                            "title": finding.title,
                        })

                # ─────────────────────────────────────────────────────────────
                # 2. Extract Header / Summary Metrics
                # ─────────────────────────────────────────────────────────────
                financial_summary = extract_financial_summary(all_text)
                summary_bboxes: dict[str, tuple[int, tuple[float, float, float, float]]] = {}

                # Scan first 3 pages with 2D spatial coordinate extractor
                for p_idx in range(min(3, len(pdf_doc))):
                    spatial_res = extract_spatial_summary(pdf_doc[p_idx])
                    for metric, info in spatial_res.items():
                        if metric not in summary_bboxes:
                            summary_bboxes[metric] = (p_idx + 1, info["bbox"])
                        if financial_summary.get(metric) is None:
                            financial_summary[metric] = info["amount"]

                stated_opening = financial_summary.get("opening_balance")
                stated_closing = financial_summary.get("closing_balance")
                stated_credits = financial_summary.get("total_credits")
                stated_debits = financial_summary.get("total_debits")

                # ─────────────────────────────────────────────────────────────
                # 3. Multi-Page Transaction Table Running Balance Verification
                # ─────────────────────────────────────────────────────────────
                # Track running balance continuously across ALL pages (never reset per page)
                previous_balance: Decimal | None = stated_opening
                last_page_closing_balance: Decimal | None = None
                first_transaction_processed: bool = False
                opening_row_found: bool = False
                implied_opening: Decimal | None = None
                all_ledger_rows: list[dict[str, Any]] = []

                # Column geometry discovered dynamically from table headers across pages
                doc_column_geometry: dict[str, Any] = {
                    "financial_x_min": 250.0,
                    "cheque_col_bounds": None,
                    "debit_col_bounds": None,
                    "credit_col_bounds": None,
                    "balance_col_bounds": None,
                    "date_col_max_x": 160.0,
                }

                for page_idx in range(len(pdf_doc)):
                    page_num = page_idx + 1
                    page = pdf_doc[page_idx]
                    page_meta = page_meta_map.get(page_num)
                    page_first_row_processed = False

                    scale_x = (page_meta.widthPx / page_meta.widthPts) if (page_meta and page_meta.widthPts) else (150.0 / 72.0)
                    scale_y = (page_meta.heightPx / page_meta.heightPts) if (page_meta and page_meta.heightPts) else (150.0 / 72.0)

                    # Extract words with coordinates: (x0, y0, x1, y1, word, block_no, line_no, word_no)
                    words = page.get_text("words")
                    if not words and page_meta and page_meta.ocrDataJson:
                        raw_words = page_meta.ocrDataJson.get("words", [])
                        words = [tuple(w[:8]) for w in raw_words]

                    if not words:
                        continue

                    # Check for structured table from Stage 5 OCR first (e.g. PP-Structure / Textract)
                    structured_rows = read_structured_table_from_page(page_meta)
                    if structured_rows:
                        sorted_lines = [(float(r["words"][0][1]), r["words"]) for r in structured_rows if r.get("words")]
                    else:
                        # Cluster words into lines using adaptive vertical bounding overlap (>= 0.40)
                        # Replaces the static 3.0pt filter and handles variable font sizes & paper skew
                        sorted_lines = cluster_words_into_lines(words)

                    # Determine financial column horizontal boundaries dynamically from table header
                    table_header_y = None
                    for line_y, l_words in sorted_lines:
                        line_txt = " ".join([w[4] for w in l_words]).lower()
                        if any(k in line_txt for k in ["booking date", "trans date", "txn date", "value date", "post date", "date"]) and any(
                            k in line_txt for k in ["description", "particulars", "narration", "balance", "credit", "debit", "withdrawal", "deposit"]
                        ):
                            table_header_y = line_y
                            for w in l_words:
                                w_low = w[4].lower()
                                if any(h in w_low for h in ["credit", "deposit"]):
                                    doc_column_geometry["credit_col_bounds"] = (w[0] - 15, w[2] + 25)
                                    doc_column_geometry["financial_x_min"] = min(doc_column_geometry["financial_x_min"], w[0] - 15)
                                elif any(h in w_low for h in ["debit", "withdrawal"]):
                                    doc_column_geometry["debit_col_bounds"] = (w[0] - 15, w[2] + 25)
                                    doc_column_geometry["financial_x_min"] = min(doc_column_geometry["financial_x_min"], w[0] - 15)
                                elif any(h in w_low for h in ["balance"]):
                                    doc_column_geometry["balance_col_bounds"] = (w[0] - 20, w[2] + 120)
                                elif any(h in w_low for h in ["cheque", "chq", "instrument", "ref"]):
                                    doc_column_geometry["cheque_col_bounds"] = (w[0] - 15, w[2] + 25)
                                elif any(h in w_low for h in ["description", "particulars", "narration"]):
                                    doc_column_geometry["date_col_max_x"] = max(doc_column_geometry["date_col_max_x"], w[0] - 10)
                            break

                    for line_y, line_words in sorted_lines:
                        # Skip lines at or above table header on this page
                        if table_header_y is not None and line_y <= table_header_y:
                            continue

                        # Sort words left-to-right
                        line_words.sort(key=lambda w: w[0])
                        line_text = " ".join([w[4] for w in line_words])

                        # Skip header metadata lines
                        if re.search(
                            r"\b(?:From\s+Date|To\s+Date|Statement\s+Period|Date\s+Range|Generated\s+On|Account\s+Number|Account\s+Title|IBAN)\b",
                            line_text,
                            re.IGNORECASE,
                        ):
                            continue

                        # Merge adjacent standalone sign tokens ('-' or '+') with monetary values
                        merged_line_words = merge_line_words(line_words)

                        # Extract monetary amounts in this line (exclude date, description & cheque columns)
                        amounts: list[tuple[Decimal, tuple[float, float, float, float], str]] = []
                        for w in merged_line_words:
                            if w[0] < doc_column_geometry["financial_x_min"]:
                                continue
                            # Exclude Cheque No column bounds if explicitly identified
                            if doc_column_geometry["cheque_col_bounds"]:
                                chq_x0, chq_x1 = doc_column_geometry["cheque_col_bounds"]
                                if chq_x0 <= w[0] <= chq_x1:
                                    continue

                            # Skip isolated date tokens (day <= 31 or year 1990-2035 without decimal)
                            w_str = w[4].strip()
                            if "." not in w_str and w_str.isdigit():
                                int_val = int(w_str)
                                if int_val <= 31 or (1990 <= int_val <= 2035):
                                    continue
                            amt = parse_pakistani_amount(w_str)
                            if amt is not None:
                                amounts.append((amt, (w[0], w[1], w[2], w[3]), w_str))

                        # Skip header summary lines in table row processing
                        if re.search(
                            r"\b(?:Total\s+Credits?|Total\s+Debits?|Total\s+Deposits?|Total\s+Withdrawals?|Closing\s+Balance)\b",
                            line_text,
                            re.IGNORECASE,
                        ):
                            continue


                        # ── Check A: Dedicated Opening Balance Row on Page 1 ──
                        if (
                            not first_transaction_processed
                            and page_num == 1
                            and OPENING_ROW_REGEX.search(line_text)
                            and DATE_REGEX.search(line_text)
                            and amounts
                        ):
                            table_opening = amounts[-1][0]
                            opening_row_found = True
                            if stated_opening is not None and abs(table_opening - stated_opening) > Decimal("0.01"):
                                discrepancy = table_opening - stated_opening
                                line_bbox_x0 = min([w[0] for w in line_words])
                                line_bbox_y0 = min([w[1] for w in line_words])
                                line_bbox_x1 = max([w[2] for w in line_words])
                                line_bbox_y1 = max([w[3] for w in line_words])

                                finding = await tx.evidenceitem.create(
                                    data={
                                        "document": {"connect": {"id": doc.id}},
                                        "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                        "category": "MATHEMATICAL_MISMATCH",
                                        "severity": "CRITICAL",
                                        "ruleId": "RULE_PK_OPENING_BALANCE_MISMATCH",
                                        "riskPoints": 50,
                                        "title": "Opening Balance Mismatch Between Header and Ledger",
                                        "description": (
                                            f"The document header states an Opening Balance of PKR {stated_opening:,.2f}, "
                                            f"but the ledger table specifies PKR {table_opening:,.2f}. "
                                            f"Discrepancy: PKR {discrepancy:+,.2f}. This indicates an edited opening figure."
                                        ),
                                        "isDeterministic": True,
                                        "pageNumber": page_num,
                                        "expectedValue": f"PKR {stated_opening:,.2f}",
                                        "actualValue": f"PKR {table_opening:,.2f}",
                                        "discrepancy": f"PKR {discrepancy:+,.2f}",
                                        "technicalDetails": Json({
                                            "stated_opening": str(stated_opening),
                                            "table_opening": str(table_opening),
                                            "discrepancy": str(discrepancy),
                                            "line_text": line_text,
                                        }),
                                    }
                                )
                                if "opening_balance" in summary_bboxes:
                                    s_page, s_box = summary_bboxes["opening_balance"]
                                    s_meta = page_meta_map.get(s_page)
                                    s_sx = (s_meta.widthPx / s_meta.widthPts) if (s_meta and s_meta.widthPts) else (150.0 / 72.0)
                                    s_sy = (s_meta.heightPx / s_meta.heightPts) if (s_meta and s_meta.heightPts) else (150.0 / 72.0)
                                    await tx.boundingbox.create(
                                        data={
                                            "evidenceItem": {"connect": {"id": finding.id}},
                                            "pageNumber": s_page,
                                            "x": float(s_box[0] * s_sx),
                                            "y": float(s_box[1] * s_sy),
                                            "width": float((s_box[2] - s_box[0]) * s_sx),
                                            "height": float((s_box[3] - s_box[1]) * s_sy),
                                            "xPts": float(s_box[0]),
                                            "yPts": float(s_box[1]),
                                            "widthPts": float(s_box[2] - s_box[0]),
                                            "heightPts": float(s_box[3] - s_box[1]),
                                            "label": "Stated Opening (Tampered)",
                                            "color": "#dc2626",
                                        }
                                    )

                                w_pts = line_bbox_x1 - line_bbox_x0
                                h_pts = line_bbox_y1 - line_bbox_y0
                                await tx.boundingbox.create(
                                    data={
                                        "evidenceItem": {"connect": {"id": finding.id}},
                                        "pageNumber": page_num,
                                        "x": float(line_bbox_x0 * scale_x),
                                        "y": float(line_bbox_y0 * scale_y),
                                        "width": float(w_pts * scale_x),
                                        "height": float(h_pts * scale_y),
                                        "xPts": float(line_bbox_x0),
                                        "yPts": float(line_bbox_y0),
                                        "widthPts": float(w_pts),
                                        "heightPts": float(h_pts),
                                        "label": "Ledger Opening Row",
                                        "color": "#f59e0b",
                                    }
                                )
                                stage_findings.append({
                                    "id": finding.id,
                                    "rule_id": "RULE_PK_OPENING_BALANCE_MISMATCH",
                                    "severity": finding.severity,
                                    "page": page_num,
                                    "title": finding.title,
                                })


                            previous_balance = table_opening
                            first_transaction_processed = True
                            implied_opening = table_opening
                            all_ledger_rows.append({
                                "date": line_text[:11].strip() if line_text else "—",
                                "particulars": "Opening Balance",
                                "debit": None,
                                "credit": None,
                                "expectedBalance": float(table_opening),
                                "recordedBalance": float(table_opening),
                                "discrepancy": float(table_opening - (stated_opening or table_opening)),
                                "isTampered": (stated_opening is not None and abs(table_opening - stated_opening) > Decimal("0.01")),
                                "pageNumber": page_num,
                            })
                            continue

                        # ── Check B: Balance Brought Forward Row (Top of page 2+) ──
                        if page_num > 1 and BROUGHT_FORWARD_REGEX.search(line_text) and amounts:
                            bf_val = amounts[-1][0]
                            if last_page_closing_balance is not None and abs(bf_val - last_page_closing_balance) > Decimal("0.01"):
                                discrepancy = bf_val - last_page_closing_balance
                                line_bbox_x0 = min([w[0] for w in line_words])
                                line_bbox_y0 = min([w[1] for w in line_words])
                                line_bbox_x1 = max([w[2] for w in line_words])
                                line_bbox_y1 = max([w[3] for w in line_words])

                                finding = await tx.evidenceitem.create(
                                    data={
                                        "document": {"connect": {"id": doc.id}},
                                        "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                        "category": "MATHEMATICAL_MISMATCH",
                                        "severity": "CRITICAL",
                                        "ruleId": "RULE_PK_PAGE_BALANCE_DISCONTINUITY",
                                        "riskPoints": 50,
                                        "title": f"Multi-Page Balance Discontinuity on Page {page_num}",
                                        "description": (
                                            f"Page {page_num - 1} concluded with a balance of PKR {last_page_closing_balance:,.2f}, "
                                            f"but Page {page_num} states Brought Forward balance of PKR {bf_val:,.2f}. "
                                            f"Discrepancy across page boundary: PKR {discrepancy:+,.2f}. This indicates inter-page balance manipulation."
                                        ),
                                        "isDeterministic": True,
                                        "pageNumber": page_num,
                                        "expectedValue": f"PKR {last_page_closing_balance:,.2f}",
                                        "actualValue": f"PKR {bf_val:,.2f}",
                                        "discrepancy": f"PKR {discrepancy:+,.2f}",
                                        "technicalDetails": Json({
                                            "previous_page_closing": str(last_page_closing_balance),
                                            "brought_forward_balance": str(bf_val),
                                            "discrepancy": str(discrepancy),
                                            "page_number": page_num,
                                        }),
                                    }
                                )
                                w_pts = line_bbox_x1 - line_bbox_x0
                                h_pts = line_bbox_y1 - line_bbox_y0
                                await tx.boundingbox.create(
                                    data={
                                        "evidenceItem": {"connect": {"id": finding.id}},
                                        "pageNumber": page_num,
                                        "x": float(line_bbox_x0 * scale_x),
                                        "y": float(line_bbox_y0 * scale_y),
                                        "width": float(w_pts * scale_x),
                                        "height": float(h_pts * scale_y),
                                        "xPts": float(line_bbox_x0),
                                        "yPts": float(line_bbox_y0),
                                        "widthPts": float(w_pts),
                                        "heightPts": float(h_pts),
                                        "label": "Page Discontinuity",
                                        "color": "#dc2626",
                                    }
                                )
                                stage_findings.append({
                                    "id": finding.id,
                                    "rule_id": "RULE_PK_PAGE_BALANCE_DISCONTINUITY",
                                    "severity": finding.severity,
                                    "page": page_num,
                                    "title": finding.title,
                                })

                            previous_balance = bf_val
                            continue

                        # ── Check C: Balance Carried Forward Row (Bottom of page) ──
                        if CARRIED_FORWARD_REGEX.search(line_text) and amounts:
                            cf_val = amounts[-1][0]
                            if previous_balance is not None and abs(cf_val - previous_balance) > Decimal("0.01"):
                                discrepancy = cf_val - previous_balance
                                line_bbox_x0 = min([w[0] for w in line_words])
                                line_bbox_y0 = min([w[1] for w in line_words])
                                line_bbox_x1 = max([w[2] for w in line_words])
                                line_bbox_y1 = max([w[3] for w in line_words])

                                finding = await tx.evidenceitem.create(
                                    data={
                                        "document": {"connect": {"id": doc.id}},
                                        "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                        "category": "MATHEMATICAL_MISMATCH",
                                        "severity": "CRITICAL",
                                        "ruleId": "RULE_PK_PAGE_BALANCE_DISCONTINUITY",
                                        "riskPoints": 50,
                                        "title": f"Page Carried Forward Balance Mismatch on Page {page_num}",
                                        "description": (
                                            f"Page {page_num} transactions left a calculated running balance of PKR {previous_balance:,.2f}, "
                                            f"but the Carried Forward total specifies PKR {cf_val:,.2f}. "
                                            f"Discrepancy: PKR {discrepancy:+,.2f}."
                                        ),
                                        "isDeterministic": True,
                                        "pageNumber": page_num,
                                        "expectedValue": f"PKR {previous_balance:,.2f}",
                                        "actualValue": f"PKR {cf_val:,.2f}",
                                        "discrepancy": f"PKR {discrepancy:+,.2f}",
                                        "technicalDetails": Json({
                                            "running_balance": str(previous_balance),
                                            "carried_forward": str(cf_val),
                                            "discrepancy": str(discrepancy),
                                            "page_number": page_num,
                                        }),
                                    }
                                )
                                w_pts = line_bbox_x1 - line_bbox_x0
                                h_pts = line_bbox_y1 - line_bbox_y0
                                await tx.boundingbox.create(
                                    data={
                                        "evidenceItem": {"connect": {"id": finding.id}},
                                        "pageNumber": page_num,
                                        "x": float(line_bbox_x0 * scale_x),
                                        "y": float(line_bbox_y0 * scale_y),
                                        "width": float(w_pts * scale_x),
                                        "height": float(h_pts * scale_y),
                                        "xPts": float(line_bbox_x0),
                                        "yPts": float(line_bbox_y0),
                                        "widthPts": float(w_pts),
                                        "heightPts": float(h_pts),
                                        "label": "Carryover Mismatch",
                                        "color": "#dc2626",
                                    }
                                )
                                stage_findings.append({
                                    "id": finding.id,
                                    "rule_id": "RULE_PK_PAGE_BALANCE_DISCONTINUITY",
                                    "severity": finding.severity,
                                    "page": page_num,
                                    "title": finding.title,
                                })

                            previous_balance = cf_val
                            continue

                        # ── Check D: Transaction Rows ──
                        date_match = DATE_REGEX.search(line_text)
                        if not date_match:
                            continue

                        # Check that the date token is in the left Date column region
                        # (excludes secondary dates mentioned inside description/narration)
                        date_str = date_match.group(1)
                        is_primary_date = False
                        for w in line_words:
                            if (date_str in w[4] or w[4] in date_str) and w[0] <= (doc_column_geometry["date_col_max_x"] + 20):
                                is_primary_date = True
                                break

                        if not is_primary_date:
                            continue

                        # ── Check E: Calendar Sanity (Bank Holiday / Future Date) ──────
                        # Runs for every confirmed transaction date row, independent of amounts.
                        try:
                            from app.features.pipeline.tasks.pk_calendar import (
                                parse_transaction_date,
                                is_bank_holiday,
                                is_future_date,
                                is_gazetted_holiday,
                            )
                            tx_date = parse_transaction_date(date_str)
                            if tx_date is not None:
                                _is_future = is_future_date(tx_date)
                                _is_holiday = is_bank_holiday(tx_date)
                                _is_gazetted = is_gazetted_holiday(tx_date)

                                # Automated 24/7 channels (Raast, ATM, IBFT, POS, Cards, Online Banking)
                                # operate legitimately on standard Saturday/Sunday weekends.
                                # Only flag weekend transactions if they represent non-digital OTC/branch transactions
                                # OR if it is an official gazetted national public holiday.
                                is_digital_channel = any(
                                    kw in line_text.lower()
                                    for kw in [
                                        "raast", "atm", "ibft", "online", "pos", "card",
                                        "1link", "p2p", "digital", "ft", "interbank",
                                        "paypak", "visa", "mastercard", "fee", "tax", "wht", "fed"
                                    ]
                                )
                                _should_flag_holiday = _is_gazetted or (_is_holiday and not is_digital_channel)

                                if _is_future or _should_flag_holiday:
                                    cal_rule = (
                                        "RULE_PK_FUTURE_DATE_TRANSACTION" if _is_future
                                        else "RULE_PK_HOLIDAY_TRANSACTION"
                                    )
                                    cal_severity = "HIGH" if _is_future else ("HIGH" if _is_gazetted else "MEDIUM")
                                    cal_risk = 30 if _is_future else (25 if _is_gazetted else 15)
                                    cal_title = (
                                        f"Impossible Future Date Transaction on Page {page_num} ({date_str})"
                                        if _is_future
                                        else (
                                            f"Transaction on Gazetted National Holiday on Page {page_num} ({date_str})"
                                            if _is_gazetted
                                            else f"Branch Transaction on Weekend on Page {page_num} ({date_str})"
                                        )
                                    )
                                    cal_desc = (
                                        f"Transaction row on Page {page_num} carries date '{date_str}' "
                                        f"({tx_date.strftime('%d %b %Y')}), which is in the future. "
                                        "No legitimate bank can post a transaction to a future date. "
                                        "This proves the transaction date was fabricated."
                                        if _is_future
                                        else (
                                            f"Transaction row on Page {page_num} carries date '{date_str}' "
                                            f"({tx_date.strftime('%d %b %Y')}), which is a gazetted national public holiday. "
                                            "Bank branches and clearing settlements are closed on this date."
                                            if _is_gazetted
                                            else (
                                                f"Transaction row on Page {page_num} carries date '{date_str}' "
                                                f"({tx_date.strftime('%d %b %Y')}), which falls on a weekend non-working day. "
                                                "Retail branch transactions on this date are abnormal and warrant verification."
                                            )
                                        )
                                    )

                                    # Find the date word's bounding box for precise highlighting
                                    date_word_bbox = None
                                    for w in line_words:
                                        if date_str in w[4] or w[4] in date_str:
                                            date_word_bbox = w
                                            break

                                    cal_finding = await tx.evidenceitem.create(
                                        data={
                                            "document": {"connect": {"id": doc.id}},
                                            "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                            "category": "DATE_SEQUENCE_VIOLATION",
                                            "severity": cal_severity,
                                            "ruleId": cal_rule,
                                            "riskPoints": cal_risk,
                                            "title": cal_title,
                                            "description": cal_desc,
                                            "isDeterministic": True,
                                            "pageNumber": page_num,
                                            "expectedValue": "Valid working-day transaction date (Mon–Fri, non-holiday)",
                                            "actualValue": f"{date_str} ({tx_date.strftime('%A, %d %b %Y')})",
                                            "discrepancy": "Future date" if _is_future else "Bank holiday / weekend",
                                            "technicalDetails": Json({
                                                "parsed_date": tx_date.isoformat(),
                                                "weekday": tx_date.strftime("%A"),
                                                "is_future": _is_future,
                                                "is_holiday": _is_holiday,
                                                "line_text": line_text[:120],
                                            }),
                                        }
                                    )

                                    if date_word_bbox is not None:
                                        dw_x0, dw_y0, dw_x1, dw_y1 = date_word_bbox[0], date_word_bbox[1], date_word_bbox[2], date_word_bbox[3]
                                        await tx.boundingbox.create(
                                            data={
                                                "evidenceItem": {"connect": {"id": cal_finding.id}},
                                                "pageNumber": page_num,
                                                "x": float(dw_x0 * scale_x),
                                                "y": float(dw_y0 * scale_y),
                                                "width": float((dw_x1 - dw_x0) * scale_x),
                                                "height": float((dw_y1 - dw_y0) * scale_y),
                                                "xPts": float(dw_x0),
                                                "yPts": float(dw_y0),
                                                "widthPts": float(dw_x1 - dw_x0),
                                                "heightPts": float(dw_y1 - dw_y0),
                                                "label": "Invalid Date" if _is_future else "Holiday Date",
                                                "color": "#dc2626" if _is_future else "#f59e0b",
                                            }
                                        )

                                    stage_findings.append({
                                        "id": cal_finding.id,
                                        "rule_id": cal_rule,
                                        "severity": cal_finding.severity,
                                        "page": page_num,
                                        "title": cal_finding.title,
                                    })
                        except Exception as _cal_err:
                            import logging as _lcal
                            _lcal.getLogger(__name__).debug("Calendar check non-fatal error: %s", _cal_err)

                        # A valid transaction row has at least an amount and a balance
                        if len(amounts) >= 2:

                            balance_candidate = amounts[-1][0]
                            balance_bbox = amounts[-1][1]

                            # Implicit Opening Balance Verification on Row 1 (if no dedicated opening row was present)
                            if not first_transaction_processed:
                                first_transaction_processed = True
                                page_first_row_processed = True

                                tx_candidates = amounts[:-1]
                                # If first candidate is an un-decimalized integer (cheque no), strip it:
                                if len(tx_candidates) >= 2 and "." not in tx_candidates[0][2]:
                                    tx_candidates = tx_candidates[1:]

                                if len(tx_candidates) == 1:
                                    tx_raw = tx_candidates[0][0]
                                    if tx_raw < 0:
                                        implied_opening = balance_candidate + abs(tx_raw)
                                        debit_1 = abs(tx_raw)
                                        credit_1 = None
                                    else:
                                        implied_opening = balance_candidate - abs(tx_raw)
                                        debit_1 = None
                                        credit_1 = abs(tx_raw)
                                else:
                                    debit_1 = abs(tx_candidates[-2][0])
                                    credit_1 = abs(tx_candidates[-1][0])
                                    implied_opening = balance_candidate - credit_1 + debit_1

                                if stated_opening is not None and abs(stated_opening - implied_opening) > Decimal("0.01"):
                                    discrepancy = stated_opening - implied_opening
                                    line_bbox_x0 = min([w[0] for w in line_words])
                                    line_bbox_y0 = min([w[1] for w in line_words])
                                    line_bbox_x1 = max([w[2] for w in line_words])
                                    line_bbox_y1 = max([w[3] for w in line_words])

                                    finding = await tx.evidenceitem.create(
                                        data={
                                            "document": {"connect": {"id": doc.id}},
                                            "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                            "category": "MATHEMATICAL_MISMATCH",
                                            "severity": "CRITICAL",
                                            "ruleId": "RULE_PK_OPENING_BALANCE_MISMATCH",
                                            "riskPoints": 50,
                                            "title": f"Opening Balance Tampering Detected (+{discrepancy:,.2f} PKR Discrepancy)",
                                            "description": (
                                                f"The statement header claims an Opening Balance of PKR {stated_opening:,.2f}, "
                                                f"but the transaction ledger calculations prove an authentic opening balance of "
                                                f"PKR {implied_opening:,.2f} (implied by Row 1 transaction math). "
                                                f"Discrepancy: PKR {discrepancy:+,.2f}. This proves the opening balance was artificially inflated."
                                            ),
                                            "isDeterministic": True,
                                            "pageNumber": 1,
                                            "expectedValue": f"PKR {implied_opening:,.2f}",
                                            "actualValue": f"PKR {stated_opening:,.2f}",
                                            "discrepancy": f"PKR {discrepancy:+,.2f}",
                                            "technicalDetails": Json({
                                                "stated_opening": str(stated_opening),
                                                "implied_opening": str(implied_opening),
                                                "discrepancy": str(discrepancy),
                                                "first_row_text": line_text,
                                            }),
                                        }
                                    )
                                    # Highlight stated opening in header
                                    if "opening_balance" in summary_bboxes:
                                        s_page, s_box = summary_bboxes["opening_balance"]
                                        s_meta = page_meta_map.get(s_page)
                                        s_sx = (s_meta.widthPx / s_meta.widthPts) if (s_meta and s_meta.widthPts) else (150.0 / 72.0)
                                        s_sy = (s_meta.heightPx / s_meta.heightPts) if (s_meta and s_meta.heightPts) else (150.0 / 72.0)
                                        await tx.boundingbox.create(
                                            data={
                                                "evidenceItem": {"connect": {"id": finding.id}},
                                                "pageNumber": s_page,
                                                "x": float(s_box[0] * s_sx),
                                                "y": float(s_box[1] * s_sy),
                                                "width": float((s_box[2] - s_box[0]) * s_sx),
                                                "height": float((s_box[3] - s_box[1]) * s_sy),
                                                "xPts": float(s_box[0]),
                                                "yPts": float(s_box[1]),
                                                "widthPts": float(s_box[2] - s_box[0]),
                                                "heightPts": float(s_box[3] - s_box[1]),
                                                "label": "Stated Opening (Tampered)",
                                                "color": "#dc2626",
                                            }
                                        )
                                    # Highlight refuting Row 1
                                    w_pts = line_bbox_x1 - line_bbox_x0
                                    h_pts = line_bbox_y1 - line_bbox_y0
                                    await tx.boundingbox.create(
                                        data={
                                            "evidenceItem": {"connect": {"id": finding.id}},
                                            "pageNumber": page_num,
                                            "x": float(line_bbox_x0 * scale_x),
                                            "y": float(line_bbox_y0 * scale_y),
                                            "width": float(w_pts * scale_x),
                                            "height": float(h_pts * scale_y),
                                            "xPts": float(line_bbox_x0),
                                            "yPts": float(line_bbox_y0),
                                            "widthPts": float(w_pts),
                                            "heightPts": float(h_pts),
                                            "label": "Ledger Origin Row",
                                            "color": "#f59e0b",
                                        }
                                    )
                                    stage_findings.append({
                                        "id": finding.id,
                                        "rule_id": "RULE_PK_OPENING_BALANCE_MISMATCH",
                                        "severity": finding.severity,
                                        "page": page_num,
                                        "title": finding.title,
                                    })

                                all_ledger_rows.append({
                                    "date": line_text[:11].strip() if line_text else "—",
                                    "particulars": line_text[11:65].strip() if len(line_text) > 11 else line_text,
                                    "debit": float(debit_1) if debit_1 else None,
                                    "credit": float(credit_1) if credit_1 else None,
                                    "expectedBalance": float(balance_candidate),
                                    "recordedBalance": float(balance_candidate),
                                    "discrepancy": 0.0,
                                    "isTampered": False,
                                    "pageNumber": page_num,
                                })
                                previous_balance = balance_candidate
                                continue

                            is_page_boundary = (page_num > 1 and not page_first_row_processed and last_page_closing_balance is not None)
                            page_first_row_processed = True

                            if previous_balance is not None:
                                reconciled = False
                                expected_balance = None
                                discrepancy = Decimal("0.00")
                                rule_id = "RULE_PK_PAGE_BALANCE_DISCONTINUITY" if is_page_boundary else "RULE_PK_LEDGER_RECONCILIATION_FAIL"
                                title = (
                                    f"Multi-Page Balance Discontinuity on Page {page_num}"
                                    if is_page_boundary
                                    else "Ledger Running Balance Mathematical Inconsistency"
                                )
                                boundary_note = (
                                    f" Across page boundary from Page {page_num - 1} (ended at PKR {last_page_closing_balance:,.2f}), "
                                    if is_page_boundary
                                    else ""
                                )

                                if len(amounts) == 2:
                                    tx_amount = amounts[0][0]
                                    abs_tx = abs(tx_amount)
                                    exp_credit = previous_balance + abs_tx
                                    exp_debit = previous_balance - abs_tx

                                    if abs(balance_candidate - exp_credit) <= Decimal("0.01"):
                                        reconciled = True
                                        previous_balance = balance_candidate
                                    elif abs(balance_candidate - exp_debit) <= Decimal("0.01"):
                                        reconciled = True
                                        previous_balance = balance_candidate
                                    else:
                                        expected_balance = exp_credit if balance_candidate > previous_balance else exp_debit
                                        discrepancy = balance_candidate - previous_balance
                                        desc_msg = (
                                            f"Transaction row on Page {page_num} ('{line_text[:80]}...') contains an impossible "
                                            f"running balance.{boundary_note} Previous balance was PKR {previous_balance:,.2f}. Transaction amount "
                                            f"is PKR {tx_amount:,.2f}. Expected resulting balance: PKR {exp_credit:,.2f} (credit) "
                                            f"or PKR {exp_debit:,.2f} (debit), but statement reports PKR {balance_candidate:,.2f}. "
                                            f"Unaccounted discrepancy: PKR {discrepancy:+,.2f}."
                                        )

                                elif len(amounts) >= 3:
                                    # Candidate amounts
                                    n1 = amounts[-3][0]
                                    n1_str = amounts[-3][2]
                                    n2 = amounts[-2][0]

                                    # Hyp A: Standard 3-col [Debit, Credit, Balance]
                                    exp_3col = previous_balance + n2 - n1
                                    # Hyp B: n1 is Cheque/Ref, n2 is Credit
                                    exp_chq_credit = previous_balance + abs(n2)
                                    # Hyp C: n1 is Cheque/Ref, n2 is Debit
                                    exp_chq_debit = previous_balance - abs(n2)

                                    if abs(balance_candidate - exp_3col) <= Decimal("0.01"):
                                        reconciled = True
                                        previous_balance = balance_candidate
                                    elif ("." not in n1_str) and abs(balance_candidate - exp_chq_credit) <= Decimal("0.01"):
                                        reconciled = True
                                        previous_balance = balance_candidate
                                    elif ("." not in n1_str) and abs(balance_candidate - exp_chq_debit) <= Decimal("0.01"):
                                        reconciled = True
                                        previous_balance = balance_candidate
                                    else:
                                        # Neither standard 3-col nor cheque-col matched -> genuine mismatch
                                        if ("." not in n1_str) and n1 > 1000:
                                            expected_balance = exp_chq_credit if balance_candidate > previous_balance else exp_chq_debit
                                            discrepancy = balance_candidate - expected_balance
                                            desc_msg = (
                                                f"Transaction row on Page {page_num} ('{line_text[:80]}...') fails arithmetic reconciliation:{boundary_note} "
                                                f"Previous (PKR {previous_balance:,.2f}) ± Tx (PKR {n2:,.2f}) [Cheque No: {n1_str}] "
                                                f"= Expected PKR {expected_balance:,.2f}, but statement reports PKR {balance_candidate:,.2f}. "
                                                f"Discrepancy: PKR {discrepancy:+,.2f}."
                                            )
                                        else:
                                            expected_balance = exp_3col
                                            discrepancy = balance_candidate - exp_3col
                                            desc_msg = (
                                                f"Transaction row on Page {page_num} fails arithmetic reconciliation:{boundary_note} "
                                                f"Previous (PKR {previous_balance:,.2f}) + Credit (PKR {n2:,.2f}) "
                                                f"- Debit (PKR {n1:,.2f}) = Expected PKR {exp_3col:,.2f}, "
                                                f"but statement reports PKR {balance_candidate:,.2f}. Discrepancy: PKR {discrepancy:+,.2f}."
                                            )

                                if not reconciled and expected_balance is not None:
                                    line_bbox_x0 = min([w[0] for w in line_words])
                                    line_bbox_y0 = min([w[1] for w in line_words])
                                    line_bbox_x1 = max([w[2] for w in line_words])
                                    line_bbox_y1 = max([w[3] for w in line_words])

                                    finding = await tx.evidenceitem.create(
                                        data={
                                            "document": {"connect": {"id": doc.id}},
                                            "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                            "category": "MATHEMATICAL_MISMATCH",
                                            "severity": "CRITICAL",
                                            "ruleId": rule_id,
                                            "riskPoints": 50,
                                            "title": title,
                                            "description": desc_msg,
                                            "isDeterministic": True,
                                            "pageNumber": page_num,
                                            "expectedValue": f"PKR {expected_balance:,.2f}",
                                            "actualValue": f"PKR {balance_candidate:,.2f}",
                                            "discrepancy": f"PKR {discrepancy:+,.2f}",
                                            "technicalDetails": Json({
                                                "line_text": line_text,
                                                "previous_balance": str(previous_balance),
                                                "reported_balance": str(balance_candidate),
                                                "expected_balance": str(expected_balance),
                                                "discrepancy": str(discrepancy),
                                                "is_page_boundary": is_page_boundary,
                                            }),
                                        }
                                    )

                                    w_pts = line_bbox_x1 - line_bbox_x0
                                    h_pts = line_bbox_y1 - line_bbox_y0
                                    await tx.boundingbox.create(
                                        data={
                                            "evidenceItem": {"connect": {"id": finding.id}},
                                            "pageNumber": page_num,
                                            "x": float(line_bbox_x0 * scale_x),
                                            "y": float(line_bbox_y0 * scale_y),
                                            "width": float(w_pts * scale_x),
                                            "height": float(h_pts * scale_y),
                                            "xPts": float(line_bbox_x0),
                                            "yPts": float(line_bbox_y0),
                                            "widthPts": float(w_pts),
                                            "heightPts": float(h_pts),
                                            "label": "Math Mismatch",
                                            "color": "#dc2626",
                                        }
                                    )

                                    stage_findings.append({
                                        "id": finding.id,
                                        "rule_id": rule_id,
                                        "severity": finding.severity,
                                        "page": page_num,
                                        "title": finding.title,
                                    })

                                row_debit = None
                                row_credit = None
                                if len(amounts) == 2:
                                    tx_amount = amounts[0][0]
                                    abs_tx = abs(tx_amount)
                                    exp_debit = previous_balance - abs_tx
                                    if (tx_amount < 0) or (abs(balance_candidate - exp_debit) <= Decimal("0.01")):
                                        row_debit = abs_tx
                                    else:
                                        row_credit = abs_tx
                                elif len(amounts) >= 3:
                                    row_debit = abs(amounts[-3][0])
                                    row_credit = abs(amounts[-2][0])

                                all_ledger_rows.append({
                                    "date": line_text[:11].strip() if line_text else "—",
                                    "particulars": line_text[11:65].strip() if len(line_text) > 11 else line_text,
                                    "debit": float(row_debit) if row_debit else None,
                                    "credit": float(row_credit) if row_credit else None,
                                    "expectedBalance": float(expected_balance or balance_candidate),
                                    "recordedBalance": float(balance_candidate),
                                    "discrepancy": float(discrepancy),
                                    "isTampered": not reconciled,
                                    "pageNumber": page_num,
                                })
                                previous_balance = balance_candidate

                    # Record page closing balance for carryover into next page
                    last_page_closing_balance = previous_balance

                # ─────────────────────────────────────────────────────────────
                # 4. Document-Level Balance & Summary Identity Reconciliation
                # ─────────────────────────────────────────────────────────────
                # Check 1: Stated Closing Balance vs Final Ledger Balance
                if stated_closing is not None and previous_balance is not None:
                    diff_closing = abs(stated_closing - previous_balance)
                    if diff_closing > Decimal("0.01"):
                        discrepancy = stated_closing - previous_balance
                        last_page_num = len(pdf_doc)

                        title = f"Closing Balance Tampering Detected (+{discrepancy:,.2f} PKR Discrepancy)" if discrepancy > 0 else f"Closing Balance Mismatch ({discrepancy:+,.2f} PKR)"
                        finding = await tx.evidenceitem.create(
                            data={
                                "document": {"connect": {"id": doc.id}},
                                "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                "category": "MATHEMATICAL_MISMATCH",
                                "severity": "CRITICAL",
                                "ruleId": "RULE_PK_CLOSING_BALANCE_MISMATCH",
                                "riskPoints": 50,
                                "title": title,
                                "description": (
                                    f"The document states an ending/closing balance of PKR {stated_closing:,.2f} in the statement summary, "
                                    f"but the transaction ledger concludes on Page {last_page_num} with a final balance of PKR {previous_balance:,.2f}. "
                                    f"Discrepancy: PKR {discrepancy:+,.2f}. This proves closing balance manipulation or fabricated summary totals."
                                ),
                                "isDeterministic": True,
                                "pageNumber": 1,
                                "expectedValue": f"PKR {previous_balance:,.2f}",
                                "actualValue": f"PKR {stated_closing:,.2f}",
                                "discrepancy": f"PKR {discrepancy:+,.2f}",
                                "technicalDetails": Json({
                                    "stated_closing_balance": str(stated_closing),
                                    "final_ledger_balance": str(previous_balance),
                                    "discrepancy": str(discrepancy),
                                    "last_page": last_page_num,
                                }),
                            }
                        )

                        # Bounding box for closing balance: prioritize exact spatial coordinates from summary_bboxes
                        if "closing_balance" in summary_bboxes:
                            s_page, s_box = summary_bboxes["closing_balance"]
                            s_meta = page_meta_map.get(s_page)
                            s_sx = (s_meta.widthPx / s_meta.widthPts) if (s_meta and s_meta.widthPts) else (150.0 / 72.0)
                            s_sy = (s_meta.heightPx / s_meta.heightPts) if (s_meta and s_meta.heightPts) else (150.0 / 72.0)
                            await tx.boundingbox.create(
                                data={
                                    "evidenceItem": {"connect": {"id": finding.id}},
                                    "pageNumber": s_page,
                                    "x": float(s_box[0] * s_sx),
                                    "y": float(s_box[1] * s_sy),
                                    "width": float((s_box[2] - s_box[0]) * s_sx),
                                    "height": float((s_box[3] - s_box[1]) * s_sy),
                                    "xPts": float(s_box[0]),
                                    "yPts": float(s_box[1]),
                                    "widthPts": float(s_box[2] - s_box[0]),
                                    "heightPts": float(s_box[3] - s_box[1]),
                                    "label": "Stated Closing (Tampered)",
                                    "color": "#dc2626",
                                }
                            )
                        else:
                            closing_rects = []
                            target_page_idx = last_page_num - 1
                            for p_i in [target_page_idx, 0]:
                                closing_rects = pdf_doc[p_i].search_for("Closing Balance") or pdf_doc[p_i].search_for(f"{stated_closing:,.2f}")
                                if closing_rects:
                                    target_page_idx = p_i
                                    break

                            if closing_rects:
                                r = closing_rects[0]
                                meta = page_meta_map.get(target_page_idx + 1)
                                sx = (meta.widthPx / meta.widthPts) if (meta and meta.widthPts) else (150.0 / 72.0)
                                sy = (meta.heightPx / meta.heightPts) if (meta and meta.heightPts) else (150.0 / 72.0)
                                w_pts = r.x1 - r.x0
                                h_pts = r.y1 - r.y0
                                await tx.boundingbox.create(
                                    data={
                                        "evidenceItem": {"connect": {"id": finding.id}},
                                        "pageNumber": target_page_idx + 1,
                                        "x": float(r.x0 * sx),
                                        "y": float(r.y0 * sy),
                                        "width": float(w_pts * sx),
                                        "height": float(h_pts * sy),
                                        "xPts": float(r.x0),
                                        "yPts": float(r.y0),
                                        "widthPts": float(w_pts),
                                        "heightPts": float(h_pts),
                                        "label": "Closing Balance Mismatch",
                                        "color": "#dc2626",
                                    }
                                )


                        stage_findings.append({
                            "id": finding.id,
                            "rule_id": "RULE_PK_CLOSING_BALANCE_MISMATCH",
                            "severity": finding.severity,
                            "page": last_page_num,
                            "title": finding.title,
                        })

                # Check 2: Macro Mathematical Balance Formula (Opening + Credits - Debits = Closing)
                if (
                    stated_opening is not None
                    and stated_closing is not None
                    and stated_credits is not None
                    and stated_debits is not None
                ):
                    expected_closing = stated_opening + stated_credits - stated_debits
                    diff_macro = abs(stated_closing - expected_closing)
                    if diff_macro > Decimal("0.01"):
                        discrepancy = stated_closing - expected_closing

                        finding = await tx.evidenceitem.create(
                            data={
                                "document": {"connect": {"id": doc.id}},
                                "pipelineStage": {"connect": {"id": pipeline_stage_id}},
                                "category": "MATHEMATICAL_MISMATCH",
                                "severity": "CRITICAL",
                                "ruleId": "RULE_PK_STATEMENT_SUMMARY_TAMPER",
                                "riskPoints": 50,
                                "title": "Statement Header Summary Arithmetic Inconsistency",
                                "description": (
                                    f"Statement summary figures violate the fundamental banking identity "
                                    f"(Opening Balance + Total Credits - Total Debits = Closing Balance): "
                                    f"Stated Opening (PKR {stated_opening:,.2f}) + Total Credits (PKR {stated_credits:,.2f}) "
                                    f"- Total Debits (PKR {stated_debits:,.2f}) = Expected Closing PKR {expected_closing:,.2f}, "
                                    f"but statement reports Closing Balance PKR {stated_closing:,.2f}. "
                                    f"Discrepancy: PKR {discrepancy:+,.2f}. This proves forged or tampered summary figures."
                                ),
                                "isDeterministic": True,
                                "pageNumber": 1,
                                "expectedValue": f"PKR {expected_closing:,.2f}",
                                "actualValue": f"PKR {stated_closing:,.2f}",
                                "discrepancy": f"PKR {discrepancy:+,.2f}",
                                "technicalDetails": Json({
                                    "stated_opening": str(stated_opening),
                                    "stated_credits": str(stated_credits),
                                    "stated_debits": str(stated_debits),
                                    "stated_closing": str(stated_closing),
                                    "expected_closing": str(expected_closing),
                                    "discrepancy": str(discrepancy),
                                }),
                            }
                        )

                        # Bounding box on summary
                        sum_rects = []
                        target_sum_page = 0
                        for p_i in range(len(pdf_doc)):
                            sum_rects = (
                                pdf_doc[p_i].search_for("Closing Balance")
                                or pdf_doc[p_i].search_for("Total Credit")
                                or pdf_doc[p_i].search_for("Total Debit")
                            )
                            if sum_rects:
                                target_sum_page = p_i
                                break

                        if sum_rects:
                            r = sum_rects[0]
                            meta = page_meta_map.get(target_sum_page + 1)
                            sx = (meta.widthPx / meta.widthPts) if (meta and meta.widthPts) else (150.0 / 72.0)
                            sy = (meta.heightPx / meta.heightPts) if (meta and meta.heightPts) else (150.0 / 72.0)
                            w_pts = r.x1 - r.x0
                            h_pts = r.y1 - r.y0
                            await tx.boundingbox.create(
                                data={
                                    "evidenceItem": {"connect": {"id": finding.id}},
                                    "pageNumber": target_sum_page + 1,
                                    "x": float(r.x0 * sx),
                                    "y": float(r.y0 * sy),
                                    "width": float(w_pts * sx),
                                    "height": float(h_pts * sy),
                                    "xPts": float(r.x0),
                                    "yPts": float(r.y0),
                                    "widthPts": float(w_pts),
                                    "heightPts": float(h_pts),
                                    "label": "Summary Arithmetic Mismatch",
                                    "color": "#dc2626",
                                }
                            )

                        stage_findings.append({
                            "id": finding.id,
                            "rule_id": "RULE_PK_STATEMENT_SUMMARY_TAMPER",
                            "severity": finding.severity,
                            "page": 1,
                            "title": finding.title,
                        })

                pdf_doc.close()

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_payload = {
                "findings_count": len(stage_findings),
                "findings": stage_findings,
                "duration_ms": duration_ms,
                "reconciled": not any(
                    "MISMATCH" in f.get("rule_id", "") or "RECONCILIATION_FAIL" in f.get("rule_id", "")
                    for f in stage_findings
                ),
                "stated_opening": float(stated_opening) if stated_opening is not None else None,
                "implied_opening": float(implied_opening) if implied_opening is not None else None,
                "opening_discrepancy": float(stated_opening - implied_opening) if (stated_opening is not None and implied_opening is not None) else None,
                "stated_closing": float(stated_closing) if stated_closing is not None else None,
                "implied_closing": float(previous_balance) if previous_balance is not None else None,
                "closing_discrepancy": float(stated_closing - previous_balance) if (stated_closing is not None and previous_balance is not None) else None,
                "iban": primary_iban_info,
                "rows": all_ledger_rows,
            }

            await tx.pipelinestage.update(
                where={"id": pipeline_stage_id},
                data={
                    "status": "COMPLETED",
                    "durationMs": duration_ms,
                    "completedAt": datetime.now(timezone.utc),
                    "outputPayload": Json(output_payload),
                },
            )
            return output_payload

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            try:
                await tx.pipelinestage.update(
                    where={"id": pipeline_stage_id},
                    data={
                        "status": "FAILED",
                        "durationMs": duration_ms,
                        "completedAt": datetime.now(timezone.utc),
                        "errorMessage": str(exc),
                        "errorStack": exc.__class__.__name__,
                    },
                )
            except Exception:
                pass
            raise


@celery_app.task(
    name="app.features.pipeline.tasks.stage_6_financial",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run(
    self,
    pipeline_run_id: str,
    pipeline_stage_id: str,
    org_id: str,
    investigation_id: str,
    document_id: str | None = None,
) -> dict:
    """Celery task entry point for Stage 6."""
    import asyncio
    return asyncio.run(
        process_financial(
            pipeline_run_id, pipeline_stage_id, org_id, investigation_id, document_id
        )
    )
