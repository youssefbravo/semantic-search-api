import os
import secrets
import uuid
import logging

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import DocStatus, Document
from ..schemas import DocumentCreatedResponse, DocumentStatusResponse
from ..tasks import ingest_document

settings = get_settings()
router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


def require_ingest_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.read_only_demo:
        raise HTTPException(status_code=403, detail="Uploads disabled in the public demo")
    if settings.ingest_api_key is None:
        return
    if x_api_key is None or not secrets.compare_digest(
        x_api_key, settings.ingest_api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.post("", response_model=DocumentCreatedResponse, status_code=202)
def upload_document(
    file: UploadFile = File(...),
    _: None = Depends(require_ingest_api_key),
    db: Session = Depends(get_db),
) -> DocumentCreatedResponse:
    """Accept a PDF/text document, persist it, and enqueue background ingestion.

    Returns 202 immediately — the heavy work (parse/chunk/embed) happens in the
    Celery worker so the request never blocks on the embedding model.
    """
    # UploadFile is spooled by Starlette; bound the application-level read too.
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > limit:
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
    ext = os.path.splitext(doc.filename)[1]
    raw_path = os.path.join(settings.upload_dir, f"{doc.id}{ext}")
    try:
        os.makedirs(settings.upload_dir, exist_ok=True)
        with open(raw_path, "wb") as f:
            f.write(data)
        ingest_document.delay(str(doc.id), raw_path)
    except Exception as exc:
        # Broker timeouts are ambiguous: delivery may have succeeded. Keep staged
        # bytes so such a delivery can still finish; never report accepted here.
        db.rollback()
        db.refresh(doc)
        if doc.status != DocStatus.done:
            doc.status = DocStatus.failed
            doc.error = "Staging or queue submission failed; upload again."
            db.commit()
        logger.exception("Unable to submit document %s", doc.id)
        raise HTTPException(status_code=503, detail="Queue submission could not be confirmed") from exc

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
