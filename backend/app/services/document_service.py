"""Document upload, retrieval, and soft deletion.

The session is already tenant-bound by the auth dependency, so the ``do_orm_execute``
guard scopes every query here to the caller's tenant.
"""

import hashlib
import io
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.storage import Storage
from app.models.document import Document

ALLOWED_MIME = "application/pdf"


def _count_pdf_pages(data: bytes) -> int | None:
    try:
        from pypdf import PdfReader

        return len(PdfReader(io.BytesIO(data)).pages)
    except Exception:  # noqa: BLE001 — malformed PDF shouldn't fail the upload
        return None


def find_by_hash(db: Session, sha256: str) -> Document | None:
    return db.execute(
        select(Document).where(
            Document.sha256 == sha256, Document.deleted_at.is_(None)
        )
    ).scalar_one_or_none()


def create_document(
    db: Session,
    storage: Storage,
    *,
    tenant_id: uuid.UUID,
    uploaded_by: uuid.UUID | None,
    filename: str,
    content_type: str,
    data: bytes,
) -> tuple[Document, bool]:
    """Store an uploaded PDF. Returns (document, is_duplicate).

    If an identical file already exists in the tenant, the existing record is returned
    and nothing new is stored.
    """
    sha256 = hashlib.sha256(data).hexdigest()

    existing = find_by_hash(db, sha256)
    if existing is not None:
        return existing, True

    document_id = uuid.uuid4()
    key = f"{tenant_id}/{document_id}/{filename}"
    storage.put_object(key, data, content_type)

    document = Document(
        id=document_id,
        tenant_id=tenant_id,
        filename=filename,
        s3_key=key,
        sha256=sha256,
        mime_type=content_type,
        page_count=_count_pdf_pages(data),
        size_bytes=len(data),
        status="uploaded",
        uploaded_by=uploaded_by,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document, False


def list_documents(db: Session) -> list[Document]:
    return list(
        db.execute(
            select(Document)
            .where(Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        ).scalars()
    )


def get_document(db: Session, document_id: uuid.UUID) -> Document | None:
    doc = db.get(Document, document_id)
    if doc is None or doc.deleted_at is not None:
        return None
    return doc


def soft_delete(db: Session, document: Document) -> None:
    document.deleted_at = datetime.now(UTC)
    db.commit()


def download_url(storage: Storage, document: Document, expires: int = 3600) -> str:
    return storage.presigned_get_url(document.s3_key, expires=expires)
