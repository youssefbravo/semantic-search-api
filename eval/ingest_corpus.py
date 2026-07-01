"""Ingest the evaluation corpus directly into the database (no Celery/HTTP).

Synchronous on purpose: the benchmark needs a deterministic, fully-populated index
before it runs. Uses the SAME chunk_text + embed_passages pipeline as production, so
what we measure reflects the real system.

    python -m eval.ingest_corpus --reset
"""
import argparse
import glob
import os

from sqlalchemy import delete

from app.chunking import chunk_text
from app.db import SessionLocal
from app.embeddings import embed_passages
from app.models import Chunk, DocStatus, Document

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "corpus")


def ingest(reset: bool) -> None:
    db = SessionLocal()
    try:
        if reset:
            db.execute(delete(Chunk))
            db.execute(delete(Document))
            db.commit()
            print("Cleared existing documents and chunks.")

        paths = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.md")))
        if not paths:
            raise SystemExit(f"No corpus files found in {CORPUS_DIR}")

        total_chunks = 0
        for path in paths:
            with open(path, encoding="utf-8") as f:
                text = f.read()

            doc = Document(
                filename=os.path.basename(path),
                content_type="text/markdown",
                status=DocStatus.done,
            )
            db.add(doc)
            db.flush()  # assign doc.id

            chunks = chunk_text(text)
            vectors = embed_passages([c.content for c in chunks])
            db.add_all(
                [
                    Chunk(
                        document_id=doc.id,
                        chunk_index=i,
                        content=c.content,
                        token_count=c.token_count,
                        embedding=v,
                    )
                    for i, (c, v) in enumerate(zip(chunks, vectors))
                ]
            )
            doc.num_chunks = len(chunks)
            total_chunks += len(chunks)
            print(f"  {os.path.basename(path):<32} -> {len(chunks):>3} chunks")

        db.commit()
        print(f"Done. {len(paths)} documents, {total_chunks} chunks total.")
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--reset", action="store_true", help="delete existing docs/chunks first"
    )
    ingest(ap.parse_args().reset)
