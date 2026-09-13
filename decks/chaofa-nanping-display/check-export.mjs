import {chromium} from '/Users/af/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const b=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});const p=await b.newPage({viewport:{width:1440,height:900}});let errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto(new URL('file://'+process.cwd()+'/decks/chaofa-nanping-display/presentation.html').href);await p.evaluate(()=>document.fonts.ready);await p.emulateMedia({media:'print'});
const a=await p.evaluate(()=>{let issues=[];const ss=[...document.querySelectorAll('.slide')];ss.forEach((s,i)=>{for(const e of s.querySelectorAll('.s-title,.s-body,.panel,.fig,.kpi,li,td,th,.hstack,.lead,.txt,.note'))if(e.clientHeight&& (e.scrollHeight>e.clientHeight+3||e.scrollWidth>e.clientWidth+3))issues.push({page:i+1,cls:e.className,text:e.textContent.slice(0,50),h:e.clientHeight,sh:e.scrollHeight,w:e.clientWidth,sw:e.scrollWidth});});return{pages:ss.length,issues,images:[...document.images].filter(x=>!x.complete||!x.naturalWidth).map(x=>x.src.slice(0,100)),titles:ss.map(x=>x.querySelector('h1,h2')?.textContent),texts:ss.map(x=>x.innerText),figures:document.querySelectorAll('.slide .fig svg').length,tables:document.querySelectorAll('.slide table').length};});a.errors=errors;fs.mkdirSync('tmp/pdfs/chaofa',{recursive:true});fs.writeFileSync('tmp/pdfs/chaofa/audit.json',JSON.stringify(a,null,2));console.log(JSON.stringify({...a,texts:undefined,titles:undefined}));
if(a.issues.length||a.images.length||errors.length)throw new Error('Audit failed');
if(process.argv.includes('--export')){await p.addStyleTag({content:'.stage,.deck{display:block!important}.deck>.row{break-after:page}.slide{break-after:auto!important}'});await p.evaluate(()=>document.querySelector('.srcov')?.remove());for(let start=0;start<a.pages;start+=15){await p.evaluate(start=>document.querySelectorAll('.deck>.row').forEach((e,i)=>e.style.display=i>=start&&i<start+15?'block':'none'),start);await p.pdf({path:`tmp/pdfs/chaofa/batch-${start}.pdf`,preferCSSPageSize:true,printBackground:true});}}
await b.close();
// Chromium export is batched to avoid full-deck print failures.
if(process.argv.includes('--export')){
const {execFileSync}=await import('node:child_process');
execFileSync('/Users/af/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',['-c',`
from pypdf import PdfReader,PdfWriter
w=PdfWriter()
for i in range(0,90,15):
 r=PdfReader(f'tmp/pdfs/chaofa/batch-{i}.pdf')
 assert len(r.pages)==15
 w.append(r)
w.add_metadata({'/Title':'潮发珠海南屏A3002a_展陈升级前瞻洞察报告_V1.1','/Author':'侍天 TIANSIGHT'})
w.write('decks/chaofa-nanping-display/潮发珠海南屏A3002a_展陈升级前瞻洞察报告_V1.1.pdf')
`],{stdio:'inherit'});
}
