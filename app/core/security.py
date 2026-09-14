"""
DeepTrace — Security Utilities
JWT encoding/decoding, bcrypt password hashing, API key generation and verification.
"""

import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

# ── Password hashing ─────────────────────────────────────────────────────────

def hash_password(plaintext: str) -> str:
    """Bcrypt hash a plaintext password directly using bcrypt library."""
    pwd_bytes = plaintext.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    pwd_bytes = plaintext.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire, "type": "access", "jti": secrets.token_urlsafe(16)}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create a signed JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {"sub": subject, "exp": expire, "type": "refresh", "jti": secrets.token_urlsafe(16)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    """SHA-256 hash a session or API token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── API Key generation ────────────────────────────────────────────────────────

_ALPHABET = string.ascii_letters + string.digits

def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        (plaintext_key, key_prefix, key_hash)
        - plaintext_key: shown to the user ONCE — never stored
        - key_prefix:    first 8 chars, stored in DB for identification
        - key_hash:      SHA-256 of plaintext, stored in DB for verification
    """
    random_part = "".join(secrets.choice(_ALPHABET) for _ in range(40))
    plaintext = f"{settings.api_key_prefix}{random_part}"
    prefix = plaintext[:8]
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, prefix, key_hash


def verify_api_key(plaintext: str, stored_hash: str) -> bool:
    """Verify a plaintext API key against its stored SHA-256 hash."""
    candidate_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return secrets.compare_digest(candidate_hash, stored_hash)


# ── Document integrity ────────────────────────────────────────────────────────

def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of binary data (for document custody locking)."""
    return hashlib.sha256(data).hexdigest()


def compute_md5(data: bytes) -> str:
    """Compute MD5 hash of binary data (secondary integrity check)."""
    return hashlib.md5(data).hexdigest()


def detect_file_mime_type(data: bytes) -> str | None:
    """Detect MIME type from file magic bytes to prevent extension spoofing."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    return None

