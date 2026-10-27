# UI simplification — integration and review

Implemented on branch `feat/portal-simplification`. This refactors the existing React/TypeScript portal and public site. The backend, database schema, scoring formulas, verification outcomes, API contracts and audit controls are unchanged.

## Audit: keep / simplify / hide / remove

| Area | Decision | Implementation and preserved dependency |
| --- | --- | --- |
| Role permissions and session | Keep | Existing route guards, API authentication, regional scope, token renewal and PII masking remain. Role home routes now lead to the relevant task. |
| Institution applications | Simplify | Status cards show the actual next action, document count, unresolved findings and workflow stage. New application leads into category, details, documents, check and submission. Existing application APIs remain authoritative. |
| Officer and director entry | Simplify | Officer opens Review queue; director opens Decision queue filtered to recommendations. Status, category, risk and search remain available; admin retains region filtering. |
| Sidebar | Simplify / hide secondary | Institution sees My applications, Alerts and My institution. Staff reference pages, overview and audit remain under Reference & audit. Admin retains rules/checklists, sources, institutions, audit and applications. |
| Application header | Simplify | Compact compliance, risk and unresolved findings; one role-appropriate primary action. Approval blocker and final decision remain visible. Secondary operations move into More actions. |
| Nine detail tabs | Hide secondary | Overview, Documents, Findings and Report remain visible. More details contains processing summary, cross-record checks, verification, infrastructure and audit. Existing tab URL values and API-backed content remain. |
| Document evidence | Keep / simplify | File names, types, all verification states, sources, confidence, comparisons, integrity evidence, provenance, original viewer and reports remain. Mismatch evidence opens by default. Technical sections expand on demand. |
| Interpretation | Simplify | Each verification state has a human next step. Issuer services are labelled simulated. Unavailable sources are not labelled fraud; integrity indicators are not presented as proof of forgery. |
| Institution correction | Simplify / repair | Deficiencies and rectification both open the correction journey. Resubmission uses the existing submit endpoint, which revalidates. It no longer calls the draft-only validate endpoint for a non-draft application. |
| Upload feedback | Remove redundant simulation | Timer-driven fake processing stages were removed. Real requests drive indeterminate progress, results, errors and retry. Client type/25 MB checks supplement server validation. |
| Dashboard charts | Hide secondary / defer | Overview remains available. Detailed charts mount and download only when expanded; real metrics and source API remain unchanged. |
| Public landing | Simplify | Three-step journey, one main sign-in action and explicit prototype limitations replace decorative sample statistics, gallery and repeated feature modules. Detailed reference pages remain. |
| Login | Simplify | Username/password first. Demo accounts and password are in an expandable section; session and role handling are preserved. |
| Duplicate document selector | Remove | One responsive document list replaces separate desktop navigation and a duplicate mobile selector. |
| Disabled profile entry | Remove | A nonfunctional prototype menu item was removed. Account, sign-out, PII and renewal controls remain. |
| Help URL | Repair | Help uses `/help`, avoiding FastAPI's existing `/docs` Swagger endpoint. The frontend `/docs` client route is retained as an alias; public links use `/help`. |
| Files, endpoints, dependencies | Keep | No backend endpoints, meaningful evidence, source assets, dependencies or routes were deleted. No file was deleted solely because it appeared unused. |

## Review the result

Open the running local site at http://127.0.0.1:8001/ and refresh any older tab. Sign in at `/portal/login`. For the local demo, all passwords are `Demo@2026`:

| Account | Initial destination | Main task |
| --- | --- | --- |
| `inst.piat` | My applications | New application or Upload documents / Correct application |
| `officer.wro` | Review queue | Review evidence, request corrections or record recommendation |
| `rd.wro` | Decision queue | Review recommendation and record a guarded decision |
| `admin` | Rules & checklists | Maintain rules, sources and review audit history |

An institution can manually test files by choosing **New application → category → Continue → Create draft & continue**. Existing draft cards have **Upload documents**. Select the appropriate checklist upload slot, then **Check documents → Submit for review**. Correction cards open findings and allow corrected uploads and resubmission.

The synthetic fixtures remain at `output/pdf/01_correct_demo_affiliation.pdf` and `output/pdf/02_imaginary_mismatch_affiliation.pdf`. They produce VERIFIED and MISMATCH_DETECTED respectively against the demo issuer. Verification does not approve an application.

## Screenshots and evidence

Open [comparison.html](comparison.html) for side-by-side screenshots. Matching screenshots are in [before](before/) and [after](after/): landing, login, institution list/mobile, document evidence, officer queue, director queue and admin rules. The screenshots use a live demo database. The after set includes synthetic application 14 created by the acceptance test, so counts differ from before.

[acceptance-results.json](acceptance-results.json) records the complete four-role workflow. [failure-responsive-results.json](failure-responsive-results.json) records fault injection, empty state, keyboard navigation and responsive checks. [regression-results.json](regression-results.json) records the existing suite's routes and runtime errors. [performance-results.json](performance-results.json) contains the measured cold-load profile and layout shift sources.

## Performance and accessibility

Application detail tabs and public pages now load separately. The detail route's own JavaScript chunk decreased from approximately 113 KB to 29.4 KB uncompressed; its dependencies still load when needed. Recharts remains installed and moves behind the overview's expandable detailed metrics. Build-time route preloads are retained for direct navigation. Alert loading placeholders have distinct keys from real alerts, preventing reused rows from jumping when data arrives. Shared query caches, existing skeletons, local font, static caching and compression remain.

Document file inputs now have accessible names. Expandable analysis sections expose state and controls; native details sections are keyboard operable. Focus rings and reduced-motion support were added. Mobile global search and breadcrumbs can shrink/wrap. Main institution, login, landing and document screens were checked at 320, 375, 768 and 1440 pixels without page overflow. Mobile navigation opens and closes with Escape. Wide evidence tables retain internal scrolling rather than discarding evidence.

Final measured `/portal/alerts` results:

| Viewport | First contentful paint | Largest contentful paint | Layout shift | Failed requests / page errors |
| --- | --- | --- | --- | --- |
| 390 ? 844 | 1.980 s | 2.208 s | 0.000 | 0 |
| 1365 ? 900 | 2.004 s | 2.196 s | 0.000 | 0 |

This is not a WCAG certification. Screen-reader testing, a full automated accessibility audit, field Core Web Vitals and production Lighthouse scores were not measured. The recorded performance profile is a single local run per width, cold cache, 150 ms latency, 200 kB/s download and 4× CPU slowdown; it is not a Lighthouse score or a production guarantee.

## Tests and limits

- Frontend TypeScript check and production build pass.
- Frontend: 12 tests pass across four files, covering role homes/navigation, workflow actions/stages and document uncertainty/evidence.
- Backend: 68 tests pass; one existing Starlette/httpx deprecation warning.
- ESLint: zero errors, 26 warnings (existing Fast Refresh and hook warnings).
- Real browser acceptance: UI sign-in for all four roles, new draft, both PDFs, deliberate upload/check service failures and recovery, submission, report PDF download, request corrections, resubmission, recommendation and final decision.
- Approval remains blocked by unresolved critical findings in both officer and director dialogs. Mandatory note, acknowledgement and confirmation remain. Backend admin-create 403, cross-region 404 and unauthenticated file 401 checks pass.
- Only a newly created synthetic application (14) was progressed to a final rejection by the acceptance test. Existing applications were not given approval or rejection decisions.
- Existing regression suite passes across 31 route visits and seven tabs for each of the twelve seeded cases, including PDF/image evidence, ELA, verification, reports, rules and audit, with no page errors or failed responses.
- Additional browser checks pass for honest empty lists, server-error retry, deferred-section download failure with recovery, mobile menu keyboard dismissal and responsive layouts.

The source adapters and handbook norms remain a prototype. Real issuer integration, production policy validation and usability research with actual institutional officers remain separate work. No official authority authentication or fraud determination is claimed.

## Integrate and reproduce

Review [CHANGELOG.md](CHANGELOG.md) and [FILES.md](FILES.md), then merge the feature branch through your normal repository workflow. No migration or new dependency is required. Do not commit runtime credentials or the local database. Keep production demo access disabled according to the existing deployment guide.

With dependencies installed:

```powershell
cd frontend
npm run typecheck
npm test
npm run lint
npm run build
cd ..\backend
.venv\Scripts\python.exe -m pytest -q
```

Rebuild `frontend/dist` and serve with the existing FastAPI setup, or use the existing Docker build. For the portable local setup, prepend `.local-tools/node-v22.23.4-win-x64` to PATH. The running server serves the latest built files. Start/stop helpers remain `scripts/start-local.ps1` and `scripts/stop-local.ps1`.

Browser checks (installed Edge, local server required):

```powershell
$env:VERISENSE_URL = 'http://127.0.0.1:8001'
node frontend/scripts/smoke-ux.mjs
node frontend/scripts/smoke-ux-states.mjs
$env:VERISENSE_SMOKE_OUTPUT = 'docs/ui-simplification/regression-rerun'
node frontend/scripts/smoke-ui.mjs
node frontend/scripts/measure-performance.mjs --output docs/ui-simplification/performance-results.json
```

`smoke-ux.mjs` deliberately creates a new synthetic application and records recommendation/final rejection through the UI; reruns create another case. Its output records the actual ID. Other browser checks read existing seeded cases and simulate network failures in the browser only.
