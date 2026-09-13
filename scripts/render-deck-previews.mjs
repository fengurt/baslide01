#!/usr/bin/env node
import { readFile, mkdir, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const root = new URL("../", import.meta.url).pathname;
const modules = process.env.RUNTIME_NODE_MODULES;
if (!modules) throw new Error("RUNTIME_NODE_MODULES is required");
const { chromium } = await import(pathToFileURL(join(modules, "playwright/index.mjs")));
const { default: sharp } = await import(pathToFileURL(join(modules, "sharp/dist/index.mjs")));
const base = (process.argv[2] || "http://127.0.0.1:8765/").replace(/\/?$/, "/");
const limit = Number(process.argv[3] || 0);
const out = join(root, "previews");
const tileWidth = 384;
const tileHeight = 216;
const source = JSON.parse(await readFile(join(root, "decks.json"), "utf8"));
const selected = new Set(process.argv.slice(4));
const targets = source.decks.flatMap(deck => deck.variants?.length ? deck.variants : [deck]).filter(deck => !selected.size || selected.has(deck.id));
const browser = await chromium.launch({ headless: true, executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" });
const manifest = { generatedAt: new Date().toISOString(), format: "webp-sprite", limit: limit || null, decks: [] };

if (selected.size) {
  const previous = JSON.parse(await readFile(join(out, "manifest.json"), "utf8"));
  manifest.decks = previous.decks.filter(deck => !selected.has(deck.id) && !(selected.has("D13.3") && deck.id === "D13"));
} else await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });

async function render(target) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 810 }, deviceScaleFactor: 1 });
  const url = new URL(target.href, base);
  url.searchParams.set("chrome", "0");
  await page.goto(url.href, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.emulateMedia({ media: "screen", reducedMotion: "reduce" });
  await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}" });
  await page.waitForFunction(() => document.fonts.status === "loaded" && [...document.images].every(image => image.complete), null, { timeout: 15000 }).catch(() => {});
  const spec = await page.evaluate(() => {
    for (const selector of ["section.slide", ".page", ".sheet > section", ".tape > section"]) {
      const count = document.querySelectorAll(selector).length;
      if (count) return { selector, count, isolate: true };
    }
    return { selector: document.querySelector("main") ? "main" : "body", count: 1, isolate: false };
  });
  const count = limit ? Math.min(limit, spec.count) : spec.count;
  const dir = target.id.toLowerCase().replace(/\W+/g, "-");
  if (spec.isolate) {
    await page.evaluate(({ selector }) => {
      const items = [...document.querySelectorAll(selector)];
      items.forEach(item => item.dataset.previewDisplay = getComputedStyle(item).display === "none" ? "block" : getComputedStyle(item).display);
      window.__showPreviewPage = index => {
        items.forEach((item, i) => item.style.setProperty("display", i === index ? item.dataset.previewDisplay : "none", "important"));
        const item = items[index];
        for (let node = item.parentElement; node; node = node.parentElement) {
          node.style.setProperty("transform", "none", "important");
          node.style.setProperty("overflow", "visible", "important");
        }
        item.style.setProperty("position", "fixed", "important");
        item.style.setProperty("margin", "0", "important");
        item.style.setProperty("opacity", "1", "important");
        item.style.setProperty("visibility", "visible", "important");
        item.style.setProperty("transform-origin", "0 0", "important");
        const width = item.offsetWidth || 1440;
        const height = item.offsetHeight || 810;
        const scale = Math.min(1440 / width, 810 / height);
        item.style.setProperty("left", `${(1440 - width * scale) / 2}px`, "important");
        item.style.setProperty("top", `${(810 - height * scale) / 2}px`, "important");
        item.style.setProperty("transform", `scale(${scale})`, "important");
      };
    }, spec);
  }
  const columns = Math.min(10, count);
  const rows = Math.ceil(count / columns);
  const tiles = [];
  for (let i = 0; i < count; i++) {
    if (spec.isolate) await page.evaluate(index => window.__showPreviewPage(index), i);
    const raw = await page.screenshot({ type: "png" });
    const tile = await sharp(raw).resize(tileWidth, tileHeight, { fit: "fill" }).removeAlpha().raw().toBuffer();
    tiles.push({ input: tile, raw: { width: tileWidth, height: tileHeight, channels: 3 }, left: (i % columns) * tileWidth, top: Math.floor(i / columns) * tileHeight });
  }
  const name = `${dir}.webp`;
  const result = await sharp({ create: { width: columns * tileWidth, height: rows * tileHeight, channels: 3, background: "#17130D" } })
    .composite(tiles).webp({ quality: 55, effort: 5, smartSubsample: true }).toFile(join(out, name));
  await page.close();
  manifest.decks.push({ id: target.id, title: target.title, href: target.href, pages: spec.count, rendered: count,
    sprite: `/previews/${name}`, columns, rows, tileWidth, tileHeight, bytes: result.size });
  console.log(`${target.id} ${count}/${spec.count} ${Math.round(result.size / 1024)} KiB`);
}

const queue = [...targets];
await Promise.all(Array.from({ length: 3 }, async () => {
  while (queue.length) await render(queue.shift());
}));
manifest.decks.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
await writeFile(join(out, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
await browser.close();
console.log(`wrote ${manifest.decks.reduce((sum, deck) => sum + deck.rendered, 0)} WebP sprite previews`);
