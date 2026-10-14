"""Submit the transient-failure probe to the test-only fault worker."""
import json
from pathlib import Path

import httpx
from scripts.verify_worker import wait

with httpx.Client(base_url='http://localhost:8000', timeout=30) as client:
    response = client.post('/documents', files={'file': (
        'transient-worker-probe.txt', b'Transient failure verification succeeds after a retry.', 'text/plain')})
    response.raise_for_status()
    doc = wait(client, response.json()['id'])
    assert doc['status'] == 'done', doc
    Path('/app/docs/verification/transient-retry.json').write_text(json.dumps(doc, indent=2))
    print(doc)
