# V1.2 · Latest D12 version

78 slides · 1280×720. Open `v1.2.html`; download `九川文化-双店诊断与六个月陪跑方案-V1.2.pdf`. A matching PDF is saved beside the original HTML. The original source is archived unchanged under `source/`.

Fixed panel overflow, clipped chart labels, crowded scatter labels, table layout, cover version, and mismatched item counts. Retained official TIANSIGHT branding. All 78 PDF pages visually reviewed; automated overflow, image loading, page dimensions, and numeric/Latin text preservation checks passed. All 78 pages subsequently received a title and subtitle editorial review to replace colloquial and overly absolute language; see `editorial-review-v1.2.json`. Business data was not independently audited. See `quality-check-v1.2.json`.

Rebuild and check: `node decks/jiuchuan-six-month/check-export-v1.2.mjs`.

# 九川文化 · 双店诊断与六个月陪跑方案

D12 · 64 slides · 1280×720. Open `presentation.html`; use the toolbar to download the PDF.

Official logo: https://apuch.art/brand?brand=tiansight via https://apuch.art/api/brands/tiansight.json, published revision 74a829b. Original HTML is preserved by SHA-256 under `source/`; original slide text and embedded source appendix are unchanged. The PDF contains the 64 visible slides; interactive data tables remain in HTML.

Fixed title flow, panel/KPI clipping on 24 pages, muted text contrast, unintended strike-through, and clipped chart legends/labels. All 64 rendered PDF pages reviewed. HTML overflow, SVG text bounds (unrotated labels), image loading, page count, aspect ratio, and source slide-text preservation checked. Business claims and external data were not independently audited.

From the repository root, run `node decks/jiuchuan-six-month/check-export.mjs` to check layout and rebuild the PDF using the existing Codex runtime and Chrome. Chromium rejects a full-deck print in this environment, so export uses four 16-page batches and merges the PDFs while retaining text and vector charts.
