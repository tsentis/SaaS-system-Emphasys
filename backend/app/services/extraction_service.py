"""Orchestrates the analyze-a-document pipeline.

Loads the stored PDF, extracts text, runs the LLM extractor, persists the resulting
project + partners, and tracks the run in ``analysis_runs`` while moving the document
through processing → done / failed.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai import text as text_util
from app.ai.embedder import Embedder, get_embedder
from app.ai.extractor import AnthropicExtractor, Extractor
from app.core.storage import Storage
from app.models.document import AnalysisRun, Document
from app.models.enrichment import Embedding
from app.models.project import Project
from app.services import project_service


def _store_embedding(
    db: Session, embedder: Embedder, *, tenant_id, project: Project
) -> None:
    chunk = " ".join(filter(None, [project.acronym, project.title, project.summary]))
    if not chunk.strip():
        return
    db.add(
        Embedding(
            tenant_id=tenant_id,
            owner_type="project",
            owner_id=project.id,
            chunk=chunk[:4000],
            vector=embedder.embed(chunk),
        )
    )


def analyze_document(
    db: Session,
    storage: Storage,
    extractor: Extractor,
    *,
    document: Document,
    embedder: Embedder | None = None,
) -> Project:
    """Run extraction for one document. Raises on failure (after recording it)."""
    embedder = embedder or get_embedder()
    model = (
        extractor.model if isinstance(extractor, AnthropicExtractor) else "fake"
    )
    run = AnalysisRun(
        tenant_id=document.tenant_id,
        document_id=document.id,
        model=model,
        prompt_version="v1",
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(run)
    document.status = "processing"
    db.commit()

    try:
        data = storage.get_object(document.s3_key)
        extracted = text_util.extract_text(data)
        project = project_service.persist_extraction(
            db,
            tenant_id=document.tenant_id,
            document_id=document.id,
            extracted=extractor.extract(extracted.full_text),
        )
        _store_embedding(db, embedder, tenant_id=document.tenant_id, project=project)
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        document.status = "done"
        db.commit()
        db.refresh(project)
        return project
    except Exception as exc:  # noqa: BLE001 — record failure then re-raise
        db.rollback()
        run_obj = db.get(AnalysisRun, run.id)
        if run_obj is not None:
            run_obj.status = "failed"
            run_obj.error = str(exc)[:1000]
            run_obj.finished_at = datetime.now(UTC)
        doc_obj = db.get(Document, document.id)
        if doc_obj is not None:
            doc_obj.status = "failed"
        db.commit()
        raise


def analyze_document_by_id(
    db: Session,
    storage: Storage,
    extractor: Extractor,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
) -> Project | None:
    """Entry point usable from a worker: binds tenant, loads the document, analyzes."""
    from app.core.db import bind_tenant

    bind_tenant(db, tenant_id)
    document = db.get(Document, document_id)
    if document is None:
        return None
    return analyze_document(db, storage, extractor, document=document)
