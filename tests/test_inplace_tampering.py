"""
Tests for In-Place Statement Tampering Detection, Magnitude Inflation Analysis,
Universal Reconciliation Sign Convention, and Stage 7 Gating.
"""
from decimal import Decimal
import unittest
from unittest.mock import MagicMock

from app.features.pipeline.tasks.ledger_state_machine import (
    CrossPageLedgerStateMachine,
    analyze_magnitude_pattern,
)
from app.features.pipeline.tasks.inplace_tampering_engine import (
    detect_stream_displacement,
    detect_whiteout_patch,
    detect_incremental_revision_diff,
    detect_comma_inconsistency,
    detect_slot_width_overflow,
)


class TestMagnitudeInflationAndPatterns(unittest.TestCase):
    def test_magnitude_exact_power_of_ten(self):
        pattern, mult = analyze_magnitude_pattern(Decimal("120.00"), Decimal("120000.00"))
        self.assertEqual(pattern, "magnitude_power_of_ten")
        self.assertEqual(mult, Decimal("1000"))

        pattern, mult = analyze_magnitude_pattern(Decimal("955.00"), Decimal("955000.00"))
        self.assertEqual(pattern, "magnitude_power_of_ten")
        self.assertEqual(mult, Decimal("1000"))

        pattern, mult = analyze_magnitude_pattern(Decimal("50.00"), Decimal("5000.00"))
        self.assertEqual(pattern, "magnitude_power_of_ten")
        self.assertEqual(mult, Decimal("100"))

    def test_digits_appended(self):
        pattern, mult = analyze_magnitude_pattern(Decimal("123.00"), Decimal("12399.00"))
        self.assertEqual(pattern, "digits_appended")
        self.assertGreater(mult, Decimal("100"))

    def test_unrelated_values(self):
        pattern, mult = analyze_magnitude_pattern(Decimal("100.00"), Decimal("250.00"))
        self.assertIsNone(pattern)
        self.assertIsNone(mult)


class TestUniversalSignConvention(unittest.TestCase):
    def test_opening_mismatch_sign_convention(self):
        sm = CrossPageLedgerStateMachine(stated_opening=Decimal("120000.00"))
        sm.start_page(1)
        finding = sm.process_opening_row(1, Decimal("120.00"))

        self.assertIsNotNone(finding)
        self.assertEqual(finding["rule_id"], "RULE_PK_OPENING_BALANCE_MISMATCH")
        self.assertEqual(finding["expected_value"], "PKR 120.00")
        self.assertEqual(finding["actual_value"], "PKR 120,000.00")
        self.assertEqual(finding["discrepancy"], "PKR +119,880.00")
        self.assertEqual(finding["pattern"], "magnitude_power_of_ten")
        self.assertEqual(finding["multiplier"], Decimal("1000"))
        self.assertEqual(finding["rule_version"], 2)

    def test_closing_mismatch_sign_convention(self):
        sm = CrossPageLedgerStateMachine(
            stated_opening=Decimal("120.00"),
            stated_closing=Decimal("955000.00"),
        )
        sm.start_page(1)
        sm.process_opening_row(1, Decimal("120.00"))
        sm.process_transaction(
            1, "01/01/2026", "Tx", Decimal("955.00"),
            [(Decimal("835.00"), (0,0,0,0), "835.00"), (Decimal("955.00"), (0,0,0,0), "955.00")]
        )
        sm.end_page(1)
        findings = sm.finalize()

        closing_f = next((f for f in findings if f["rule_id"] == "RULE_PK_CLOSING_BALANCE_MISMATCH"), None)
        self.assertIsNotNone(closing_f)
        self.assertEqual(closing_f["expected_value"], "PKR 955.00")
        self.assertEqual(closing_f["actual_value"], "PKR 955,000.00")
        self.assertEqual(closing_f["discrepancy"], "PKR +954,045.00")
        self.assertEqual(closing_f["pattern"], "magnitude_power_of_ten")
        self.assertEqual(closing_f["multiplier"], Decimal("1000"))
        self.assertEqual(closing_f["rule_version"], 2)


class TestInPlaceTamperingEngine(unittest.TestCase):
    def test_incremental_revision_diff(self):
        clean_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<< /Size 2 >>\nstartxref\n100\n%%EOF\n"
        findings = detect_incremental_revision_diff(clean_pdf)
        self.assertEqual(len(findings), 0)

        tampered_pdf = (
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<< /Size 2 >>\nstartxref\n100\n%%EOF\n"
            b"2 0 obj\n<<>>\nendobj\ntrailer\n<< /Size 3 /Prev 100 >>\nstartxref\n250\n%%EOF\n"
        )
        findings = detect_incremental_revision_diff(tampered_pdf)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "RULE_PDF_INCREMENTAL_REVISION_PREV")
        self.assertEqual(findings[0]["technical_details"]["prev_offsets"], [100])

        linearized_pdf = (
            b"%PDF-1.4\n/Linearized 1.0\n1 0 obj\n<<>>\nendobj\ntrailer\n<< /Size 2 >>\nstartxref\n50\n%%EOF\n"
            b"2 0 obj\n<<>>\nendobj\ntrailer\n<< /Size 3 >>\nstartxref\n150\n%%EOF\n"
        )
        findings = detect_incremental_revision_diff(linearized_pdf)
        self.assertEqual(len(findings), 0)

    def test_whiteout_patch_detection(self):
        page_mock = MagicMock()
        page_mock.get_drawings.return_value = [
            {"fill": (1.0, 1.0, 1.0), "rect": (100, 100, 200, 120), "seqno": 10}
        ]
        page_mock.get_texttrace.return_value = [
            {"seqno": 20, "bbox": (105, 105, 195, 115), "chars": [[ord(c)] for c in "Text On Top"]}
        ]
        findings = detect_whiteout_patch(page_mock, 1)
        self.assertEqual(len(findings), 0)

        page_mock.get_drawings.return_value = [
            {"fill": (1.0, 1.0, 1.0), "rect": (100, 100, 200, 120), "seqno": 15}
        ]
        page_mock.get_texttrace.return_value = [
            {"seqno": 5, "bbox": (105, 105, 195, 115), "chars": [[ord(c)] for c in "Original Text"]},
            {"seqno": 25, "bbox": (105, 105, 195, 115), "chars": [[ord(c)] for c in "Forged Text"]},
        ]
        findings = detect_whiteout_patch(page_mock, 1)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "RULE_INPLACE_WHITEOUT_PATCH")
        self.assertEqual(findings[0]["technical_details"]["text_under"], "Original Text")
        self.assertEqual(findings[0]["technical_details"]["text_over"], "Forged Text")

    def test_comma_inconsistency_detector(self):
        page_mock = MagicMock()
        page_mock.get_text.side_effect = lambda arg=None: (
            "PKR 1,500.00 and PKR120000.00" if arg != "words" else [
                (100, 100, 150, 112, "PKR 1,500.00", 0, 0, 0),
                (200, 100, 250, 112, "PKR120000.00", 0, 0, 0),
                (300, 100, 350, 112, "1788943474.0360272", 0, 0, 0),
            ]
        )
        findings = detect_comma_inconsistency(page_mock, 1, bank_code="MEEZAN")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "RULE_INPLACE_COMMA_FORMAT_INCONSISTENCY")
        self.assertEqual(findings[0]["technical_details"]["unformatted_amount"], "120000.00")
        self.assertEqual(findings[0]["technical_details"]["expected_format"], "120,000.00")

    def test_slot_width_overflow(self):
        page_mock = MagicMock()
        page_mock.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [
                                {"text": "PKR 120.00", "bbox": (100.0, 150.0, 132.0, 160.0)}
                            ]
                        }
                    ],
                }
            ]
        }
        findings = detect_slot_width_overflow(page_mock, 1, bank_code="MEEZAN")
        self.assertEqual(len(findings), 0)

        page_mock.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [
                                {"text": "PKR 120000.00", "bbox": (100.0, 150.0, 147.5, 160.0)}
                            ]
                        }
                    ],
                }
            ]
        }
        findings = detect_slot_width_overflow(page_mock, 1, bank_code="MEEZAN")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "RULE_INPLACE_SLOT_WIDTH_OVERFLOW")
        self.assertEqual(findings[0]["technical_details"]["width_pts"], 47.5)


if __name__ == "__main__":
    unittest.main()
