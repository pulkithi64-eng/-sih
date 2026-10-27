# Implementation handoff

## Architecture

Retained React/Vite, centralized typed REST client, FastAPI, SQLAlchemy and local document AI. No Express/PHP service, schema migration or destructive data action. ADR: adr/0001-retain-fastapi.md. SQLite demo deployment remains; PostgreSQL operational support is deferred explicitly.

## Numbered delivery

Completed source-review/documentation/conditional-no-op IDs: M1-01, M1-03, M1-05, M3-17, M3-18. Implementation portions address M1-02/04/06-11/14-15/17-20, M2-01/12/16-17/20, M3-02/05/07-09/11-13/19-20, M4-18, M5-10/11 and M6-01/02/03/07-10/14/15/17/20. These code-related IDs are partial or unverified. See MASTER_PROMPT_STATUS.md for every one of the 120 IDs; no blanket completion claim.

## Changed files

Backend: app/config.py, security.py, main.py, audit.py, tracing.py (new), workflow.py (new), upload_validation.py (new), adapters/registry.py, engine/ingest.py, routers/auth.py, applications.py, institutions.py, findings.py, documents.py, audit_log.py; serve.py; .env.example.

Tests: backend/tests/conftest.py, test_api.py, test_release_guards.py (new); frontend/src/test/api.test.ts (new). The existing decision test now requires reasoned resolution rather than allowing escalation to unlock approval. The deliberate audit-tamper test restores its fixture and database triggers after asserting detection.

Frontend: src/lib/api.ts, hooks.ts, app/PortalApp.tsx, app/pages/InstitutionsPage.tsx, app/pages/application/ActionDialogs.tsx, FindingsTab.tsx, ReportTab.tsx, SummaryTab.tsx, app/pages/wizard/StepDocuments.tsx. Corrected role-helper argument types, administrative controls, approval guard, cache invalidation, report errors, request IDs, cancellation and filename sanitization.

Operations: .github/workflows/ci.yml, .github/pull_request_template.md, .github/CODEOWNERS.proposal, CONTRIBUTING.md, compose.staging.yaml, scripts/check.ps1, scripts/smoke.py. Existing Dockerfile/compose.yaml are retained.

Documentation: TEAM_AUDIT.md, BASELINE.md, TEAM_CONTRACTS.md, UI_AUDIT.md, adr/0001-retain-fastapi.md, RUNBOOK.md, RELEASE_BLOCKERS.md, RELEASE_CHECKLIST.md, FINAL_DEMO.md, MASTER_PROMPT_STATUS.md, check-results.json and this file; README/API/hosting/security addenda point to current behavior.

## Routes and endpoints

Existing UI routes preserved; relevant fixes wired into `/portal/institutions`, `/portal/applications/:id` (findings, director decision, summary, PDF report), `/portal/applications/:id/edit` and upload wizard. Authenticated routes wait for session initialization. No new fake counters, success states or unrelated pages.

REST paths preserved. Behavior hardened: GET applications/institutions/audit; POST institutions; PATCH institutions/{id}; POST applications/{id}/documents; PATCH applications/{id}; POST applications/{id}/validate and /decision; PATCH findings/{id}; POST documents/{id}/verify; GET applications/{id}/processing-summary; GET health/system. Existing report.pdf uses authenticated blob transport; report JSON service errors now get retry UI. All regular API responses/errors include a safe request ID; audit details link it to persisted actions. Mock routes are mounted only in demo mode.

## Database/auth

No schema/data migration. Existing SQLite tables, relationships, hashes and append-only triggers preserved; new requestId enters new event details without altering historic hashes. Regionless staff denied; applicant official-record edits prohibited; director creation region scoped; only admin edits official records. Invalid signed token subject returns 401. Non-demo logins reject accounts with known demo password. Environment validation rejects unsafe deployment defaults; session revocation/reset remains pending.

## Evidence and running

`powershell -NoProfile -File scripts/check.ps1` was blocked by Windows execution policy. Running with process-only `-ExecutionPolicy Bypass` successfully produced check-results.json and returned a failing gate because all seven commands were NOT RUN (npm, uv and Docker unavailable). No persistent execution policy was changed. PowerShell JSON parsing and 120-ID inventory checks passed; source/file review passed. Python/TypeScript/runtime tests, browser checks, dependency scans, image build, benchmarks, load and recovery were NOT RUN. Test additions are unverified code, not passing evidence.

RUNBOOK.md has exact local/container commands and rollback procedure. RELEASE_BLOCKERS.md lists remaining gaps with owners/reproduction. FINAL_DEMO.md contains the seven-minute rehearsal, including expired/tampered/source-down/rectification/director cases. No Git release/tag or production readiness is claimed.
