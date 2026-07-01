"""The four search modes: BM25, semantic, hybrid (RRF), and rerank.

Every mode returns a list[SearchResult] with a 1-based `rank` and a `score`. Note
the scores are NOT comparable across modes (BM25 scores, cosine similarities, RRF
scores, and cross-encoder logits live on different scales) — `rank` is the common
currency, which is exactly why hybrid fuses on rank (RRF), not on raw score.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .config import get_settings
from .embeddings import embed_query
from .models import Chunk
from .reranker import rerank
from .schemas import SearchMode

settings = get_settings()

# Characters with special meaning in ParadeDB's query parser. We strip them so a
# user query can't break the parser or inject query operators.
_BM25_SPECIAL = set('+-&|!(){}[]^"~*?:\\/')


@dataclass
class SearchResult:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    rank: int


def _sanitize_bm25(query: str) -> str:
    return "".join(" " if c in _BM25_SPECIAL else c for c in query).strip()


def keyword_search(db: Session, query: str, k: int) -> list[SearchResult]:
    """True BM25 via the ParadeDB pg_search bm25 index."""
    q = _sanitize_bm25(query)
    if not q:
        return []
    # paradedb.match(field, value) tokenizes `value` as PLAIN TEXT, so user queries
    # (apostrophes, punctuation, multiple words) can't break the query parser the way
    # the raw `content @@@ 'string'` form does.
    rows = db.execute(
        text(
            """
            SELECT id, document_id, content, paradedb.score(id) AS score
            FROM chunks
            WHERE id @@@ paradedb.match('content', :q)
            ORDER BY score DESC
            LIMIT :k
            """
        ),
        {"q": q, "k": k},
    ).fetchall()
    return [
        SearchResult(r.id, r.document_id, r.content, float(r.score), i + 1)
        for i, r in enumerate(rows)
    ]


def semantic_search(
    db: Session, query: str, k: int, qvec: list[float] | None = None
) -> list[SearchResult]:
    """Vector similarity via pgvector HNSW (cosine)."""
    qvec = qvec if qvec is not None else embed_query(query)
    distance = Chunk.embedding.cosine_distance(qvec)
    stmt = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.content,
            (1 - distance).label("score"),  # cosine similarity for readability
        )
        .order_by(distance)  # ascending distance == descending similarity
        .limit(k)
    )
    rows = db.execute(stmt).fetchall()
    return [
        SearchResult(r.id, r.document_id, r.content, float(r.score), i + 1)
        for i, r in enumerate(rows)
    ]


def hybrid_search(
    db: Session, query: str, k: int, qvec: list[float] | None = None
) -> list[SearchResult]:
    """Reciprocal Rank Fusion of BM25 + semantic.

    RRF: score(d) = Σ_lists 1 / (rrf_k + rank_in_list(d)). It needs no score
    normalization (the two rankers' scores are incomparable) and is robust — a
    document ranked highly by EITHER signal floats up, agreement by both wins.
    """
    bm25 = keyword_search(db, query, settings.hybrid_pool)
    semantic = semantic_search(db, query, settings.hybrid_pool, qvec=qvec)

    fused: dict[uuid.UUID, float] = {}
    meta: dict[uuid.UUID, SearchResult] = {}
    for ranked_list in (bm25, semantic):
        for res in ranked_list:
            fused[res.chunk_id] = fused.get(res.chunk_id, 0.0) + 1.0 / (
                settings.rrf_k + res.rank
            )
            meta[res.chunk_id] = res

    top = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:k]
    return [
        SearchResult(meta[cid].chunk_id, meta[cid].document_id, meta[cid].content, sc, i + 1)
        for i, (cid, sc) in enumerate(top)
    ]


def rerank_search(
    db: Session, query: str, k: int, qvec: list[float] | None = None
) -> list[SearchResult]:
    """Retrieve-then-rerank over a HIGH-RECALL candidate union.

    The candidate set is the union of BM25's and semantic's top results (deduped),
    NOT hybrid's fused top-k. Reranking the fused list would inherit RRF's failure to
    surface a strong single-signal match: e.g. a passage that only semantic ranks
    highly can be voted below the fusion cutoff and would never reach the reranker.
    Unioning the two retrievers maximizes first-stage recall so the cross-encoder can
    actually see (and correctly rank) the right passage — a reranker can only reorder
    what it is given.
    """
    pool = settings.rerank_pool
    semantic = semantic_search(db, query, pool, qvec=qvec)
    bm25 = keyword_search(db, query, pool)

    seen: dict[uuid.UUID, SearchResult] = {}
    for r in (*semantic, *bm25):  # semantic first so it wins identical-id ties
        seen.setdefault(r.chunk_id, r)
    candidates = list(seen.values())
    if not candidates:
        return []

    scores = rerank(query, [c.content for c in candidates])
    ranked = sorted(zip(candidates, scores), key=lambda cs: cs[1], reverse=True)[:k]
    return [
        SearchResult(c.chunk_id, c.document_id, c.content, float(s), i + 1)
        for i, (c, s) in enumerate(ranked)
    ]


def search(db: Session, query: str, mode: SearchMode, k: int) -> list[SearchResult]:
    """Dispatch to a mode. The query is embedded at most once per request and
    threaded through the vector-using modes."""
    if mode == SearchMode.keyword:
        return keyword_search(db, query, k)

    qvec = embed_query(query)  # shared by semantic / hybrid / rerank
    if mode == SearchMode.semantic:
        return semantic_search(db, query, k, qvec=qvec)
    if mode == SearchMode.hybrid:
        return hybrid_search(db, query, k, qvec=qvec)
    if mode == SearchMode.rerank:
        return rerank_search(db, query, k, qvec=qvec)
    raise ValueError(f"Unknown search mode: {mode}")
