"""
Documents service — upload, SHA-256 custody lock, page image rendering, and custody logging.
Compliant with NIST SP 800-86 and ETO 2002.
"""
import io
import uuid
import fitz  # PyMuPDF
from PIL import Image
from fastapi import HTTPException, status
from prisma import Prisma

from app.config import get_settings
from app.core import security, storage
from app.db.client import set_org_context

settings = get_settings()

HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

VALID_DOCUMENT_TYPES = {
    "BANK_STATEMENT", "SALARY_SLIP", "UTILITY_BILL", "TAX_CERTIFICATE",
    "IDENTITY_DOCUMENT", "COMMERCIAL_INVOICE", "DIGITAL_WALLET_LEDGER", "OTHER"
}


async def upload_document(
    db: Prisma,
    investigation: object,
    filename: str,
    data: bytes,
    document_type: str = "OTHER",
    actor_id: str | None = None,
    ip_address: str | None = None,
) -> object:
    """
    Ingest a document into an investigation:
    1. Validate size and binary magic-bytes.
    2. Check for duplicate upload (investigationId + sha256Hash).
    3. Detect password-encryption (reject if locked).
    4. Compute SHA-256 + MD5 cryptographic custody hashes.
    5. Fast-path multi-modal document classification triage (Stage 0).
    6. Save working copy + immutable custody clone.
    7. Render multi-res page images (150 DPI canvas + 72 DPI thumbnail).
    8. Atomically create Document, DocumentPage, and CustodyEvent records.
    """
    # 1. Size check (Max 50MB)
    max_size = 50 * 1024 * 1024
    if len(data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 50MB (received {len(data) / (1024*1024):.1f}MB)."
        )

    # 2. Magic-byte MIME detection
    mime = security.detect_file_mime_type(data)
    if not mime:
        raise HTTPException(
            status_code=HTTP_422,
            detail="Unsupported or corrupt file format. Only PDF, PNG, JPEG, and WebP are allowed."
        )

    # 3. Cryptographic Hashes
    sha256 = security.compute_sha256(data)
    md5 = security.compute_md5(data)

    # Normalize document type
    raw_type = (document_type or "OTHER").strip().upper()
    if raw_type == "CNIC":
        norm_doc_type = "IDENTITY_DOCUMENT"
    elif raw_type in ("TAX_CHALLAN", "FBR_CHALLAN"):
        norm_doc_type = "TAX_CERTIFICATE"
    elif raw_type in VALID_DOCUMENT_TYPES:
        norm_doc_type = raw_type
    else:
        norm_doc_type = "OTHER"

    # Fast-path multi-modal auto-classification (Stage 0 triage)
    if norm_doc_type in ("OTHER", "AUTO", "AUTO_DETECT"):
        try:
            from app.features.pipeline.tasks.document_classifier import document_classifier
            cls_res = document_classifier.classify_document(data, mime)
            if cls_res and cls_res.document_type in VALID_DOCUMENT_TYPES:
                norm_doc_type = cls_res.document_type
        except Exception:
            pass

    doc_uuid = str(uuid.uuid4())
    primary_key = f"documents/{investigation.id}/{doc_uuid}/{filename}"
    clone_key = f"custody/{investigation.id}/{sha256}/{filename}"
    thumb_key = None

    # 4. Page Rendering & Physical Point Geometry
    pages_to_create = []

    if mime == "application/pdf":
        try:
            pdf_doc = fitz.open(stream=data, filetype="pdf")
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_422,
                detail=f"Corrupt or malformed PDF structure: {str(e)}"
            )

        if pdf_doc.is_encrypted:
            pdf_doc.close()
            raise HTTPException(
                status_code=HTTP_422,
                detail="PASSWORD_PROTECTED_PDF: This PDF is password-protected or encrypted. Please remove password encryption before submitting for digital forensics."
            )

        page_count = len(pdf_doc)
        if page_count == 0:
            pdf_doc.close()
            raise HTTPException(
                status_code=HTTP_422,
                detail="PDF contains 0 pages."
            )

        zoom = 150.0 / 72.0  # 150 DPI render
        mat = fitz.Matrix(zoom, zoom)

        for pno in range(page_count):
            page = pdf_doc[pno]
            rect = page.rect
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")

            page_key = f"documents/{investigation.id}/{doc_uuid}/pages/page_{pno + 1}.png"
            storage.upload_file(settings.s3_bucket_documents, page_key, img_bytes, "image/png")

            if pno == 0:
                thumb_pix = page.get_pixmap(matrix=fitz.Matrix(72.0 / 72.0, 72.0 / 72.0))
                thumb_bytes = thumb_pix.tobytes("png")
                thumb_key = f"documents/{investigation.id}/{doc_uuid}/pages/thumb_1.png"
                storage.upload_file(settings.s3_bucket_documents, thumb_key, thumb_bytes, "image/png")

            pages_to_create.append({
                "pageNumber": pno + 1,
                "widthPx": pix.width,
                "heightPx": pix.height,
                "widthPts": float(rect.width),
                "heightPts": float(rect.height),
                "dpi": 150,
                "renderedImagePath": page_key,
            })

        pdf_doc.close()

    else:
        # Raster Image (PNG / JPEG / WebP)
        try:
            pil_img = Image.open(io.BytesIO(data))
            width_px, height_px = pil_img.size
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_422,
                detail=f"Unable to decode image: {str(e)}"
            )

        page_count = 1
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        page_key = f"documents/{investigation.id}/{doc_uuid}/pages/page_1.png"
        storage.upload_file(settings.s3_bucket_documents, page_key, img_bytes, "image/png")
        thumb_key = page_key

        pages_to_create.append({
            "pageNumber": 1,
            "widthPx": width_px,
            "heightPx": height_px,
            "widthPts": float(width_px * 72 / 96),
            "heightPts": float(height_px * 72 / 96),
            "dpi": 96,
            "renderedImagePath": page_key,
        })

    # 5. Dual Storage Dispatch & DB Transaction under Tenant RLS Context
    from prisma.errors import UniqueViolationError

    async with set_org_context(investigation.organizationId) as tx:
        # Duplicate Check (Idempotency) with active RLS
        existing = await tx.document.find_first(
            where={
                "investigationId": investigation.id,
                "sha256Hash": sha256,
            }
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate document detected. This file (SHA-256: {sha256[:12]}...) is already in this investigation as Document ID: '{existing.id}'."
            )

        storage.upload_file(settings.s3_bucket_documents, primary_key, data, mime)
        storage.upload_file(settings.s3_bucket_artifacts, clone_key, data, mime)

        try:
            doc = await tx.document.create(
                data={
                    "investigationId": investigation.id,
                    "originalFilename": filename,
                    "mimeType": mime,
                    "fileSizeBytes": len(data),
                    "documentType": norm_doc_type,
                    "sha256Hash": sha256,
                    "md5Hash": md5,
                    "storagePath": primary_key,
                    "storagePathClone": clone_key,
                    "thumbnailPath": thumb_key,
                    "pageCount": page_count,
                    "processingStatus": "UPLOADED",
                }
            )
        except UniqueViolationError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate document detected (SHA-256: {sha256[:12]}... already exists in this investigation)."
            )

        # Insert rendered pages
        for p_info in pages_to_create:
            await tx.documentpage.create(
                data={
                    "documentId": doc.id,
                    **p_info,
                }
            )

        # Insert NIST/ETO Custody Event
        await tx.custodyevent.create(
            data={
                "investigationId": investigation.id,
                "eventType": "ACQUISITION",
                "description": f"Document '{filename}' acquired, SHA-256 fingerprinted, and dual custody clones locked.",
                "sha256Hash": sha256,
                "actorId": actor_id,
                "actorType": "user" if actor_id else "system",
                "ipAddress": ip_address,
            }
        )

    return doc


async def list_documents(db: Prisma, org_id: str, investigation_id: str) -> list:
    """Return all documents associated with an investigation under tenant RLS context."""
    async with set_org_context(org_id) as tx:
        return await tx.document.find_many(
            where={"investigationId": investigation_id},
            order={"createdAt": "desc"}
        )


async def get_document(db: Prisma, org_id: str, document_id: str) -> object:
    """Fetch single document detail with its pages under tenant RLS context."""
    async with set_org_context(org_id) as tx:
        doc = await tx.document.find_unique(
            where={"id": document_id},
            include={"pages": True}
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found."
            )
        return doc


async def list_pages(db: Prisma, org_id: str, document_id: str) -> list:
    """Return all pages for a document with accessible URLs under tenant RLS context."""
    async with set_org_context(org_id) as tx:
        pages = await tx.documentpage.find_many(
            where={"documentId": document_id},
            order={"pageNumber": "asc"}
        )
        results = []
        for page in pages:
            p_dict = page.model_dump() if hasattr(page, "model_dump") else page.__dict__
            img_url = None
            if page.renderedImagePath:
                img_url = storage.generate_presigned_url(
                    settings.s3_bucket_documents,
                    page.renderedImagePath,
                    expiry_seconds=3600
                )
            p_dict["rendered_image_url"] = img_url
            results.append(p_dict)
        return results


async def get_custody_chain(db: Prisma, org_id: str, investigation_id: str) -> list:
    """Return chronological chain-of-custody audit log under tenant RLS context."""
    async with set_org_context(org_id) as tx:
        return await tx.custodyevent.find_many(
            where={"investigationId": investigation_id},
            order={"timestamp": "asc"}
        )


async def get_document_metadata(db: Prisma, org_id: str, document_id: str) -> object:
    """Fetch extracted PDF metadata for a document under tenant RLS context."""
    async with set_org_context(org_id) as tx:
        meta = await tx.documentmetadata.find_unique(where={"documentId": document_id})
        if not meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Metadata has not been extracted for this document yet."
            )
        return meta

