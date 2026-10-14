# Verification report — 14 October 2026

This report records fresh local checks, not prior-session claims. Cloud deployment is pending
project/budget approval. Original project copies and their changes were preserved.

## Discovery and baseline

The review copy was clean at main/53808b9. The Desktop semantic-search copy was at
4ca2965 on audit/phase-0 with one untracked handoff note; that note was stale relative to
later retry fixes. A separate local clone was created for this work. The unrelated TaskFlow
copy was identified by its Git remote and excluded. Documents/Desktop/Downloads and the
identified development workspace were searched by manifests/README/repository identity,
with dependencies/caches excluded. No repository AGENTS.md applied to this project.

The initial cached-image run used a fresh Compose project, DB, Redis instance and upload
volume. It produced **52 passes, 3 skips, 0 failures** (empty corpus). After corpus loading,
the unchanged original suite produced **55 passes, 0 skips, 0 failures**. Host Python lacked
pytest; the cached API image lacked ruff/mypy. Those missing checks were not counted as passes.
CI-only ruff 0.8.4 and mypy 1.14.1 were installed in the disposable API container.

The original retrieval baseline was completed and preserved in
[baseline-20261014](baseline-20261014/benchmark.json), with a separate environment/context file.
Its first uncapped attempt was stopped for CPU oversubscription and produced no claimed result.
The completed baseline used requested two-thread limits. Other containers/tests/builds were
running: these timings are not a controlled experiment for before/after speed claims.

## Defects reproduced and repaired

- Existing `autoretry_for`/late-ack settings were already implemented in the newer branch;
  they were verified rather than attributed to this session.
- A 40-token budget emitted 52 tokens; a single unbroken alpha string emitted 400 with
  a budget of 40; explicit zero overlap still repeated a sentence. The new regression
  fixture initially failed all three checks. Whole-chunk limits, zero-overlap handling and
  source-offset hard splitting now pass, including a one-token budget and original-text checks.
- Upload code used an unbounded read. It now reads at most configured bytes + 1 and rejects
  excess. Multipart spooling still happens before this application-level check.
- Staging/producer failures could leave pending rows. They now return 503 and record failed
  state, retaining raw bytes for ambiguous broker timeouts. Completed deliveries are not
  overwritten as failed. Operator recovery is explicit; this is not a transactional outbox.
- Duplicate chunk deletion was insufficient for simultaneous deliveries. A connection-pinned
  PostgreSQL session lock now serializes one document across processing-status commits.
- Cache keys now include committed corpus count/latest completion update and preserve case.
  New ingestion changes the key even if Redis was unavailable during commit.
- Embedding checks include query prefixes/special tokens. Invalid chunk budgets fail; reranker
  pairs have explicit 512-token truncation. Overlong pair endings may still lose useful content.
- ParadeDB/Redis digests and model revisions are pinned. Redis has an AOF-backed volume.
- Frontend dependencies were updated and locked, all four modes are visible, errors are shown,
  and the browser calls a same-origin proxy. Public-demo mode disables ingestion.

[Defect reproduction XML](defect-reproduction.xml) contains three failures and two passes;
the upload fixes had already been applied for those two endpoint checks. It is not represented
as a wholly untouched baseline.

## Real worker evidence

A separate worker_verification database and disposable Redis container isolated these probes
from benchmark data. Queue submission was real, not patched to a no-op.

- Text ingestion, valid synthetic PDF ingestion, concurrent duplicates and delivery after
  file cleanup passed. Stored chunk counts and indices remained consistent.
- Malformed PDF tasks retried twice, then failed with zero chunks and staged-file cleanup.
- A test-only worker wrapper injected one embedding error. Celery logged `Retry in 1s`, then
  completed the same task. Production workers never import the fault harness.
- SIGKILL interrupted two processing documents with a third pending. Restart recovered all
  three to done, each with 58 actual chunks matching its status count. The drill used a
  ten-second visibility timeout; the regular stack uses 300 seconds. It does not prove zero-loss
  behavior for Redis/host crashes or all production failure modes.
- Stopping the actual disposable Redis broker caused HTTP 503 and a failed document row,
  with staged bytes retained. After broker restoration, explicit operator requeue completed it.
- Main isolated Redis reported appendonly=yes; a probe in broker DB 1 survived container restart.
  AOF everysec still allows recent write loss after an abrupt host failure.

Evidence: [worker JSON](worker-verification.json), [transient retry](transient-retry.json),
[retry log](transient-worker-log.txt), [crash drill](worker-crash.json),
[crash log](worker-crash-log.txt), [broker failure/recovery](broker-failure.json).

## Reproduction commands

The local audit override changes host ports to API 48090 / UI 43000 and uses project
semantic-finalise. It is ignored because ordinary clones should use the README defaults.

```bash
docker compose -p semantic-finalise -f docker-compose.yml -f compose.audit.yml up -d --no-build --pull never
docker compose -p semantic-finalise -f docker-compose.yml -f compose.audit.yml exec -T api pytest --strict-integration -ra
docker compose -p semantic-finalise -f docker-compose.yml -f compose.audit.yml exec -T api ruff check app eval scripts tests
# Final direct evaluation used explicit process thread overrides:
docker compose -p semantic-finalise -f docker-compose.yml -f compose.audit.yml exec -T \
  -e OMP_NUM_THREADS=4 -e MKL_NUM_THREADS=4 -e OPENBLAS_NUM_THREADS=2 api \
  python -m eval.run_benchmark --k 5 --repeats 1 --output-dir docs/verification/final-20261014
```

For a new run, choose another output directory. The runner refuses overwriting a benchmark.
The final root README uses ordinary ports and new timestamped result directories.

The broker/drill containers use app source mounts, a separately named DB, Redis and upload
volume, with broker/result/cache URLs pointing at the drill Redis. `tests/run_worker_crash.py`
is deliberately host-side and names only the disposable drill worker. The test-only fault
worker is launched via `PYTHONPATH=/app python tests/worker_fault_harness.py`; use
`tests/request_retry_probe.py` to submit its fixture. Do not run fault/crash helpers on a
production stack. Human interview answers and the student's code exercise remain pending.

## Build, security and deployment scope

Backend dependencies/models were reused from cached image 42d803df475c; a derived local
image copied current source on top. This is **not a clean backend image build**. The checked-in
Dockerfile describes the clean build path, which CI will exercise. Frontend npm ci and Next.js
16.4.0/React 19.3.1/Tailwind 4.3.3 production builds succeeded; npm audit reported zero findings.
The dependency audit is time-specific, not a guarantee of future safety.

Compose cloud override parsed successfully. Caddy 2.10.2 validated the prepared configuration
without a network. This does not prove DNS, external TLS, firewall behavior or deployment.
Private multi-user use remains unsupported. No paid services/resources were provisioned.


## Final checks and measured retrieval

| Check | Passes | Failures | Skips |
|---|---:|---:|---:|
| Original suite, before corpus | 52 | 0 | 3 |
| Original suite, after corpus | 55 | 0 | 0 |
| New defect fixtures before chunk repairs | 2 | 3 | 0 |
| Final strict suite | 68 | 0 | 0 |

Ruff passed; the selected mypy check passed across 11 source files. These are the
workflow's scoped type checks, not a claim that every function is fully type-checked.
The nDCG regression guard passed at the existing 5% relative floor for all four modes.

| Mode | P@5 | Recall@5 | MRR | nDCG@5 | p50 (ms) | p95 (ms) |
|---|---|---|---|---|---|---|
| keyword | 0.203 | 0.958 | 0.918 | 0.927 | 5.4 | 8.9 |
| semantic | 0.207 | 0.966 | 0.898 | 0.914 | 27.2 | 37.1 |
| hybrid | 0.210 | 0.992 | 0.972 | 0.973 | 32.3 | 41.0 |
| rerank | 0.210 | 0.983 | 0.975 | 0.977 | 16220.7 | 20743.8 |

[Final JSON with model/hardware fingerprints](final-20261014/benchmark.json).
The first direct rerank request including disk model load took 19,793.83 ms.
Warm rerank median was 16,220.68 ms; warmed semantic/hybrid medians were 27.16/32.29 ms.
A separate keyword HTTP cache probe measured 45.26 ms uncached and 3.02 ms cached
inside the endpoint. These measure different paths; no speedup claim is made from comparing them.

The final benchmark used four PyTorch threads, whereas the original baseline requested two.
Background checks/drills/builds ran during these sessions. Rank quality can be compared
on the unchanged 29 indexed chunks, but latency changes cannot be attributed to the fixes.
At this corpus size the top-30 semantic pool contains all 29 chunks, so reranker candidate
recall is effectively exhaustive; this does not show large-corpus candidate-selection quality.
Most queries mark roughly one chunk relevant, so P@5 near 0.2 is compatible with high recall.

The JSON's `n_documents=30` records all database rows at report time: 22 indexed corpus
items plus eight test fixture rows without chunks. It is not a 30-document evaluation corpus.
The separate context file clarifies this census; future runner outputs distinguish indexed
documents from all document rows. Original JSON is preserved unchanged. No relevance labels
or ranking hyperparameters were tuned to the original report set during these repairs.


The browser exercised all four modes via the same-origin proxy and successfully uploaded
`docs/demo-document.txt` to the real worker, showing done / 1 chunk. Narrow-layout screenshots
are saved because the in-app browser desktop capture was blurred and Chrome automation was
unavailable. The desktop four-column breakpoint was inspected; no clear desktop screenshot
is claimed. Disposable drill containers were stopped after checks; their volumes were retained.
The live local corpus now includes the synthetic browser-upload document, after evaluation.

The separate six-query [development report](dev-20261014/benchmark.json) is authored probe
evidence, not held-out validation. A [semantic-only development sweep](dev-sweep-20261014/chunk_sweep.json)
compares 200/400/500 tokens without overwriting historical results or changing the default 400.
The corpus is fixed retrieval input and contains educational simplifications/older implementation
descriptions; the root README, not these passages, documents current behavior.

Final local checks were repeated after API/worker recreation: 68 passed with strict skips
policy. Ruff and the selected 11-file mypy check passed on the running rebuilt-source stack.
The disposable staging volume was inspected read-only and was empty after completed/failed
worker probes. Compose defaults, alternate ports and the cloud override all parsed successfully.
Backend source at fd9c734 matches the application source hashes in the final context file;
later commits update evaluation bookkeeping, development sweep behavior and documentation.
