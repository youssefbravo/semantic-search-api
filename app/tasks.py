import logging
import os

from sqlalchemy import delete

from .celery_app import celery_app
from .chunking import chunk_text
from .db import SessionLocal
from .embeddings import embed_passages
from .models import Chunk, DocStatus, Document
from .parsing import extract_text

logger = logging.getLogger(__name__)


@celery_app.task(
    name="ingest_document",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=2,
)
def ingest_document(self, document_id: str, raw_path: str) -> None:
    """Background ingestion: parse -> chunk -> embed -> store.

    Runs off the request path so uploads return immediately (202). Each stage
    updates the document row so the client can poll GET /documents/{id}.
    Raw bytes are read from a shared upload volume rather than passed through the
    broker (brokers are for small messages, not file payloads).
    """
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            logger.error("Document %s vanished before ingestion", document_id)
            return
        if doc.status == DocStatus.done:
            logger.info(
                "Document %s already ingested; skipping duplicate delivery",
                document_id,
            )
            return

        doc.status = DocStatus.processing
        doc.error = None
        db.commit()

        with open(raw_path, "rb") as f:
            data = f.read()
        text = extract_text(data, doc.content_type, doc.filename)

        chunks = chunk_text(text)
        if not chunks:
            doc.num_chunks = 0
            doc.status = DocStatus.done
            db.commit()
            logger.warning("Document %s produced no chunks (empty text)", document_id)
            _remove_staged_file(raw_path)
            return

        vectors = embed_passages([c.content for c in chunks])
        db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
        db.add_all(
            [
                Chunk(
                    document_id=doc.id,
                    chunk_index=i,
                    content=c.content,
                    token_count=c.token_count,
                    embedding=v,
                )
                for i, (c, v) in enumerate(zip(chunks, vectors))
            ]
        )
        doc.num_chunks = len(chunks)
        doc.status = DocStatus.done
        db.commit()
        logger.info("Ingested %s: %d chunks", document_id, len(chunks))
        _remove_staged_file(raw_path)

    except Exception as exc:  # noqa: BLE001 - we record + re-raise for Celery retry
        db.rollback()
        if self.request.retries >= self.max_retries:
            doc = db.get(Document, document_id)
            if doc is not None:
                doc.status = DocStatus.failed
                doc.error = str(exc)[:1000]
                doc.num_chunks = 0
                db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
                db.commit()
            _remove_staged_file(raw_path)
        logger.exception("Ingestion failed for %s", document_id)
        raise
    finally:
        db.close()


def _remove_staged_file(raw_path: str) -> None:
    try:
        os.remove(raw_path)
    except OSError:
        pass
