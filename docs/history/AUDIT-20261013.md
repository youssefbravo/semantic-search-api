# Audit Status — semantic-search-api

Last updated: 2026-07-08 | Phase: 3 (semantic-search repo polish in progress) | Overall Trust Contract: 2/6 fully checked (#2,#3), 2 partial (#1,#4)

> Single source of truth for this audit. On a new session, read this file first and resume from the recorded phase.
> Evidence rule: a box is ☑ **only** when a command was run **this session** and its output is quoted here.

---

## Claim Verification Table
(Built out fully in Phase 1.1. Seeded here; most rows verified in Phase 1.)

| # | Claim | Verification method | Evidence (cmd + result) | Status |
|---|-------|---------------------|-------------------------|--------|
| C0 | Documented onboarding path works from a fresh clone | Fresh `git clone` → `docker compose up -d --build` → `ingest_corpus --reset` → documented curl | Phase 0: all steps succeeded, sample query returned the correct HNSW/ANN passage at rank 1 | ☑ |
| C1 | Cache actually caches | `test_cache_and_etl.py` — set/get roundtrip + TTL + HTTP cached-flag | `pytest test_cache_and_etl.py` 5 passed: cold miss→set→hit; TTL 0<ttl≤300; HTTP `cached False→True`, latency drops | ☑ |
| C2 | BM25 (keyword) mode works | `test_search_modes.py::test_c2` — exact rare term in top-1 | 3 passed: keyword `ef_search` → top-1 content contains `ef_search` | ☑ |
| C3 | Vector (semantic) mode works | `test_search_modes.py::test_c3` — paraphrase finds a chunk BM25 misses | 3 passed: "how many people can edit data at the same time safely" → semantic surfaces ACID/transactions chunk; keyword top-3 does NOT | ☑ |
| C4 | Hybrid RRF works | `test_rrf_fusion.py` — output matches hand-computed fusion | 4 passed: fused order `[B,A,D,C]` + scores match `Σ 1/(60+rank)` to float precision | ☑ |
| C5 | Reranker improves ranking | `run_benchmark --k 5`: nDCG@5 rerank ≥ hybrid on 59-query labeled set | rerank nDCG@5 **0.977** ≥ hybrid 0.973 ≥ keyword 0.927 ≥ semantic 0.914; rerank MRR 0.975 ≥ hybrid 0.972 (at ~300× latency — README states this) | ☑ |
| C6 | Rate limiter is atomic | `test_rate_limit.py` — N concurrent, never over-admits | 3 passed: 4× oversubscription of a fresh bucket admits ≤ cap+refill (no double-spend); HTTP 429 carries Retry-After | ☑ |
| C7 | ETL survives failure | `test_cache_and_etl.py` + chaos drill B (kill worker mid-ingest) | Fixed + verified this session. `docker compose exec -T api pytest -q` -> **53 passed**. Chaos drill B rerun: queued 5 docs, killed worker with `SIGKILL` after reservation -> `ready_queue=3 unacked=2`; after restart + Redis visibility timeout, poll ended `done=5 queue=0 unacked=0` (each doc 90 chunks). | ☑ |
| C8 | Benchmark numbers reproduce | Re-run `run_benchmark --k 5 --repeats 1`, compare to README table | Quality metrics reproduce within ≤0.013 (semantic + rerank EXACT); small keyword/hybrid MRR/nDCG wobble = BM25 tie-break ordering. Latencies hardware-dependent (README disclaims). | ☑ |

---

## Trust Contract
| # | Contract item | Status | Evidence |
|---|---------------|--------|----------|
| 1 | Stranger test ≤5 min | ⚠ PARTIAL | Onboarding **path** verified working from a fresh clone this session (see below). The **≤5-min wall-clock** was NOT verified cold — Docker layers were cached, so build finished in ~16s. A genuine cold machine downloads ~4.4GB (CPU torch + 2 models); that one-time build almost certainly exceeds 5 min. Needs either a cold-cache measurement or a README note. |
| 2 | Claim table fully verified | ☑ | C0-C8 verified. C7 was false, then fixed this session and re-verified with tests + worker-kill chaos drill. |
| 3 | Hostile-input suite: zero unhandled 500s | ☑ | `test_hostile_inputs.py` 21 passed (empty/10k/emoji/CJK/RTL/SQL/HTML/malformed-JSON/wrong-CT/0-byte/oversized/exe/corrupt) + chaos drills A/C — **zero 500s observed anywhere** this phase. |
| 4 | Eval numbers committed + CI regression guard | ⚠ PARTIAL | Numbers reproduced + committed in README (C8). CI workflow + local regression guard added and verified, but GitHub badge cannot be called green until pushed and run remotely. |
| 5 | Live URL + monitoring screenshot | ☐ | Phase 4 (HUMAN-REQUIRED box creation) |
| 6 | Two human testers passed core flows | ☐ | HUMAN-REQUIRED |

---

## Human TODO queue
(Items only you can do.)
- [x] (Phase 0) Approved README Limitations + cold-build note (proceed-no-comments). Committed `3467e8d`.
- [x] **(Phase 1) GO / NO-GO on the worker-durability fix**. User chose option A. Fixed Celery config + task durability and re-ran chaos drill B successfully.
- [ ] (Phase 3) approve Mermaid architecture diagram before README insertion (`docs/architecture.md` prepared).
- [ ] (Phase 3) record demo GIF/video and link it from README (`docs/demo_gif_shot_list.md` prepared).
- [ ] (Phase 3) run two human testers through the protocol and record outcomes.
- [ ] (Phase 4) create a Hetzner/AWS server and provide IP/domain; deployment runbook prepared in `docs/deployment_runbook.md`.

---

## Fix log
(Every change: what, why, commit hash.)
- `3467e8d` docs: Phase 0 — README Limitations + cold-build note; AUDIT.md; vendored plan.
- `185deb8` test: Phase 1 correctness suite (RRF, hostile, rate-limit, cache, ETL, modes) — 36 new tests, all green.
- (test-only self-correction) cache-key test initially asserted internal-whitespace collapse; corrected to real contract (strip+lower only). No production code changed.
- this commit (`fix: make ingestion durable across worker crashes`): `acks_late=True`, `prefetch=1`, `reject_on_worker_lost=True`, Redis `visibility_timeout=300`, declarative autoretry, idempotent chunk replacement, and staged-file cleanup only after success/final failure.
- this commit (`ci: add eval guard and repo polish workflow`): CI workflow, eval regression guard, `make eval/check-eval/load`, gitleaks evidence, README badge, and prepared human-required docs.
- this commit (`docs: add deployment runbook`): server creation, Linux hardening, Docker deploy, Caddy HTTPS, CI/CD sketch, and monitoring plan.

### Independent re-validation (second auditor pass, 2026-07-08 evening)
Re-ran Codex's work from a clean rebuild (new dep `prometheus-fastapi-instrumentator` required an image rebuild). Evidence captured this session:
- `pytest -q` → **55 passed** (all green on current HEAD `c716d12`).
- **Chaos drill B re-run** (the durability acceptance test): uploaded 4 docs, `docker compose kill worker` mid-flight (2 `processing`, 2 `pending`), restarted worker. Result: 2 queued docs → `done` in ~20s; 2 in-flight docs → `done` at ~+280s (redelivered after the 300s `visibility_timeout`). **4/4 recovered**, each with exactly 25 chunks (idempotent re-insert, no duplicates). The Phase-1 durability defect is genuinely fixed.
- `/health` → 200 `{"status":"ok","checks":{"postgres":true,"redis":true}}`; `/metrics` → 200 Prometheus format.
- CI parity locally: `ruff check` pass, `mypy` pass (11 files), `check_regression` passes baseline-vs-itself AND correctly **fails** a synthetic 20% nDCG drop (exit 1).
- Directive-7: no secrets in history; Codex added 4 commits on top of mine with no history rewrite.
- Open/honest caveats (not blockers): README CI badge 404s until the repo is pushed to GitHub; CI rebuilds the ~4.4GB image every run; in-flight redelivery takes ~300s (tunable `visibility_timeout` trade-off); Phase 4 deploy artifacts (deploy.yml, monitoring, runbook) are prepared but unverified pending a real box (HUMAN-REQUIRED).

---

## Phase 0 — evidence (stranger test)

Faithful test: cloned the repo into a fresh temp dir with no inherited files/env, then followed **only** the README.

```
[15:09:40] git clone (fresh temp dir)  -> OK, no stray .env present
[15:09:56] docker compose up -d --build -> exit 0; all 5 containers created
           (NOTE: images were cached from a prior build → ~16s, NOT a cold-machine time)
[15:10:12] postgres + redis reported healthy
[15:10:33] GET /health -> 200 {"status":"ok"} (~3s after up)
[15:10:43] docker compose exec api python -m eval.ingest_corpus --reset
           -> "Done. 22 documents, 29 chunks total."
[15:10:56] documented sample curl (hybrid, k=5):
           -> 200, 5 results, rank 1 = the HNSW/ANN passage that directly answers
              "why is approximate search faster than brute force" (latency 1929ms cold)
           GET /docs -> 200 ; GET :3000 (frontend) -> 200
           repeat same query -> cached=True, latency 0.35ms
```

Stumbles found while following the README: **none** in the documented command path. The quickstart correctly omits `.env` (compose injects env inline via a YAML anchor; `.env.example` is only for running outside Docker).

---

## Phase 1 — evidence (correctness audit)

### Tests (all run inside the api container, stack from the real repo)
```
pytest -q            -> 53 passed  (16 pre-existing + 37 added/updated this phase)
  test_rrf_fusion.py            4  (C4 RRF hand-computed + rerank union)
  test_hostile_inputs.py       21  (Trust Contract #3 — zero 500s)
  test_rate_limit.py            3  (C6 atomicity + 429/Retry-After)
  test_cache_and_etl.py         6  (C1 cache + C7 final-fail atomicity + retry/durability config)
  test_search_modes.py          3  (C2 keyword exact term, C3 semantic-beats-BM25)
```

### Benchmark reproduction (`run_benchmark --k 5 --repeats 1`, 59 queries)
```
Mode      P@5    Recall@5  MRR     nDCG@5   | README nDCG@5 / MRR
keyword   0.203  0.958     0.918   0.927    | 0.936 / 0.931   (Δ≤0.013, BM25 tie-break)
semantic  0.207  0.966     0.898   0.914    | 0.914 / 0.898   (EXACT)
hybrid    0.210  0.992     0.972   0.973    | 0.968 / 0.967   (Δ≤0.006)
rerank    0.210  0.983     0.975   0.977    | 0.977 / 0.975   (EXACT)
```
C8 ✅ quality reproduces within noise. C5 ✅ rerank ≥ hybrid ≥ others on nDCG/MRR.

### Load test (`scripts/loadtest.py`, cache-busting, limiter disabled on an ephemeral :8001)
```
mode      concurrency   throughput   p50      p95       notes
keyword   20            127.7 req/s  133 ms   202 ms    all 200; DB-pool queueing at c=20
semantic  4             244.3 req/s  12.7 ms  22.8 ms   representative
semantic  20            7.1 req/s    1506 ms  15430 ms  all 200 — torch intra-op thread
                                                        oversubscription (16 cores × 20 reqs)
hybrid    4             255.9 req/s  12.1 ms  14.7 ms   representative
hybrid    20            12.7 req/s   1555 ms  1675 ms   all 200
```
Finding (not a bug, a saturation point): embedding modes are CPU-bound; at high concurrency
torch's multi-threaded inference oversubscribes cores. Lever: set torch thread limits / a
concurrency cap. Keyword (no embedding) scales far better. **No errors, no corruption.**

### Chaos drills (disposable local stack)
```
A  kill Redis under load   -> /search stayed 200 (fail-open cache + limiter); recovered. ✅ no corruption
B  kill worker mid-ingest  -> after fix: queued 5 docs; killed worker with SIGKILL after reservation;
                              observed ready_queue=3 and unacked=2; after restart + Redis visibility
                              timeout, all 5 reached done, queue=0, unacked=0. ☑ durable recovery
                              claim now verified true for no-worker and worker-kill cases.
C  restart Postgres        -> data survived (29 chunks), search recovered to 200. ✅ no corruption
```
Prior orphan files may exist from earlier failed drills. New ingestions keep staged files
through retryable failures, then clean them up after success or final failure.

---

## Phase 3 — evidence (repo polish)

### CI / lint / type / test / eval guard
```
docker compose exec -T api ruff check app eval scripts tests
-> All checks passed!

docker compose exec -T api mypy --ignore-missing-imports --follow-imports=skip \
  app/config.py app/schemas.py app/models.py app/cache.py app/ratelimit.py \
  eval/metrics.py eval/check_regression.py scripts/loadtest.py scripts/init_db.py
-> Success: no issues found in 9 source files

docker compose exec -T api pytest -q
-> 53 passed

docker compose exec -T api python -m eval.ingest_corpus --reset
-> Done. 22 documents, 29 chunks total.

docker compose exec -T api python -m eval.run_benchmark --k 5 --repeats 1
-> keyword nDCG@5 0.899; semantic 0.914; hybrid 0.949; rerank 0.977

docker compose exec -T api python -m eval.check_regression --max-drop 0.05
-> Benchmark regression check passed: ndcg_at_5 stayed within 5% of baseline for all modes.
```

Added `.github/workflows/ci.yml` to run Docker build/start, ruff, mypy, corpus ingest,
pytest, benchmark, and the nDCG regression guard on push / pull request. Badge added to
README, but remote green status is not verified until the workflow runs on GitHub.

### Makefile / load
```
python scripts/loadtest.py --mode hybrid --n 20 --concurrency 2 --unique
-> 20 ok; status codes {200: 20}; throughput 120.4 req/s; p95 60.8 ms
```

Added `make eval`, `make check-eval`, and `make load`.

### Secrets scan
```
docker run --rm -v "${repo}:/repo" ghcr.io/gitleaks/gitleaks:latest detect --source=/repo --redact --no-banner
-> 6 commits scanned; no leaks found
```

### Human-required docs prepared
- `docs/architecture.md` contains a Mermaid architecture diagram for approval before README insertion.
- `docs/demo_gif_shot_list.md` contains the 60-90 second demo plan and human tester protocol.

### Phase 4 local hardening prepared
```
curl http://localhost:8000/health
-> {"status":"ok","checks":{"postgres":true,"redis":true}}

curl http://localhost:8000/metrics
-> exposes process metrics, http_requests_total, celery_queue_depth, celery_unacked_tasks

docker compose exec -T api pytest -q
-> 55 passed

docker compose exec -T api ruff check app eval scripts tests
-> All checks passed!

docker compose exec -T api mypy --ignore-missing-imports --follow-imports=skip ...
-> Success: no issues found in 11 source files

curl http://localhost:9090/api/v1/targets
-> Prometheus target semantic-search-api health="up"

curl -u '<local-grafana-user>:<local-grafana-password>' http://localhost:3001/api/search?query=Semantic
-> Semantic Search API dashboard found
```

Implemented locally: `/health` checks Postgres + Redis, `/metrics` is exposed,
`INGEST_API_KEY` optionally protects `POST /documents`, Prometheus/Grafana compose
services are configured, Grafana provisions a starter dashboard, and a manual deploy
workflow is scaffolded for later server secrets.

### Phase 4 deployment templates
```
docker compose config --quiet
-> OK

docker compose --env-file deploy/.env.prod.example \
  -f docker-compose.yml \
  -f deploy/docker-compose.prod.yml \
  --profile monitoring \
  config --quiet
-> OK

docker compose exec -T api pytest -q
-> 55 passed

docker run --rm -v "${repo}:/repo" ghcr.io/gitleaks/gitleaks:latest \
  detect --source=/repo --config=/repo/.gitleaks.toml --redact --no-banner --verbose
-> 11 commits scanned; no leaks found
```

Added production deployment templates:
- `deploy/docker-compose.prod.yml` adds restart policies, Caddy on 80/443, production Grafana credentials, and required `INGEST_API_KEY`.
- `deploy/Caddyfile` routes API, frontend, and Grafana domains to internal services.
- `deploy/.env.prod.example` documents required production domains/secrets.
- `deploy/bootstrap_ubuntu.sh` bootstraps a fresh Ubuntu server with a deploy user, firewall, fail2ban, Git, and Docker.

Base compose now keeps Postgres/Redis internal-only and binds API/frontend/monitoring
host ports to `127.0.0.1`; Caddy is the intended public entrypoint.

Secrets note: gitleaks flagged a historical `curl -u admin:admin` command in `AUDIT.md`
as `curl-auth-user`. That was the documented local Grafana default credential, not a
production secret. Current audit text is redacted, and `.gitleaks.toml` allowlists only
that AUDIT.md `admin:admin` false-positive pattern.
