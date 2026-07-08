from celery import Celery

from .config import get_settings

settings = get_settings()

celery_app = Celery(
    "semantic_search",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_transport_options={
        "visibility_timeout": settings.redis_visibility_timeout_seconds
    },
    result_backend_transport_options={
        "visibility_timeout": settings.redis_visibility_timeout_seconds
    },
    worker_prefetch_multiplier=1,
    # torch can grow worker memory over time; recycle children periodically.
    worker_max_tasks_per_child=50,
)
