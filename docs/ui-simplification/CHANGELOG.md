# Changelog — portal simplification

## Added

- Role-aware next-action and workflow-stage helpers, verification guidance and eight focused tests.
- Deferred-content error boundary with a reload action.
- Four-role synthetic workflow acceptance test and failure/responsive browser checks.
- Audit/integration report, complete file inventory, visual comparison and test evidence.
- `/help` public route to avoid the backend API documentation URL.

## Simplified

- Role landing routes, sidebar, top bar, institution application list, wizard, application header and detail navigation.
- Document selection and analysis, source evidence disclosure, provenance/technical sections, record details.
- Login, public header/footer/landing and in-app help instructions.
- Dashboard chart loading, route/tab code splitting, reduced motion, focus states and alert skeleton sizing and stable placeholder keys.
- Error and retry feedback for document upload, draft checks, recognised text and deferred chunks.

## Removed UI elements

- Timer-driven upload stage simulation.
- Duplicate mobile document selector, duplicate sidebar New application entry and disabled Profile (prototype) menu entry.
- Repeated default header summary/report buttons and landing sample-statistic/feature galleries.

## Deleted files, dependencies, backend endpoints

None. Rules, scoring, state transitions, verification outcomes, role permissions, audit logs, decision notes, evidence and reports retain their existing backend behavior.
