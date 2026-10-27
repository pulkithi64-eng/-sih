// Rechecks the existing test draft; creates no new applications or uploads.
import { chromium, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const resultPath = new URL('../../output/upload-test/results.json', import.meta.url);
const results = JSON.parse(await readFile(resultPath, 'utf8'));
results.review = [];
results.pass = false;
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const consoleErrors = [];
page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
await context.addInitScript(() => {
  window.__securityViolations = [];
  document.addEventListener('securitypolicyviolation', event => window.__securityViolations.push({ directive: event.violatedDirective, blockedURI: event.blockedURI }));
});
try {
  await page.goto(`${results.base}/portal/login`);
  await page.getByLabel('Username', { exact: true }).fill('inst.piat');
  await page.getByLabel('Password', { exact: true }).fill('Demo@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL(url => !url.pathname.endsWith('/login'));
  const token = await page.evaluate(() => localStorage.getItem('verisense.token'));
  const headers = { Authorization: `Bearer ${token}` };
  const application = await (await context.request.get(`${results.base}/api/applications/${results.applicationId}`, { headers })).json();
  expect(application.status).toBe('DRAFT');
  for (const upload of results.uploads) {
    const document = application.documents.find(item => item.id === upload.documentId);
    expect(document.verification.status).toBe(upload.expected);
    const binary = await context.request.get(`${results.base}/api/documents/${upload.documentId}/file`, { headers });
    expect(binary.status()).toBe(200);
    expect((await binary.body()).subarray(0, 4).toString()).toBe('%PDF');
    const anonymous = await context.request.get(`${results.base}/api/documents/${upload.documentId}/file`);
    expect(anonymous.status()).toBe(401);
    await page.goto(`${results.detailsUrl}&doc=${upload.documentId}`);
    await expect(page.getByRole('tab', { name: /^Documents\b/ })).toBeVisible();
    await expect(page.getByRole('tabpanel')).toContainText(upload.file);
    const frame = page.locator(`iframe[title="Original document: ${upload.file}"]`);
    await expect(frame).toHaveAttribute('src', /^blob:/);
    await page.waitForTimeout(1000);
    const violations = await page.evaluate(() => window.__securityViolations);
    results.review ??= [];
    results.review.push({ documentId: upload.documentId, file: upload.file, download: 'PASS', anonymousAccessDenied: true, securityViolations: violations });
    await page.screenshot({ path: fileURLToPath(new URL(`../../output/upload-test/${upload.expected.toLowerCase()}-review.png`, import.meta.url)), fullPage: true });
  }
  results.reviewConsoleErrors = consoleErrors;
  console.log(JSON.stringify({ applicationId: results.applicationId, review: results.review, consoleErrors }));
  expect(results.review.flatMap(item => item.securityViolations)).toEqual([]);
  expect(results.uploads.every(upload => upload.pass)).toBe(true);
  expect(results.selfCheck.httpStatus).toBe(200);
  results.pass = true;
  delete results.failure;
} finally {
  await writeFile(resultPath, JSON.stringify(results, null, 2));
  await browser.close();
}
