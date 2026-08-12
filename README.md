# Baslide01

HTML slide workshop: generate, preview, and keep working decks in one static repo.

The original drop in `files (10)/` is the 侍天 Sidera report prototype. Script tags pointed at `src/` while the JS files sat next to `index.html`, so the demo did not load. The working copy is `demos/sidera/` with that layout restored.

## Local run

```bash
bash scripts/dev-up.sh
```

The script frees only a listener that belongs to this repo, then binds the first free port among **8765 → 8080 → 5173**. It opens the gallery in the browser.

| Surface | Path |
|---|---|
| Gallery | `/` |
| Sidera demo | `/demos/sidera/` |
| Zengcheng deck | `/decks/zengcheng-taizikeng/deck.html` |
| Sidera 8 layouts | `/templates/sidera/layouts.html` |
| Magazine template | `/templates/magazine/template.html` |
| Swiss template | `/templates/swiss/template-swiss.html` |
| Table AI template | `/templates/tableai/template-tableai.html` |
| Atelier template | `/templates/atelier/template-atelier.html` |
| Guizang skill index | `/skills/guizang-ppt/INDEX.html` |

## Skills

Installed into this repo and into `~/.cursor/skills/guizang-ppt` / `~/.claude/skills/guizang-ppt-skill`.

- **guizang-ppt** — single-file HTML PPT. Style A magazine, Style B Swiss, Style C Table AI. Source: [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) with Table AI fork.
- **sidera-html-slides** — 1440×810 report slides using Sidera tokens, 8 layouts, six rendering rules.

Ask an agent: “用瑞士风做 8 页 PPT” or “按 Sidera viz-full 版式出一页经营诊断”.

## Templates

| Folder | Style | Use |
|---|---|---|
| `templates/magazine/` | A · 电子杂志 × 电子墨水 | Narrative, essays, talks |
| `templates/swiss/` | B · Swiss International | Product, data, method |
| `templates/tableai/` | C · Table AI Design System | KPI, SaaS, brand decks |
| `templates/atelier/` | Atelier (gold + navy serif) | Editorial brand talks |
| `templates/sidera/` | 侍天 8 layouts | F&B diagnosis report pages |

## Existing decks

- `decks/zengcheng-taizikeng/` — Style C deck with local SVG images. Keyboard ← →, ESC overview, B low-power.
- `demos/sidera/` — ingest → align → gate → render. Click **载入演示数据** if the first paint is empty; it auto-clicks on load.

## Constraints

- No bundler. Open HTML, or serve the repo root.
- Do not invent CSS classes that are missing from the chosen template.
- Sidera canvas is 1440×810. Tokens live in `cursor_project_rules/project-context.mdc`.
