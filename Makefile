# Convenience wrapper around docker compose. On Windows, run these from Git Bash,
# or just copy the underlying `docker compose ...` commands (see README).

.PHONY: build up down logs ps init ingest benchmark sweep test shell clean

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

benchmark:    ## Run the 4-mode benchmark -> eval/results/benchmark.{json,md,png}
	docker compose exec api python -m eval.run_benchmark --k 10 --repeats 3

sweep:        ## Run the chunk-size sweep -> eval/results/chunk_sweep.{json,png}
	docker compose exec api python -m eval.chunk_sweep --sizes 200 400 600

test:         ## Run the test suite inside the api container
	docker compose exec api pytest

shell:        ## Open a shell in the api container
	docker compose exec api bash

clean:        ## Stop the stack AND delete volumes (postgres data + uploads)
	docker compose down -v
