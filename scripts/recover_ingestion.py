"""Inspect a stuck ingestion and optionally requeue its preserved staged file.

Use a known document ID; does not scan/delete corpora or uploads. Repeated delivery
is safe, but operators should diagnose database/broker faults before requeueing.
"""
import argparse
from pathlib import Path

from app.config import get_settings
from app.db import SessionLocal
from app.models import DocStatus, Document
from app.tasks import ingest_document


def recover(document_id, requeue):
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if doc is None:
            raise SystemExit('Document not found')
        raw = Path(get_settings().upload_dir) / f'{doc.id}{Path(doc.filename).suffix}'
        print(f'status={doc.status.value} staged_file_exists={raw.is_file()}')
        if not requeue:
            return
        if doc.status == DocStatus.done:
            raise SystemExit('Document already completed; no recovery needed')
        if not raw.is_file():
            raise SystemExit('No staged file remains; upload the document again')
        doc.status = DocStatus.pending
        doc.error = None
        db.commit()
        try:
            task = ingest_document.delay(str(doc.id), str(raw))
        except Exception:
            db.rollback()
            db.refresh(doc)
            if doc.status != DocStatus.done:
                doc.status = DocStatus.failed
                doc.error = 'Recovery queue submission failed; staged file retained.'
                db.commit()
            raise
        print(f'queued_task={task.id}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('document_id')
    parser.add_argument('--requeue', action='store_true', help='Explicitly enqueue the preserved file')
    args = parser.parse_args()
    recover(args.document_id, args.requeue)
