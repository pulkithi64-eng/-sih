# Acceptance gate - 27 October 2026

Update: subsequent local hosting checks now pass for frontend lint/typecheck/test/build, 67 backend tests and running API smoke checks. See LOCAL_HOSTING.md for current evidence, warnings and dependency advisories. The original inventory below and check-results.json record the earlier environment before portable runtimes were installed; production gates remain open.

See check-results.json for actual command status from this environment. PASS on source inventory is not equivalent to tests passing. NOT RUN checks are release blockers.

| Gate | Status | Evidence / next command |
|---|---|---|
| Source/router/config review | PASS | TEAM_AUDIT.md, BASELINE.md; static review only |
| Frontend lint | NOT RUN | cd frontend; npm run lint |
| Frontend typecheck | NOT RUN | cd frontend; npm run typecheck |
| Frontend tests | NOT RUN | cd frontend; npm test |
| Frontend build | NOT RUN | cd frontend; npm run build |
| Backend regressions | NOT RUN | cd backend; uv run --frozen pytest |
| npm dependency audit | NOT RUN | cd frontend; npm audit --omit=dev --audit-level=high |
| Python dependency audit | NOT RUN | uv export --frozen --no-dev --no-hashes -o requirements-audit.txt; uvx pip-audit -r requirements-audit.txt |
| Container config/build | NOT RUN | docker compose config --quiet; docker compose build |
| Read-only running API smoke | NOT RUN | python scripts/smoke.py --base-url http://localhost:8001 |
| Browser/four-role/axe/responsive | NOT RUN | Start synthetic stack, run frontend/scripts/smoke-ui.mjs; expand automated journeys/axe |
| PostgreSQL migrations and recovery | NOT RUN | Not implemented; see RUNBOOK.md |
| Held-out evaluation/latency/load | NOT RUN | Existing evaluation is historical synthetic data; no new measurements |
| Human review and release tag | NOT RUN | Configure protection, review actual CI results, resolve blockers, then tag |

No database/schema resets were executed. Master prompt status and changed files are in MASTER_PROMPT_STATUS.md and CHANGE_SUMMARY.md. Performance, accessibility, security and deployment exceptions are in RELEASE_BLOCKERS.md.
