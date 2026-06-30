"""Document upload and management endpoints."""

import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user, require_roles
from app.core.roles import ADMIN, ANALYST
from app.core.storage import Storage, get_storage
from app.schemas.document import DocumentOut, DownloadUrl, UploadResult
from app.services import audit_service, document_service

router = APIRouter(tags=["documents"])

_DOWNLOAD_EXPIRY = 3600


@router.post("", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    current: CurrentUser = Depends(require_roles(ADMIN, ANALYST)),
) -> UploadResult:
    if file.content_type != document_service.ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only application/pdf is accepted",
        )
    data = file.file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    document, duplicate = document_service.create_document(
        db,
        storage,
        tenant_id=current.tenant_id,
        uploaded_by=current.id,
        filename=file.filename or "document.pdf",
        content_type=file.content_type,
        data=data,
    )
    if not duplicate:
        audit_service.record(
            db,
            tenant_id=current.tenant_id,
            user_id=current.id,
            action="document.upload",
            entity="document",
            entity_id=document.id,
            ip_address=request.client.host if request.client else None,
        )
    return UploadResult(document=DocumentOut.model_validate(document), duplicate=duplicate)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in document_service.list_documents(db)]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
) -> DocumentOut:
    doc = document_service.get_document(db, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return DocumentOut.model_validate(doc)


@router.get("/{document_id}/download", response_model=DownloadUrl)
def get_download_url(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    _: CurrentUser = Depends(get_current_user),
) -> DownloadUrl:
    doc = document_service.get_document(db, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    url = document_service.download_url(storage, doc, expires=_DOWNLOAD_EXPIRY)
    return DownloadUrl(url=url, expires_in=_DOWNLOAD_EXPIRY)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles(ADMIN, ANALYST)),
) -> None:
    doc = document_service.get_document(db, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    document_service.soft_delete(db, doc)
    audit_service.record(
        db,
        tenant_id=current.tenant_id,
        user_id=current.id,
        action="document.delete",
        entity="document",
        entity_id=doc.id,
        ip_address=request.client.host if request.client else None,
    )
