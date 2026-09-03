"""
Documents service — upload, SHA-256 hashing, custody lock, S3 storage.
TODO: Implement each function stub.
"""
from prisma import Prisma

from app.core import security, storage
from app.config import get_settings

settings = get_settings()


async def upload_document(db: Prisma, investigation_id: str, filename: str,
                          data: bytes, content_type: str, document_type: str) -> object:
    """
    Upload a document:
    1. Compute SHA-256 + MD5 hashes immediately on raw bytes (ETO 2002)
    2. Write primary copy to S3 documents bucket
    3. Write immutable custody clone to S3 artifacts bucket (never overwritten)
    4. Create Document + CustodyEvent records in DB
    """
    sha256 = security.compute_sha256(data)
    md5 = security.compute_md5(data)

    import uuid
    object_key = f"{investigation_id}/{uuid.uuid4()}/{filename}"
    clone_key = f"custody/{investigation_id}/{sha256}/{filename}"

    # TODO: storage.upload_file(settings.s3_bucket_documents, object_key, data, content_type)
    # TODO: storage.upload_file(settings.s3_bucket_artifacts, clone_key, data, content_type)
    # TODO: db.document.create(...)
    # TODO: db.custodyevent.create(eventType="ACQUIRED", sha256Hash=sha256)
    raise NotImplementedError


async def get_document_metadata(db: Prisma, document_id: str) -> object:
    """Fetch extracted PDF metadata for a document."""
    # TODO: db.documentmetadata.find_unique(where={"documentId": document_id})
    raise NotImplementedError


async def list_pages(db: Prisma, document_id: str) -> list:
    """Return all pages with pre-signed rendered image URLs."""
    # TODO: db.documentpage.find_many(...) + generate_presigned_url per page
    raise NotImplementedError
