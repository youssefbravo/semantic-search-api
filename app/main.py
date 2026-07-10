import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import get_settings
from .db import engine
from .redis_client import get_redis
from .routers import documents, search

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

settings = get_settings()

app = FastAPI(
    title="Document Semantic Search API",
    version="0.1.0",
    description=(
        "Ingest documents and search them via BM25, semantic, hybrid, and "
        "rerank modes."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(search.router)

if settings.metrics_enabled:
    try:
        import redis
        from prometheus_fastapi_instrumentator import Instrumentator
        from prometheus_client import Gauge

        broker = redis.Redis.from_url(settings.celery_broker_url)
        Gauge(
            "celery_queue_depth",
            "Number of ready Celery tasks waiting in the Redis broker queue.",
        ).set_function(lambda: broker.llen("celery"))
        Gauge(
            "celery_unacked_tasks",
            "Number of Celery tasks reserved by workers but not yet acknowledged.",
        ).set_function(lambda: broker.hlen("unacked"))

        Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["meta"])
    except ImportError:
        logging.warning(
            "METRICS_ENABLED=true but prometheus-fastapi-instrumentator is not installed"
        )


@app.get("/health", tags=["meta"])
def health() -> dict:
    checks = {"postgres": False, "redis": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "checks": checks, "error": str(exc)},
        ) from exc

    try:
        checks["redis"] = bool(get_redis().ping())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "checks": checks, "error": str(exc)},
        ) from exc

    return {"status": "ok", "checks": checks}
