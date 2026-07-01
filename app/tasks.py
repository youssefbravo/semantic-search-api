import logging
import os

from .celery_app import celery_app
from .chunking import chunk_text
from .db import SessionLocal
from .embeddings import embed_passages
from .models import Chunk, DocStatus, Document
from .parsing import extract_text

logger = logging.getLogger(__name__)


@celery_app.task(name="ingest_document", bind=True, max_retries=2)
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

        doc.status = DocStatus.processing
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
            return

        vectors = embed_passages([c.content for c in chunks])
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

    except Exception as exc:  # noqa: BLE001 - we record + re-raise for Celery retry
        db.rollback()
        doc = db.get(Document, document_id)
        if doc is not None:
            doc.status = DocStatus.failed
            doc.error = str(exc)[:1000]
            db.commit()
        logger.exception("Ingestion failed for %s", document_id)
        raise
    finally:
        db.close()
        try:
            os.remove(raw_path)  # best-effort cleanup of staged upload
        except OSError:
            pass
