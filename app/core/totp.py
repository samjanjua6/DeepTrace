"""
DeepTrace — RFC 6238 Time-Based One-Time Password (TOTP) Engine.
Pure Python standard-library implementation with zero external dependencies.
Conforms to RFC 6238 (TOTP) and RFC 4226 (HOTP).
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_totp_secret(num_bytes: int = 20) -> str:
    """Generate a cryptographically secure 160-bit Base32 TOTP secret key.
    
    160 bits (20 bytes) is the recommended key length for HMAC-SHA1 in RFC 6238.
    Returns a 32-character uppercase Base32 string (without padding).
    """
    raw_bytes = secrets.token_bytes(num_bytes)
    return base64.b32encode(raw_bytes).decode("ascii").rstrip("=")


def generate_totp_uri(secret: str, email: str, issuer: str = "DeepTrace") -> str:
    """Generate an otpauth:// URI for enrollment in authenticator apps.
    
    Compatible with Google Authenticator, Microsoft Authenticator, 1Password, etc.
    """
    clean_secret = secret.strip().replace(" ", "").upper()
    label = f"{issuer}:{email}"
    encoded_label = quote(label)
    encoded_issuer = quote(issuer)
    return (
        f"otpauth://totp/{encoded_label}"
        f"?secret={clean_secret}&issuer={encoded_issuer}&algorithm=SHA1&digits=6&period=30"
    )


def get_totp_code(secret: str, timestamp: int | None = None, time_step: int = 30) -> str:
    """Generate a 6-digit decimal TOTP code for a given timestamp (default: current time)."""
    if timestamp is None:
        timestamp = int(time.time())
    
    clean_secret = secret.strip().replace(" ", "").upper()
    missing_padding = len(clean_secret) % 8
    if missing_padding:
        clean_secret += "=" * (8 - missing_padding)
        
    key = base64.b32decode(clean_secret, casefold=True)
    counter = timestamp // time_step
    
    # Pack counter as 8-byte big-endian integer
    msg = struct.pack(">Q", counter)
    
    # Compute HMAC-SHA1
    hmac_digest = hmac.new(key, msg, hashlib.sha1).digest()
    
    # Dynamic truncation (RFC 4226 Section 5.4)
    offset = hmac_digest[-1] & 0x0F
    code_int = (
        struct.unpack(">I", hmac_digest[offset : offset + 4])[0] & 0x7FFFFFFF
    ) % 1000000
    
    return f"{code_int:06d}"


def verify_totp(
    secret: str | None,
    code: str | None,
    window: int = 1,
    time_step: int = 30,
) -> bool:
    """Verify a user-provided 6-digit TOTP code against a Base32 secret.
    
    Args:
        secret: Base32 secret string.
        code: User-supplied 6-digit code string.
        window: Drift tolerance window. 1 means ±1 time-step (±30 seconds, 90s total window).
        time_step: TOTP interval in seconds (default: 30).
        
    Returns:
        True if the code matches any interval within the window, False otherwise.
    """
    if not secret or not code:
        return False
        
    clean_code = code.strip().replace(" ", "")
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False
        
    current_time = int(time.time())
    
    for offset in range(-window, window + 1):
        test_time = current_time + (offset * time_step)
        expected_code = get_totp_code(secret, timestamp=test_time, time_step=time_step)
        if secrets.compare_digest(clean_code, expected_code):
            return True
            
    return False
