"""Documents router — nested under /api/v1/investigations/{investigation_id}/documents."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from prisma import Prisma

from app.db.client import get_db_dep
from app.features.auth.dependencies import get_current_user
from app.features.documents import schemas, service
from app.features.investigations.dependencies import get_investigation

router = APIRouter()


@router.post("/{investigation_id}/documents", response_model=schemas.DocumentResponse,
             status_code=201, summary="Upload a document to an investigation")
async def upload_document(
    investigation=Depends(get_investigation),
    file: UploadFile = File(...),
    document_type: str = Form(default="BANK_STATEMENT"),
    user=Depends(get_current_user),
    request: Request = None,
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """
    Ingest a document into an investigation:
    Computes SHA-256 fingerprint, stores immutable custody clone,
    and renders 150 DPI page preview images for the forensic canvas.
    """
    data = await file.read()
    ip = request.client.host if request and request.client else None
    return await service.upload_document(
        db=db,
        investigation=investigation,
        filename=file.filename or "document.pdf",
        data=data,
        document_type=document_type,
        actor_id=user.id if user else None,
        ip_address=ip,
    )


@router.get("/{investigation_id}/documents", response_model=list[schemas.DocumentResponse],
            summary="List documents in an investigation")
async def list_documents(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None
):
    """List all documents uploaded to this investigation."""
    return await service.list_documents(db, investigation.organizationId, investigation.id)


@router.get("/{investigation_id}/documents/{document_id}", response_model=schemas.DocumentDetailResponse,
            summary="Get document detail with rendered pages and custody history")
async def get_document(
    document_id: str,
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None
):
    """Fetch complete document detail including page image dimensions and custody log."""
    doc = await service.get_document(db, investigation.organizationId, document_id)
    pages = await service.list_pages(db, investigation.organizationId, document_id)
    custody = await service.get_custody_chain(db, investigation.organizationId, investigation.id)
    doc_dict = doc.model_dump() if hasattr(doc, "model_dump") else doc.__dict__
    doc_dict["pages"] = pages
    doc_dict["custody_events"] = custody
    return doc_dict


@router.get("/{investigation_id}/documents/{document_id}/pages",
            response_model=list[schemas.DocumentPageResponse],
            summary="Get per-page data with pre-signed image URLs")
async def get_pages(
    document_id: str,
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None
):
    """Fetch all rendered page objects with image URLs for bounding box display."""
    return await service.list_pages(db, investigation.organizationId, document_id)


@router.get("/{investigation_id}/documents/{document_id}/metadata",
            response_model=schemas.DocumentMetadataResponse,
            summary="Get extracted PDF metadata for a document")
async def get_metadata(
    document_id: str,
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None
):
    """Get structural metadata extracted from the document."""
    return await service.get_document_metadata(db, investigation.organizationId, document_id)


@router.get("/{investigation_id}/custody",
            response_model=list[schemas.CustodyEventResponse],
            summary="Get chronological chain-of-custody audit log")
async def get_custody_log(
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None
):
    """Return chronological chain-of-custody log (NIST SP 800-86 / ETO 2002 / PECA 2016)."""
    return await service.get_custody_chain(db, investigation.organizationId, investigation.id)


@router.get("/{investigation_id}/custody/{event_id}/rfc3161-token",
            summary="Download RFC 3161 TimeStampToken (.tst) binary for court submission")
async def download_rfc3161_token(
    event_id: str,
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """Download RFC 3161 TimeStampToken (.tst) binary for court submission under PECA 2016."""
    from fastapi import HTTPException, Response
    import base64

    event = await db.custodyevent.find_first(
        where={"id": event_id, "investigationId": investigation.id}
    )
    if not event:
        raise HTTPException(status_code=404, detail="Custody event not found")

    meta = event.metadata if isinstance(event.metadata, dict) else {}
    rfc_info = meta.get("rfc3161")
    if not rfc_info:
        raise HTTPException(status_code=404, detail="No RFC 3161 timestamp seal attached to this custody event")

    tst_bytes = None
    if rfc_info.get("token_b64"):
        tst_bytes = base64.b64decode(rfc_info["token_b64"])
    elif rfc_info.get("token_storage_path"):
        from app.config import get_settings
        from app.core import storage
        settings = get_settings()
        tst_bytes = storage.get_file(settings.s3_bucket_artifacts, rfc_info["token_storage_path"])

    if not tst_bytes:
        raise HTTPException(status_code=404, detail="RFC 3161 binary token not found in storage")

    return Response(
        content=tst_bytes,
        media_type="application/vnd.etsi.timestamp-token",
        headers={
            "Content-Disposition": f'attachment; filename="deeptrace_rfc3161_{event.id}.tst"'
        },
    )


@router.get("/{investigation_id}/custody/{event_id}/rfc3161-verify",
            response_model=schemas.RFC3161VerificationResponse,
            summary="Verify RFC 3161 TimeStampToken cryptographically against evidence hash")
async def verify_rfc3161_token(
    event_id: str,
    investigation=Depends(get_investigation),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    """Verify an RFC 3161 TimeStampToken cryptographically against the evidence SHA-256 hash."""
    from fastapi import HTTPException
    import base64

    event = await db.custodyevent.find_first(
        where={"id": event_id, "investigationId": investigation.id}
    )
    if not event or not event.sha256Hash:
        raise HTTPException(status_code=404, detail="Custody event or evidence hash not found")

    meta = event.metadata if isinstance(event.metadata, dict) else {}
    rfc_info = meta.get("rfc3161")
    if not rfc_info:
        raise HTTPException(status_code=404, detail="No RFC 3161 timestamp seal attached to this custody event")

    tst_bytes = None
    if rfc_info.get("token_b64"):
        tst_bytes = base64.b64decode(rfc_info["token_b64"])
    elif rfc_info.get("token_storage_path"):
        from app.config import get_settings
        from app.core import storage
        settings = get_settings()
        tst_bytes = storage.get_file(settings.s3_bucket_artifacts, rfc_info["token_storage_path"])

    if not tst_bytes:
        raise HTTPException(status_code=404, detail="RFC 3161 binary token not found")

    from app.core import rfc3161_service
    verified_data = rfc3161_service.verify_timestamp_token_bytes(tst_bytes, event.sha256Hash)

    return schemas.RFC3161VerificationResponse(
        event_id=event.id,
        status=verified_data["status"],
        verified=verified_data["verified"],
        tsa_provider=verified_data["tsa_provider"],
        is_pakistan_accredited=verified_data["is_pakistan_accredited"],
        gen_time=verified_data["gen_time"],
        serial_number=verified_data["serial_number"],
        digest_algorithm=verified_data["digest_algorithm"],
        message_imprint=verified_data["message_imprint"],
        legal_framework=verified_data["legal_framework"],
        tsa_certificate=verified_data.get("tsa_certificate"),
    )


