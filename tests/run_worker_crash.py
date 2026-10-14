"""Host-side crash drill for the named disposable verification worker only."""
import json
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

BASE = 'http://localhost:48091'
WORKER = 'semantic-finalise-drill-worker'


def status(doc_id):
    with urllib.request.urlopen(BASE + '/documents/' + doc_id) as response:
        return json.load(response)


ids = []
for n in range(3):
    boundary = 'probe' + uuid.uuid4().hex
    content = ('Crash recovery verification uses retry-safe document ingestion. ' * 1500).encode()
    payload = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="crash-probe-{n}.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()
               + content + f'\r\n--{boundary}--\r\n'.encode())
    request = urllib.request.Request(BASE + '/documents', data=payload,
                                    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(request) as response:
        ids.append(json.load(response)['id'])
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    before = [status(i) for i in ids]
    if any(d['status'] == 'processing' for d in before):
        break
    time.sleep(0.1)
assert any(d['status'] == 'processing' for d in before), before
subprocess.run(['docker', 'kill', WORKER], check=True)
subprocess.run(['docker', 'start', WORKER], check=True)
deadline = time.monotonic() + 180
while time.monotonic() < deadline:
    after = [status(i) for i in ids]
    if all(d['status'] == 'done' for d in after):
        break
    time.sleep(1)
assert all(d['status'] == 'done' for d in after), after
result = {'worker_container': WORKER, 'visibility_timeout_seconds': 10,
          'before_sigkill': before, 'after_restart': after,
          'all_recovered': True, 'scope': 'disposable database and Redis instance'}
Path('docs/verification/worker-crash.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
