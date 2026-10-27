// Reproduce: VERISENSE_URL=http://127.0.0.1:5186 node scripts/smoke-ui.mjs
// Uses installed Edge; starts no servers and never changes approval decisions.
import { chromium, expect } from '@playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const base = process.env.VERISENSE_URL ?? 'http://127.0.0.1:5186';
const images = fileURLToPath(new URL('../../docs/images/', import.meta.url));
const evaluation = JSON.parse(await readFile(new URL('../src/site/data/evaluation.generated.json', import.meta.url), 'utf8'));
await mkdir(images, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const errors = [], failedResponses = [], checks = [];
page.on('pageerror', error => errors.push(error.message));
page.on('response', response => { if (response.url().startsWith(base) && response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`); });
async function visit(route) {
  await page.goto(base + route);
  await expect(page.locator('h1, h2').first()).toBeVisible();
  await expect(page.locator('body')).not.toContainText('Something went wrong');
  checks.push(route);
}
async function shot(name) {
  await page.screenshot({ path: path.join(images, name + '.png'), fullPage: false });
}
async function login(username) {
  await page.goto(base + '/portal/login');
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill('Demo@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL(url => !url.pathname.endsWith('/login'));
  await expect(page.locator('h1').first()).toBeVisible();
}
try {
  for (const route of ['/', '/how-it-works', '/architecture', '/compliance', '/evaluation', '/docs']) {
    await visit(route);
    if (route === '/') await shot('landing');
    if (route === '/evaluation') {
      await expect(page.getByText(evaluation.results.extraction.headline, { exact: true })).toBeVisible();
      await shot('evaluation');
    }
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await visit('/evaluation');
  const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  if (mobileOverflow) throw new Error('Evaluation page overflows mobile viewport');
  await shot('evaluation-mobile');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login('officer.wro');
  await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  await shot('dashboard');
  for (const route of ['/portal/applications', '/portal/sources', '/portal/rules', '/portal/alerts', '/portal/audit']) await visit(route);
  // Log in through UI as admin for all-region scenario checks.
  await page.evaluate(() => localStorage.clear());
  await login('admin');
  const auth = await context.request.post(base + '/api/auth/login', { data: { username: 'admin', password: 'Demo@2026' } });
  const { accessToken } = await auth.json();
  const response = await context.request.get(base + '/api/applications', { headers: { Authorization: `Bearer ${accessToken}` } });
  const apps = await response.json();
  const list = Array.isArray(apps) ? apps : apps.items;
  if (!list || list.length !== 12) throw new Error(`Expected 12 demo applications, got ${list?.length}`);
  for (const app of list) {
    await visit(`/portal/applications/${app.id}`);
    await expect(page.getByRole('tab', { name: 'Overview', exact: true })).toBeVisible();
    for (const tab of ['Documents', 'Findings', 'Verification', 'Infrastructure', 'Audit trail', 'Report']) {
      await page.getByRole('tab', { name: new RegExp('^' + tab) }).click();
      await expect(page.getByRole('tabpanel')).toBeVisible();
      await expect(page.getByRole('tabpanel')).not.toContainText('No documents uploaded');
    }
  }
  await visit('/portal/applications/4?tab=verification');
  await expect(page.getByRole('tabpanel')).toContainText('Source unavailable');
  await shot('verification');
  await visit('/portal/applications/1');
  await expect(page.locator('body')).toContainText('Low risk');
  await shot('clean-application');
  await visit('/portal/applications/3?tab=findings');
  await shot('findings');
  await visit('/portal/applications/3?tab=documents');
  const detailResponse = await context.request.get(base + '/api/applications/3', { headers: { Authorization: `Bearer ${accessToken}` } });
  const detail = await detailResponse.json();
  const tampered = detail.documents.find(d => d.fileName === 'land_khatauni_extract_scan.jpg');
  if (!tampered) throw new Error('Tampered scan fixture missing');
  await visit(`/portal/applications/3?tab=documents&doc=${tampered.id}`);
  const ela = page.getByRole('switch');
  await expect(ela).toBeVisible();
  await ela.click();
  await expect(ela).toBeChecked();
  await expect(page.getByRole('img', { name: 'land_khatauni_extract_scan.jpg' })).toBeVisible();
  await shot('document-ela');
  await visit('/portal/rules');
  await shot('rules');
  await visit('/portal/audit');
  await shot('audit');
  if (errors.length || failedResponses.length) throw new Error(JSON.stringify({ errors, failedResponses }));
  console.log(JSON.stringify({ passed: true, routes: checks.length, applications: list.length, tabsPerApplication: 7, consoleErrors: errors, failedResponses }, null, 2));
} finally {
  await writeFile(path.join(images, 'ui-checks.json'), JSON.stringify({ checks, errors, failedResponses }, null, 2));
  await browser.close();
}
