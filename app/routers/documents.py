import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import DocStatus, Document
from ..schemas import DocumentCreatedResponse, DocumentStatusResponse
from ..tasks import ingest_document

settings = get_settings()
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentCreatedResponse, status_code=202)
def upload_document(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> DocumentCreatedResponse:
    """Accept a PDF/text document, persist it, and enqueue background ingestion.

    Returns 202 immediately — the heavy work (parse/chunk/embed) happens in the
    Celery worker so the request never blocks on the embedding model.
    """
    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit"
        )

    doc = Document(
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        status=DocStatus.pending,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Stage raw bytes on the shared upload volume for the worker to read.
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(doc.filename)[1]
    raw_path = os.path.join(settings.upload_dir, f"{doc.id}{ext}")
    with open(raw_path, "wb") as f:
        f.write(data)

    ingest_document.delay(str(doc.id), raw_path)

    return DocumentCreatedResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        message="Accepted. Poll GET /documents/{id} for ingestion status.",
    )


@router.get("/{document_id}", response_model=DocumentStatusResponse)
def get_document(
    document_id: uuid.UUID, db: Session = Depends(get_db)
) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
