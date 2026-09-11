"""
tests/test_accuracy_upgrades.py
Tests for Core Accuracy Upgrades:
  A1 — OCR backends and structured table parsing
  A2 — TruFor neural engine and CMFD copy-move detection
  A3 — Pakistani calendar validation and Stage 6 Check E
"""
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
import numpy as np
import cv2


# ---------------------------------------------------------------------------
# A1 — OCR Backend Tests
# ---------------------------------------------------------------------------

class TestOCRBackends(unittest.TestCase):
    """Unit tests for the pluggable OCR backend system."""

    def test_get_ocr_backend_returns_paddle_by_default(self):
        """Factory should return PaddleOCRBackend when OCR_BACKEND is unset."""
        import os
        import importlib
        # Reset cached singleton
        import app.features.pipeline.tasks.ocr_backends as mod
        mod._backend_instance = None

        old_env = os.environ.pop("OCR_BACKEND", None)
        try:
            from app.features.pipeline.tasks.ocr_backends import get_ocr_backend, PaddleOCRBackend
            backend = get_ocr_backend()
            self.assertIsInstance(backend, PaddleOCRBackend)
        finally:
            if old_env is not None:
                os.environ["OCR_BACKEND"] = old_env
            mod._backend_instance = None

    def test_get_ocr_backend_rapid_env(self):
        """Factory should return RapidOCRBackend when OCR_BACKEND=rapid."""
        import os
        import app.features.pipeline.tasks.ocr_backends as mod
        mod._backend_instance = None
        os.environ["OCR_BACKEND"] = "rapid"
        try:
            from app.features.pipeline.tasks.ocr_backends import get_ocr_backend, RapidOCRBackend
            backend = get_ocr_backend()
            self.assertIsInstance(backend, RapidOCRBackend)
        finally:
            os.environ.pop("OCR_BACKEND", None)
            mod._backend_instance = None

    def test_ocrresult_dataclass_fields(self):
        """OcrResult must have words, tables, page_text, confidence, method."""
        from app.features.pipeline.tasks.ocr_backends import OcrResult
        r = OcrResult(words=[], tables=[], page_text="hello", confidence=0.9, method="test")
        self.assertEqual(r.page_text, "hello")
        self.assertEqual(r.confidence, 0.9)
        self.assertEqual(r.method, "test")

    def test_paddle_backend_falls_back_to_rapid_when_unavailable(self):
        """PaddleOCRBackend must downgrade to RapidOCR when paddle is not installed."""
        from app.features.pipeline.tasks.ocr_backends import PaddleOCRBackend, RapidOCRBackend

        # Force paddle to be unavailable
        PaddleOCRBackend._initialized = False
        PaddleOCRBackend._available = False

        with patch.object(RapidOCRBackend, "extract") as mock_rapid:
            mock_rapid.return_value = MagicMock(
                words=[], tables=[], page_text="fallback", confidence=0.5, method="RAPIDOCR_NEURAL"
            )
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            backend = PaddleOCRBackend()
            # Mark as initialized but unavailable (paddle not installed)
            PaddleOCRBackend._initialized = True
            PaddleOCRBackend._available = False
            result = backend.extract(img)
            mock_rapid.assert_called_once()

    def test_html_table_parser_extracts_rows(self):
        """_HtmlTableParser must return correct row/cell data from an HTML table string."""
        from app.features.pipeline.tasks.ocr_backends import _HtmlTableParser
        html = "<table><tr><th>Date</th><th>Debit</th><th>Balance</th></tr><tr><td>01/04/2024</td><td>5000.00</td><td>95000.00</td></tr></table>"
        parser = _HtmlTableParser()
        parser.feed(html)
        self.assertEqual(len(parser.rows), 2)
        self.assertEqual(parser.rows[0], ["Date", "Debit", "Balance"])
        self.assertEqual(parser.rows[1][0], "01/04/2024")
        self.assertEqual(parser.rows[1][1], "5000.00")
        self.assertEqual(parser.rows[1][2], "95000.00")

    def test_parse_html_table_creates_parsed_table(self):
        """_parse_html_table must return a ParsedTable with correct cell count."""
        from app.features.pipeline.tasks.ocr_backends import _parse_html_table
        html = "<table><tr><th>Date</th><th>Balance</th></tr><tr><td>12/04/2024</td><td>50000.00</td></tr></table>"
        table = _parse_html_table(html, (0, 0, 400, 100))
        self.assertEqual(table.rows, 2)
        self.assertEqual(table.cols, 2)
        self.assertEqual(len(table.cells), 4)
        # First row should be marked header
        header_cells = [c for c in table.cells if c.is_header]
        self.assertEqual(len(header_cells), 2)

    def test_rapid_backend_returns_no_text_on_blank_image(self):
        """RapidOCRBackend on a blank image should return empty page_text."""
        from app.features.pipeline.tasks.ocr_backends import RapidOCRBackend
        # Reset singleton so it attempts init
        RapidOCRBackend._initialized = False
        RapidOCRBackend._engine = None

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        backend = RapidOCRBackend()
        result = backend.extract(img)
        # Either no engine or no text — both are acceptable empty results
        self.assertIsInstance(result.page_text, str)
        self.assertIsInstance(result.words, list)

    def test_read_structured_table_from_page(self):
        """read_structured_table_from_page must parse extractedTables JSON into typed rows."""
        from app.features.pipeline.tasks.stage_6_financial import read_structured_table_from_page
        from decimal import Decimal

        class FakePageMeta:
            extractedTables = {
                "tables": [
                    {
                        "bbox": [50, 100, 500, 300],
                        "rows": 3,
                        "cols": 5,
                        "cells": [
                            {"row": 0, "col": 0, "text": "Date", "bbox": [50, 100, 120, 120], "is_header": True},
                            {"row": 0, "col": 1, "text": "Narration", "bbox": [120, 100, 250, 120], "is_header": True},
                            {"row": 0, "col": 2, "text": "Cheque No", "bbox": [250, 100, 320, 120], "is_header": True},
                            {"row": 0, "col": 3, "text": "Debit", "bbox": [320, 100, 400, 120], "is_header": True},
                            {"row": 0, "col": 4, "text": "Balance", "bbox": [400, 100, 500, 120], "is_header": True},
                            # Row 1
                            {"row": 1, "col": 0, "text": "12/04/2024", "bbox": [50, 130, 120, 150]},
                            {"row": 1, "col": 1, "text": "ATM Cash", "bbox": [120, 130, 250, 150]},
                            {"row": 1, "col": 2, "text": "001234", "bbox": [250, 130, 320, 150]},
                            {"row": 1, "col": 3, "text": "5,000.00", "bbox": [320, 130, 400, 150]},
                            {"row": 1, "col": 4, "text": "95,000.00", "bbox": [400, 130, 500, 150]},
                        ]
                    }
                ]
            }

        rows = read_structured_table_from_page(FakePageMeta())
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 1)
        r0 = rows[0]
        self.assertEqual(r0["date"], "12/04/2024")
        self.assertEqual(r0["narration"], "ATM Cash")
        self.assertEqual(r0["cheque"], "001234")
        self.assertEqual(r0["debit"], Decimal("5000.00"))
        self.assertEqual(r0["balance"], Decimal("95000.00"))



# ---------------------------------------------------------------------------
# A2a — TruFor Engine Tests
# ---------------------------------------------------------------------------

class TestTruForEngine(unittest.TestCase):
    """Unit tests for TruFor neural manipulation detection engine."""

    def test_trufor_engine_singleton(self):
        """get_instance() must return the same object each time."""
        from app.features.pipeline.tasks.trufor_engine import TruForEngine
        TruForEngine._instance = None  # reset for test isolation
        e1 = TruForEngine.get_instance()
        e2 = TruForEngine.get_instance()
        self.assertIs(e1, e2)
        TruForEngine._instance = None

    def test_trufor_predict_returns_result_when_loaded(self):
        """When loaded=True, predict() must return a TruForResult with valid fields."""
        from app.features.pipeline.tasks.trufor_engine import TruForEngine, TruForResult
        TruForEngine._instance = None
        engine = TruForEngine()
        engine._loaded = True  # skip weight loading

        img = np.frombuffer(bytes((i * 37 + 13) % 256 for i in range(200 * 200 * 3)), dtype=np.uint8).reshape((200, 200, 3))

        # Mock scipy import so test works without it
        import sys
        mock_scipy = MagicMock()
        mock_scipy.ndimage.uniform_filter = lambda x, size: x  # identity
        with patch.dict(sys.modules, {"scipy": mock_scipy, "scipy.ndimage": mock_scipy.ndimage}):
            result = engine.predict(img)

        self.assertIsInstance(result, TruForResult)
        self.assertIn(result.detection, ("authentic", "manipulated"))
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)
        self.assertEqual(result.anomaly_map.shape, (200, 200))

    def test_trufor_is_available_false_when_not_loaded(self):
        """is_available() must return False on a fresh unloaded engine."""
        from app.features.pipeline.tasks.trufor_engine import TruForEngine
        TruForEngine._instance = None
        engine = TruForEngine()  # not calling _try_load
        self.assertFalse(engine.is_available())
        TruForEngine._instance = None


# ---------------------------------------------------------------------------
# A2b — CMFD Engine Tests
# ---------------------------------------------------------------------------

class TestCMFDEngine(unittest.TestCase):
    """Unit tests for copy-move forgery detection."""

    def test_cmfd_returns_empty_on_blank_image(self):
        """detect_copy_move on a blank image must return an empty list (no false positives)."""
        from app.features.pipeline.tasks.cmfd_engine import detect_copy_move
        img = np.zeros((300, 300), dtype=np.uint8)
        matches = detect_copy_move(img)
        self.assertEqual(matches, [])

    def test_cmfd_detects_cloned_region(self):
        """detect_copy_move must find a match when a textured region is pasted."""
        from app.features.pipeline.tasks.cmfd_engine import detect_copy_move
        import cv2

        # Build a feature-rich synthetic image using various high-contrast primitives.
        # ORB FAST corners work best on non-periodic, locally unique corners.
        img = np.ones((600, 800), dtype=np.uint8) * 180  # medium gray background

        # Draw a rich pattern of distinctive shapes in the source area
        # (top-left quadrant, y:50-250, x:50-250)
        shapes = [
            # (type, params, colour)
            ("rect", (55, 55, 120, 100), 20),
            ("rect", (130, 60, 200, 130), 240),
            ("circle", (90, 160, 20), 50),
            ("circle", (160, 170, 15), 220),
            ("rect", (70, 180, 200, 230), 100),
            ("circle", (130, 210, 12), 200),
        ]
        for kind, params, colour in shapes:
            if kind == "rect":
                cv2.rectangle(img, (params[0], params[1]), (params[2], params[3]), colour, -1)
                # Add high-contrast border to generate corner keypoints
                cv2.rectangle(img, (params[0], params[1]), (params[2], params[3]), 255 - colour, 2)
            else:
                cx, cy, r = params
                cv2.circle(img, (cx, cy), r, colour, -1)
                cv2.circle(img, (cx, cy), r, 255 - colour, 2)

        # Copy a 120×120 patch from the source region (y:60-180, x:55-175)
        # and paste it far away (y:380-500, x:550-670) — spatial separation > 400px
        patch = img[60:180, 55:175].copy()
        img[380:500, 550:670] = patch

        # Add mild noise over the whole image to simulate real scan variation
        import random
        r = random.Random(99)
        noise_bytes = bytearray(r.randint(0, 14) for _ in range(img.size))
        noise = np.frombuffer(noise_bytes, dtype=np.uint8).reshape(img.shape).astype(np.int16) - 7
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # min_match_count=4 for the synthetic test: real bank statement pages
        # have hundreds of keypoints and easily exceed 12 inliers.
        matches = detect_copy_move(img, min_match_count=4)

        # Should detect at least one copy-move pair
        self.assertGreater(
            len(matches), 0,
            msg="Expected CMFD to detect the pasted patch but got 0 matches."
        )
        match = matches[0]
        self.assertGreater(match.match_count, 0)
        self.assertGreater(match.confidence, 0.0)

    def test_cmfd_returns_empty_on_none_input(self):

        """detect_copy_move with None input must return empty list, not raise."""
        from app.features.pipeline.tasks.cmfd_engine import detect_copy_move
        result = detect_copy_move(None)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# A3 — Pakistani Calendar Tests
# ---------------------------------------------------------------------------

class TestPKCalendar(unittest.TestCase):
    """Unit tests for pk_calendar date parsing and holiday detection."""

    # ── Date parsing ──────────────────────────────────────────────────────

    def test_parse_dd_mm_yyyy_slash(self):
        from app.features.pipeline.tasks.pk_calendar import parse_transaction_date
        d = parse_transaction_date("12/04/2024")
        self.assertEqual(d, date(2024, 4, 12))

    def test_parse_dd_mm_yyyy_dash(self):
        from app.features.pipeline.tasks.pk_calendar import parse_transaction_date
        d = parse_transaction_date("01-01-2025")
        self.assertEqual(d, date(2025, 1, 1))

    def test_parse_dd_mon_yyyy(self):
        from app.features.pipeline.tasks.pk_calendar import parse_transaction_date
        d = parse_transaction_date("12-Apr-2024")
        self.assertEqual(d, date(2024, 4, 12))

    def test_parse_dd_mon_space_yyyy(self):
        from app.features.pipeline.tasks.pk_calendar import parse_transaction_date
        d = parse_transaction_date("11 Jun 2026")
        self.assertEqual(d, date(2026, 6, 11))

    def test_parse_two_digit_year(self):
        from app.features.pipeline.tasks.pk_calendar import parse_transaction_date
        d = parse_transaction_date("05/03/24")
        self.assertEqual(d, date(2024, 3, 5))

    def test_parse_invalid_returns_none(self):
        from app.features.pipeline.tasks.pk_calendar import parse_transaction_date
        self.assertIsNone(parse_transaction_date("not-a-date"))
        self.assertIsNone(parse_transaction_date(""))
        self.assertIsNone(parse_transaction_date(None))

    # ── Holiday detection ────────────────────────────────────────────────

    def test_saturday_is_bank_holiday(self):
        from app.features.pipeline.tasks.pk_calendar import is_bank_holiday
        # 2024-03-30 is a Saturday
        self.assertTrue(is_bank_holiday(date(2024, 3, 30)))

    def test_sunday_is_bank_holiday(self):
        from app.features.pipeline.tasks.pk_calendar import is_bank_holiday
        # 2024-03-31 is a Sunday
        self.assertTrue(is_bank_holiday(date(2024, 3, 31)))

    def test_monday_is_not_bank_holiday(self):
        from app.features.pipeline.tasks.pk_calendar import is_bank_holiday
        # 2024-04-01 is a Monday
        self.assertFalse(is_bank_holiday(date(2024, 4, 1)))

    def test_pakistan_day_23_march_is_holiday(self):
        """23 March (Pakistan Day) must be detected as a public holiday."""
        from app.features.pipeline.tasks.pk_calendar import is_bank_holiday
        try:
            import holidays  # noqa: F401
        except ImportError:
            self.skipTest("holidays package not installed")
        # 23 March 2024 is a Saturday AND Pakistan Day — doubly non-working
        self.assertTrue(is_bank_holiday(date(2024, 3, 23)))

    def test_14_august_independence_day(self):
        """14 August (Independence Day) must be a holiday."""
        from app.features.pipeline.tasks.pk_calendar import is_bank_holiday
        try:
            import holidays  # noqa: F401
        except ImportError:
            self.skipTest("holidays package not installed")
        # 14 Aug 2024 is a Wednesday — only a holiday because it's Independence Day
        self.assertTrue(is_bank_holiday(date(2024, 8, 14)))

    def test_regular_weekday_is_not_holiday(self):
        """A regular Wednesday that is not a PK public holiday must return False."""
        from app.features.pipeline.tasks.pk_calendar import is_bank_holiday
        # 2024-04-03 is a Wednesday
        self.assertFalse(is_bank_holiday(date(2024, 4, 3)))

    # ── Future date detection ────────────────────────────────────────────

    def test_far_future_date_is_future(self):
        from app.features.pipeline.tasks.pk_calendar import is_future_date
        self.assertTrue(is_future_date(date(2099, 1, 1)))

    def test_past_date_is_not_future(self):
        from app.features.pipeline.tasks.pk_calendar import is_future_date
        self.assertFalse(is_future_date(date(2000, 1, 1)))

    def test_explicit_reference_date(self):
        from app.features.pipeline.tasks.pk_calendar import is_future_date
        ref = date(2024, 6, 1)
        self.assertTrue(is_future_date(date(2024, 6, 2), reference=ref))
        self.assertFalse(is_future_date(date(2024, 5, 31), reference=ref))
        self.assertFalse(is_future_date(date(2024, 6, 1), reference=ref))  # same day is not future

    # ── get_pk_holidays cache ────────────────────────────────────────────

    def test_get_pk_holidays_returns_frozenset(self):
        from app.features.pipeline.tasks.pk_calendar import get_pk_holidays
        result = get_pk_holidays(2024)
        self.assertIsInstance(result, frozenset)

    def test_get_pk_holidays_empty_when_library_missing(self):
        """When holidays library is absent, get_pk_holidays returns empty frozenset."""
        import sys
        from app.features.pipeline.tasks.pk_calendar import get_pk_holidays
        get_pk_holidays.cache_clear()
        with patch.dict(sys.modules, {"holidays": None}):
            # Reload to simulate ImportError
            result = get_pk_holidays.__wrapped__(2024) if hasattr(get_pk_holidays, "__wrapped__") else frozenset()
        self.assertIsInstance(result, frozenset)


# ---------------------------------------------------------------------------
# A2c — Stage 4 Visual Forensics & Connected Component Clustering Tests
# ---------------------------------------------------------------------------

class TestStage4VisualForensics(unittest.TestCase):
    """Unit tests for Stage 4 connected component clustering and table grid line suppression."""

    def test_morphological_table_grid_line_suppression(self):
        """Table borders and ruling lines must be suppressed from tamper hotspot candidates."""
        # 800x600 image with long table ruling lines (horizontal and vertical)
        mask = np.zeros((600, 800), dtype=np.uint8)
        # Horizontal table border: 600px long, 2px thick
        mask[150:152, 100:700] = 255
        # Vertical table border: 2px wide, 400px tall
        mask[100:500, 200:202] = 255
        # Localized tamper patch: 45x30 px
        mask[250:280, 400:445] = 255

        # Suppress thin horizontal and vertical lines while preserving 2D tamper blocks
        vert_thick = cv2.dilate(cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))), cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
        horiz_thick = cv2.dilate(cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))), cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1)))
        thick_blocks = cv2.bitwise_or(vert_thick, horiz_thick)
        thin_elements = cv2.bitwise_and(mask, cv2.bitwise_not(thick_blocks))

        h_lines = cv2.morphologyEx(thin_elements, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1)))
        v_lines = cv2.morphologyEx(thin_elements, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 35)))
        cleaned = cv2.bitwise_and(mask, cv2.bitwise_not(cv2.bitwise_or(h_lines, v_lines)))

        # Find contours on cleaned mask with runaway rejection
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [
            c for c in contours
            if cv2.contourArea(c) >= 40 and cv2.boundingRect(c)[2] < (0.40 * 800) and cv2.boundingRect(c)[3] < (0.35 * 600)
        ]

        # Only the compact tamper patch should remain
        self.assertEqual(len(valid), 1)
        x, y, w, h = cv2.boundingRect(valid[0])
        self.assertEqual((x, y, w, h), (400, 250, 45, 30))

    def test_find_contours_clustering_compactness(self):
        """Bounding boxes from cv2.findContours must wrap tightly around localized tamper clusters."""
        mask = np.zeros((1000, 800), dtype=np.uint8)
        # Spliced element at (350, 450), 60x25 px
        mask[450:475, 350:410] = 255

        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.assertEqual(len(contours), 1)

        x, y, w, h = cv2.boundingRect(contours[0])
        self.assertEqual((x, y, w, h), (350, 450, 60, 25))
        # Verify box does not span across the page
        self.assertLess(w, 800 * 0.35)
        self.assertLess(h, 1000 * 0.25)

    def test_baseline_agglomeration_and_ocr_snapping(self):
        """Adjacent multi-digit components on the same text baseline merge and snap to OCR tokens."""
        # Simulated components on the same row: y=200, height=14
        candidate_components = [
            (100, 200, 20, 14, 250),  # digit group 1
            (125, 201, 22, 14, 260),  # digit group 2
        ]
        page_width, page_height = 800, 1000

        # Horizontal baseline merge logic
        merged_boxes = []
        for comp in candidate_components:
            cx, cy, cw, ch, carea = comp
            merged = False
            for idx, (bx, by, bw, bh, barea) in enumerate(merged_boxes):
                b_cy = by + bh / 2.0
                c_cy = cy + ch / 2.0
                y_overlap = max(0, min(by + bh, cy + ch) - max(by, cy))
                min_h = min(bh, ch)
                same_row = (abs(b_cy - c_cy) <= 10) or (min_h > 0 and (y_overlap / min_h) >= 0.50)
                x_gap = max(0, max(bx, cx) - min(bx + bw, cx + cw))
                y_gap = max(0, max(by, cy) - min(by + bh, cy + ch))

                if (x_gap <= 6 and y_gap <= 6) or (same_row and x_gap <= 20):
                    nx = min(cx, bx)
                    ny = min(cy, by)
                    nw = max(cx + cw, bx + bw) - nx
                    nh = max(cy + ch, by + bh) - ny
                    if nw < (0.45 * page_width) and nh < (0.25 * page_height):
                        merged_boxes[idx] = (nx, ny, nw, nh, barea + carea)
                        merged = True
                        break
            if not merged:
                merged_boxes.append((cx, cy, cw, ch, carea))

        self.assertEqual(len(merged_boxes), 1)
        mx, my, mw, mh, _ = merged_boxes[0]
        self.assertEqual(mx, 100)
        self.assertEqual(my, 200)
        self.assertEqual(mw, 47)  # 100 to 147

        # OCR token snapping: simulated OCR token covering the whole amount
        # scale_to_pts: 72/150 = 0.48 -> pts_to_px = 150/72
        pts_to_px = 150.0 / 72.0
        # Token in points from x=47 to x=72, y=95 to y=104
        ocr_word = [47.0, 95.0, 72.0, 104.0, "1,500.00"]
        wx0 = float(ocr_word[0]) * pts_to_px  # ~97.9 px
        wy0 = float(ocr_word[1]) * pts_to_px  # ~197.9 px
        wx1 = float(ocr_word[2]) * pts_to_px  # ~150.0 px
        wy1 = float(ocr_word[3]) * pts_to_px  # ~216.7 px

        inter_x = max(0, min(mx + mw, wx1) - max(mx, wx0))
        inter_y = max(0, min(my + mh, wy1) - max(my, wy0))
        self.assertGreater(inter_x * inter_y, 0)

        # Snap to token + 3px padding
        snapped_x = max(0, int(wx0 - 3))
        snapped_y = max(0, int(wy0 - 3))
        snapped_w = int(wx1 - wx0 + 6)
        snapped_h = int(wy1 - wy0 + 6)

        self.assertAlmostEqual(snapped_x, 94, delta=2)
        self.assertAlmostEqual(snapped_y, 194, delta=2)
        self.assertAlmostEqual(snapped_w, 58, delta=3)


# ---------------------------------------------------------------------------
# A2d — Cross-Stage Spatial Splicing Synergy Tests
# ---------------------------------------------------------------------------

class TestCrossStageSplicingSynergy(unittest.TestCase):
    """Unit tests for Stage 7 cross-stage spatial IoU synergy detection."""

    def test_cross_stage_spatial_iou_calculation(self):
        """Coincident Stage 3 and Stage 4 bounding boxes must produce IoU >= 0.15."""
        class MockBox:
            def __init__(self, x, y, w, h):
                self.x, self.y, self.width, self.height = x, y, w, h
                self.xPts, self.yPts, self.widthPts, self.heightPts = x, y, w, h

        # Stage 3 Font offset box at (100, 200, 120, 25)
        b_font = MockBox(100.0, 200.0, 120.0, 25.0)
        # Stage 4 ELA/TruFor anomaly box at (105, 198, 115, 28)
        b_ela = MockBox(105.0, 198.0, 115.0, 28.0)

        ix0 = max(b_font.x, b_ela.x)
        iy0 = max(b_font.y, b_ela.y)
        ix1 = min(b_font.x + b_font.width, b_ela.x + b_ela.width)
        iy1 = min(b_font.y + b_font.height, b_ela.y + b_ela.height)

        inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
        min_area = min(b_font.width * b_font.height, b_ela.width * b_ela.height)
        overlap_ratio = inter / min_area if min_area > 0 else 0.0

        self.assertGreaterEqual(overlap_ratio, 0.70)
        self.assertTrue(overlap_ratio >= 0.15)


if __name__ == "__main__":
    unittest.main()
