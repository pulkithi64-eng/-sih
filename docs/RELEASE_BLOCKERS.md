# Release blockers

Release status: NOT READY for production or a frozen demonstration release. No tag created, no deployment performed. Source changes require execution on a provisioned machine.

| Priority / owner | Blocker | Reproduction / required evidence |
|---|---|---|
| P0 M6 | Execution unavailable | Run scripts/check.ps1; npm/uv/docker absent -> NOT RUN. Install prerequisites, locked dependencies, run all checks and attach logs. |
| P0 M3/M6 | Concurrent workflow/audit writers | Race PATCH finding against approval, or concurrent decisions; no row lock/version token. Add transaction-level guards, optimistic concurrency and concurrent tests. Thread-only audit lock is insufficient across processes. |
| P0 M3/M6 | PostgreSQL/migrations/restore | Configure PostgreSQL URL; driver and migration workflow missing. Add migrations and PostgreSQL audit triggers, migrate disposable SQLite fixture and perform DB/file restore drill. |
| P0 M5 | Authorised sources absent | Non-demo Registry.verify returns MANUAL_REVIEW_REQUIRED. Obtain authorization/configure real adapters and trust-store separation before external verification claims. |
| P1 M3 | JWT revocation/reset/absolute lifetime | Change password/logout, replay previous JWT: remains usable until expiry. Add token revocation/version and controlled account recovery. |
| P1 M3/M4 | Synchronous CPU processing | Upload large valid PDF: request holds worker. Add durable jobs, idempotency, cancellation/deadlines, resource sandbox and malware quarantine hook. Current page/pixel limits are preliminary controls. |
| P1 M5 | Rule history/report reproducibility | Update override then inspect old report: rules snapshot coexists with live findings/current score. Add immutable revisions/effective dates/rollback and explicit snapshot-versus-live sections. |
| P1 M2/M6 | UI/accessibility/localization/browser acceptance | Run 320-768px, keyboard, zoom, axe and four-role browser journeys. Hindi framework and full route error-state integration remain. Historical screenshots are not current evidence. |
| P1 M3/M5 | Alert recipient semantics | Mark read as one scoped user; another sees same read state. Add per-recipient read records/dedup and optional non-sensitive mail adapter. |
| P1 M4 | Independent evaluation/forensic recall | Existing samples/evaluation.json is generated synthetic evaluation; independence not established. Anomaly recall is 5/12 = 41.7%. Freeze held-out provenance and benchmark before improving claims. |
| P1 M1/M6 | CI/review enforcement | Workflow committed but not executed; branch protection and real CODEOWNERS not configured. Run CI, configure one human review, resolve failures without suppression. |
| P2 M1/M2 | Full API schemas/type generation | Frontend models are handwritten. Add stable response_model declarations, OpenAPI generation/drift check and full cancellation propagation. |

Reproduction uses synthetic data only. No measured throughput, new accuracy, browser compliance, dependency-audit cleanliness or certification is asserted.
