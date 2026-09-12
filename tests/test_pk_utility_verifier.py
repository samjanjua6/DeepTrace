"""
Unit tests for Pakistani Utility Bill Online Authority Registry Verifier.
Validates extraction of DISCO identifiers, reference numbers, HTML response parsing,
and deterministic cross-referencing against live or simulated PITC records.
"""
from unittest.mock import AsyncMock, patch
import pytest

from app.features.pipeline.tasks.pk_utility_verifier import (
    DISCO_PORTAL_URLS,
    UtilityLiveRecord,
    UtilityVerificationResult,
    extract_disco_and_reference,
    parse_pitc_html_bill,
    verify_utility_bill_registry,
)


class TestUtilityVerifier:
    """Test suite for Pakistani utility bill reference extraction and verification."""

    def test_extract_disco_and_reference_gepco(self):
        """Test extraction of GEPCO and formatted reference number."""
        text = "GEPCO ONLINE BILL\nReference No: 16 12632 1059202 U\nConsumer: Muhammad Akram"
        disco, ref_no = extract_disco_and_reference(text)
        assert disco == "gepco"
        assert ref_no == "16126321059202"

    def test_extract_disco_and_reference_lesco(self):
        """Test extraction of LESCO and contiguous 14-digit reference number."""
        text = "LAHORE ELECTRIC SUPPLY COMPANY (LESCO)\nRef: 08123456789012\nPayable: Rs. 12,500"
        disco, ref_no = extract_disco_and_reference(text)
        assert disco == "lesco"
        assert ref_no == "08123456789012"

    def test_extract_disco_other_disco_names(self):
        """Test secondary name recognition for various DISCOs."""
        text = "Multan Electric Power Company bill\nRef: 12 34567 8901234"
        disco, ref_no = extract_disco_and_reference(text)
        assert disco == "mepco"
        assert ref_no == "12345678901234"

        text_fesco = "Faisalabad electric supply\nRef: 99123456789012"
        disco_f, ref_no_f = extract_disco_and_reference(text_fesco)
        assert disco_f == "fesco"
        assert ref_no_f == "99123456789012"

    def test_parse_pitc_html_bill(self):
        """Test parsing of PITC HTML bill format."""
        mock_html = """
        <html>
        <body>
        <div style="font-size:10px">NAME & ADDRESS</div>
        <div>MUHAMMAD AKRAM, SAHNA PHL RURAL</div>
        <div class="slip-main-amount">641</div>
        <div class="slip-matrix-value">AUG 26</div>
        <div class="slip-matrix-value">11 SEP 26</div>
        <div class="slip-late-box">Till 11-09-2026<br/>695</div>
        <div class="slip-late-box">After 11-09-2026<br/>740</div>
        <div>UNITS CONSUMED</div>
        <div>85</div>
        </body>
        </html>
        """ + (" " * 2000)  # Pad length >= 2000

        rec = parse_pitc_html_bill(mock_html, "gepco", "16126321059202")
        assert rec is not None
        assert rec.disco == "gepco"
        assert rec.reference_number == "16126321059202"
        assert "MUHAMMAD AKRAM" in rec.consumer_name
        assert rec.payable_within_due_date == "641"
        assert rec.billing_month == "AUG 26"
        assert rec.due_date == "11 SEP 26"
        assert rec.payable_after_due_date_till == "695"

    @pytest.mark.asyncio
    async def test_verify_utility_bill_registry_match(self):
        """Verify authentic document matching official registry values."""
        doc_text = """
        GEPCO ONLINE ELECTRIC BILL
        REF NO: 16 12632 1059202 U
        CONSUMER: MUHAMMAD AKRAM
        MONTH: AUG 26
        DUE DATE: 11 SEP 26
        PAYABLE WITHIN DUE DATE: 641
        """
        mock_record = UtilityLiveRecord(
            disco="gepco",
            reference_number="16126321059202",
            consumer_name="MUHAMMAD AKRAM",
            billing_month="AUG 26",
            due_date="11 SEP 26",
            payable_within_due_date="641",
        )

        with patch("app.features.pipeline.tasks.pk_utility_verifier.fetch_live_pitc_bill", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_record

            result = await verify_utility_bill_registry(doc_text)
            assert result.status == "MATCH"
            assert result.disco == "gepco"
            assert result.reference_number == "16126321059202"
            assert result.matches["payable_within_due_date"] is True
            assert len(result.discrepancies) == 0
            assert "Official Government Registry Verified" in result.message

    @pytest.mark.asyncio
    async def test_verify_utility_bill_registry_mismatch(self):
        """Verify altered document (tampered amount) triggers MISMATCH with discrepancy."""
        doc_text = """
        GEPCO ONLINE ELECTRIC BILL
        REF NO: 16 12632 1059202 U
        CONSUMER: MUHAMMAD AKRAM
        MONTH: AUG 26
        DUE DATE: 11 SEP 26
        PAYABLE WITHIN DUE DATE: 5641
        """
        mock_record = UtilityLiveRecord(
            disco="gepco",
            reference_number="16126321059202",
            consumer_name="MUHAMMAD AKRAM",
            billing_month="AUG 26",
            due_date="11 SEP 26",
            payable_within_due_date="641",  # Registry has 641, doc forged to 5641
        )

        with patch("app.features.pipeline.tasks.pk_utility_verifier.fetch_live_pitc_bill", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_record

            result = await verify_utility_bill_registry(doc_text)
            assert result.status == "MISMATCH"
            assert result.matches["payable_within_due_date"] is False
            assert len(result.discrepancies) >= 1
            assert "Payable Within Due Date discrepancy" in result.discrepancies[0]
            assert "Government Utility Registry Discrepancy" in result.message

    @pytest.mark.asyncio
    async def test_verify_utility_bill_registry_no_ref(self):
        """Verify document with no reference number returns UNAVAILABLE."""
        doc_text = "Generic text without reference number"
        result = await verify_utility_bill_registry(doc_text)
        assert result.status == "UNAVAILABLE"
        assert "No 14-digit" in result.message
