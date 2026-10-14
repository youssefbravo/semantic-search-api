# Evaluation contract

The root README summarizes scope. Original queries are in eval/queries.json (59); the
22 corpus files are authored educational passages. Gold sets are chunk IDs containing
one of each query's normalized marker phrases. `favors` is commentary only, not scoring.
Missing gold sets now fail the run; a warning followed by zero scores would be misleading.

These labels are not exhaustive relevance judgments. Changes to chunking can split markers,
add duplicate relevant chunks via overlap, or change denominators. Metrics are chunk-level,
not document-level. There are no confidence intervals, adversarial held-out tests or
independent human labels. Historical sweep results used the same authored query set for
comparison; they do not establish that 400 tokens generalizes. A 600-token setting exceeded
the embedding model's 512-token limit and is no longer offered as a valid sweep setting.
Use 200/400/500 and keep historical files as historical evidence.

The new development probes are separate examples, but were authored after inspecting the
implementation and corpus. They are **not an unbiased holdout**. There was no ranking-quality
hyperparameter tuning during the reliability repairs. A future comparison should freeze a
configuration using dev probes, then use independently judged unseen queries for reporting.

## Metric conventions

For retrieved IDs [x, a, b, y, c] with gold {a,b,c,d}:
P@5 = 3/5 = 0.6. Recall@5 = 3/4 = 0.75. Reciprocal rank = 1/2 = 0.5.
DCG = 1/log2(3)+1/log2(4)+1/log2(6). IDCG has four relevant positions:
1/log2(2)+1/log2(3)+1/log2(4)+1/log2(5). nDCG = DCG/IDCG.
MRR is the mean reciprocal rank over queries, limited to the retrieval cutoff here.
The old precision denominator used returned list length; new reports use the fixed cutoff.

## Timing boundaries

First direct retrieval in a new process includes loading both pretrained models from disk.
Subsequent retrievals are warmed inference and DB operations. The benchmark does not call
FastAPI, use Redis caching or simulate multiple users. Its p50/p95 pool query runtimes and
repeats; one repeat per 59 queries is a small sample, not a service-level guarantee.

HTTP first-use can load another model copy in the API process. A repeated cached response
avoids retrieval entirely. UI timing includes network, parallel requests and rendering.
Never compare these as if they were the same experiment. Thread counts, CPU contention,
model revisions and chunk boundaries affect reproducibility. Numeric timings are descriptive.

## Reproduce and preserve

Run the corpus loader only in a disposable DB, before worker probes add demonstration docs.
Use a new output directory for every run. Commit selected JSON, Markdown, environment context
and source commit/config; retain older reports. Report actual corpus counts, package/model
versions and hardware; record cached-image reuse separately from image builds.

The CI nDCG guard compares against eval/baseline/benchmark.json with a 5% relative floor.
It now rejects mismatched k/query counts. Historical baseline lacks fingerprints; it is a
limited fixture, not a complete experiment manifest. Latency is not a CI gate because hardware
and noise differ. A matching score is not proof of equivalent relevance labels.

The pinned reranker uses a sigmoid activation. Scores are relevance estimates on a different
scale from cosine/BM25/RRF, not calibrated probabilities. This was checked on the loaded model.

The maintained chunk sweep defaults to development probes and a fresh timestamped folder.
It rejects missing marker labels and refuses overwriting previous sweep results.
Quality uses the last repeat per query; repeated runs mainly supply latency samples.
The fixed corpus is retained for comparability and includes earlier project descriptions and
educational simplifications. Treat it as retrieval input, not current implementation documentation.
