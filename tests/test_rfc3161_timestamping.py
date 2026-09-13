"""
Tests for RFC 3161 Cryptographic Timestamping Authority (TSA) Service.
Validates PECA 2016 (Sections 13, 14, 33, 34, 38 & 39), ETO 2002, and QSO 1984 Art 164 compliance,
RFC 3161 TimeStampToken construction, tamper-evident digest verification, and offline fallback.
"""

from datetime import datetime, timezone
import hashlib
import os
import pytest
from asn1crypto import tsp

from app.core import rfc3161_service
from app.config import get_settings

settings = get_settings()


def test_rfc3161_request_der_generation():
    """Verify that build_timestamp_request generates a compliant RFC 3161 TimeStampReq DER."""
    doc_bytes = b"Bank Alfalah Official Account Statement - Balance PKR 750,000"
    digest = hashlib.sha256(doc_bytes).digest()
    nonce = 1234567890987654321

    req_der = rfc3161_service.build_timestamp_request(digest, algo="sha256", nonce=nonce)
    assert isinstance(req_der, bytes)
    assert len(req_der) > 0

    # Parse with asn1crypto
    parsed_req = tsp.TimeStampReq.load(req_der)
    assert parsed_req["version"].native in (1, "v1")
    assert parsed_req["cert_req"].native is True
    assert parsed_req["nonce"].native == nonce
    assert parsed_req["message_imprint"]["hash_algorithm"]["algorithm"].native == "sha256"
    assert parsed_req["message_imprint"]["hashed_message"].native == digest


def test_rfc3161_offline_token_generation_and_verification():
    """Verify that offline station token generation produces a valid, cryptographically verifiable TimeStampToken."""
    doc_bytes = b"Meezan Bank E-Statement - Acquired Evidence Data"
    digest = hashlib.sha256(doc_bytes).digest()

    token_info = rfc3161_service.generate_offline_timestamp_token(digest)

    assert token_info["status"] == "SEALED"
    assert token_info["verified"] is True
    assert token_info["is_offline_local_seal"] is True
    assert "DeepTrace Forensic Station Local TSA" in token_info["tsa_provider"]
    assert token_info["message_imprint"] == digest.hex()
    assert token_info["serial_number"] is not None
    assert token_info["gen_time"] is not None
    assert "PECA 2016" in token_info["legal_framework"]
    assert token_info["token_der"] is not None
    assert token_info["token_b64"] is not None

    # Cryptographically verify the binary token
    verify_res = rfc3161_service.verify_timestamp_token_bytes(token_info["token_der"], digest.hex())
    assert verify_res["status"] == "SEALED"
    assert verify_res["verified"] is True
    assert verify_res["message_imprint"] == digest.hex()
    assert verify_res["serial_number"] == token_info["serial_number"]


def test_rfc3161_tamper_detection_mismatch():
    """Verify that verifying a TimeStampToken against a modified evidence hash detects tampering."""
    original_bytes = b"Legitimate Statement: Salary PKR 200,000"
    tampered_bytes = b"Altered Statement: Salary PKR 900,000"

    orig_digest = hashlib.sha256(original_bytes).digest()
    tamp_digest_hex = hashlib.sha256(tampered_bytes).hexdigest()

    token_info = rfc3161_service.generate_offline_timestamp_token(orig_digest)

    # Verify against tampered hash
    verify_res = rfc3161_service.verify_timestamp_token_bytes(token_info["token_der"], tamp_digest_hex)
    assert verify_res["verified"] is False
    assert verify_res["message_imprint"] == orig_digest.hex()
    assert verify_res["expected_imprint"] == tamp_digest_hex
    assert verify_res["message_imprint"] != verify_res["expected_imprint"]


def test_remote_tsa_request_or_safe_fallback():
    """Verify that request_timestamp_token acquires a valid RFC 3161 token with GenTime and serial number."""
    evidence_hash = hashlib.sha256(b"PECA 2016 Section 33 Evidence Fingerprint").hexdigest()

    token_info = rfc3161_service.request_timestamp_token(evidence_hash)

    assert token_info["status"] == "SEALED"
    assert token_info["verified"] is True
    assert token_info["message_imprint"] == evidence_hash
    assert len(token_info["serial_number"]) > 0
    assert len(token_info["gen_time"]) > 0
    assert "token_der" in token_info
    assert len(token_info["token_der"]) > 500


def test_tsa_provider_classification():
    """Verify classification of Pakistani accredited vs global accredited TSAs."""
    # NTC Pakistan
    provider, is_pk = rfc3161_service._classify_tsa_provider(
        subject_cn="NTC National PKI TSA",
        subject_org="National Telecommunication Corporation",
        issuer_cn="NTC Root CA",
        issuer_org="NTC",
        url="http://tsa.ntc.net.pk",
    )
    assert is_pk is True
    assert "National Telecommunication Corporation" in provider

    # NIFT Pakistan
    provider, is_pk = rfc3161_service._classify_tsa_provider(
        subject_cn="NIFT e-Sign TSA",
        subject_org="NIFT",
        issuer_cn="ECAC Root CA",
        issuer_org="ECAC",
        url="http://tsa.nift.pk",
    )
    assert is_pk is True
    assert "NIFT" in provider

    # DigiCert Global
    provider, is_pk = rfc3161_service._classify_tsa_provider(
        subject_cn="DigiCert Timestamp Responder",
        subject_org="DigiCert, Inc.",
        issuer_cn="DigiCert Root",
        issuer_org="DigiCert Inc",
        url="http://timestamp.digicert.com",
    )
    assert is_pk is False
    assert "DigiCert" in provider


def test_offline_fallback_when_remote_fails(monkeypatch):
    """Verify that when remote TSAs are unreachable, request_timestamp_token safely falls back to local station TSA."""
    # Force preferred_url to an unroutable address with 0.1s timeout
    broken_url = "http://192.0.2.1:9999/tsa"
    monkeypatch.setattr(settings, "tsa_primary_url", broken_url)
    monkeypatch.setattr(settings, "tsa_fallback_urls", [])
    monkeypatch.setattr(settings, "tsa_timeout_seconds", 0.1)

    evidence_hash = hashlib.sha256(b"Air-gapped military/banking evidence lock").hexdigest()
    res = rfc3161_service.request_timestamp_token(evidence_hash, preferred_url=broken_url)

    assert res["status"] == "SEALED"
    assert res["verified"] is True
    assert res["is_offline_local_seal"] is True
    assert "DeepTrace Forensic Station Local TSA" in res["tsa_provider"]


def test_court_dossier_pdf_peca2016_regulatory_disclosures():
    """Verify that court report service contains updated PECA 2016 §33/§34 and RFC 3161 disclosures."""
    import inspect
    from app.features.reports import service as report_service

    src = inspect.getsource(report_service.generate_report)
    assert "PECA 2016" in src
    assert "RFC 3161" in src
    assert "DIGITAL CHAIN OF CUSTODY" in src
    assert "_rfc3161.tst" in src

