"""Documents router — nested under /api/v1/investigations/{investigation_id}/documents."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
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
    document_type: str = Form(default="OTHER"),
    db: Annotated[Prisma, Depends(get_db_dep)] = None,
):
    data = await file.read()
    # TODO: call service.upload_document(...)
    raise NotImplementedError


@router.get("/{investigation_id}/documents", response_model=list[schemas.DocumentResponse],
            summary="List documents in an investigation")
async def list_documents(investigation=Depends(get_investigation), db: Annotated[Prisma, Depends(get_db_dep)] = None):
    # TODO: db.document.find_many(where={"investigationId": investigation.id})
    raise NotImplementedError


@router.get("/{investigation_id}/documents/{document_id}/metadata",
            response_model=schemas.DocumentMetadataResponse,
            summary="Get extracted PDF metadata for a document")
async def get_metadata(document_id: str, investigation=Depends(get_investigation),
                       db: Annotated[Prisma, Depends(get_db_dep)] = None):
    return await service.get_document_metadata(db, document_id)


@router.get("/{investigation_id}/documents/{document_id}/pages",
            response_model=list[schemas.DocumentPageResponse],
            summary="Get per-page data with pre-signed image URLs")
async def get_pages(document_id: str, investigation=Depends(get_investigation),
                    db: Annotated[Prisma, Depends(get_db_dep)] = None):
    return await service.list_pages(db, document_id)
