import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.RUNTIME_NODE_MODULES+'/playwright/index.mjs'));
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const text=readFileSync('platform_app/app.py','utf8');const js=text.split('ADMIN_JS = r"""')[1].split('"""')[0];
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{
 const page=await browser.newPage();await page.setContent('<header><select id="scenario"><option value="S" data-slug="s">S</option></select><input id="override" type="checkbox"><button id="publish">publish</button></header><div id="save-state"></div><div id="revision"></div><div id="modules"></div><div id="fields"></div><iframe id="preview"></iframe>');
 await page.evaluate(()=>{window.calls=[];window.PROJECT='P';window.LABELS={'admin.saved':'saved'};window.EventSource=class {addEventListener(){}};window.fetch=async(url,options)=>{if(options){if(options.method==='PATCH')await new Promise(r=>setTimeout(r,30));calls.push({url,...options});return {ok:true,json:async()=>({version:2})}};return {ok:true,json:async()=>({revision:{code:'P.DRAFT'},scenario:{code:'S'},modules:[],fields:['A','B'].map(code=>({code,module_code:'M',role:'p',value:'old',base_version:1}))})}}});
 await page.addScriptTag({content:js});await page.waitForSelector('textarea');
 await page.locator('textarea').nth(0).fill('first');await page.locator('textarea').nth(1).fill('second');await page.locator('#publish').click();await page.waitForFunction(()=>calls.length===3);
 const calls=await page.evaluate(()=>calls);assert.deepEqual(calls.map(c=>c.method),['PATCH','PATCH','POST']);assert.equal(JSON.parse(calls[0].body).value,'first');assert.equal(JSON.parse(calls[1].body).value,'second');console.log('PASS rapid multi-field edits complete before publish');
}finally{await browser.close()}
