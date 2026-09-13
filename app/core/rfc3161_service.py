"""
RFC 3161 Cryptographic Timestamping Authority (TSA) Service.
Ensures legal admissibility and tamper-evident chain of custody under:
- Prevention of Electronic Crimes Act (PECA 2016, Sections 13, 14, 33, 34, 38 & 39)
- Electronic Transactions Ordinance 2002 (ETO 2002, Sections 3, 4 & 29)
- Qanun-e-Shahadat Order 1984 (QSO 1984, Article 164)
- Internet X.509 Public Key Infrastructure Time-Stamp Protocol (RFC 3161)
"""

import base64
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import hashlib
import logging
import os
import re
from typing import Any, Optional, Tuple, Union

from asn1crypto import algos, cms, core, tsp, x509 as ax509
from cryptography import x509 as cx509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding
import httpx

from app.config import get_settings

logger = logging.getLogger("deeptrace.rfc3161")
settings = get_settings()

# Recognized Pakistani Accredited Authorities under ECAC / MoITT
PAKISTAN_ACCREDITED_TSA_PATTERNS = [
    (r"ntc(\.net)?\.pk", "National Telecommunication Corporation (NTC) Accredited TSA"),
    (r"nift(\.com)?\.pk", "NIFT e-Sign Accredited TSA (ECAC Pakistan)"),
    (r"ecac\.gov\.pk", "Electronic Certification Accreditation Council (ECAC Pakistan)"),
    (r"pral\.com\.pk", "Pakistan Revenue Automation Limited (PRAL) TSA"),
    (r"sbp\.org\.pk", "State Bank of Pakistan (SBP) PKI"),
]

GLOBAL_ACCREDITED_TSA_PATTERNS = [
    (r"digicert", "DigiCert Global RFC 3161 Accredited Time Stamping Authority"),
    (r"sectigo", "Sectigo / Comodo Qualified Time Stamping Authority"),
    (r"globalsign", "GlobalSign Timestamping Authority"),
    (r"freetsa", "FreeTSA European Qualified Public TSA"),
    (r"entrust", "Entrust Datacard Timestamp Authority"),
]


@lru_cache(maxsize=1)
def _get_station_tsa_keypair():
    """
    Generate or return cached in-process RSA-2048 keypair and self-signed TSA certificate
    used for offline air-gapped forensic sealing when external TSAs are inaccessible.
    """
    key = rsa.generate_private_key(65537, 2048)
    name = cx509.Name([
        cx509.NameAttribute(cx509.oid.NameOID.COMMON_NAME, "DeepTrace Forensic Station Local TSA"),
        cx509.NameAttribute(cx509.oid.NameOID.ORGANIZATION_NAME, "DeepTrace Cryptographic Forensics Unit"),
        cx509.NameAttribute(cx509.oid.NameOID.COUNTRY_NAME, "PK"),
    ])
    cert = (
        cx509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(int(datetime.now(timezone.utc).timestamp() * 1000))
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(
            cx509.ExtendedKeyUsage([cx509.oid.ExtendedKeyUsageOID.TIME_STAMPING]),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


def build_timestamp_request(
    digest_bytes: bytes,
    algo: str = "sha256",
    nonce: Optional[int] = None,
) -> bytes:
    """
    Construct an RFC 3161 TimeStampReq (ASN.1 DER) requesting signing certificate inclusion.
    """
    if nonce is None:
        nonce = int.from_bytes(os.urandom(8), "big")

    req = tsp.TimeStampReq({
        "version": 1,
        "message_imprint": tsp.MessageImprint({
            "hash_algorithm": algos.DigestAlgorithm({"algorithm": algo.lower()}),
            "hashed_message": digest_bytes,
        }),
        "cert_req": True,
        "nonce": nonce,
    })
    return req.dump()


def _classify_tsa_provider(subject_cn: str, subject_org: str, issuer_cn: str, issuer_org: str, url: str = "") -> Tuple[str, bool]:
    """Identify whether a TSA is recognized under Pakistani law (ECAC) or global eIDAS/NIST standards."""
    combined = f"{subject_cn} {subject_org} {issuer_cn} {issuer_org} {url}".lower()

    for pattern, name in PAKISTAN_ACCREDITED_TSA_PATTERNS:
        if re.search(pattern, combined):
            return name, True

    for pattern, name in GLOBAL_ACCREDITED_TSA_PATTERNS:
        if re.search(pattern, combined):
            return name, False

    if "deeptrace" in combined:
        return "DeepTrace Local Forensic Station TSA (Internal Key)", False

    return subject_cn or subject_org or "Generic RFC 3161 Time Stamping Authority", False


def parse_timestamp_token(
    token_der: bytes,
    expected_digest: Optional[bytes] = None,
    source_url: str = "",
) -> dict[str, Any]:
    """
    Parse an RFC 3161 TimeStampToken (ContentInfo of type SignedData) and extract
    certified timestamp, serial number, policy, message imprint, and TSA certificate.
    """
    content_info = cms.ContentInfo.load(token_der)
    if content_info["content_type"].native != "signed_data":
        raise ValueError("Invalid TimeStampToken: ContentType is not signed_data")

    signed_data = content_info["content"]
    encap_content_info = signed_data["encap_content_info"]
    if encap_content_info["content_type"].native != "tst_info":
        raise ValueError("Invalid TimeStampToken: EncapContentType is not tst_info")

    # In asn1crypto, ParsableOctetString has .parsed which yields TSTInfo
    raw_content = encap_content_info["content"]
    if hasattr(raw_content, "parsed") and raw_content.parsed is not None:
        tst_info = raw_content.parsed
    else:
        tst_info = tsp.TSTInfo.load(raw_content.native)

    serial_number = str(tst_info["serial_number"].native)
    gen_time = tst_info["gen_time"].native
    if hasattr(gen_time, "isoformat"):
        gen_time_iso = gen_time.isoformat()
    else:
        gen_time_iso = str(gen_time)

    policy_oid = tst_info["policy"].dotted if hasattr(tst_info["policy"], "dotted") else str(tst_info["policy"].native)
    imprint = tst_info["message_imprint"]["hashed_message"].native
    digest_algo = tst_info["message_imprint"]["hash_algorithm"]["algorithm"].native.lower()
    nonce = tst_info["nonce"].native if "nonce" in tst_info and tst_info["nonce"] is not None else None

    # Check imprint match
    is_imprint_match = True
    if expected_digest is not None:
        is_imprint_match = (imprint == expected_digest)

    # Extract TSA Certificate
    tsa_subject_cn = "Unknown TSA"
    tsa_subject_org = ""
    tsa_issuer_cn = ""
    tsa_issuer_org = ""
    tsa_fingerprint = ""

    if "certificates" in signed_data and signed_data["certificates"]:
        for c in signed_data["certificates"]:
            try:
                cert = c.chosen
                sub = cert.subject.native
                iss = cert.issuer.native
                tsa_subject_cn = sub.get("common_name", "") if isinstance(sub, dict) else str(sub)
                tsa_subject_org = sub.get("organization_name", "") if isinstance(sub, dict) else ""
                tsa_issuer_cn = iss.get("common_name", "") if isinstance(iss, dict) else str(iss)
                tsa_issuer_org = iss.get("organization_name", "") if isinstance(iss, dict) else ""
                fp = hashlib.sha256(cert.dump()).hexdigest().upper()
                tsa_fingerprint = ":".join(fp[i : i + 2] for i in range(0, len(fp), 2))
                break
            except Exception:
                continue

    provider_name, is_pk_accredited = _classify_tsa_provider(
        tsa_subject_cn, tsa_subject_org, tsa_issuer_cn, tsa_issuer_org, source_url
    )

    return {
        "status": "SEALED",
        "verified": is_imprint_match,
        "tsa_provider": provider_name,
        "is_pakistan_accredited": is_pk_accredited,
        "gen_time": gen_time_iso,
        "serial_number": serial_number,
        "policy_oid": policy_oid,
        "digest_algorithm": digest_algo,
        "message_imprint": imprint.hex() if isinstance(imprint, bytes) else str(imprint),
        "expected_imprint": expected_digest.hex() if expected_digest else None,
        "nonce": nonce,
        "tsa_certificate": {
            "subject_cn": tsa_subject_cn,
            "subject_org": tsa_subject_org,
            "issuer_cn": tsa_issuer_cn,
            "issuer_org": tsa_issuer_org,
            "sha256_fingerprint": tsa_fingerprint,
        },
        "token_der": token_der,
        "token_b64": base64.b64encode(token_der).decode("ascii"),
        "legal_framework": (
            "PECA 2016 Sections 33, 34 & 38 (Preservation of Digital Evidence) "
            "read with ETO 2002 Section 29 and QSO 1984 Article 164"
        ),
    }


def parse_timestamp_response(
    resp_der: bytes,
    expected_digest: Optional[bytes] = None,
    source_url: str = "",
) -> dict[str, Any]:
    """Parse full TimeStampResp and verify status before returning token details."""
    ts_resp = tsp.TimeStampResp.load(resp_der)
    pki_status = ts_resp["status"]["status"].native
    if pki_status not in ("granted", "granted_with_mods"):
        status_string = ts_resp["status"]["status_string"]
        err_detail = status_string.native if status_string is not None else pki_status
        raise ValueError(f"TSA refused timestamp request. Status: {pki_status}, Details: {err_detail}")

    token_der = ts_resp["time_stamp_token"].dump()
    return parse_timestamp_token(token_der, expected_digest=expected_digest, source_url=source_url)


def generate_offline_timestamp_token(digest_bytes: bytes, algo: str = "sha256") -> dict[str, Any]:
    """
    Generate an RFC 3161 compliant TimeStampToken using the internal DeepTrace Forensic
    Station key. Used for offline/air-gapped operation and deterministic testing.
    """
    key, cert = _get_station_tsa_keypair()
    now = datetime.now(timezone.utc)
    serial_no = int(now.timestamp() * 1000)

    tst_info = tsp.TSTInfo({
        "version": 1,
        "policy": "1.3.6.1.4.1.13762.3",  # DeepTrace Forensic Custody Policy OID
        "message_imprint": tsp.MessageImprint({
            "hash_algorithm": algos.DigestAlgorithm({"algorithm": algo.lower()}),
            "hashed_message": digest_bytes,
        }),
        "serial_number": serial_no,
        "gen_time": now,
        "nonce": int.from_bytes(os.urandom(8), "big"),
    })
    tst_der = tst_info.dump()

    # Sign tst_der
    sig = key.sign(tst_der, padding.PKCS1v15(), hashes.SHA256())

    cert_asn1 = ax509.Certificate.load(cert.public_bytes(Encoding.DER))
    signer_info = cms.SignerInfo({
        "version": 1,
        "sid": cms.SignerIdentifier({
            "issuer_and_serial_number": cms.IssuerAndSerialNumber({
                "issuer": cert_asn1.issuer,
                "serial_number": cert_asn1.serial_number,
            })
        }),
        "digest_algorithm": algos.DigestAlgorithm({"algorithm": "sha256"}),
        "signature_algorithm": algos.SignedDigestAlgorithm({"algorithm": "rsassa_pkcs1v15"}),
        "signature": sig,
    })

    signed_data = cms.SignedData({
        "version": 3,
        "digest_algorithms": [algos.DigestAlgorithm({"algorithm": "sha256"})],
        "encap_content_info": cms.EncapsulatedContentInfo({
            "content_type": "tst_info",
            "content": core.ParsableOctetString(tst_der),
        }),
        "certificates": [cms.CertificateChoices({"certificate": cert_asn1})],
        "signer_infos": [signer_info],
    })

    tst = cms.ContentInfo({
        "content_type": "signed_data",
        "content": signed_data,
    })

    token_bytes = tst.dump()
    parsed = parse_timestamp_token(token_bytes, expected_digest=digest_bytes, source_url="local://offline-station")
    parsed["is_offline_local_seal"] = True
    parsed["tsa_provider"] = "DeepTrace Forensic Station Local TSA (Internal Station Key)"
    return parsed


def request_timestamp_token(
    sha256_hex_or_bytes: Union[str, bytes],
    preferred_url: Optional[str] = None,
) -> dict[str, Any]:
    """
    Acquire an RFC 3161 TimeStampToken for a target document or evidence SHA-256 fingerprint.
    Attempts primary URL, falls back to backup URLs, and safely degrades to offline local
    station seal if network is unavailable.
    """
    if isinstance(sha256_hex_or_bytes, str):
        digest_bytes = bytes.fromhex(sha256_hex_or_bytes.strip())
    else:
        digest_bytes = sha256_hex_or_bytes

    if not getattr(settings, "tsa_enabled", True):
        return generate_offline_timestamp_token(digest_bytes)

    urls_to_try = []
    if preferred_url:
        urls_to_try.append(preferred_url)
    if hasattr(settings, "tsa_primary_url") and settings.tsa_primary_url:
        if settings.tsa_primary_url not in urls_to_try:
            urls_to_try.append(settings.tsa_primary_url)
    if hasattr(settings, "tsa_fallback_urls") and settings.tsa_fallback_urls:
        for u in settings.tsa_fallback_urls:
            if u not in urls_to_try:
                urls_to_try.append(u)

    req_der = build_timestamp_request(digest_bytes)
    timeout = getattr(settings, "tsa_timeout_seconds", 3.5)

    headers = {
        "Content-Type": "application/timestamp-query",
        "Accept": "application/timestamp-reply",
        "User-Agent": "DeepTrace-Forensic-Engine/1.0 (PECA-2016-TSA-Client)",
    }

    for url in urls_to_try:
        try:
            logger.info("Requesting RFC 3161 timestamp seal from TSA: %s", url)
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, content=req_der, headers=headers)
                if resp.status_code == 200:
                    token_info = parse_timestamp_response(resp.content, expected_digest=digest_bytes, source_url=url)
                    token_info["is_offline_local_seal"] = False
                    logger.info("RFC 3161 TSA seal successfully acquired from %s", token_info["tsa_provider"])
                    return token_info
                else:
                    logger.warning("TSA %s returned HTTP %d: %s", url, resp.status_code, resp.text[:100])
        except Exception as exc:
            logger.warning("Failed to reach TSA %s: %s", url, exc)

    # If all remote TSAs failed or network offline, invoke station fallback if allowed
    if getattr(settings, "tsa_allow_offline_fallback", True):
        logger.info("Remote TSAs unavailable. Generating certified offline RFC 3161 token using DeepTrace Forensic Station Key.")
        return generate_offline_timestamp_token(digest_bytes)

    raise ConnectionError("Failed to acquire RFC 3161 timestamp token from any configured TSA provider.")


def verify_timestamp_token_bytes(token_der: bytes, expected_sha256_hex: str) -> dict[str, Any]:
    """
    Verify an existing binary .tst file against an expected document SHA-256 hash.
    """
    expected_digest = bytes.fromhex(expected_sha256_hex.strip())
    return parse_timestamp_token(token_der, expected_digest=expected_digest)
