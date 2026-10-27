# Alerts performance improvements - 27 October 2026

The supplied Lighthouse screenshot reports FCP 4.2s, LCP 5.9s, CLS 0.662, TBT 30ms, approximately 566 KiB of cache-lifetime opportunities and a 1,200ms render-blocking opportunity. Its browser/network configuration is not available, so local measurements below are a separate experiment, not a replacement Lighthouse score.

## Changes

- Removed both Google Fonts stylesheet requests (index.html and the public site's CSS import). Inter is now a local variable WOFF2 asset with optional display, a font preload and its SIL OFL license. Vite fingerprints the font. Mono/Hindi text uses the existing local/system fallbacks when those named fonts are unavailable.
- The static SPA mount compresses public files with gzip. It serves fingerprinted `/assets/` files with `public, max-age=31536000, immutable`; HTML and SPA deep links revalidate with `no-cache`. Unfingerprinted files have a one-hour cache lifetime. Authenticated API/document responses retain their existing authorization and no-store behavior and are outside the static compression mount.
- Build-time route-specific module preloads start the matching lazy portal/page modules during HTML parsing, while retaining code splitting. They do not execute page actions or fetch application data.
- Alerts reserve action/filter space, use card-shaped loading rows and consistent minimum row heights, and wrap long messages. The portal main area reserves viewport height so a footer initially visible during loading does not jump below the loaded list. A stable scrollbar gutter avoids horizontal reflow.
- Global search fetches applications only after typing starts. Alert observers reuse fresh data for 30 seconds; mutation invalidation still refreshes read state.

## Controlled local result

Route: `/portal/alerts`, signed in as synthetic officer. Edge headless, cold cache, 150ms latency, 200,000 bytes/second download, 93,750 bytes/second upload and 4x CPU slowdown. One run at each viewport before and after, with a six-second observation period after load. This is not Lighthouse simulation and does not measure TBT or Speed Index.

| Viewport | Before FCP | After FCP | Before LCP | After LCP | Before CLS | After CLS |
|---|---:|---:|---:|---:|---:|---:|
| 390 x 844 | 14.020s | 2.864s | 14.372s | 3.196s | 0.06174 | 0 |
| 1365 x 900 | 14.184s | 2.400s | 14.568s | 2.648s | 0.00536 | 0 |

The baseline browser was denied access to fonts.googleapis.com; that failure contributes to its slow timings and limits comparison with the supplied screenshot. The final run has no failed requests/page errors and no horizontal overflow at either measured viewport. Raw evidence: performance/before.json and performance/after.json. Static asset transfer decreased from 574,337 bytes to 218,895 bytes, including the new local font (61.9% reduction).

Live HTTP verification confirms gzip, one-year immutable cache headers on the main JS bundle, and no-cache HTML. Backend regression checks also cover compressed content integrity, conditional 304 responses, cache revalidation and exclusion of private API responses from static compression.

## Validation and reproduction

PASS: frontend typecheck, build, 4 frontend tests; 68 backend tests (one dependency deprecation warning); frontend lint (27 existing warnings, no errors); local API smoke; build configuration TypeScript check. The new hosting fixture was corrected to write exact bytes on Windows instead of allowing CRLF conversion.

With the local server running and project dependencies installed:

```powershell
cd frontend
..\.local-tools\node-v22.23.4-win-x64\node.exe scripts/measure-performance.mjs --output ../.local-run/perf-current.json
```

For a comparable Lighthouse score, audit the same authenticated route using the same browser, throttling and session settings as the original run. Refresh the page to load the new build. Development-server responses and third-party hosting that bypasses FastAPI may have different caching/compression behavior. Mobile LCP remains above 2.5s under this local profile; a green score on all environments is not claimed. Further work should profile the shared portal JavaScript and use repeated runs before drawing broader conclusions.
