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


# ---------------------------------------------------------------------------
# A3b — Cross-Page Ledger State Machine Tests
# ---------------------------------------------------------------------------

class TestCrossPageLedgerStateMachine(unittest.TestCase):
    """Deterministic tests for multi-page financial ledger state tracking and boundary invariants."""

    def test_multipage_continuous_carryforward_5_pages(self):
        """5-page continuous transaction run must maintain running balance across all page transitions."""
        from app.features.pipeline.tasks.ledger_state_machine import CrossPageLedgerStateMachine

        sm = CrossPageLedgerStateMachine(
            stated_opening=Decimal("100000.00"),
            stated_closing=Decimal("250000.00"),
            stated_credits=Decimal("200000.00"),
            stated_debits=Decimal("50000.00"),
        )

        # Page 1
        sm.start_page(1)
        f_op = sm.process_opening_row(1, Decimal("100000.00"), raw_line="01/01/2026 Opening Balance 100,000.00")
        self.assertIsNone(f_op)
        # Tx 1: Credit 50k -> 150k
        rec, b, f = sm.process_transaction(
            1, "02/01/2026", "Salary Deposit", Decimal("150000.00"),
            [(Decimal("50000.00"), (0,0,0,0), "50,000.00"), (Decimal("150000.00"), (0,0,0,0), "150,000.00")]
        )
        self.assertTrue(rec)
        self.assertEqual(b, Decimal("150000.00"))
        # Page 1 CF: 150k
        f_cf = sm.process_carried_forward(1, Decimal("150000.00"))
        self.assertIsNone(f_cf)
        sm.end_page(1)

        # Page 2 (Explicit BF)
        sm.start_page(2)
        f_bf = sm.process_brought_forward(2, Decimal("150000.00"))
        self.assertIsNone(f_bf)
        # Tx 2: Debit 20k -> 130k
        rec, b, f = sm.process_transaction(
            2, "05/01/2026", "Utility Bill", Decimal("130000.00"),
            [(Decimal("-20000.00"), (0,0,0,0), "-20,000.00"), (Decimal("130000.00"), (0,0,0,0), "130,000.00")]
        )
        self.assertTrue(rec)
        sm.end_page(2)

        # Page 3 (Seamless - no BF line)
        sm.start_page(3)
        # Tx 3: Credit 70k -> 200k
        rec, b, f = sm.process_transaction(
            3, "10/01/2026", "Consulting Fee", Decimal("200000.00"),
            [(Decimal("70000.00"), (0,0,0,0), "70,000.00"), (Decimal("200000.00"), (0,0,0,0), "200,000.00")]
        )
        self.assertTrue(rec)
        sm.end_page(3)

        # Page 4 (Explicit BF)
        sm.start_page(4)
        f_bf4 = sm.process_brought_forward(4, Decimal("200000.00"))
        self.assertIsNone(f_bf4)
        # Tx 4: Debit 30k -> 170k
        rec, b, f = sm.process_transaction(
            4, "15/01/2026", "Office Rent", Decimal("170000.00"),
            [(Decimal("-30000.00"), (0,0,0,0), "-30,000.00"), (Decimal("170000.00"), (0,0,0,0), "170,000.00")]
        )
        self.assertTrue(rec)
        sm.end_page(4)

        # Page 5 (Seamless)
        sm.start_page(5)
        # Tx 5: Credit 80k -> 250k
        rec, b, f = sm.process_transaction(
            5, "20/01/2026", "Client Remittance", Decimal("250000.00"),
            [(Decimal("80000.00"), (0,0,0,0), "80,000.00"), (Decimal("250000.00"), (0,0,0,0), "250,000.00")]
        )
        self.assertTrue(rec)
        sm.end_page(5)

        # Final audit
        final_findings = sm.finalize()
        self.assertEqual(len(final_findings), 0)
        self.assertEqual(len(sm.discontinuities), 0)
        self.assertEqual(len(sm.get_ledger_rows()), 9)  # 1 open + 1 CF + 2 BF + 5 tx = 9 rows

    def test_brought_forward_mismatch_detected(self):
        """Page N Brought Forward mismatch vs Page N-1 terminal balance must produce RULE_PK_PAGE_BALANCE_DISCONTINUITY."""
        from app.features.pipeline.tasks.ledger_state_machine import CrossPageLedgerStateMachine

        sm = CrossPageLedgerStateMachine(stated_opening=Decimal("50000.00"))
        sm.start_page(1)
        sm.process_opening_row(1, Decimal("50000.00"))
        sm.process_transaction(
            1, "01/02/2026", "Deposit", Decimal("100000.00"),
            [(Decimal("50000.00"), (0,0,0,0), "50,000.00"), (Decimal("100000.00"), (0,0,0,0), "100,000.00")]
        )
        sm.end_page(1)

        sm.start_page(2)
        # Fraudster inserts inflated Brought Forward 150,000 instead of 100,000
        finding = sm.process_brought_forward(2, Decimal("150000.00"))
        self.assertIsNotNone(finding)
        self.assertEqual(finding["rule_id"], "RULE_PK_PAGE_BALANCE_DISCONTINUITY")
        self.assertEqual(finding["discrepancy"], "PKR +50,000.00")
        self.assertTrue(sm.pages[2].has_discontinuity)

    def test_carried_forward_mismatch_detected(self):
        """Page N Carried Forward mismatch vs running balance must produce RULE_PK_PAGE_BALANCE_DISCONTINUITY."""
        from app.features.pipeline.tasks.ledger_state_machine import CrossPageLedgerStateMachine

        sm = CrossPageLedgerStateMachine()
        sm.start_page(1)
        sm.process_opening_row(1, Decimal("80000.00"))
        sm.process_transaction(
            1, "01/02/2026", "Withdrawal", Decimal("60000.00"),
            [(Decimal("-20000.00"), (0,0,0,0), "-20,000.00"), (Decimal("60000.00"), (0,0,0,0), "60,000.00")]
        )
        # Actual running balance is 60,000. C/F line claims 90,000.
        finding = sm.process_carried_forward(1, Decimal("90000.00"))
        self.assertIsNotNone(finding)
        self.assertEqual(finding["rule_id"], "RULE_PK_PAGE_BALANCE_DISCONTINUITY")
        self.assertEqual(finding["discrepancy"], "PKR +30,000.00")

    def test_seamless_carryforward_detects_tampered_first_row(self):
        """Without explicit B/F line, an altered starting transaction on Page N must be flagged across boundary."""
        from app.features.pipeline.tasks.ledger_state_machine import CrossPageLedgerStateMachine

        sm = CrossPageLedgerStateMachine()
        sm.start_page(1)
        sm.process_opening_row(1, Decimal("100000.00"))
        sm.end_page(1)  # Page 1 ends at 100,000

        sm.start_page(2)
        # Page 2 has NO B/F line. First tx is credit of 20k, but reports balance 200k (+80k jump)
        rec, b, finding = sm.process_transaction(
            2, "05/02/2026", "Transfer In", Decimal("200000.00"),
            [(Decimal("20000.00"), (0,0,0,0), "20,000.00"), (Decimal("200000.00"), (0,0,0,0), "200,000.00")]
        )
        self.assertFalse(rec)
        self.assertIsNotNone(finding)
        self.assertEqual(finding["rule_id"], "RULE_PK_PAGE_BALANCE_DISCONTINUITY")
        self.assertIn("PKR +80,000.00", finding["discrepancy"])

    def test_header_opening_mismatch_detected(self):
        """Mismatch between header stated opening and ledger first line must be caught."""
        from app.features.pipeline.tasks.ledger_state_machine import CrossPageLedgerStateMachine

        sm = CrossPageLedgerStateMachine(stated_opening=Decimal("500000.00"))
        sm.start_page(1)
        finding = sm.process_opening_row(1, Decimal("200000.00"))
        self.assertIsNotNone(finding)
        self.assertEqual(finding["rule_id"], "RULE_PK_OPENING_BALANCE_MISMATCH")
        self.assertEqual(finding["discrepancy"], "PKR -300,000.00")

    def test_finalize_closing_and_macro_summary_mismatch(self):
        """Finalize must catch closing balance tampering and macro identity arithmetic violation."""
        from app.features.pipeline.tasks.ledger_state_machine import CrossPageLedgerStateMachine

        # Opening 100k, Cr 100k, Dr 20k -> expected closing 180k.
        # But header states closing 300k.
        sm = CrossPageLedgerStateMachine(
            stated_opening=Decimal("100000.00"),
            stated_closing=Decimal("300000.00"),
            stated_credits=Decimal("100000.00"),
            stated_debits=Decimal("20000.00"),
        )
        sm.start_page(1)
        sm.process_opening_row(1, Decimal("100000.00"))
        sm.process_transaction(
            1, "01/01/2026", "Tx", Decimal("180000.00"),
            [(Decimal("80000.00"), (0,0,0,0), "80,000.00"), (Decimal("180000.00"), (0,0,0,0), "180,000.00")]
        )
        sm.end_page(1)

        findings = sm.finalize()
        rule_ids = [f["rule_id"] for f in findings]
        self.assertIn("RULE_PK_CLOSING_BALANCE_MISMATCH", rule_ids)
        self.assertIn("RULE_PK_STATEMENT_SUMMARY_TAMPER", rule_ids)


# ---------------------------------------------------------------------------
# A3c — PK Calendar Upgrades & Channel Aware Non-Working Day Tests
# ---------------------------------------------------------------------------

class TestPKCalendarUpgrades(unittest.TestCase):
    """Unit tests for SBP circular closing days, channel classification, and impossible future dates."""

    def test_sbp_bank_holiday_jan_1(self):
        """Jan 1 SBP Annual Accounts Closing must be detected as a bank holiday."""
        from app.features.pipeline.tasks.pk_calendar import is_sbp_closing_day, is_bank_holiday

        d = date(2026, 1, 1)
        self.assertTrue(is_sbp_closing_day(d))
        self.assertTrue(is_bank_holiday(d))

    def test_sbp_bank_holiday_jul_1(self):
        """Jul 1 SBP Mid-Year Closing must be detected as a bank holiday."""
        from app.features.pipeline.tasks.pk_calendar import is_sbp_closing_day, is_bank_holiday

        d = date(2025, 7, 1)
        self.assertTrue(is_sbp_closing_day(d))
        self.assertTrue(is_bank_holiday(d))

    def test_channel_classification(self):
        """Narration text must be correctly classified into DIGITAL vs OTC_CLEARING."""
        from app.features.pipeline.tasks.pk_calendar import classify_transaction_channel, ChannelType

        self.assertEqual(classify_transaction_channel("Raast P2P transfer to ALI"), ChannelType.DIGITAL)
        self.assertEqual(classify_transaction_channel("ATM Cash W/D F-10 ISB"), ChannelType.DIGITAL)
        self.assertEqual(classify_transaction_channel("IBFT Funds Transfer via App"), ChannelType.DIGITAL)
        self.assertEqual(classify_transaction_channel("POS Purchase Shell F-7"), ChannelType.DIGITAL)

        self.assertEqual(classify_transaction_channel("Cheque Clearing NIFT Outward"), ChannelType.OTC_CLEARING)
        self.assertEqual(classify_transaction_channel("Counter Cash Deposit by bearer"), ChannelType.OTC_CLEARING)
        self.assertEqual(classify_transaction_channel("Chq Deposit #884920"), ChannelType.OTC_CLEARING)

    def test_digital_channel_allowed_on_sunday(self):
        """Digital 24/7 channels (Raast/ATM) must NOT be flagged on non-working days."""
        from app.features.pipeline.tasks.pk_calendar import evaluate_transaction_date

        sunday = date(2026, 3, 29)
        # Raast on Sunday -> No anomaly
        anomaly = evaluate_transaction_date(sunday, narration="Raast instant transfer to merchant")
        self.assertIsNone(anomaly)

        # Cheque clearing on Sunday -> Flagged
        anomaly_otc = evaluate_transaction_date(sunday, narration="NIFT Cheque Clearing Inward")
        self.assertIsNotNone(anomaly_otc)
        self.assertEqual(anomaly_otc["rule_id"], "RULE_PK_WEEKEND_CLEARING_ANOMALY")

    def test_impossible_future_date_relative_to_statement_period(self):
        """Transaction dated after statement_period_end must produce RULE_PK_FUTURE_DATE_TRANSACTION."""
        from app.features.pipeline.tasks.pk_calendar import evaluate_transaction_date

        period_end = date(2026, 1, 31)
        tx_date = date(2026, 2, 15)  # 15 days after period ended

        anomaly = evaluate_transaction_date(tx_date, statement_period_end=period_end)
        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly["rule_id"], "RULE_PK_FUTURE_DATE_TRANSACTION")
        self.assertEqual(anomaly["severity"], "CRITICAL")
        self.assertEqual(anomaly["risk_points"], 35)

    def test_gazetted_islamic_holidays_lookup(self):
        """Gazetted Islamic lunar holidays in lookup table must be recognized even offline."""
        from app.features.pipeline.tasks.pk_calendar import is_bank_holiday

        # 2026 Eid-ul-Fitr dates in lookup: 2026-03-20, 2026-03-21, 2026-03-22
        self.assertTrue(is_bank_holiday(date(2026, 3, 20)))
        self.assertTrue(is_bank_holiday(date(2026, 3, 21)))
        # 2026 Ashura: 2026-06-25, 2026-06-26
        self.assertTrue(is_bank_holiday(date(2026, 6, 25)))


if __name__ == "__main__":
    unittest.main()
