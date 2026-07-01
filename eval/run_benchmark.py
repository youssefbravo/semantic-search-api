"""Benchmark the four search modes against the labeled query set.

Prereqs: stack running + corpus ingested (python -m eval.ingest_corpus --reset).

    python -m eval.run_benchmark --k 10 --repeats 3

Outputs (to eval/results/):
  benchmark.json   raw metrics
  benchmark.md     markdown table for the README
  benchmark_quality.png / benchmark_latency.png   charts (if matplotlib present)
"""
import argparse
import json
import os
import re
import time

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
    with open(QUERIES_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    queries = spec["queries"]

    db = SessionLocal()
    try:
        gold = _gold_sets(db, queries)
        missing = [qid for qid, g in gold.items() if not g]
        if missing:
            print(f"WARNING: no relevant chunk found for {missing} "
                  f"(check markers vs corpus / ingestion).")

        # Warm up models + connection so the first query doesn't skew latency.
        run_search(db, queries[0]["query"], SearchMode.rerank, k)

        results: dict[str, dict] = {}
        for mode in MODES:
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

    _write_outputs(results, k, len(queries), repeats)


def _write_outputs(results: dict, k: int, n_queries: int, repeats: int) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(os.path.join(RESULTS_DIR, "benchmark.json"), "w", encoding="utf-8") as f:
        json.dump({"k": k, "n_queries": n_queries, "repeats": repeats,
                   "modes": results}, f, indent=2)

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
    args = ap.parse_args()
    run(args.k, args.repeats)
