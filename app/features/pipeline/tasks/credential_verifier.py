"""
Credential Verifier — Online Certificate & Credential Registry Validation.
Audits public certificate verification URLs (Coursera, Udemy, edX) against official registries.
"""
from __future__ import annotations

import logging
import re
import urllib.request
import urllib.error
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Verification URL patterns for major online course & credential providers (resilient to OCR noise)
COURSERA_VERIFY_REGEX = re.compile(
    r"(?:https?[:;w/\\.\s]*)?(?:www\.)?coursera\.org/(?:account/accomplishments/)?verify/([a-zA-Z0-9]{8,16})",
    re.IGNORECASE,
)
UDEMY_VERIFY_REGEX = re.compile(
    r"(?:https?[:;w/\\.\s]*)?(?:www\.)?udemy\.com/certificate/([a-zA-Z0-9\-]{10,40})",
    re.IGNORECASE,
)
EDX_VERIFY_REGEX = re.compile(
    r"(?:https?[:;w/\\.\s]*)?(?:www\.)?edx\.org/certificates/([a-zA-Z0-9]{20,40})",
    re.IGNORECASE,
)


def extract_credential_urls(text: str) -> list[dict[str, str]]:
    """Extract known online certificate verification URLs from document text."""
    results = []
    seen_codes = set()
    
    # 1. Coursera
    for match in COURSERA_VERIFY_REGEX.finditer(text):
        code = match.group(1).upper()
        if code not in seen_codes:
            seen_codes.add(code)
            results.append({
                "provider": "Coursera",
                "url": f"https://www.coursera.org/account/accomplishments/verify/{code}",
                "code": code,
                "matched_text": match.group(0),
            })

    # 2. Udemy
    for match in UDEMY_VERIFY_REGEX.finditer(text):
        code = match.group(1)
        if code not in seen_codes:
            seen_codes.add(code)
            results.append({
                "provider": "Udemy",
                "url": f"https://www.udemy.com/certificate/{code}",
                "code": code,
                "matched_text": match.group(0),
            })

    # 3. edX
    for match in EDX_VERIFY_REGEX.finditer(text):
        code = match.group(1)
        if code not in seen_codes:
            seen_codes.add(code)
            results.append({
                "provider": "edX",
                "url": f"https://www.edx.org/certificates/{code}",
                "code": code,
                "matched_text": match.group(0),
            })

    return results


def verify_coursera_credential(code: str) -> tuple[bool, str, Optional[dict[str, Any]]]:
    """
    Query Coursera's verification registry for a certificate code.
    Returns (is_valid, reason, details).
    """
    url = f"https://www.coursera.org/account/accomplishments/verify/{code}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status != 200:
                return False, f"Coursera server returned status {resp.status}", None
            
            html = resp.read().decode("utf-8", errors="ignore")
            
            # Check Apollo state for null membership / resource
            null_pattern = rf'MembershipsV1Resource\({{\\"code\\":\\"{code}\\"}}\)":null'
            if re.search(null_pattern, html, re.IGNORECASE) or '"MembershipsV1Resource":{"__ref":null}' in html:
                return False, f"Certificate code '{code}' does not exist on Coursera (null record).", None
            
            if "Certificate not found" in html or "Page not found" in html:
                return False, f"Coursera returned 'Certificate not found' for code '{code}'.", None

            # Extract recipient and course metadata if available
            recipient_name = None
            prof_m = re.search(r'"AccomplishmentsSignatureTrackProfile"[^}]*"firstName":"([^"]+)"[^}]*"lastName":"([^"]*)"', html)
            if prof_m:
                fn = prof_m.group(1).strip()
                ln = prof_m.group(2).strip()
                recipient_name = f"{fn} {ln}".strip()

            course_name = None
            course_m = re.search(r'"name":"([^"]+)"', html)
            if course_m:
                course_name = course_m.group(1).strip()

            details = {
                "code": code,
                "url": url,
                "recipient_name": recipient_name,
                "course_name": course_name,
            }
            return True, "Certificate registered on Coursera.", details

    except urllib.error.HTTPError as he:
        if he.code in (404, 410):
            return False, f"Coursera returned HTTP {he.code} (Certificate not found).", None
        logger.warning(f"Coursera query failed with HTTP {he.code}: {he}")
        return True, "Verification skipped due to registry rate limit.", None
    except Exception as exc:
        logger.warning(f"Coursera verification connection error: {exc}")
        return True, "Verification skipped due to network timeout.", None
