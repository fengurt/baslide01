import { chromium } from '/Users/af/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const root=process.cwd(), dir=root+'/decks/jiuchuan-six-month';
fs.mkdirSync(root+'/tmp/pdfs/jiuchuan',{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const page=await browser.newPage({viewport:{width:1440,height:900}});
await page.goto(pathToFileURL(dir+'/presentation.html').href);
await page.evaluate(()=>document.fonts.ready);
await page.emulateMedia({media:'print'});
const audit=await page.evaluate(()=>{
 const slides=[...document.querySelectorAll('.slide')];
 let issues=[];
 slides.forEach((s,i)=>{
  for(const e of s.querySelectorAll('svg text')){const box=e.getBBox(),v=e.ownerSVGElement.viewBox.baseVal;if(!e.hasAttribute('transform')&&(box.x<-2||box.y<-2||box.x+box.width>v.width+2||box.y+box.height>v.height+2))issues.push({page:i+1,svgText:e.textContent,box:{x:box.x,y:box.y,w:box.width,h:box.height},view:{w:v.width,h:v.height}});}
  for(const e of s.querySelectorAll('.s-title,.s-body,.panel,.fig,.kpi,li,td,th,.hstack,.lead,.txt,.note')){
   if(e.scrollHeight>e.clientHeight+3||e.scrollWidth>e.clientWidth+3)issues.push({page:i+1,tag:e.tagName,cls:e.className,text:e.textContent.slice(0,65),h:e.clientHeight,sh:e.scrollHeight,w:e.clientWidth,sw:e.scrollWidth});
  }
 });
 return {slides:slides.length,images:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.src),issues,texts:slides.map(s=>s.innerText),titles:slides.map(s=>s.querySelector('.s-title')?.textContent||s.querySelector('.dv-h')?.textContent||'Cover')};
});
fs.writeFileSync(root+'/tmp/pdfs/jiuchuan/audit.json',JSON.stringify(audit,null,2));
console.log(JSON.stringify(audit.issues));
if(audit.slides!==64||audit.images.length||audit.issues.length)throw new Error('Layout check failed');
await page.addStyleTag({content:'#stage{display:block}'});
await page.evaluate(()=>{document.querySelector('#srcov')?.remove();document.querySelector('#wb')?.remove();});
for(let start=0;start<64;start+=16){
 await page.evaluate(start=>{[...document.querySelectorAll('#deck>.row')].forEach((e,i)=>e.style.display=i>=start&&i<start+16?'block':'none');},start);
 await page.pdf({path:root+'/tmp/pdfs/jiuchuan/batch-'+start+'.pdf',printBackground:true,preferCSSPageSize:true});
}
await browser.close();

// ponytail: 16-page batches avoid Chromium's full-deck print failure; merge without rasterizing.
execFileSync('/Users/af/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',['-c',`
from pypdf import PdfReader,PdfWriter
w=PdfWriter()
for i in range(0,64,16):
 r=PdfReader(f'tmp/pdfs/jiuchuan/batch-{i}.pdf')
 assert len(r.pages)==16
 w.append(r)
w.add_metadata({'/Title':'九川文化 · 双店诊断与六个月教练式陪跑方案','/Author':'侍天 TIANSIGHT'})
w.write('decks/jiuchuan-six-month/九川文化-双店诊断与六个月陪跑方案-TIANSIGHT.pdf')
`],{stdio:'inherit'});
