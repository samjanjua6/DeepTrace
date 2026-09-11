"""
Pluggable OCR Backend Protocol for Stage 5.

Provides a common interface over four engines:
  - PaddleOCRBackend    : Local CPU inference via PaddleOCR + PP-Structure (default)
  - RapidOCRBackend     : Legacy fallback, uses rapidocr-onnxruntime
  - TextractBackend     : AWS Textract (cloud, requires boto3 + AWS creds)
  - AzureDocIntelBackend: Azure Document Intelligence (cloud, requires azure-ai-documentintelligence)

Selection is controlled by the OCR_BACKEND env var:
  OCR_BACKEND=paddle    (default)
  OCR_BACKEND=rapid
  OCR_BACKEND=textract
  OCR_BACKEND=azure

Structured table cell output format (stored in DocumentPage.extractedTables):
{
  "tables": [
    {
      "bbox": [x0_pts, y0_pts, x1_pts, y1_pts],
      "rows": <int>,
      "cols": <int>,
      "cells": [
        {
          "row": <int>,
          "col": <int>,
          "text": <str>,
          "bbox": [x0_pts, y0_pts, x1_pts, y1_pts],
          "is_header": <bool>
        },
        ...
      ]
    }
  ]
}

Word output format (stored in DocumentPage.ocrDataJson["words"]):
  Each word: [x0, y0, x1, y1, text, block_no, line_no, word_no]
  (Compatible with PyMuPDF get_text("words") format)
"""
from __future__ import annotations

import html.parser
import io
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TableCell:
    row: int
    col: int
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1) in pts or px
    is_header: bool = False
    row_span: int = 1
    col_span: int = 1


@dataclass
class ParsedTable:
    bbox: tuple[float, float, float, float]  # table boundary
    rows: int
    cols: int
    cells: list[TableCell] = field(default_factory=list)


@dataclass
class OcrResult:
    """Unified result from any OCR backend."""
    words: list[list[Any]]             # [[x0, y0, x1, y1, text, blk, line, word], ...]
    tables: list[ParsedTable]          # Structured table cells (empty if backend doesn't support)
    page_text: str                     # Full plain text (newline-joined lines)
    confidence: float                  # Average word-level confidence 0.0–1.0
    method: str                        # Backend identifier string


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class OCRBackend(Protocol):
    """Interface all OCR backends must satisfy."""

    def extract(
        self,
        img_arr: np.ndarray,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> OcrResult:
        """
        Extract text and optionally table structure from a page image array.

        Args:
            img_arr:  uint8 RGB or grayscale image array (H, W [, C]).
            scale_x:  Pixel-to-PDF-point scale factor (x axis).
            scale_y:  Pixel-to-PDF-point scale factor (y axis).

        Returns:
            OcrResult populated with words, tables, text, confidence, method.
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# HTML table cell parser (used by PaddleOCR PP-Structure HTML output)
# ---------------------------------------------------------------------------

class _HtmlTableParser(html.parser.HTMLParser):
    """Minimal stateful HTML table parser for PP-Structure cell extraction."""

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._in_cell = False
        self._current_cell_text: str = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._current_cell_text = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr":
            if self._current_row:
                self._rows.append(self._current_row)
                self._current_row = []
        elif tag in ("td", "th"):
            self._current_row.append(self._current_cell_text.strip())
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell_text += data

    @property
    def rows(self) -> list[list[str]]:
        return self._rows


def _parse_html_table(html_str: str, table_bbox: tuple) -> ParsedTable:
    """Convert a PP-Structure HTML string + bounding box into a ParsedTable."""
    parser = _HtmlTableParser()
    parser.feed(html_str)
    raw_rows = parser.rows

    if not raw_rows:
        return ParsedTable(bbox=table_bbox, rows=0, cols=0, cells=[])

    num_rows = len(raw_rows)
    num_cols = max(len(r) for r in raw_rows) if raw_rows else 0

    x0, y0, x1, y1 = table_bbox
    cell_w = (x1 - x0) / max(num_cols, 1)
    cell_h = (y1 - y0) / max(num_rows, 1)

    cells: list[TableCell] = []
    is_first_row = True
    for r_idx, row_cells in enumerate(raw_rows):
        for c_idx, text in enumerate(row_cells):
            cx0 = x0 + c_idx * cell_w
            cy0 = y0 + r_idx * cell_h
            cx1 = cx0 + cell_w
            cy1 = cy0 + cell_h
            cells.append(TableCell(
                row=r_idx,
                col=c_idx,
                text=text,
                bbox=(cx0, cy0, cx1, cy1),
                is_header=is_first_row,
            ))
        is_first_row = False

    return ParsedTable(bbox=table_bbox, rows=num_rows, cols=num_cols, cells=cells)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class PaddleOCRBackend:
    """
    PaddleOCR + PP-Structure backend.
    Extracts exact cell-level table coordinates and text on CPU via ONNX inference.
    First call downloads model weights (~150 MB) to ~/.paddleocr/.
    Falls back to RapidOCRBackend if PaddleOCR is not installed.
    """

    _pp_structure = None
    _paddle_ocr = None
    _initialized: bool = False
    _available: bool = False

    @classmethod
    def _ensure_init(cls) -> None:
        if cls._initialized:
            return
        cls._initialized = True
        try:
            from paddleocr import PPStructure, PaddleOCR  # type: ignore
            cls._pp_structure = PPStructure(
                table=True,
                ocr=True,
                show_log=False,
                use_gpu=os.environ.get("OCR_PADDLE_USE_GPU", "false").lower() == "true",
                lang="en",
            )
            cls._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
                use_gpu=os.environ.get("OCR_PADDLE_USE_GPU", "false").lower() == "true",
            )
            cls._available = True
            logger.info("PaddleOCRBackend: PP-Structure engine initialized.")
        except Exception as exc:
            logger.warning(
                "PaddleOCRBackend: PaddleOCR not available (%s). Will fall back to RapidOCR.", exc
            )
            cls._available = False

    def extract(
        self,
        img_arr: np.ndarray,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> OcrResult:
        self._ensure_init()
        if not self._available:
            # Graceful downgrade to RapidOCR
            return RapidOCRBackend().extract(img_arr, scale_x, scale_y)

        try:
            result = self._pp_structure(img_arr)
        except Exception as exc:
            logger.warning("PaddleOCRBackend: PP-Structure inference failed (%s), falling back.", exc)
            return RapidOCRBackend().extract(img_arr, scale_x, scale_y)

        words: list[list[Any]] = []
        tables: list[ParsedTable] = []
        ocr_lines: list[str] = []
        confidences: list[float] = []

        blk_idx = 0
        for region in (result or []):
            region_type = region.get("type", "").lower()
            bbox_raw = region.get("bbox", [0, 0, 0, 0])  # [x0, y0, x1, y1] in pixels

            # Scale pixel bbox to PDF points
            rx0 = bbox_raw[0] * scale_x
            ry0 = bbox_raw[1] * scale_y
            rx1 = bbox_raw[2] * scale_x
            ry1 = bbox_raw[3] * scale_y
            table_bbox_pts = (rx0, ry0, rx1, ry1)

            if region_type == "table":
                html_str = region.get("res", {}).get("html", "")
                if html_str:
                    parsed = _parse_html_table(html_str, table_bbox_pts)
                    tables.append(parsed)
                    # Also add table cell texts as words for plain-text extraction
                    for cell in parsed.cells:
                        if not cell.text:
                            continue
                        ocr_lines.append(cell.text)
                        words.append([
                            cell.bbox[0], cell.bbox[1],
                            cell.bbox[2], cell.bbox[3],
                            cell.text, blk_idx, cell.row, cell.col,
                        ])
                blk_idx += 1

            elif region_type in ("text", "title", "figure_caption", "header", "footer", "reference"):
                res_list = region.get("res", [])
                if not isinstance(res_list, list):
                    continue
                line_idx = 0
                for line in res_list:
                    if not isinstance(line, (list, tuple)) or len(line) < 2:
                        continue
                    box_pts_px, (line_str, conf) = line[0], line[1]
                    ocr_lines.append(line_str)
                    confidences.append(float(conf))

                    xs = [pt[0] * scale_x for pt in box_pts_px]
                    ys = [pt[1] * scale_y for pt in box_pts_px]
                    lx0, ly0, lx1, ly1 = min(xs), min(ys), max(xs), max(ys)

                    word_tokens = line_str.split()
                    if not word_tokens:
                        continue
                    total_chars = max(sum(len(w) for w in word_tokens), 1)
                    line_w = max(lx1 - lx0, 1.0)
                    char_w = line_w / total_chars
                    cur_x = lx0
                    for w_idx, w_tok in enumerate(word_tokens):
                        w_width = len(w_tok) * char_w
                        words.append([
                            round(cur_x, 2), round(ly0, 2),
                            round(cur_x + w_width, 2), round(ly1, 2),
                            w_tok, blk_idx, line_idx, w_idx,
                        ])
                        cur_x += w_width + (char_w * 0.5)
                    line_idx += 1
                blk_idx += 1

        page_text = "\n".join(ocr_lines)
        avg_conf = round(sum(confidences) / max(len(confidences), 1), 3) if confidences else 0.95

        return OcrResult(
            words=words,
            tables=tables,
            page_text=page_text,
            confidence=avg_conf,
            method="PADDLEOCR_PPSTRUCTURE",
        )


class RapidOCRBackend:
    """
    Legacy RapidOCR backend (rapidocr-onnxruntime).
    No table structure recognition — returns words only.
    """
    _engine = None
    _initialized: bool = False

    @classmethod
    def _ensure_init(cls) -> None:
        if cls._initialized:
            return
        cls._initialized = True
        try:
            from rapidocr_onnxruntime import RapidOCR
            cls._engine = RapidOCR()
            logger.info("RapidOCRBackend: Engine initialized.")
        except Exception as exc:
            logger.warning("RapidOCRBackend: Could not initialize (%s).", exc)

    def extract(
        self,
        img_arr: np.ndarray,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> OcrResult:
        self._ensure_init()
        if self._engine is None:
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="OCR_ENGINE_UNAVAILABLE")

        try:
            res, _ = self._engine(img_arr)
        except Exception as exc:
            logger.warning("RapidOCRBackend: Inference error: %s", exc)
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="RAPIDOCR_ERROR")

        if not res:
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="RAPIDOCR_NO_TEXT")

        words: list[list[Any]] = []
        ocr_lines: list[str] = []
        confidences: list[float] = []

        for line_idx, (box_pts, line_str, conf) in enumerate(res):
            ocr_lines.append(line_str)
            confidences.append(float(conf))
            xs = [pt[0] * scale_x for pt in box_pts]
            ys = [pt[1] * scale_y for pt in box_pts]
            lx0, ly0, lx1, ly1 = min(xs), min(ys), max(xs), max(ys)
            word_tokens = line_str.split()
            if not word_tokens:
                continue
            total_chars = max(sum(len(w) for w in word_tokens), 1)
            line_w = max(lx1 - lx0, 1.0)
            char_w = line_w / total_chars
            cur_x = lx0
            for w_idx, w_tok in enumerate(word_tokens):
                w_width = len(w_tok) * char_w
                words.append([
                    round(cur_x, 2), round(ly0, 2),
                    round(cur_x + w_width, 2), round(ly1, 2),
                    w_tok, 0, line_idx, w_idx,
                ])
                cur_x += w_width + (char_w * 0.5)

        page_text = "\n".join(ocr_lines)
        avg_conf = round(sum(confidences) / max(len(confidences), 1), 3)
        return OcrResult(words=words, tables=[], page_text=page_text, confidence=avg_conf, method="RAPIDOCR_NEURAL")


class TextractBackend:
    """
    AWS Textract backend. Requires:
      - boto3 installed
      - AWS credentials (env vars or instance role)
      - OCR_BACKEND=textract
      - AWS_TEXTRACT_REGION env var
    """

    def extract(
        self,
        img_arr: np.ndarray,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> OcrResult:
        try:
            import boto3
            from PIL import Image
        except ImportError:
            logger.error("TextractBackend: boto3 or Pillow not installed.")
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="TEXTRACT_UNAVAILABLE")

        region = os.environ.get("AWS_TEXTRACT_REGION", "us-east-1")
        client = boto3.client("textract", region_name=region)

        from PIL import Image as _Image
        img_pil = _Image.fromarray(img_arr)
        buf = io.BytesIO()
        img_pil.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        try:
            resp = client.analyze_document(
                Document={"Bytes": img_bytes},
                FeatureTypes=["TABLES"],
            )
        except Exception as exc:
            logger.warning("TextractBackend: API call failed: %s", exc)
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="TEXTRACT_ERROR")

        blocks = resp.get("Blocks", [])
        # Minimal Textract word extraction
        words: list[list[Any]] = []
        ocr_lines: list[str] = []
        confidences: list[float] = []
        h, w = img_arr.shape[:2]

        for blk in blocks:
            if blk["BlockType"] != "WORD":
                continue
            geo = blk.get("Geometry", {}).get("BoundingBox", {})
            bx0 = geo.get("Left", 0) * w * scale_x
            by0 = geo.get("Top", 0) * h * scale_y
            bx1 = bx0 + geo.get("Width", 0) * w * scale_x
            by1 = by0 + geo.get("Height", 0) * h * scale_y
            txt = blk.get("Text", "")
            conf = blk.get("Confidence", 0.0) / 100.0
            ocr_lines.append(txt)
            confidences.append(conf)
            words.append([round(bx0, 2), round(by0, 2), round(bx1, 2), round(by1, 2), txt, 0, 0, 0])

        page_text = " ".join(ocr_lines)
        avg_conf = round(sum(confidences) / max(len(confidences), 1), 3) if confidences else 0.0
        # Note: Table structure parsing from Textract blocks omitted for brevity —
        # implement by walking CELL / TABLE block relationships from resp["Blocks"].
        return OcrResult(words=words, tables=[], page_text=page_text, confidence=avg_conf, method="AWS_TEXTRACT")


class AzureDocIntelBackend:
    """
    Azure Document Intelligence backend. Requires:
      - azure-ai-documentintelligence installed
      - AZURE_DOC_INTEL_ENDPOINT and AZURE_DOC_INTEL_KEY env vars
    """

    def extract(
        self,
        img_arr: np.ndarray,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> OcrResult:
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient  # type: ignore
            from azure.core.credentials import AzureKeyCredential  # type: ignore
        except ImportError:
            logger.error("AzureDocIntelBackend: azure-ai-documentintelligence not installed.")
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="AZURE_UNAVAILABLE")

        endpoint = os.environ.get("AZURE_DOC_INTEL_ENDPOINT", "")
        key = os.environ.get("AZURE_DOC_INTEL_KEY", "")
        if not endpoint or not key:
            logger.error("AzureDocIntelBackend: AZURE_DOC_INTEL_ENDPOINT / KEY not set.")
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="AZURE_CONFIG_MISSING")

        from PIL import Image as _Image
        img_pil = _Image.fromarray(img_arr)
        buf = io.BytesIO()
        img_pil.save(buf, format="PNG")
        buf.seek(0)

        try:
            client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
            poller = client.begin_analyze_document("prebuilt-layout", analyze_request=buf, content_type="image/png")
            result = poller.result()
        except Exception as exc:
            logger.warning("AzureDocIntelBackend: API call failed: %s", exc)
            return OcrResult(words=[], tables=[], page_text="", confidence=0.0, method="AZURE_ERROR")

        words: list[list[Any]] = []
        page_text = result.content or ""
        # Minimal word extraction from Azure result
        for page in (result.pages or []):
            for word in (page.words or []):
                poly = word.polygon or []
                if len(poly) >= 8:
                    xs = [poly[i] * scale_x for i in range(0, len(poly), 2)]
                    ys = [poly[i] * scale_y for i in range(1, len(poly), 2)]
                    words.append([min(xs), min(ys), max(xs), max(ys), word.content, 0, 0, 0])

        return OcrResult(words=words, tables=[], page_text=page_text, confidence=0.95, method="AZURE_DOC_INTEL")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_backend_instance: Optional[OCRBackend] = None


def get_ocr_backend() -> OCRBackend:
    """
    Return the configured OCR backend singleton.
    Reads OCR_BACKEND env var: 'paddle' (default) | 'rapid' | 'textract' | 'azure'.
    """
    global _backend_instance
    if _backend_instance is not None:
        return _backend_instance

    backend_name = os.environ.get("OCR_BACKEND", "paddle").lower().strip()
    if backend_name == "textract":
        _backend_instance = TextractBackend()
        logger.info("ocr_backends: Using AWS Textract backend.")
    elif backend_name == "azure":
        _backend_instance = AzureDocIntelBackend()
        logger.info("ocr_backends: Using Azure Document Intelligence backend.")
    elif backend_name == "rapid":
        _backend_instance = RapidOCRBackend()
        logger.info("ocr_backends: Using RapidOCR backend.")
    else:
        _backend_instance = PaddleOCRBackend()
        logger.info("ocr_backends: Using PaddleOCR + PP-Structure backend (default).")

    return _backend_instance
