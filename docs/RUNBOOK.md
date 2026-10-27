# Local and synthetic staging runbook

Prerequisites: Python 3.11, uv, Node 22/npm; Docker with Compose for containers. They are absent from this task environment's PATH. Install these separately before running checks.

## Local

1. Copy backend/.env.example to backend/.env and use a generated random secret. The example is local synthetic mode. Set AUTOSEED=0 to preserve an existing database. Never use real institutional documents in this demo.
2. In backend: `uv sync --frozen`, then `uv run uvicorn app.main:app --port 8001`.
3. In frontend: `npm ci`, then `npm run dev`. Open http://localhost:5176/portal/login. API docs: http://localhost:8001/docs.
4. Use the synthetic credentials in README.md only in demo mode. Optional seed command: `uv run python -m seed.seed` against a new disposable database. Neither `--reset` nor `--refresh` belongs in ordinary startup/checks.
5. From repository root: `python scripts/smoke.py --base-url http://localhost:8001`; on Windows `powershell -File scripts/check.ps1`. The latter returns nonzero for FAIL or NOT RUN.

## Containers

`docker compose up --build -d` builds the multistage frontend/FastAPI image, seeds synthetic data into an image snapshot, and initializes a new named volume on first run. It serves http://localhost:7860 and uses a non-root runtime. Existing volume/database is preserved by serve.restore_demo; do not use `down -v` on valuable state. Build requires network and potentially expensive OCR.

For explicitly synthetic staging, set a random VERISENSE_SECRET of at least 32 characters in the shell/root .env (never commit it), then run `docker compose -f compose.yaml -f compose.staging.yaml up --build -d`. Run `docker compose ps` and smoke.py against port 7860. Place behind an HTTPS reverse proxy with a 25 MiB request body limit plus multipart overhead and bounded timeouts. Ensure no public raw storage mount exists. The single worker avoids pretending the current audit lock is distributed-safe.

Staging override is SQLite/demo only and has NOT been built or executed here. No PostgreSQL deployment/migration success is claimed. Existing SQLAlchemy accepts a PostgreSQL URL, but psycopg driver, Alembic revisions, append-only SQL triggers, data export/import and rollback tests must be added before PostgreSQL is supported operationally. Do not point the current create_all startup at a populated production database and call it a migration.

## Backup and rollback

Stop writes before backup. Stop the container, then make an offline copy of the entire named volume including database, WAL/SHM if present, storage, source-state JSON and persisted JWT secret. Protect the backup and record its checksum/image identifier. For local SQLite, stop the backend and copy its data/storage directories together. Never copy a live SQLite file alone and claim consistency.

Restore drill: restore to a new disposable volume, use the matching image, confirm readiness, scoped document downloads, report generation, audit chain and row/document counts. This drill is NOT RUN. Roll back by stopping the new image and restoring the matching volume backup and prior image; never merge two SQLite files or selectively overwrite evidence. No schema migration is included in this change.

## Non-demo configuration

Production requires ENVIRONMENT=production, DEMO_MODE=false, AUTOSEED=0, explicit random secret, restricted CORS, separately provisioned accounts and storage. Accounts retaining the known demo password cannot log in outside demo mode. Mock routes are omitted and registry results become MANUAL_REVIEW_REQUIRED; real authority APIs are not implemented. Illustrative rules, demo QR trust store, JWT revocation gaps and SQLite audit/concurrency limits remain release blockers. See RELEASE_BLOCKERS.md. This mode is a safety boundary, not production certification.
