# Frontend audit

Static review only; fresh screenshots/browser/axe measurements NOT RUN (Node/browser build unavailable).

Existing public routes, prototype disclaimers, evaluation metrics, responsive headers, common badges/dialogs and role portal already exist. See BASELINE.md route/screenshot checklist and historical docs/images.

Priority findings:

1. Critical: ActionDialogs.tsx suggested approving despite critical findings. Fixed with unresolved-critical count, disabled approval, backend guard and explicit remediation guidance.
2. High: ReportTab.tsx collapsed service/permission errors into 'No report yet'. Fixed non-404 error/retry. All other query screens still need full fault-state review.
3. Medium: PortalApp.tsx redirected while stored-session validation was loading. Added initialization skeleton. Transient auth revalidation currently retains cached user; server authorization remains required.
4. Medium: lib/hooks.ts left processing summaries, cross-verification and institution views stale after case actions. Added invalidation.
5. Medium: FindingsTab.tsx allowed institution self-rectification. Removed institution resolution control; reviewers confirm with reason.
6. Medium: Upload accepted image/* despite narrower validation. Picker now explicitly PDF/PNG/JPEG; progress, draft conflict handling and complete wizard acceptance remain.
7. Remaining: English/Hindi key structure/language selector, full keyboard/focus/200% zoom/reduced-motion/320px checks, saved queue URL filters/pagination and accessible error summaries. Do not claim WCAG conformance without manual and automated evidence.
