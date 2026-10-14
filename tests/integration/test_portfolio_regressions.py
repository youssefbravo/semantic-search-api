import io
import uuid

import pytest
from fastapi import UploadFile, HTTPException
from sqlalchemy import select

from app.chunking import chunk_text, count_tokens
from app.db import SessionLocal
from app.models import DocStatus, Document
from app.routers import documents


def test_overlap_is_inside_budget():
    chunks = chunk_text('Alpha beta gamma delta epsilon. ' * 4 + 'Token ' * 90, 40, 15)
    assert all(c.token_count <= 40 for c in chunks)


def test_single_word_can_exceed_budget():
    chunks = chunk_text('alpha-' * 200, 40, 0)
    assert len(chunks) > 1
    assert all(count_tokens(c.content) <= 40 for c in chunks)


def test_zero_overlap_is_respected():
    chunks = chunk_text('First alpha beta gamma. Second delta epsilon zeta. Third eta theta iota.', 10, 0)
    assert sum(c.content.count('First') for c in chunks) == 1
    assert sum(c.content.count('Second') for c in chunks) == 1


@pytest.mark.parametrize('budget,overlap', [(0, 0), (600, 0), (40, 40), (40, -1)])
def test_invalid_token_budgets_rejected(budget, overlap):
    with pytest.raises(ValueError):
        chunk_text('Hello world.', budget, overlap)


def test_model_limit_counts_query_prefix():
    from app.embeddings import embed_query, get_model
    from app.config import get_settings
    model = get_model()
    query = 'token ' * 505
    assert len(model.tokenizer.encode(query)) <= model.max_seq_length
    assert len(model.tokenizer.encode(get_settings().query_prefix + query)) > model.max_seq_length
    with pytest.raises(ValueError, match='including prefix'):
        embed_query(query)


def test_public_demo_disables_ingestion(monkeypatch):
    monkeypatch.setattr(documents.settings, 'read_only_demo', True)
    with pytest.raises(HTTPException) as exc:
        documents.require_ingest_api_key(None)
    assert exc.value.status_code == 403


def test_upload_read_is_bounded(monkeypatch):
    class BoundedRead(io.BytesIO):
        def read(self, size=-1):
            assert size == documents.settings.max_upload_mb * 1024 * 1024 + 1
            return super().read(size)
    monkeypatch.setattr(documents.settings, 'max_upload_mb', 1)
    with pytest.raises(HTTPException) as exc:
        documents.upload_document(UploadFile(filename='huge.txt', file=BoundedRead(b'x' * (1024 * 1024 + 2))), None, None)
    assert exc.value.status_code == 413


@pytest.mark.integration
def test_submission_failure_is_terminal(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(documents.settings, 'upload_dir', str(tmp_path))
    def unavailable(*args):
        raise ConnectionError('broker unavailable')
    monkeypatch.setattr(documents.ingest_document, 'delay', unavailable)
    name = f'queue-failure-{uuid.uuid4()}.txt'
    response = TestClient(app).post('/documents', files={'file': (name, b'Test content.', 'text/plain')})
    assert response.status_code == 503
    with SessionLocal() as db:
        doc = db.scalar(select(Document).where(Document.filename == name))
        assert doc.status == DocStatus.failed
        assert doc.error
        db.delete(doc)
        db.commit()
