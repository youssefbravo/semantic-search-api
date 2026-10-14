# Google Cloud demo preparation — not deployed

Deployment awaits an approved project ID, spending cap and access policy. No cloud
resource has been created for this project in this session. These files are preparation,
not a live demo or proof of deployment.

The API and Celery worker currently share a filesystem. A Google Compute Engine VM
running Docker Compose preserves this architecture: frontend, API, worker, ParadeDB and
Redis share an internal network. Use persistent storage and a TLS proxy for one demo
domain. An e2-standard-4 (4 vCPU, 16 GB) is a capacity candidate, not a measured minimum.
Confirm cost with the Google Cloud calculator and configure a budget alert before
provisioning. Budget alerts do not cap spending.

Cloud Run is not a direct substitute: files are not shared across independent instances,
Celery needs an active consumer, and ParadeDB is not a managed Cloud SQL configuration.
Moving there requires object storage and external services or a different read-only demo.

Public demos must use only the authored corpus and disable uploads. An API key embedded
in the browser cannot protect ingestion. The prepared proxy blocks uploads, document
status, API docs and metrics, caps bodies, and serves frontend/search through TLS. Private
documents need login, ownership and retrieval filtering before deployment.

After approval:

1. Confirm project, billing, budget, region, owner and demo DNS name. Review API permissions.
2. Provision the approved VM/disk; restrict administration to IAP or a named operator network.
   Expose only proxy ports 80/443 publicly; keep DB, Redis and monitoring internal.
3. Install Docker/Compose, clone the verified commit, and build images. Copy the example
   environment file locally; never commit real deployment environment files.
4. Start using the dedicated override and load the corpus internally:

   ```bash
   docker compose --env-file deploy/google-cloud/.env -f docker-compose.yml \
     -f deploy/google-cloud/compose.yml up -d --build
   docker compose exec -T api python -m eval.ingest_corpus --reset
   ```

5. Verify external TLS, four-mode UI search, upload rejection, hidden metrics, closed DB
   ports, health, resource usage and restart recovery. Record deployed commit and URL.
6. Define a stop date and review incurred costs. Cloud DNS/TLS/firewall behavior and pricing
   remain unverified until this deployment is actually performed.

References: [Compute Engine](https://cloud.google.com/compute/docs/instances/create-start-instance)
and [budget alerts](https://cloud.google.com/billing/docs/how-to/manage-budgets).
