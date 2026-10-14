# Explain it, then change it

This is retrieval, not answer-generating RAG. A RAG system could use these passages
as context for a generator, but there is no generator here. BGE inference transforms
text using pretrained weights; it does not train a model on uploads.

## Keyword versus meaning

A query `car repair` shares no word with `automobile maintenance`. BM25 rewards term
matches, weighted by rarity and saturated term frequency, so this lexical mismatch can
miss the passage. A pretrained encoder may place the two texts nearby because it learned
language relationships. That is a possibility, not a guarantee: negation, rare identifiers,
languages outside the model's coverage and domain shifts can fail. Conversely, an exact
identifier such as `ef_search` is often useful to keyword retrieval. In this implementation
ParadeDB tokenizes text and BGE adds a retrieval instruction to the query.

An embedding is a vector, here 384 numbers, summarizing features useful to the model's
training objective. Coordinates are not named concepts and similarity is not truth or
confidence. The model can confidently retrieve a false or unrelated statement.

## Cosine: a tiny example

Take toy vectors q=(1,0), a=(3,4), b=(0,2). These are teaching vectors, not actual BGE output.

cos(q,a) = (1*3 + 0*4)/(sqrt(1)*sqrt(9+16)) = 3/5 = 0.6.
cos(q,b) = 0. Multiplying a by 10 does not change its angle or cosine similarity.
Normalize a to (0.6,0.8), and q dot a is now 0.6 directly. The code calls
`normalize_embeddings=True`; pgvector orders ascending cosine distance, `1 - cosine`.

Code: [`embed_query`](../app/embeddings.py), [`semantic_search`](../app/search.py).

## Chunking and overlap

Suppose a fact is split between two chunks: `The broker uses Redis ...` / `... and tasks
may be delivered again.` Repeating a trailing sentence in the next chunk can keep the
context together. It costs extra storage and may return redundant passages.
With a 40-token budget, 12 tokens of overlap and a 35-token next unit cannot fit: 12+35=47.
The fixed chunker drops some overlap to keep the *whole* chunk <=40. Previously it emitted
52 tokens for the specific 40-token regression fixture. Long unbroken input also needs
splitting; counting whitespace-separated words is insufficient. Tokenizer offsets preserve the original text.

Code: [`chunk_text`](../app/chunking.py) and
[`test_overlap_is_inside_budget`](../tests/integration/test_portfolio_regressions.py).
Special tokens consume space; queries additionally use the BGE prefix. The query limit
check happens before embedding. The cross-encoder separately truncates query/passage pairs
at 512 tokens, so relevant passage endings can be omitted for long queries.

## Reciprocal Rank Fusion

For each candidate, sum 1/(60+rank) over retrievers that returned it. A missing candidate
contributes zero; it does not receive a guessed rank. For A ranked (1,3),
RRF(A)=1/61+1/63=0.032266. For B ranked (2,1),
RRF(B)=1/62+1/61=0.032522. B wins. Raw BM25 and cosine scores need not share a scale.

Code: [`hybrid_search`](../app/search.py), with `settings.rrf_k` in
[`Settings`](../app/config.py). Ties currently follow insertion order; this is a small
implementation detail, not a claim about relevance.

## Reranking's ceiling

If the correct passage is absent from both first-stage top-30 lists, the cross-encoder
never sees it. It only reorders the deduplicated union. Bigger candidate pools can improve
recall but cost more pair inference. It cannot create missing information or certify facts.

Code: [`rerank_search`](../app/search.py), [`rerank`](../app/reranker.py).

## Why queues mean repeated work

Imagine the worker commits chunks, then dies before acknowledging its message. The broker
redelivers because it cannot know whether the database commit happened. Late acknowledgements
protect against lost work but permit duplicates. The task therefore locks one document,
skips already-completed work and replaces chunks in one transaction with the completion status.
A retry must still have its staging file, so cleanup waits until success or terminal failure.
The database and Redis cannot commit atomically here: producer timeouts remain ambiguous,
and a transactional outbox is an honest future improvement.

Code: [`ingest_document`](../app/tasks.py), [`celery_app`](../app/celery_app.py).
Redis AOF with a one-second flush improves persistence but is not zero-loss durability.

## Your small change

On a local branch, change `rrf_k` from 60 to 20 in `app/config.py`. Before running it,
predict how rank 1 versus rank 10 contributes: with 60, 1/61 versus 1/70; with 20,
1/21 versus 1/30. The smaller constant makes the first rank relatively more influential.

1. Run `pytest tests/unit/test_rrf_fusion.py` inside the API container.
2. Restart the API so imported settings reload.
3. Use **eval/queries.dev.json** for comparison; save a new result directory.
4. Explain one changed rank or why none changed on this corpus. Do not choose the best
   constant on the original report queries and call that an unbiased test.
5. Restore 60 when finished unless you intentionally want to keep your experiment.

Tell me your diff and explanation and I can review it. This exercise is not marked completed.

## Interview practice based on this code

- Why does `max_retries=2` alone not cause retries? Where is retry behavior actually configured?
- Why does the lock survive a commit, and why does its connection stay pinned?
- How can a timed-out queue submission still be delivered? Why retain the file then?
- Why can keyword search be useful even with a strong embedding model?
- Compute the RRF example above without comparing raw scores.
- Why is a cached response different from warmed model inference?
- What would you add before sharing private documents across users?
- How would you replace marker labels with independent relevance judgments?

Answers to check against: autoretry wraps exceptions; session locks survive commits;
Redis acknowledgement can be lost; exact terms and identifiers; B wins; cache bypasses
retrieval; authentication/ownership filtering at every access; blinded assessors and a
separate held-out query set. Give your own reasoning, not just these phrases.
