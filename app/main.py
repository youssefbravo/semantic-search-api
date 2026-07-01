import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
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


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
