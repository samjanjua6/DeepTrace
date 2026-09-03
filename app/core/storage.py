"""
DeepTrace — Object Storage Abstraction (S3 / MinIO)
All file I/O goes through this module. Swap S3 for MinIO or GCS without
touching feature code.
"""

import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()


def _get_client():
    """Create a boto3 S3 client configured for AWS S3 or MinIO."""
    kwargs = dict(
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=Config(signature_version="s3v4"),
    )
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def upload_file(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to S3/MinIO. Returns the object key."""
    client = _get_client()
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return key


def download_file(bucket: str, key: str) -> bytes:
    """Download object from S3/MinIO and return raw bytes."""
    client = _get_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def generate_presigned_url(bucket: str, key: str, expiry_seconds: int = 3600) -> str:
    """Generate a pre-signed GET URL for temporary public access."""
    client = _get_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiry_seconds,
    )


def delete_file(bucket: str, key: str) -> None:
    """Delete an object from S3/MinIO."""
    client = _get_client()
    client.delete_object(Bucket=bucket, Key=key)


def file_exists(bucket: str, key: str) -> bool:
    """Check if an object exists in S3/MinIO."""
    client = _get_client()
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except client.exceptions.ClientError:
        return False
