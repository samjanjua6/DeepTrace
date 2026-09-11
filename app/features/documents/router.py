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
    """Return chronological chain-of-custody log (NIST SP 800-86 / ETO 2002)."""
    return await service.get_custody_chain(db, investigation.organizationId, investigation.id)


