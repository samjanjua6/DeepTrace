"""
Tests for PDF Digital Signature & X.509 PKI Certificate Forensic Engine
Validates ETO 2002 (Sections 3 & 29) compliance, cryptographic byte-range tamper detection,
post-signing revision detection, and accredited CA chain verification.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import pkcs7, Encoding
from cryptography import x509
import pymupdf

from app.features.pipeline.tasks.pdf_signature_forensics import (
    inspect_pdf_signatures,
    verify_byte_range_integrity,
    parse_pdf_byte_range,
    extract_der_from_contents,
    parse_pkcs7_signed_data,
)


def _generate_test_cert_and_key(subject_name: str, issuer_name: str, self_signed: bool = False):
    """Helper to generate RSA key and X.509 certificate for testing."""
    key = rsa.generate_private_key(65537, 2048)
    s_name = x509.Name([
        x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, subject_name),
        x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, subject_name),
        x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "PK"),
    ])
    i_name = s_name if self_signed else x509.Name([
        x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, issuer_name),
        x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, issuer_name),
        x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "PK"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(s_name)
        .issuer_name(i_name)
        .public_key(key.public_key())
        .serial_number(1234567890)
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=5))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _create_signed_synthetic_pdf(subject: str = "Meezan Bank Limited", issuer: str = "NIFT e-Sign Root CA", self_signed: bool = False):
    """Construct a minimal valid PDF container with embedded /ByteRange and PKCS#7 /Contents."""
    key, cert = _generate_test_cert_and_key(subject, issuer, self_signed=self_signed)

    part1_base = (
        b"%PDF-1.7\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 45 >>\nstream\n"
        b"BT /F1 12 Tf 72 712 Td (Meezan Bank Account Balance: PKR 150,000) Tj ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /adbe.pkcs7.detached /Name (" + subject.encode() + b") /ByteRange ["
    )

    dummy_builder = pkcs7.PKCS7SignatureBuilder().set_data(b"x").add_signer(cert, key, hashes.SHA256())
    dummy_der = dummy_builder.sign(Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary])
    hex_len = len(dummy_der.hex())

    dummy_br = b"0 000450 005000 000300] /Contents <"
    actual_len1 = len(part1_base) + len(dummy_br)
    actual_off2 = actual_len1 + hex_len + 1

    startxref_offset = actual_off2 + len(b" >>\nendobj\n")
    part3_final = (
        b" >>\nendobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000178 00000 n \n"
        b"0000000299 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n" + str(startxref_offset).encode() + b"\n%%EOF"
    )
    actual_len2 = len(part3_final)

    real_br = f"0 {actual_len1:06d} {actual_off2:06d} {actual_len2:06d}] /Contents <".encode()
    part1_final = part1_base + real_br
    signed_payload = part1_final + part3_final

    real_sig = pkcs7.PKCS7SignatureBuilder().set_data(signed_payload).add_signer(cert, key, hashes.SHA256()).sign(
        Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary]
    )
    full_pdf = part1_final + real_sig.hex().encode() + b">" + part3_final
    byte_range = [0, actual_len1, actual_off2, actual_len2]

    return full_pdf, byte_range, real_sig


def test_genuine_pdf_signature_verification():
    """Verify that a clean signed PDF passes cryptographic verification with 0 risk points and ETO 2002 confirmation."""
    pdf_bytes, byte_range, der_bytes = _create_signed_synthetic_pdf(
        subject="Meezan Bank Limited",
        issuer="NIFT e-Sign Root CA",
        self_signed=False,
    )

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    res = inspect_pdf_signatures(pdf_bytes, doc)

    assert res["has_signatures"] is True
    assert res["signature_count"] == 1
    assert res["overall_status"] == "VALID"
    assert res["eto_2002_compliance"]["section_29_presumption"] == "CONFIRMED_VALID"

    # Should contain RULE_PDF_SIGNATURE_VALID
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "RULE_PDF_SIGNATURE_VALID" in rule_ids
    assert "RULE_PDF_SIGNATURE_INVALIDATED" not in rule_ids


def test_tampered_pdf_signature_invalidation():
    """Verify that altering even 1 character in the PDF invalidates the signature under ETO 2002 §29 with CRITICAL severity."""
    pdf_bytes, byte_range, der_bytes = _create_signed_synthetic_pdf(
        subject="Meezan Bank Limited",
        issuer="NIFT e-Sign Root CA",
        self_signed=False,
    )

    # Attacker alters salary from PKR 150,000 to PKR 950,000
    assert b"PKR 150,000" in pdf_bytes
    tampered_bytes = pdf_bytes.replace(b"PKR 150,000", b"PKR 950,000")

    doc = pymupdf.open(stream=tampered_bytes, filetype="pdf")
    res = inspect_pdf_signatures(tampered_bytes, doc)

    assert res["has_signatures"] is True
    assert res["overall_status"] == "INVALIDATED"
    assert res["eto_2002_compliance"]["section_29_presumption"] == "REBUTTED_ALTERED"

    # Must contain RULE_PDF_SIGNATURE_INVALIDATED with CRITICAL severity and 50 points
    invalid_findings = [f for f in res["findings"] if f["rule_id"] == "RULE_PDF_SIGNATURE_INVALIDATED"]
    assert len(invalid_findings) >= 1
    assert invalid_findings[0]["severity"] == "CRITICAL"
    assert invalid_findings[0]["risk_points"] == 50
    assert "ETO 2002" in invalid_findings[0]["title"] or "ETO 2002" in invalid_findings[0]["description"]


def test_post_signing_trailing_byte_injection():
    """Verify detection when unauthorized bytes/revisions are appended after digital signature affixation."""
    pdf_bytes, byte_range, der_bytes = _create_signed_synthetic_pdf()

    # Append 1,024 unauthorized bytes after %%EOF
    trailing_payload = b"\n% Tampered revision: unauthorized trailing object stream\n" + (b"X" * 1000)
    pdf_with_trailing = pdf_bytes + trailing_payload

    doc = pymupdf.open(stream=pdf_with_trailing, filetype="pdf")
    res = inspect_pdf_signatures(pdf_with_trailing, doc)

    assert res["has_signatures"] is True
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "RULE_PDF_SIGNATURE_POST_SIGNING_MODIFICATION" in rule_ids

    mod_finding = next(f for f in res["findings"] if f["rule_id"] == "RULE_PDF_SIGNATURE_POST_SIGNING_MODIFICATION")
    assert mod_finding["severity"] == "CRITICAL"
    assert mod_finding["risk_points"] == 40
    assert mod_finding["technical_details"]["trailing_bytes"] == len(trailing_payload)


def test_self_signed_certificate_flagged():
    """Verify that an unaccredited self-signed digital certificate is flagged as high risk."""
    pdf_bytes, byte_range, der_bytes = _create_signed_synthetic_pdf(
        subject="Fraudulent Bank Entity",
        issuer="Fraudulent Bank Entity",
        self_signed=True,
    )

    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    res = inspect_pdf_signatures(pdf_bytes, doc)

    assert res["has_signatures"] is True
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "RULE_PDF_SIGNATURE_SELF_SIGNED" in rule_ids

    self_signed_finding = next(f for f in res["findings"] if f["rule_id"] == "RULE_PDF_SIGNATURE_SELF_SIGNED")
    assert self_signed_finding["severity"] == "HIGH"
    assert self_signed_finding["risk_points"] == 30


def test_bank_template_signature_stripped():
    """Verify that an unsigned e-statement matching a signing bank template (Meezan Bank) flags signature stripping."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Meezan Bank Limited - Official Electronic Account Statement", fontsize=14)
    page.insert_text((72, 150), "IBAN: PK65MEZN0001020304050607 | Closing Balance: PKR 500,000", fontsize=10)
    unsigned_pdf_bytes = doc.tobytes()

    res = inspect_pdf_signatures(unsigned_pdf_bytes, doc, document_template_bank="Meezan Bank")

    assert res["has_signatures"] is False
    assert res["overall_status"] == "STRIPPED"
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "RULE_PDF_SIGNATURE_STRIPPED" in rule_ids

    stripped_finding = next(f for f in res["findings"] if f["rule_id"] == "RULE_PDF_SIGNATURE_STRIPPED")
    assert stripped_finding["severity"] == "HIGH"
    assert stripped_finding["risk_points"] == 25


def test_parse_byte_range_and_contents_helpers():
    """Verify helper parsing functions handle diverse string and list formats."""
    assert parse_pdf_byte_range("[0 100 200 50]") == [0, 100, 200, 50]
    assert parse_pdf_byte_range([0, 100, 200, 50]) == [0, 100, 200, 50]
    assert parse_pdf_byte_range("invalid") == []

    assert extract_der_from_contents("<414243>") == b"ABC"
    assert extract_der_from_contents(b"raw") == b"raw"
    assert extract_der_from_contents(None) is None
