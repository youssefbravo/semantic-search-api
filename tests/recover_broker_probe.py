"""Recover the real broker-outage fixture once the disposable broker is restored."""
import json
from pathlib import Path
import httpx
from scripts.recover_ingestion import recover
from scripts.verify_worker import wait

path = Path('/app/docs/verification/broker-failure.json')
result = json.loads(path.read_text())
recover(result['id'], True)
with httpx.Client(base_url='http://localhost:8000', timeout=30) as client:
    doc = wait(client, result['id'])
    assert doc['status'] == 'done', doc
result['after_operator_requeue'] = doc
path.write_text(json.dumps(result, indent=2))
print(result)
