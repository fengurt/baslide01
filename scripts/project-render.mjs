#!/usr/bin/env node
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

const [landingUrl, slidesUrl, pngPath, pdfPath] = process.argv.slice(2);
if (!pdfPath) throw new Error("usage: project-render.mjs LANDING_URL SLIDES_URL PNG_PATH PDF_PATH");
const chrome = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const profile = await mkdtemp(join(tmpdir(), "baslide-chrome-"));
const port = 9237;
const child = spawn(chrome, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"], {stdio:"ignore"});
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

async function endpoint(path, init) {
  for (let i = 0; i < 80; i++) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}${path}`, init);
      if (response.ok) return response.json();
    } catch {}
    await wait(100);
  }
  throw new Error("Chrome debugging endpoint did not start");
}

try {
  const tab = await endpoint(`/json/new?${encodeURIComponent(landingUrl)}`, {method:"PUT"});
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  const pending = new Map();
  let id = 0;
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const item = pending.get(message.id);
    pending.delete(message.id);
    message.error ? item.reject(new Error(message.error.message)) : item.resolve(message.result);
  };
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  const send = (method, params={}) => new Promise((resolve, reject) => {
    const callId = ++id;
    pending.set(callId, {resolve, reject});
    ws.send(JSON.stringify({id:callId, method, params}));
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", {width:1440,height:900,deviceScaleFactor:1,mobile:false});
  async function ready(url) {
    await send("Page.navigate", {url});
    for (let i=0;i<120;i++) {
      const state = await send("Runtime.evaluate", {expression:"document.readyState==='complete'&&[...document.images].every(i=>i.complete&&i.naturalWidth)&&document.fonts.status==='loaded'", returnByValue:true});
      if (state.result.value) return;
      await wait(100);
    }
    throw new Error(`page did not finish loading: ${url}`);
  }
  await ready(landingUrl);
  const png = await send("Page.captureScreenshot", {format:"png",fromSurface:true,captureBeyondViewport:true});
  await mkdir(dirname(pngPath), {recursive:true});
  await writeFile(pngPath, Buffer.from(png.data,"base64"));
  await ready(slidesUrl);
  const pdf = await send("Page.printToPDF", {printBackground:true,landscape:false,paperWidth:13.333,paperHeight:7.5,marginTop:0,marginBottom:0,marginLeft:0,marginRight:0,preferCSSPageSize:true});
  await mkdir(dirname(pdfPath), {recursive:true});
  await writeFile(pdfPath, Buffer.from(pdf.data,"base64"));
  await send("Browser.close");
  ws.close();
  console.log(JSON.stringify({png:pngPath,pdf:pdfPath}));
} finally {
  child.kill();
  await rm(profile, {recursive:true,force:true});
}
