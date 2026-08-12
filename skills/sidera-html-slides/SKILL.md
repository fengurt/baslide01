---
name: sidera-html-slides
description: Generate 1440×810 HTML report slides with 侍天 Sidera design tokens, eight locked layouts, D3 chart slots, and six rendering rules. Use when the user asks for Sidera slides, 侍天报告页, F&B diagnosis decks, viz-full/roster/verdict layouts, or HTML slides that must carry denominator, how-to-read, and takeaway bars.
---

# Sidera HTML slides

Generate **fixed-canvas HTML slides** (1440×810) for 侍天 Sidera diagnosis reports. One decision per page. Do not turn this into a dashboard.

## When to use

- User wants Sidera / 侍天 / 清水亭-style report pages
- User names a layout: `cover` `viz-full` `viz-table` `viz-duo` `matrix-full` `kpi-grid` `roster` `verdict`
- User wants HTML slides with gold/paper tokens, IBM Plex Mono numbers, Noto Serif SC body

For magazine / Swiss / Table AI swipe decks, use `skills/guizang-ppt` instead.

## Tokens (locked)

```css
--surface:#F4F0E7; --paper:#FFFDF8; --ink-primary:#EFE6D2;
--charcoal:#17130D; --gold:#76551F; --gold-hi:#D4A862; --seal:#8C3228;
--ink-muted:#706758;
font-body: "Noto Serif SC";
font-num: "IBM Plex Mono";
font-cap: "Noto Serif";
canvas: 1440 × 810;
```

Copy the shell from `templates/sidera/layouts.html`. Replace slot text. Do not invent class names.

## Eight layouts

| Code | Structure | Use |
|---|---|---|
| `cover` | Vertical chapter number + one-line decision + analysis-point chips | Chapter openers |
| `viz-full` | Header → SOURCE → chart 72% height → HOW TO READ → TAKEAWAY | Default |
| `viz-table` | Chart 58% / table 42%, shared takeaway | Chart + roster |
| `viz-duo` | Two charts with a “因此” arrow | Contrast |
| `matrix-full` | Heat matrix + dual marginal bars + zero≠gap footnote | Unlock / ABC / 九宫格 |
| `kpi-grid` | 3×2 or 4×2 cards: big number + label + delta | Scorecards |
| `roster` | Sortable full list + **sum-check row** | Completeness |
| `verdict` | Dispute / fact / handling / falsify + seal | A58 |

## Six elements every page must have

1. Header chip: analysis-point id · basis A/B · period
2. SOURCE bar: file + row count + denominator formula
3. Main chart or table
4. HOW TO READ bar
5. TAKEAWAY: one executable sentence with a number
6. Footer: denominator + degradation watermark if any + falsify id

## Six rendering rules

1. Denominator travels with the chart (`opts.denom`)
2. Median split uses `≥` (high side)
3. Zero is not a gap unless the column base meets the threshold
4. `n` below threshold gets hatch fill, never hidden
5. Proxy metrics get a “禁止外部对标” watermark
6. Category sums must close; refuse to render if they do not

## Workflow

1. Read `demos/sidera/docs/01_总纲_报告大纲与页面规范.md` for the page id and layout.
2. Clone the matching `<section class="slide layout-…">` from `templates/sidera/layouts.html`.
3. Fill chips, source, takeaway. Keep one decision per page.
4. If a D3 primitive is needed, call `Sidera.viz.*` from `demos/sidera/src/sidera.viz.js` after loading d3 v7.
5. Serve via `bash scripts/dev-up.sh` and open `/templates/sidera/layouts.html`.

## Do not

- Mix Guizang Swiss classes (`h-hero`, `stat-nb`) into Sidera pages
- Use Inter / purple gradients / card-dashboard chrome
- Emit a page that cannot answer “tomorrow, do what?”
