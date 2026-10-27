// Uploads two synthetic PDFs through the real local UI into a NEW draft only.
import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const base = process.env.VERISENSE_URL ?? 'http://127.0.0.1:8001';
const out = path.join(root, 'output', 'upload-test');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const results = { base, applicationId: null, applicationNo: null, uploads: [], pageErrors: errors };
try {
  await page.goto(`${base}/portal/login`);
  await page.getByLabel('Username', { exact: true }).fill('inst.piat');
  await page.getByLabel('Password', { exact: true }).fill('Demo@2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForURL(url => !url.pathname.endsWith('/login'));
  const token = await page.evaluate(() => localStorage.getItem('verisense.token'));
  if (!token) throw new Error('Institution UI sign-in did not establish a session');
  const headers = { Authorization: `Bearer ${token}` };
  const created = await context.request.post(`${base}/api/applications`, {
    headers,
    data: { category: 'EOA', academicYear: '2027-28', formData: {
      testScenario: 'Two-PDF upload: matching issuer record vs deliberately imaginary values',
      totalIntake: 300, facultyCount: 20, locationType: 'URBAN',
    } },
  });
  if (created.status() !== 201) throw new Error(`Draft creation failed: ${created.status()} ${await created.text()}`);
  const application = await created.json();
  results.applicationId = application.id;
  results.applicationNo = application.applicationNo;
  const metadata = await (await context.request.get(`${base}/api/meta`, { headers })).json();
  const label = metadata.docTypes.find(type => type.id === 'UNIVERSITY_AFFILIATION').label;
  await page.goto(`${base}/portal/applications/${application.id}/edit`);
  await page.getByRole('list', { name: 'Progress' }).getByRole('button', { name: /Documents/ }).click();
  const slot = page.locator('li').filter({ has: page.getByText(label, { exact: true }) }).locator('input[type=file]');
  await expect(slot).toHaveCount(1);
  const fixtures = [
    { file: '01_correct_demo_affiliation.pdf', expected: 'VERIFIED' },
    { file: '02_imaginary_mismatch_affiliation.pdf', expected: 'MISMATCH_DETECTED' },
  ];
  for (const fixture of fixtures) {
    const responsePromise = page.waitForResponse(response => response.url().endsWith(`/api/applications/${application.id}/documents`) && response.request().method() === 'POST', { timeout: 60000 });
    await slot.setInputFiles(path.join(root, 'output', 'pdf', fixture.file));
    const response = await responsePromise;
    const body = await response.json();
    const result = {
      file: fixture.file, httpStatus: response.status(), documentId: body.id,
      docType: body.docType, verification: body.verification,
      extractedFields: body.extractedFields, pipelineErrors: body.pipelineErrors,
      expected: fixture.expected, pass: response.status() === 201 && body.verification?.status === fixture.expected,
    };
    results.uploads.push(result);
    console.log(JSON.stringify({ file: result.file, httpStatus: result.httpStatus, status: body.verification?.status, pass: result.pass }));
    expect(result.httpStatus).toBe(201);
    expect(result.docType).toBe('UNIVERSITY_AFFILIATION');
    expect(result.pipelineErrors ?? []).toEqual([]);
    expect(body.verification?.status).toBe(fixture.expected);
    await expect(page.getByText(fixture.file, { exact: true }).first()).toBeVisible();
  }
  await page.screenshot({ path: path.join(out, 'both-upload-results.png'), fullPage: true });
  const validationPromise = page.waitForResponse(response => response.url().endsWith(`/api/applications/${application.id}/validate`) && response.request().method() === 'POST', { timeout: 60000 });
  await page.getByRole('button', { name: 'Run self-check', exact: true }).click();
  const validation = await validationPromise;
  expect(validation.status()).toBe(200);
  const report = await validation.json();
  results.selfCheck = { httpStatus: validation.status(), status: report.status, summary: report.summary, verifications: report.verifications };
  expect(report.status).toBe('DRAFT');
  for (const upload of results.uploads) {
    const verdict = report.verifications.find(item => String(item.documentId) === String(upload.documentId));
    expect(verdict?.status).toBe(upload.expected);
  }
  results.detailsUrl = `${base}/portal/applications/${application.id}?tab=documents`;
  await page.goto(results.detailsUrl);
  await expect(page.getByRole('tab', { name: /^Documents\b/ })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Documents', exact: true })).toContainText('Verified');
  await expect(page.getByRole('navigation', { name: 'Documents', exact: true })).toContainText('Mismatch detected');
  await page.screenshot({ path: path.join(out, 'documents-review.png'), fullPage: true });
  expect(errors).toEqual([]);
  results.pass = true;
} catch (error) {
  results.pass = false;
  results.failure = String(error);
  await page.screenshot({ path: path.join(out, 'failure.png'), fullPage: true }).catch(() => {});
  throw error;
} finally {
  await writeFile(path.join(out, 'results.json'), JSON.stringify(results, null, 2));
  await browser.close();
}
console.log(JSON.stringify({ pass: results.pass, applicationId: results.applicationId, applicationNo: results.applicationNo, detailsUrl: results.detailsUrl }));
