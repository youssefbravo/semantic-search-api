# Convenience wrapper around docker compose. On Windows, run these from Git Bash,
# or just copy the underlying `docker compose ...` commands (see README).

.PHONY: build up down logs ps init ingest benchmark eval check-eval sweep load test shell clean

build:        ## Build the app image (downloads + bakes in the models)
	docker compose build

up:           ## Start the full stack (postgres, redis, api, worker)
	docker compose up -d

down:         ## Stop the stack (keep volumes/data)
	docker compose down

logs:         ## Tail logs from all services
	docker compose logs -f

ps:           ## Show service status
	docker compose ps

ingest:       ## Ingest the evaluation corpus (resets existing docs)
	docker compose exec api python -m eval.ingest_corpus --reset

benchmark:    ## Run the 4-mode benchmark -> a new timestamped eval/results directory
	docker compose exec api python -m eval.run_benchmark --k 5 --repeats 3

eval:         ## Run a one-repeat evaluation -> a new timestamped result directory
	docker compose exec api python -m eval.run_benchmark --k 5 --repeats 1

check-eval:   ## Fail if nDCG drops >5% vs eval/baseline/benchmark.json
	$(if $(CURRENT),,$(error Supply CURRENT=eval/results/<run>/benchmark.json))
	docker compose exec api python -m eval.check_regression --max-drop 0.05 --current "$(CURRENT)"

sweep:        ## Compare chunk sizes on dev probes -> a new timestamped directory
	docker compose exec api python -m eval.chunk_sweep --sizes 200 400 500

load:         ## Run a small cache-busting load smoke test against localhost:8000
	python scripts/loadtest.py --mode hybrid --n 20 --concurrency 2 --unique

test:         ## Run the test suite inside the api container
	docker compose exec api pytest --strict-integration -ra

shell:        ## Open a shell in the api container
	docker compose exec api bash

clean:        ## Stop the stack AND delete volumes (postgres data + uploads)
	docker compose down -v
