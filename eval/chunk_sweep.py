"""Chunk-size sweep: isolate the effect of chunk size on retrieval quality.

This is intentionally self-contained and DB-free. For each chunk size it re-chunks
the corpus, embeds passages + queries, and runs pure semantic retrieval in-memory
(cosine over normalized vectors). Isolating one variable (chunk size) with one
retriever (semantic) makes the result clean to interpret and fast to run.

    python -m eval.chunk_sweep --sizes 200 400 600

Turns "I picked 400 tokens" into "I measured that 400 won on my set."
"""
import argparse
import glob
import json
import os
import re

import numpy as np

from app.chunking import chunk_text
from app.embeddings import embed_passages, embed_query
from eval.metrics import ndcg_at_k, recall_at_k

HERE = os.path.dirname(__file__)
CORPUS_DIR = os.path.join(HERE, "corpus")
QUERIES_PATH = os.path.join(HERE, "queries.json")
RESULTS_DIR = os.path.join(HERE, "results")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _load_corpus() -> list[str]:
    texts = []
    for path in sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md"))):
        with open(path, encoding="utf-8") as f:
            texts.append(f.read())
    return texts


def sweep(sizes: list[int], k: int) -> None:
    corpus = _load_corpus()
    with open(QUERIES_PATH, encoding="utf-8") as f:
        queries = json.load(f)["queries"]

    # Embed queries once (independent of chunk size).
    query_vecs = {q["id"]: np.array(embed_query(q["query"])) for q in queries}
    norm_markers = {q["id"]: [_normalize(m) for m in q["markers"]] for q in queries}

    rows = []
    for size in sizes:
        overlap = int(size * 0.15)  # hold overlap ratio fixed so size is the only var
        contents: list[str] = []
        for text in corpus:
            contents.extend(c.content for c in chunk_text(text, size, overlap))

        matrix = np.array(embed_passages(contents))  # (n_chunks, dim), normalized
        norm_contents = [_normalize(c) for c in contents]

        recalls, ndcgs = [], []
        for q in queries:
            relevant = {
                i for i, c in enumerate(norm_contents)
                if any(m in c for m in norm_markers[q["id"]])
            }
            sims = matrix @ query_vecs[q["id"]]  # cosine (vectors normalized)
            ranked = list(np.argsort(-sims))
            recalls.append(recall_at_k(ranked, relevant, k))
            ndcgs.append(ndcg_at_k(ranked, relevant, k))

        row = {
            "chunk_size": size,
            "overlap": overlap,
            "n_chunks": len(contents),
            f"recall_at_{k}": round(sum(recalls) / len(recalls), 4),
            f"ndcg_at_{k}": round(sum(ndcgs) / len(ndcgs), 4),
        }
        rows.append(row)
        print(f"size={size:>4} overlap={overlap:>3} chunks={len(contents):>3} "
              f"recall@{k}={row[f'recall_at_{k}']:.3f} "
              f"ndcg@{k}={row[f'ndcg_at_{k}']:.3f}")

    _write_outputs(rows, k)


def _write_outputs(rows: list[dict], k: int) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "chunk_sweep.json"), "w", encoding="utf-8") as f:
        json.dump({"k": k, "rows": rows}, f, indent=2)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed — skipping chart)")
        return

    sizes = [r["chunk_size"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sizes, [r[f"recall_at_{k}"] for r in rows], marker="o", label=f"Recall@{k}")
    ax.plot(sizes, [r[f"ndcg_at_{k}"] for r in rows], marker="s", label=f"nDCG@{k}")
    ax.set_xlabel("chunk size (tokens)")
    ax.set_ylabel("score")
    ax.set_title("Semantic retrieval quality vs chunk size")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "chunk_sweep.png"), dpi=130)
    plt.close(fig)
    print(f"Wrote chunk_sweep.json / chunk_sweep.png to {RESULTS_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[200, 400, 600])
    ap.add_argument("--k", type=int, default=10)
    args = ap.parse_args()
    sweep(args.sizes, args.k)
