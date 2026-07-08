# Demo GIF Shot List

Human-required artifact: record this locally after the app is running. Do not mark the demo complete until the GIF/video exists and is linked from the README.

Target length: 60-90 seconds, no voiceover needed.

## Setup

1. Start the stack with `docker compose up -d`.
2. Ingest the sample corpus with `docker compose exec api python -m eval.ingest_corpus --reset`.
3. Open `http://localhost:3000`.
4. Use a clean browser window at 1440px width if possible.

## Shots

1. Show the frontend landing state with all four search modes visible.
2. Upload a small `.txt` or `.pdf` document and show the `pending -> processing -> done` status.
3. Search: `why is approximate search faster than brute force`.
4. Show the same query across keyword, semantic, hybrid, and rerank columns.
5. Repeat the search once and briefly show that the API response is cached, either in the UI if visible or in the browser devtools network response.
6. Show `GET /docs` or the API docs page at `http://localhost:8000/docs`.
7. End on the README benchmark table or the generated benchmark chart.

## Caption Text

Suggested README caption:

> 75-second walkthrough: upload, async ingestion status, four retrieval modes, cache hit, and benchmark evidence.

## Human Tester Protocol

Give each tester only this prompt:

> Clone the repo, follow the README quickstart, upload one document, and run one search. Say out loud whenever something is confusing.

Record:

- Setup time from clone to working search.
- Any command that failed or required guessing.
- Any confusion pause longer than 5 seconds.
- Any unhandled error or unclear API/UI message.
- Whether they could explain the four retrieval modes after reading the README.
