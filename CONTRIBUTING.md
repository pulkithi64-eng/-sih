# Contributing

Use `feat/M3-07-region-scoping`, `fix/M1-11-report-errors` or `docs/M1-01-audit` branches. Keep changes scoped to a numbered requirement. See docs/TEAM_CONTRACTS.md for ownership; agree before editing another member's shared contract.

Install locked dependencies with `cd backend; uv sync --frozen` and `cd frontend; npm ci`. Use synthetic data only. Tests must use temporary database, storage and source-state paths. Never run a seed reset or refresh on a shared database as part of CI or smoke checks.

Before merging, run frontend lint, typecheck, tests and build; backend pytest; and the applicable dependency audits in `.github/workflows/ci.yml`. Document any NOT RUN checks and keep the PR unmerged until required checks pass. Do not suppress failing checks to obtain a green build.

Repository administrators must enable branch protection for main: require the frontend/backend/container checks, one human approval, dismissal of stale approvals, conversation resolution, and no force pushes. A workflow file cannot enforce human review by itself. `.github/CODEOWNERS.proposal` needs actual handles before activation.

Preserve REST compatibility and stored evidence. New services require an ADR with measured benefit. No simulated authority result may be described as an authorised verification. Report measured versus estimated metrics separately and include fixture provenance.
