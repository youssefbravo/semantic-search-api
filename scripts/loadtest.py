"""Dependency-free load driver for the /search endpoint (audit plan §1.4).

Fires a fixed number of requests at a chosen concurrency and reports throughput
(req/s) and latency percentiles (p50/p95/p99) per run. Uses only the Python stdlib
(threads + urllib) so it needs no locust/k6 install.

Notes on a fair measurement:
  * The API rate-limits per client IP (token bucket, cap 30). A single-client load
    test would mostly measure 429s, so run this with the limiter disabled
    (RATE_LIMIT_ENABLED=false on the api container) to measure raw server throughput.
  * --unique appends a nonce to every query so each request MISSES the cache and we
    measure real retrieval cost, not cache hits.

Usage (from the host, stack running):
    python scripts/loadtest.py --mode keyword --n 300 --concurrency 20 --unique
    python scripts/loadtest.py --mode semantic --n 200 --concurrency 20 --unique
    python scripts/loadtest.py --mode hybrid --n 200 --concurrency 20 --unique
"""
import argparse
import itertools
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_QUERIES = [
    "approximate nearest neighbour search",
    "how does BM25 score documents",
    "what is reciprocal rank fusion",
    "why normalize embeddings for cosine similarity",
    "token bucket rate limiting",
    "chunking strategy for retrieval",
    "cross encoder reranking tradeoffs",
    "redis caching with ttl",
    "celery background task queue",
    "postgres mvcc and transactions",
]


def _percentile(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1))))
    return s[idx]


def one_request(url, query, mode, k):
    body = json.dumps({"query": query, "mode": mode, "k": k}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"content-type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception:  # noqa: BLE001
        status = -1
    return status, (time.perf_counter() - t0) * 1000.0


def run(url, mode, n, concurrency, k, unique):
    counter = itertools.count()

    def task(_):
        i = next(counter)
        q = BASE_QUERIES[i % len(BASE_QUERIES)]
        if unique:
            q = f"{q} #{i}"
        return one_request(url, q, mode, k)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(task, range(n)))
    wall = time.perf_counter() - started

    oks = [lat for status, lat in results if status == 200]
    codes = {}
    for status, _ in results:
        codes[status] = codes.get(status, 0) + 1

    print(f"\n=== mode={mode}  n={n}  concurrency={concurrency}  unique={unique} ===")
    print(f"wall time      : {wall:.2f} s")
    print(f"throughput     : {n / wall:.1f} req/s ({len(oks)} ok)")
    print(f"status codes   : {codes}")
    if oks:
        print(f"latency p50    : {_percentile(oks, 50):.1f} ms")
        print(f"latency p95    : {_percentile(oks, 95):.1f} ms")
        print(f"latency p99    : {_percentile(oks, 99):.1f} ms")
        print(f"latency max    : {max(oks):.1f} ms")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000/search")
    ap.add_argument("--mode", default="hybrid",
                    choices=["keyword", "semantic", "hybrid", "rerank"])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--unique", action="store_true",
                    help="append a nonce so every request misses the cache")
    args = ap.parse_args()
    run(args.url, args.mode, args.n, args.concurrency, args.k, args.unique)
