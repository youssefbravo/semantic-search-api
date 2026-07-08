# Audit Status — semantic-search-api

Last updated: 2026-07-08 | Phase: 0 (complete, pending your quiz + README sign-off) | Overall Trust Contract: 0/6 fully checked

> Single source of truth for this audit. On a new session, read this file first and resume from the recorded phase.
> Evidence rule: a box is ☑ **only** when a command was run **this session** and its output is quoted here.

---

## Claim Verification Table
(Built out fully in Phase 1.1. Seeded here; most rows verified in Phase 1.)

| # | Claim | Verification method | Evidence (cmd + result) | Status |
|---|-------|---------------------|-------------------------|--------|
| C0 | Documented onboarding path works from a fresh clone | Fresh `git clone` → `docker compose up -d --build` → `ingest_corpus --reset` → documented curl | See Phase 0 evidence below — all steps succeeded, sample query returned the correct HNSW/ANN passage at rank 1 | ☑ |
| C1 | Cache actually caches | Repeat identical query, assert `cached=true` + latency drop | Same query twice: `cached=False latency=1929.72ms` → `cached=True latency=0.35ms` | ☑ (smoke; formal test in Phase 1.3) |
| C2 | BM25 (keyword) mode works | Phase 1 test: known corpus/query, expected doc in top-k | pending | ☐ |
| C3 | Vector (semantic) mode works | Phase 1 test: paraphrase query finds doc BM25 misses | pending | ☐ |
| C4 | Hybrid RRF works | Phase 1 test: RRF output matches hand-computed fusion | pending | ☐ |
| C5 | Reranker improves ranking | Phase 1 eval: nDCG@k rerank ≥ hybrid on labeled set | pending | ☐ |
| C6 | Rate limiter is atomic | Phase 1 test: N concurrent requests, exactly C pass | pending | ☐ |
| C7 | ETL survives failure | Phase 1 test: kill worker mid-task → retry → index consistent | pending | ☐ |
| C8 | Benchmark numbers reproduce | Phase 1: re-run `run_benchmark`, compare to README table | pending | ☐ |

---

## Trust Contract
| # | Contract item | Status | Evidence |
|---|---------------|--------|----------|
| 1 | Stranger test ≤5 min | ⚠ PARTIAL | Onboarding **path** verified working from a fresh clone this session (see below). The **≤5-min wall-clock** was NOT verified cold — Docker layers were cached, so build finished in ~16s. A genuine cold machine downloads ~4.4GB (CPU torch + 2 models); that one-time build almost certainly exceeds 5 min. Needs either a cold-cache measurement or a README note. |
| 2 | Claim table fully verified | ☐ | Phase 1 |
| 3 | Hostile-input suite: zero unhandled 500s | ☐ | Phase 1.3 |
| 4 | Eval numbers committed + CI regression guard | ☐ | Phase 1.2 / Phase 3 |
| 5 | Live URL + monitoring screenshot | ☐ | Phase 4 (HUMAN-REQUIRED box creation) |
| 6 | Two human testers passed core flows | ☐ | HUMAN-REQUIRED |

---

## Human TODO queue
(Items only you can do. None actionable yet — populated in Phase 3/4.)
- [ ] (Phase 0, optional) Decide: measure a true cold build time, OR approve a README note that first build downloads ~4.4GB and takes N minutes.
- [ ] (Phase 0) Approve the honest "Limitations" section wording before it goes in the README (your judgment to sign off).

---

## Fix log
(Every change: what, why, commit hash. Nothing committed yet — awaiting your Phase 0 sign-off.)
- (pending) `docs:` add honest Limitations section + cold-build note to README — awaiting your approval of wording.

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
