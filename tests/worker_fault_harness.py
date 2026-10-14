"""Test-only worker that injects one transient embedding failure for a probe.

Run only with a disposable broker/database. Production workers do not import this.
"""
from app.celery_app import celery_app
from app.redis_client import get_redis
import app.tasks as tasks

original_embed = tasks.embed_passages


def fail_once(texts):
    if any('Transient failure verification' in t for t in texts):
        if get_redis().set('worker-probe-failed-once', '1', nx=True):
            raise ConnectionError('Injected transient embedding failure for verification')
    return original_embed(texts)


tasks.embed_passages = fail_once
celery_app.worker_main(['worker', '--loglevel=info', '--concurrency=1'])
