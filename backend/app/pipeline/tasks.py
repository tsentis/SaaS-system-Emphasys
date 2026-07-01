"""Celery tasks for the asynchronous extraction pipeline.

The API can enqueue ``analyze_document_task`` to run extraction off the request path.
The task builds its own DB session, storage, and extractor, then delegates to the
extraction service.
"""

import uuid

from app.pipeline.celery_app import celery_app


@celery_app.task(name="analyze_document")
def analyze_document_task(tenant_id: str, document_id: str) -> str | None:
    from app.ai.extractor import get_extractor
    from app.core.db import SessionLocal
    from app.core.storage import get_storage
    from app.services import extraction_service

    db = SessionLocal()
    try:
        project = extraction_service.analyze_document_by_id(
            db,
            get_storage(),
            get_extractor(),
            tenant_id=uuid.UUID(tenant_id),
            document_id=uuid.UUID(document_id),
        )
        return str(project.id) if project else None
    finally:
        db.close()
