"""Submit to the real HTTP API while the disposable Redis broker is stopped."""
import json
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select
from app.db import SessionLocal
from app.models import DocStatus, Document
from app.config import get_settings

name = 'broker-failure-' + uuid.uuid4().hex + '.txt'
with httpx.Client(base_url='http://localhost:8000', timeout=60) as client:
    response = client.post('/documents', files={'file': (name, b'Broker recovery verification document.', 'text/plain')})
    assert response.status_code == 503, response.text
with SessionLocal() as db:
    doc = db.scalar(select(Document).where(Document.filename == name))
    assert doc.status == DocStatus.failed
    raw = Path(get_settings().upload_dir) / f'{doc.id}.txt'
    assert raw.is_file()
    result = {'id': str(doc.id), 'http_status': 503, 'document_status': doc.status.value,
              'staging_retained_for_ambiguous_delivery': True, 'real_broker_outage': True}
    Path('/app/docs/verification/broker-failure.json').write_text(json.dumps(result, indent=2))
    print(result)
