// Controlled local navigation measurements, not a Lighthouse score.
// node scripts/measure-performance.mjs --output ../.local-run/perf-before.json
import { chromium } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

const base = process.env.VERISENSE_URL ?? 'http://127.0.0.1:8001';
const output = process.argv[process.argv.indexOf('--output') + 1];
if (!process.argv.includes('--output') || !output) throw new Error('--output is required');
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const results = [];
try {
  for (const viewport of [{ width: 390, height: 844 }, { width: 1365, height: 900 }]) {
    const context = await browser.newContext({ viewport });
    const login = await context.request.post(`${base}/api/auth/login`, { data: { username: 'officer.wro', password: 'Demo@2026' } });
    if (!login.ok()) throw new Error(`Demo login failed: ${login.status()}`);
    const auth = await login.json();
    await context.addInitScript(({ accessToken, user }) => {
      localStorage.setItem('verisense.token', accessToken);
      localStorage.setItem('verisense.user', JSON.stringify(user));
      window.__perf = { fcp: null, lcp: null, cls: 0, shifts: [], errors: [] };
      let sessionStart = 0, sessionLast = 0, sessionValue = 0;
      new PerformanceObserver(list => {
        for (const e of list.getEntries()) if (e.name === 'first-contentful-paint') window.__perf.fcp = e.startTime;
      }).observe({ type: 'paint', buffered: true });
      new PerformanceObserver(list => {
        for (const e of list.getEntries()) { window.__perf.lcp = e.startTime; window.__perf.lcpElement = e.element?.tagName; }
      }).observe({ type: 'largest-contentful-paint', buffered: true });
      new PerformanceObserver(list => {
        for (const e of list.getEntries()) {
          if (e.hadRecentInput) continue;
          if (e.startTime - sessionLast > 1000 || e.startTime - sessionStart > 5000) { sessionStart = e.startTime; sessionValue = 0; }
          sessionLast = e.startTime; sessionValue += e.value;
          window.__perf.cls = Math.max(window.__perf.cls, sessionValue);
          window.__perf.shifts.push({ value: e.value, at: e.startTime, nodes: (e.sources ?? []).map(s => ({ tag: s.node?.tagName, class: s.node?.className, from: s.previousRect, to: s.currentRect })) });
        }
      }).observe({ type: 'layout-shift', buffered: true });
    }, auth);
    const page = await context.newPage();
    const failed = [];
    page.on('requestfailed', request => failed.push({ url: request.url(), error: request.failure()?.errorText }));
    page.on('pageerror', error => failed.push({ error: error.message }));
    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: 200000, uploadThroughput: 93750 });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
    await page.goto(`${base}/portal/alerts`, { waitUntil: 'load', timeout: 60000 });
    await page.getByRole('heading', { name: 'Alerts', exact: true }).waitFor();
    await page.waitForTimeout(6000);
    const metrics = await page.evaluate(() => ({ ...window.__perf, overflow: document.documentElement.scrollWidth > innerWidth + 1, resources: performance.getEntriesByType('resource').map(r => ({ url: r.name, bytes: r.transferSize, start: r.startTime, duration: r.duration })) }));
    results.push({ viewport, metrics, failed });
    await context.close();
  }
} finally { await browser.close(); }
await writeFile(output, JSON.stringify({ conditions: 'Cold cache, 150ms latency, 200kB/s download, 4x CPU slowdown; Edge; local server; two viewport sizes; one run each; not Lighthouse.', results }, null, 2));
console.log(JSON.stringify(results.map(r => ({ viewport: r.viewport, fcp: r.metrics.fcp, lcp: r.metrics.lcp, cls: r.metrics.cls, overflow: r.metrics.overflow, failed: r.failed })), null, 2));
