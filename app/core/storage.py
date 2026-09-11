"""
DeepTrace — Object Storage Abstraction (S3 / MinIO + Local Filesystem Fallback)
All file I/O goes through this module.
In production, files are saved to S3/MinIO.
In development, if S3/MinIO is unreachable, it seamlessly falls back to
local filesystem storage under ./storage/ without breaking workflows.
"""
import os
from pathlib import Path
import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()

import time
from typing import Any

# Configurable shared volume path for multi-container deployments
LOCAL_STORAGE_DIR = Path(
    os.environ.get("STORAGE_LOCAL_DIR")
    or os.environ.get("SHARED_STORAGE_PATH")
    or getattr(settings, "storage_local_dir", "storage")
)

_s3_available: bool | None = None
_last_s3_check_time: float = 0.0
_S3_CHECK_TTL_SECONDS: float = 30.0


class StorageError(Exception):
    """Base exception for DeepTrace storage operations."""
    pass


class StorageUploadError(StorageError):
    """Raised when an upload fails, especially in strict remote mode."""
    pass


def _get_client():
    """Create a boto3 S3 client configured for AWS S3 or MinIO."""
    kwargs: dict[str, Any] = dict(
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=Config(signature_version="s3v4", connect_timeout=1, read_timeout=3),
    )
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def _check_s3(force_refresh: bool = False) -> bool:
    """
    Check if remote S3 / MinIO endpoint is reachable.
    Uses head_bucket (IAM-scoped safe) instead of list_buckets (which requires root account permissions).
    Features a 30-second TTL to allow automatic recovery from transient network partitions.
    """
    global _s3_available, _last_s3_check_time
    now = time.time()
    if not force_refresh and _s3_available is not None and (now - _last_s3_check_time < _S3_CHECK_TTL_SECONDS):
        return _s3_available

    try:
        client = _get_client()
        try:
            client.head_bucket(Bucket=settings.s3_bucket_documents)
            _s3_available = True
        except Exception as exc:
            err_str = str(exc)
            if any(code in err_str for code in ["404", "NoSuchBucket", "403", "AccessDenied"]):
                _s3_available = True
            else:
                _s3_available = False
    except Exception:
        _s3_available = False

    _last_s3_check_time = now
    return _s3_available


def upload_file(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """
    Upload bytes to S3/MinIO or fallback to local/shared volume.
    In staging or production (or when storage_strict_remote=True), failure to upload to S3
    raises StorageUploadError immediately to prevent silent multi-replica data partition.
    """
    is_prod_or_strict = (
        settings.app_env in ["staging", "production"]
        or getattr(settings, "storage_strict_remote", False)
    )

    if _check_s3():
        try:
            client = _get_client()
            client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
            # Also populate local/shared read cache
            try:
                local_path = LOCAL_STORAGE_DIR / bucket / key
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(data)
            except Exception:
                pass
            return key
        except Exception as exc:
            if is_prod_or_strict:
                raise StorageUploadError(
                    f"Failed to upload '{key}' to remote bucket '{bucket}' in strict remote mode: {exc}"
                ) from exc

    if is_prod_or_strict:
        raise StorageUploadError(
            f"Remote S3 object storage is unavailable and strict mode is active. Refusing ephemeral container write for '{key}'."
        )

    # Local / shared volume fallback (development / single-node / PVC mount)
    local_path = LOCAL_STORAGE_DIR / bucket / key
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    return key


def download_file(bucket: str, key: str) -> bytes | None:
    """
    Download object from local disk / shared volume or S3/MinIO.
    Implements read-through caching: if downloaded from S3, caches to local/shared disk.
    """
    local_path = LOCAL_STORAGE_DIR / bucket / key
    if local_path.is_file():
        return local_path.read_bytes()

    if _check_s3():
        try:
            client = _get_client()
            response = client.get_object(Bucket=bucket, Key=key)
            data = response["Body"].read()
            # Read-through cache
            try:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(data)
            except Exception:
                pass
            return data
        except Exception:
            return None
    return None


def generate_presigned_url(bucket: str, key: str, expiry_seconds: int = 3600) -> str:
    """
    Generate a pre-signed GET URL or local API storage route.
    Prioritizes remote S3 pre-signed URLs when remote storage is reachable.
    """
    if _check_s3():
        try:
            client = _get_client()
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiry_seconds,
            )
        except Exception:
            pass

    # Local proxy route served by FastAPI
    return f"/api/v1/storage/{bucket}/{key}"


def delete_file(bucket: str, key: str) -> None:
    """Delete an object from local disk and S3/MinIO."""
    local_path = LOCAL_STORAGE_DIR / bucket / key
    if local_path.is_file():
        local_path.unlink()

    if _check_s3():
        try:
            client = _get_client()
            client.delete_object(Bucket=bucket, Key=key)
        except Exception:
            pass


def file_exists(bucket: str, key: str) -> bool:
    """Check if an object exists on local disk or in S3/MinIO."""
    local_path = LOCAL_STORAGE_DIR / bucket / key
    if local_path.is_file():
        return True

    if _check_s3():
        client = _get_client()
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False
    return False


def ensure_buckets_exist() -> None:
    """Provision required storage buckets if MinIO / S3 is reachable."""
    if not _check_s3():
        return
    try:
        client = _get_client()
        for b in [settings.s3_bucket_documents, settings.s3_bucket_artifacts]:
            try:
                client.head_bucket(Bucket=b)
            except Exception:
                try:
                    kwargs: dict[str, Any] = {"Bucket": b}
                    if settings.s3_region and settings.s3_region != "us-east-1" and not settings.s3_endpoint_url:
                        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": settings.s3_region}
                    client.create_bucket(**kwargs)
                except Exception:
                    pass
    except Exception:
        pass


get_file = download_file
get_url = generate_presigned_url


class _StorageFacade:
    upload_file = staticmethod(upload_file)
    download_file = staticmethod(download_file)
    get_file = staticmethod(download_file)
    generate_presigned_url = staticmethod(generate_presigned_url)
    get_url = staticmethod(generate_presigned_url)
    delete_file = staticmethod(delete_file)
    file_exists = staticmethod(file_exists)
    ensure_buckets_exist = staticmethod(ensure_buckets_exist)


storage = _StorageFacade()

__all__ = [
    "upload_file",
    "download_file",
    "get_file",
    "generate_presigned_url",
    "get_url",
    "delete_file",
    "file_exists",
    "ensure_buckets_exist",
    "storage",
    "StorageError",
    "StorageUploadError",
    "LOCAL_STORAGE_DIR",
]

