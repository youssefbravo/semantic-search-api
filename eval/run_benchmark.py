"""Benchmark the four search modes against the labeled query set.

Prereqs: stack running + corpus ingested (python -m eval.ingest_corpus --reset).

    python -m eval.run_benchmark --k 10 --repeats 3

Outputs (to a new timestamped eval/results/ directory, or --output-dir):
  benchmark.json   raw metrics
  benchmark.md     markdown table for the README
  benchmark_quality.png / benchmark_latency.png   charts (if matplotlib present)
"""
import argparse
import json
import os
import re
import time
import hashlib
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from app.config import get_settings
from app.models import Document

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Chunk
from app.schemas import SearchMode
from app.search import search as run_search
from eval.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank

HERE = os.path.dirname(__file__)
QUERIES_PATH = os.path.join(HERE, "queries.json")
RESULTS_DIR = os.path.join(HERE, "results")
MODES = [SearchMode.keyword, SearchMode.semantic, SearchMode.hybrid, SearchMode.rerank]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1))))
    return s[idx]


def _gold_sets(db, queries: list[dict]) -> dict[str, set]:
    """Map each query id -> set of relevant chunk ids (marker containment)."""
    rows = db.execute(select(Chunk.id, Chunk.content)).fetchall()
    norm_chunks = [(cid, _normalize(content)) for cid, content in rows]
    gold: dict[str, set] = {}
    for q in queries:
        markers = [_normalize(m) for m in q["markers"]]
        gold[q["id"]] = {
            cid for cid, content in norm_chunks if any(m in content for m in markers)
        }
    return gold


def run(k: int, repeats: int) -> None:
    if k < 5 or repeats < 1:
        raise ValueError("k must be at least 5 for P@5; repeats must be positive")
    with open(QUERIES_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    queries = spec["queries"]

    db = SessionLocal()
    try:
        gold = _gold_sets(db, queries)
        missing = [qid for qid, g in gold.items() if not g]
        if missing:
            raise ValueError(f"Missing relevance labels for {missing}; check markers and corpus")

        # Warm up models + connection so the first query doesn't skew latency.
        cold_start = time.perf_counter()
        run_search(db, queries[0]["query"], SearchMode.rerank, k)
        first_request_ms = (time.perf_counter() - cold_start) * 1000

        results: dict[str, dict] = {}
        for mode in MODES:
            print(f"Evaluating {mode.value} ({len(queries)} queries)...", flush=True)
            per_query = {"precision_at_5": [], "recall_at_k": [],
                         "mrr": [], "ndcg_at_k": []}
            latencies: list[float] = []

            for q in queries:
                relevant = gold[q["id"]]
                retrieved_ids: list = []
                for _ in range(repeats):
                    t0 = time.perf_counter()
                    hits = run_search(db, q["query"], mode, k)
                    latencies.append((time.perf_counter() - t0) * 1000.0)
                    retrieved_ids = [h.chunk_id for h in hits]

                per_query["precision_at_5"].append(
                    precision_at_k(retrieved_ids, relevant, 5))
                per_query["recall_at_k"].append(
                    recall_at_k(retrieved_ids, relevant, k))
                per_query["mrr"].append(reciprocal_rank(retrieved_ids, relevant))
                per_query["ndcg_at_k"].append(ndcg_at_k(retrieved_ids, relevant, k))

            def avg(xs):
                return sum(xs) / len(xs) if xs else 0.0

            results[mode.value] = {
                "precision_at_5": round(avg(per_query["precision_at_5"]), 4),
                f"recall_at_{k}": round(avg(per_query["recall_at_k"]), 4),
                "mrr": round(avg(per_query["mrr"]), 4),
                f"ndcg_at_{k}": round(avg(per_query["ndcg_at_k"]), 4),
                "latency_p50_ms": round(_percentile(latencies, 50), 2),
                "latency_p95_ms": round(_percentile(latencies, 95), 2),
            }
    finally:
        db.close()

    import torch
    settings = get_settings()
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "embedding_model": settings.embedding_model_name,
        "embedding_revision": settings.embedding_model_revision,
        "reranker_model": settings.reranker_model_name,
        "reranker_revision": settings.reranker_model_revision,
        "configuration": {key: getattr(settings, key) for key in
                          ("chunk_max_tokens", "chunk_overlap_tokens", "hybrid_pool", "rerank_pool", "rrf_k")},
        "platform": platform.platform(), "machine": platform.machine(),
        "cpu": next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                     if line.startswith("model name")), "unknown") if Path("/proc/cpuinfo").exists() else platform.processor(),
        "torch_threads": torch.get_num_threads(),
        "packages": {name: version(name) for name in ("torch", "transformers", "sentence-transformers", "SQLAlchemy")},
        "first_request_including_model_load_ms": round(first_request_ms, 2),
        "latency_scope": "warmed direct retrieval; excludes HTTP, Redis cache, network and UI",
        "label_method": "binary marker containment; authored corpus; not independent human judgments",
        "queries_sha256": hashlib.sha256(Path(QUERIES_PATH).read_bytes()).hexdigest(),
        "corpus_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in sorted((Path(HERE)/"corpus").glob("*.md")))).hexdigest(),
        "precision_denominator": "fixed k (missing returned positions score zero)",
    }
    with SessionLocal() as session:
        metadata["n_document_rows"] = len(session.execute(select(Document.id)).all())
        metadata["n_indexed_documents"] = len(session.execute(select(Chunk.document_id).distinct()).all())
        metadata["n_chunks"] = len(session.execute(select(Chunk.id)).all())
    _write_outputs(results, k, len(queries), repeats, metadata)


def _write_outputs(results: dict, k: int, n_queries: int, repeats: int, metadata: dict) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(os.path.join(RESULTS_DIR, "benchmark.json"), "w", encoding="utf-8") as f:
        json.dump({"k": k, "n_queries": n_queries, "repeats": repeats,
                   "modes": results, "metadata": metadata}, f, indent=2)

    # Markdown table for the README.
    headers = ["Mode", "P@5", f"Recall@{k}", "MRR", f"nDCG@{k}",
               "p50 (ms)", "p95 (ms)"]
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for mode, m in results.items():
        lines.append("| " + " | ".join([
            mode,
            f"{m['precision_at_5']:.3f}",
            f"{m[f'recall_at_{k}']:.3f}",
            f"{m['mrr']:.3f}",
            f"{m[f'ndcg_at_{k}']:.3f}",
            f"{m['latency_p50_ms']:.1f}",
            f"{m['latency_p95_ms']:.1f}",
        ]) + " |")
    md = "\n".join(lines) + "\n"
    with open(os.path.join(RESULTS_DIR, "benchmark.md"), "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\nResults (k={k}, {n_queries} queries, {repeats} repeats):\n")
    print(md)
    _write_charts(results, k)
    print(f"Wrote benchmark.json / benchmark.md to {RESULTS_DIR}")


def _write_charts(results: dict, k: int) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed — skipping charts)")
        return

    modes = list(results.keys())
    quality_metrics = [("precision_at_5", "P@5"), (f"recall_at_{k}", f"Recall@{k}"),
                       ("mrr", "MRR"), (f"ndcg_at_{k}", f"nDCG@{k}")]

    # Grouped quality bars.
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.2
    for i, (key, label) in enumerate(quality_metrics):
        xs = [j + i * width for j in range(len(modes))]
        ax.bar(xs, [results[m][key] for m in modes], width=width, label=label)
    ax.set_xticks([j + 1.5 * width for j in range(len(modes))])
    ax.set_xticklabels(modes)
    ax.set_ylabel("score")
    ax.set_title("Retrieval quality by search mode")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "benchmark_quality.png"), dpi=130)
    plt.close(fig)

    # Latency (p50/p95).
    fig, ax = plt.subplots(figsize=(9, 5))
    xs = range(len(modes))
    ax.bar([x - 0.2 for x in xs], [results[m]["latency_p50_ms"] for m in modes],
           width=0.4, label="p50")
    ax.bar([x + 0.2 for x in xs], [results[m]["latency_p95_ms"] for m in modes],
           width=0.4, label="p95")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(modes)
    ax.set_ylabel("latency (ms)")
    ax.set_title("Search latency by mode")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "benchmark_latency.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--repeats", type=int, default=3,
                    help="runs per query for the latency distribution")
    ap.add_argument("--output-dir", default=None, help="New run directory; existing benchmark.json is never overwritten")
    ap.add_argument("--queries", default=QUERIES_PATH)
    args = ap.parse_args()
    QUERIES_PATH = args.queries
    RESULTS_DIR = args.output_dir or os.path.join(RESULTS_DIR, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
    if os.path.exists(os.path.join(RESULTS_DIR, "benchmark.json")):
        raise SystemExit("Output already contains a benchmark; choose a new --output-dir")
    run(args.k, args.repeats)
