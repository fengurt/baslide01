# TIANSIGHT generation quality checklist

Use this checklist while generating or materially redesigning a deck. The renderer must encode these rules; do not rely on manual cleanup page by page when a shared rule can solve the class of problem.

## 1. Benchmark and classify first

- Inspect representative pages in `decks/stone-briefing`, `decks/stone-dossier`, and `decks/stone-roadmap` before choosing layouts.
- Classify every page into one of the 12 supported L2 jobs. Do not let an unclassified page fall into a generic text card.
- Group recurring content into explicit page families: insight, opportunity, KPI evidence, comparison, roster/table, chart-table, process, divider, and closing.
- Use one visual grammar per family across the deck: same hierarchy, number treatment, margins, and evidence order.

## 2. Data visualization

- A key-data page needs an actual figure or a justified semantic table. Large numbers placed in cards are not, by themselves, data visualization.
- When two or more comparable values share a unit, show the comparison: bar, slope, benchmark axis, variance, distribution, or another fitting mark.
- Percentages carry a visible 100% denominator. Same-unit comparisons carry a visible maximum or benchmark. Zero values render as zero, never as a fake minimum bar.
- Show the decision math when it matters: multiple, percentage-point change, premium/discount, contribution, or annualized value.
- Keep units attached to values and denominators attached to figures. Direct-label series; avoid detached legends for small charts.
- Do not render a heatmap from a prose-heavy table. Heatmaps require a genuine numeric or categorical matrix. A table with no usable measure and any prose cell of 60+ characters stays a roster.
- Long labels must receive a larger label region, line wrapping, or a roster page. Never overlap labels, clip them, or replace required text with ellipsis.
- Pages titled as an insight, opportunity, core conclusion, market comparison, or key metric must communicate the conclusion visually within five seconds.
- When a chart and a raw table of eight or more rows share one slide, split the table into balanced columns or move it to a roster page. Never preserve all rows by shrinking decision-critical text.
- Reflow panels that leave more than 30% unexplained blank area while adjacent evidence is compressed; whitespace must express hierarchy, not a failed layout.

## 3. Semantic tables

- Use fixed, semantic column widths rather than equal widths. Recommended weights:
  - index/rank `0.38`
  - category/store `0.65`
  - date/period `1.15`
  - status/confidence `0.90`
  - measure/volume `1.05`
  - asset/file/name `1.35`
  - purpose/definition/evidence/fields/method/citation `1.65`
- Normalize weights to 100% with `<colgroup>`. Five or more columns use the wide-table density; nine or more rows use the dense-table density.
- Chinese prose uses the serif family. Only pure numeric values, codes, and dates use the mono family.
- A cell is numeric only when its complete value is numeric plus a short unit. Text that merely contains a number, such as a filename or a methodology sentence, stays left-aligned prose.
- Index is centered; dates are centered and may wrap; pure measures are right-aligned; text is left-aligned; confidence/status is emphasized without a heavy filled badge.
- Keep header/body columns aligned, use tabular numerals, alternate row tint sparingly, and preserve visible row separators.
- Wide and dense tables may reduce type within the locked table scale, but never below the data-text floor or by arbitrary per-cell sizing.

## 4. Typography and language

- Use only the two-family system: `--sd-font-serif` and `--sd-font-mono`. Do not mix ad-hoc Chinese fonts on one page.
- Body copy stays regular. Headings and key conclusions may use 600; avoid repeated heavy bold that turns Chinese glyphs into dark blocks.
- Keep type size consistent within the same information level. Do not make one KPI, one label, or one table cell smaller merely to force a fit.
- Decision-critical body copy, table values, and non-scaling labels stay at or above 30 px on the native 2880 × 1620 canvas and at or above 13 px when fitted to a 1280 px-wide browser viewport. Source notes may use 24 px but must not carry key evidence. SVG labels are measured at their rendered size, not only by their viewBox font-size attribute.
- Same-level peer text may differ by no more than 20%. Excluding slide title and page chrome, a data page should use no more than three content type levels.
- Use professional analytical language. Distinguish observed association, explanatory hypothesis, and causal conclusion; avoid conversational qualifiers or imperative wording when the evidence supports only a validation requirement.
- Do not leave orphan characters, orphan lines, broken punctuation, distorted Chinese glyphs, or awkward manual line breaks.
- PDF export must embed the Chinese fonts used by the deck.

## 5. Internal-field hygiene

- Never paint implementation notes, code, audit text, template names, overflow markers, or hidden explanations on the canvas.
- Remove strings such as `溢出链末页`, `overflow_of`, `data-pack`, debug labels, fenced code, `<cite`, `cite index=`, and tool tokens from visible output.
- SOURCE / GLOSSARY / CONCLUSION / CONFIDENCE stay in `#sd-explain`; `?export=1` and print omit the drawer and workshop chrome.
- Hidden audit copies must not be used as visible evidence or leak into PDF text.

## 6. Efficient export

- Finish the complete HTML render and browser audit before the first PDF export. Do not export after every CSS adjustment.
- Export only changed decks after deck-local edits. Re-export every affected deck after shared renderer, token, font, or page-family changes.
- Use project names for final PDFs and place them in one explicit output folder.
- For long decks, print in resumable chunks: 32 pages normally, 16 pages for 1,000+ page decks, and 8 pages only for an isolated failing range.
- Reuse already printed valid chunks within the same export run. If Chrome fails, isolate the smallest failing range and resume; do not restart completed chunks.
- Keep the server on an unoccupied port and verify final folder and file URLs return HTTP 200.
- Before replacing a published HTML or PDF, preserve the current pair as an immutable, named revision with checksums. Never use the live filename as the only copy.
- Register every project in the project catalog so the shared revision store and `/projects/<project>/history` view apply uniformly; do not implement deck-specific version logic when the platform history model already covers it.

### Long-form HTML module export

- Treat each top-level semantic module (normally `section`) as an indivisible page unit. PDF page count must equal module count; decorative document footers do not create another page.
- Give every module an explicit print page size, zero external print margin, `break-after: page`, and a fixed printable content box. Hide interactive controls, tooltips, reveal states, and screen-only ornament during print.
- `break-inside: avoid` is insufficient: a module taller than the printable box can still be clipped or fragmented. Before print, measure the module's rendered content after fonts, SVG, and charts finish; uniformly scale the module wrapper only when it exceeds the available height.
- Scale the complete module as one unit. Do not shrink individual labels, tables, or figures independently, and do not change copy, data, chart geometry, or module order merely to make pagination pass.
- If the fitted module falls below the applicable typography floor, redesign that module's internal layout while preserving its single-page semantic boundary. Do not accept unreadable scale as a successful export.
- Activate print media, wait for fonts/SVG/charts, run fitting against the print layout, then invoke PDF generation. Also register `beforeprint` as a manual-print fallback; screen-layout measurements are not authoritative. An automated exporter must explicitly emulate print media and call the fitter before `page.pdf()`.
