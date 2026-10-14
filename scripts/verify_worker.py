"""Exercise the real broker and worker against a disposable stack.

Run after the full benchmark: adds uniquely named demonstration documents.
Never mocks queue submission. Does not reset or delete existing documents.
"""
import argparse
import json
import time
import uuid
import io
from pathlib import Path

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Chunk, Document
from app.tasks import ingest_document


def wait(client, doc_id):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        response = client.get(f'/documents/{doc_id}')
        response.raise_for_status()
        doc = response.json()
        if doc['status'] in ('done', 'failed'):
            return doc
        time.sleep(0.5)
    raise AssertionError(f'Worker timed out for {doc_id}')


def verify(base_url, output):
    token = 'workerprobe' + uuid.uuid4().hex
    with httpx.Client(base_url=base_url, timeout=30) as client:
        body = {'query': token, 'mode': 'keyword', 'k': 5}
        cold = client.post('/search', json=body).json()
        warm = client.post('/search', json=body).json()
        assert cold['count'] == 0
        assert warm['cached'] is True
        uploaded = client.post('/documents', files={'file': ('worker-demo.txt', f'{token} demonstrates reliable document ingestion.'.encode(), 'text/plain')})
        uploaded.raise_for_status()
        doc_id = uploaded.json()['id']
        # Concurrent duplicate delivery while the staged file still exists.
        from app.config import get_settings
        path = str(Path(get_settings().upload_dir) / f'{doc_id}.txt')
        duplicate = ingest_document.delay(doc_id, path)
        done = wait(client, doc_id)
        assert done['status'] == 'done', done
        duplicate.get(timeout=120)
        duplicate2 = ingest_document.delay(doc_id, path)
        duplicate2.get(timeout=120)  # success even after the file has been removed
        with SessionLocal() as db:
            doc = db.get(Document, doc_id)
            chunks = db.scalars(select(Chunk).where(Chunk.document_id == doc.id)).all()
            assert len(chunks) == done['num_chunks'] > 0
            assert len({c.chunk_index for c in chunks}) == len(chunks)
        fresh = client.post('/search', json=body).json()
        assert fresh['cached'] is False and fresh['count'] > 0, fresh
        bad = client.post('/documents', files={'file': ('invalid-worker-demo.pdf', b'not a pdf', 'application/pdf')})
        bad.raise_for_status()
        failed = wait(client, bad.json()['id'])
        assert failed['status'] == 'failed' and failed['num_chunks'] == 0, failed
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({
            NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 72 720 Td (Local PDF parsing verification.) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_response = client.post('/documents', files={'file': (
            'valid-worker-demo.pdf', pdf_bytes.getvalue(), 'application/pdf')})
        pdf_response.raise_for_status()
        pdf_doc = wait(client, pdf_response.json()['id'])
        assert pdf_doc['status'] == 'done' and pdf_doc['num_chunks'] > 0, pdf_doc
        result = {'success': done, 'failed_after_worker_retries': failed,
                  'valid_pdf': pdf_doc,
                  'concurrent_and_completed_redelivery': 'passed',
                  'cache_refresh_after_ingestion': 'passed', 'mocked_queue': False,
                  'keyword_uncached_latency_ms': cold['latency_ms'],
                  'keyword_cached_latency_ms': warm['latency_ms']}
        Path(output).write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://localhost:8000')
    parser.add_argument('--output', default='eval/results/worker-verification.json')
    args = parser.parse_args()
    verify(args.base_url, args.output)
