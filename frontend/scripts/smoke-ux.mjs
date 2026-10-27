import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const base = process.env.VERISENSE_URL ?? 'http://127.0.0.1:8001';
const root = fileURLToPath(new URL('../../', import.meta.url));
const out = path.join(root, 'docs/ui-simplification');
await mkdir(out, {recursive:true});
const browser = await chromium.launch({channel:'msedge',headless:true});
const checks=[], errors=[]; let id, docId;
async function login(name) {
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
  const page=await context.newPage(); page.setDefaultTimeout(15000); page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/portal/login');
  await page.getByLabel('Username',{exact:true}).fill(name);
  await page.getByLabel('Password',{exact:true}).fill('Demo@2026');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.waitForURL(u=>!u.pathname.endsWith('/login'));
  const token=await page.evaluate(()=>localStorage.getItem('verisense.token'));
  return {context,page,headers:{Authorization:`Bearer ${token}`}};
}
function post(page,suffix){return page.waitForResponse(r=>r.url().endsWith(suffix)&&r.request().method()==='POST',{timeout:60000});}
async function action(page,value) {
  const dialog=page.getByRole('dialog');
  await dialog.locator(`[role=radio][value="${value}"]`).click();
  await dialog.getByLabel('Reasoned note').fill('Synthetic UX acceptance test: missing mandatory evidence and conflicting issuer values require human review.');
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button',{name:'Review & confirm',exact:true}).click();
  const response=post(page,`/api/applications/${id}/decision`);
  await dialog.getByRole('button',{name:'Confirm and record',exact:true}).click();
  expect((await response).status()).toBe(200); await expect(dialog).not.toBeVisible();
}
let inst, officer, rd, admin;
try {
  inst=await login('inst.piat'); const p=inst.page;
  await expect(p.getByRole('heading',{name:'My applications',exact:true})).toBeVisible();
  await p.getByRole('link',{name:/New application/}).first().click();
  await p.getByRole('radio').filter({hasText:'Extension of Approval'}).click();
  await p.getByRole('button',{name:'Continue',exact:true}).click();
  const creating=post(p,'/api/applications');
  await p.getByRole('button',{name:'Create draft & continue',exact:true}).click();
  const cr=await creating; expect(cr.status()).toBe(201); id=(await cr.json()).id;
  await expect(p.getByRole('heading',{name:'Upload documents',exact:true})).toBeVisible();
  checks.push('Institution: UI login, category, create draft, direct upload step');
  const meta=await (await inst.context.request.get(base+'/api/meta',{headers:inst.headers})).json();
  const label=meta.docTypes.find(t=>t.id==='UNIVERSITY_AFFILIATION').label;
  const slot=p.getByLabel(`Upload ${label}`,{exact:true});
  for(const [file,status] of [['01_correct_demo_affiliation.pdf','VERIFIED'],['02_imaginary_mismatch_affiliation.pdf','MISMATCH_DETECTED']]){
    const req=post(p,`/api/applications/${id}/documents`);
    await slot.setInputFiles(path.join(root,'output/pdf',file)); const r=await req; const d=await r.json();
    expect(r.status()).toBe(201); expect(d.verification.status).toBe(status); docId=d.id;
  }
  checks.push('Correct PDF VERIFIED; imaginary PDF MISMATCH_DETECTED through real upload UI');
  const route=`**/api/applications/${id}/documents`;
  await p.route(route,r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Simulated upload outage for UX test'})}),{times:1});
  await slot.setInputFiles(path.join(root,'output/pdf/01_correct_demo_affiliation.pdf'));
  await expect(p.getByRole('button',{name:/Retry upload/})).toBeVisible();
  const retry=post(p,`/api/applications/${id}/documents`); await p.getByRole('button',{name:/Retry upload/}).click();
  expect((await retry).status()).toBe(201); checks.push('Upload service failure is visible and Retry upload succeeds');
  await p.route(`**/api/applications/${id}/validate`,r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Simulated check outage for UX test'})}),{times:1});
  await p.getByRole('button',{name:'Check documents',exact:true}).click();
  await expect(p.getByText('Could not load data',{exact:true})).toBeVisible();
  const validation=post(p,`/api/applications/${id}/validate`); await p.getByRole('button',{name:'Retry',exact:true}).click(); expect((await validation).status()).toBe(200);
  checks.push('Check service failure exits loading state and Retry succeeds');
  const submission=post(p,`/api/applications/${id}/submit`); await p.getByRole('button',{name:'Submit for review',exact:true}).click(); expect((await submission).status()).toBe(200);
  await p.getByRole('tab',{name:'Report',exact:true}).click();
  const download=p.waitForEvent('download'); await p.getByRole('button',{name:'Download PDF',exact:true}).click(); await (await download).saveAs(path.join(root,'.local-run/ux-report.pdf'));
  checks.push('Institution submits for review and downloads generated PDF report');
  for(const width of [320,375,768,1440]){
    await p.setViewportSize({width,height:900}); await p.goto(`${base}/portal/my-applications`);
    await expect(p.getByRole('heading',{name:'My applications',exact:true})).toBeVisible();
    expect(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  }
  checks.push('Institution list has no page overflow at 320, 375, 768 and 1440 pixels');
  officer=await login('officer.wro'); await expect(officer.page.getByRole('heading',{name:'Review queue',exact:true})).toBeVisible();
  await officer.page.goto(`${base}/portal/applications/${id}`);
  await officer.page.getByRole('button',{name:'More actions',exact:true}).click();
  await officer.page.getByRole('menuitem',{name:'Request corrections',exact:true}).click();
  await officer.page.getByLabel('Instructions to the institution').fill('Synthetic UX test: replace mismatching issuer evidence and supply all missing mandatory documents.');
  const correcting=post(officer.page,`/api/applications/${id}/request-rectification`);
  await officer.page.getByRole('button',{name:'Send request',exact:true}).click(); expect((await correcting).status()).toBe(200);
  checks.push('Officer review queue and request corrections with mandatory note');
  await p.setViewportSize({width:1440,height:1000}); await p.goto(`${base}/portal/applications/${id}/edit?step=respond`);
  await expect(p.getByRole('heading',{name:'Correct your application',exact:true})).toBeVisible();
  await p.getByRole('button',{name:'Continue',exact:true}).click(); await p.getByRole('button',{name:'Save & continue',exact:true}).click();
  await expect(p.getByRole('heading',{name:'Upload documents',exact:true})).toBeVisible();
  let forbiddenCheck=false; p.on('request',r=>{if(r.url().endsWith(`/api/applications/${id}/validate`)) forbiddenCheck=true;});
  await p.getByRole('button',{name:'Check documents',exact:true}).click(); await expect(p.getByText('Review your corrections',{exact:true})).toBeVisible();
  const resubmit=post(p,`/api/applications/${id}/submit`); await p.getByRole('button',{name:'Resubmit for review',exact:true}).click(); expect((await resubmit).status()).toBe(200); expect(forbiddenCheck).toBe(false);
  checks.push('Correction and resubmission use permitted workflow without draft-only validate request');
  await officer.page.reload(); await officer.page.getByRole('button',{name:'Record recommendation',exact:true}).click();
  let d=officer.page.getByRole('dialog'); await d.locator('[role=radio][value=RECOMMEND_APPROVE_FOR_EOA]').click(); await d.getByLabel('Reasoned note').fill('This attempt verifies that unresolved critical findings block approval.'); await d.getByRole('checkbox').check(); await expect(d.getByRole('button',{name:'Review & confirm',exact:true})).toBeDisabled();
  await action(officer.page,'RECOMMEND_ORDER_INSPECTION'); checks.push('Officer approval blocked by critical findings; reasoned inspection recommendation recorded');
  rd=await login('rd.wro'); await expect(rd.page.getByRole('heading',{name:'Decision queue',exact:true})).toBeVisible(); await rd.page.goto(`${base}/portal/applications/${id}`);
  await rd.page.getByRole('button',{name:'Record decision',exact:true}).click(); d=rd.page.getByRole('dialog'); await d.locator('[role=radio][value=APPROVE_FOR_EOA]').click(); await d.getByLabel('Reasoned note').fill('This attempt verifies unresolved critical findings block final approval.'); await d.getByRole('checkbox').check(); await expect(d.getByRole('button',{name:'Review & confirm',exact:true})).toBeDisabled();
  await action(rd.page,'REJECT'); checks.push('Director decision queue, critical approval guard, reasoned final rejection of synthetic test case');
  admin=await login('admin'); await expect(admin.page.getByRole('heading',{name:/Rules/})).toBeVisible();
  await admin.page.goto(base+'/portal/applications/new'); await expect(admin.page).toHaveURL(/\/portal\/rules/);
  expect((await admin.context.request.post(base+'/api/applications',{headers:admin.headers,data:{category:'EOA',academicYear:'2027-28',formData:{}}})).status()).toBe(403);
  const northern=await admin.context.request.post(base+'/api/auth/login',{data:{username:'officer.nro',password:'Demo@2026'}}); const n=await northern.json();
  expect((await admin.context.request.get(`${base}/api/applications/${id}`,{headers:{Authorization:`Bearer ${n.accessToken}`}})).status()).toBe(404);
  const anon=await browser.newContext(); expect((await anon.request.get(`${base}/api/documents/${docId}/file`)).status()).toBe(401); await anon.close();
  checks.push('Admin route restriction and backend 403; cross-region 404; anonymous document download 401');
  await expect(errors).toEqual([]);
  await writeFile(path.join(out,'acceptance-results.json'),JSON.stringify({pass:true,applicationId:id,checks,pageErrors:errors},null,2));
  console.log(JSON.stringify({pass:true,applicationId:id,checks:checks.length,pageErrors:errors}));
} catch(e){
 await writeFile(path.join(out,'acceptance-results.json'),JSON.stringify({pass:false,applicationId:id,checks,pageErrors:errors,error:String(e)},null,2)); throw e;
} finally {await browser.close();}
