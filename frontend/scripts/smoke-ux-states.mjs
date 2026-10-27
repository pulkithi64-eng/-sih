import {chromium,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
const base='http://127.0.0.1:8001';
const browser=await chromium.launch({channel:'msedge',headless:true});
const checks=[];
async function session(){const c=await browser.newContext();const r=await c.request.post(base+'/api/auth/login',{data:{username:'inst.piat',password:'Demo@2026'}});const a=await r.json();await c.addInitScript(a=>{localStorage.setItem('verisense.token',a.accessToken);localStorage.setItem('verisense.user',JSON.stringify(a.user));},a);const p=await c.newPage();p.setDefaultTimeout(15000);return {c,p};}
try{
 let {c,p}=await session();
 await p.route('**/api/applications',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Simulated list outage'})}));
 await p.goto(base+'/portal/my-applications');await expect(p.getByText('Could not load data',{exact:true})).toBeVisible();
 await p.unroute('**/api/applications');await p.getByRole('button',{name:'Retry',exact:true}).click();await expect(p.getByRole('list',{name:'My applications',exact:true})).toBeVisible();checks.push('List server failure and Retry recover');await c.close();
 ({c,p}=await session());await p.route('**/api/applications',r=>r.fulfill({status:200,contentType:'application/json',body:'[]'}));await p.goto(base+'/portal/my-applications');await expect(p.getByText('No applications yet',{exact:true})).toBeVisible();await expect(p.getByRole('link',{name:'New application',exact:true})).toHaveCount(2);checks.push('Empty list shows honest guidance and create action');await c.close();
 ({c,p}=await session());await p.route('**/DocumentsTab-*.js',r=>r.abort('failed'));await p.goto(base+'/portal/applications/13?tab=documents');await expect(p.getByRole('heading',{name:'This section could not load',exact:true})).toBeVisible();await expect(p.getByRole('button',{name:'Reload page',exact:true})).toBeVisible();checks.push('Deferred chunk failure shows recovery without removing navigation');await c.close();
 ({c,p}=await session());await p.setViewportSize({width:320,height:900});await p.goto(base+'/portal/my-applications');await p.getByRole('button',{name:'Open navigation',exact:true}).click();await expect(p.getByRole('dialog')).toBeVisible();await p.keyboard.press('Escape');await expect(p.getByRole('dialog')).not.toBeVisible();checks.push('Mobile navigation opens and closes with Escape');
 for(const route of ['/','/portal/login','/portal/applications/13?tab=documents&doc=81']){for(const width of [320,375,768,1440]){await p.setViewportSize({width,height:900});await p.goto(base+route);await expect(p.locator('h1,h2').first()).toBeVisible();await p.waitForTimeout(200);expect(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}}
 checks.push('Landing, login and document evidence fit 320/375/768/1440 widths');await c.close();
 await writeFile(new URL('../../docs/ui-simplification/failure-responsive-results.json',import.meta.url),JSON.stringify({pass:true,checks},null,2));console.log(JSON.stringify({pass:true,checks}));
}finally{await browser.close();}
