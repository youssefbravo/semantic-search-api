import math
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..cache import cache_key, get_cached, set_cached
from ..db import get_db
from ..ratelimit import check_rate_limit
from ..schemas import SearchHit, SearchRequest, SearchResponse
from ..search import search as run_search

router = APIRouter(prefix="/search", tags=["search"])


def rate_limiter(request: Request) -> None:
    """Per-client token-bucket gate. Raises 429 with Retry-After when exhausted."""
    client = request.client.host if request.client else "unknown"
    allowed, retry_after = check_rate_limit(client)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Slow down.",
            headers={"Retry-After": str(math.ceil(retry_after))},
        )


@router.post("", response_model=SearchResponse)
def search_endpoint(
    req: SearchRequest,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limiter),
) -> SearchResponse:
    started = time.perf_counter()
    key = cache_key(req.query, req.mode.value, req.k)

    cached = get_cached(key)
    if cached is not None:
        return SearchResponse(
            query=req.query,
            mode=req.mode,
            latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
            cached=True,
            count=cached["count"],
            results=[SearchHit(**hit) for hit in cached["results"]],
        )

    results = run_search(db, req.query, req.mode, req.k)
    hits = [
        SearchHit(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            content=r.content,
            score=r.score,
            rank=r.rank,
        )
        for r in results
    ]

    # Cache the serialized hits (JSON-safe: UUIDs -> strings).
    set_cached(
        key,
        {"count": len(hits), "results": [h.model_dump(mode="json") for h in hits]},
    )

    return SearchResponse(
        query=req.query,
        mode=req.mode,
        latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
        cached=False,
        count=len(hits),
        results=hits,
    )
