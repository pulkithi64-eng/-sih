# Baseline inventory

Source baseline inspected 27 October 2026. This is a working-tree inventory, not a Git commit/tag: Git is unavailable. Preserve a source archive and database/storage backup before deployment. No local database was reset or seeded during this task.

Public React routes: `/`, `/how-it-works`, `/architecture`, `/compliance`, `/evaluation`, `/docs` (frontend/src/site/SiteApp.tsx).

Portal routes: `/portal/login`, `/portal/dashboard`, `/portal/applications`, `/portal/my-applications`, `/portal/institutions`, `/portal/applications/new`, `/portal/applications/:id/edit`, `/portal/applications/:id`, `/portal/rules`, `/portal/sources`, `/portal/alerts`, `/portal/audit` (frontend/src/app/PortalApp.tsx). Case tabs: overview, documents, verification, cross-verification, processing summary, findings, infrastructure, report and audit; inspect ApplicationDetailPage.tsx for current tab labels.

REST inventory is documented in API.md and implemented in backend/app/routers/*.py. Protected `/api` families: auth, meta, applications, documents, findings, dashboard, institutions, alerts, audit, rules, checklists and sources. Public probes `/api/health`, `/api/health/live`, `/api/health/ready`; `/api/health/system` requires ADMIN. `/mock` is demo-only. OpenAPI at `/openapi.json`, interactive docs `/docs` on the backend port.

Environment: backend/.env.example and app/config.py define SECRET, DB, STORAGE, SAMPLES, CONFIG_DIR, AUTOSEED, ENVIRONMENT, DEMO_MODE, FRONTEND_DIR, OCR_THREADS, OCR_CACHE, JWT_EXPIRY_HOURS, REFERENCE_DATE, CORS_ORIGINS and manual-effort estimate assumptions, prefixed VERISENSE_. Adapter transport also uses VERISENSE_MOCK_MODE, VERISENSE_MOCK_BASE, VERISENSE_MOCK_TIMEOUT, VERISENSE_SOURCES_STATE (see adapters/base.py/state.py). Container bootstrap accepts VERISENSE_DATA_DIR, VERISENSE_DEMO_SNAPSHOT and PORT. Frontend uses VITE_API_BASE and VERISENSE_BACKEND (build/dev settings; never put secrets in VITE variables).

Install/start: see RUNBOOK.md. Existing demo seed: `uv run python -m seed.seed` (synthetic only). `--refresh` changes synthetic records/analysis; run only on disposable backed-up demo state. `--reset` is destructive and must never be run on a shared database. Default local autoseed remains for compatibility; set AUTOSEED=0 for an existing database.

Checks: `frontend: npm run lint`, `npm run typecheck`, `npm test`, `npm run build`; `backend: uv run pytest`; read-only `python scripts/smoke.py --base-url http://localhost:8001`. `scripts/check.ps1` records PASS/FAIL/NOT RUN without installing dependencies or resetting data. Tests isolate database, storage and source toggles in temporary paths.

Screenshot checklist (NOT RUN for this change): public desktop/mobile, 320/375/768px portal navigation, keyboard menu/dialog/focus, institution draft/upload/error/submission, source outage and expired evidence, officer finding response, blocked director approval, authorized PDF, admin rules/audit, 200% zoom and reduced motion. Existing docs/images are historical references, not new acceptance evidence.
