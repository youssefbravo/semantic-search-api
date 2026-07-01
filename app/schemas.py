import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .models import DocStatus


class SearchMode(str, Enum):
    keyword = "keyword"      # BM25 (ParadeDB pg_search)
    semantic = "semantic"    # vector similarity (pgvector)
    hybrid = "hybrid"        # BM25 + semantic fused via RRF
    rerank = "rerank"        # hybrid retrieval + cross-encoder rerank


class DocumentCreatedResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocStatus
    message: str


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    status: DocStatus
    num_chunks: int
    error: str | None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    mode: SearchMode = SearchMode.hybrid
    k: int = Field(default=5, ge=1, le=50)


class SearchHit(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    rank: int


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    latency_ms: float
    cached: bool = False
    count: int
    results: list[SearchHit]
