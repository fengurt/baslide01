# TIANSIGHT publishing audit checklist

Complete every applicable gate before declaring a deck or PDF finished. Record counts and failures; “looked okay” is not an audit result.

## A. Content fidelity

- Run `deck-audit` against the source material for dropped numbers, invented claims, altered units, and mismatched page evidence.
- Verify every visible number is source-authorized or an explicitly identified renderer-derived value.
- Confirm titles, conclusions, periods, scopes, denominators, and units agree with the source.

## B. Page-family coverage

- Count pages by L2 job and list unclassified fallbacks. Required result: zero unexplained fallbacks.
- Sample every recurring page family, not only covers and charts.
- Verify insight, opportunity, KPI, roster, and comparison pages follow their shared family grammar.

## C. Figure audit

- Count formal SVG figures and identify key-data pages without a figure or semantic-table rationale.
- Check chart choice, direct labels, units, denominators, zero behavior, negative values, small-n treatment, and decision math.
- Reject fake microbars, text-only “charts”, prose heatmaps, overlapping labels, clipped marks, and legends that cannot be mapped quickly.
- For same-unit KPI groups, verify proportional zero-baseline marks. For percentages, verify the visible 100% baseline.
- When a chart shares a page with eight or more raw-data rows, verify that the table is split, continued, or moved without reducing decision-critical type below the font floor.
- Reject unexplained blank regions exceeding 30% of a data panel when adjacent evidence is visibly compressed.

## D. Table audit

- Count all roster tables and wide/dense subsets.
- Browser-check every roster table against its `.sd-content` rectangle. Required result: zero left, right, top, or bottom overflow.
- Verify semantic `<colgroup>` widths, header/body alignment, and correct field-specific alignment.
- Flag mixed text cells carrying the numeric class, dates forced into adjacent columns, prose rendered in mono, or status text rendered as an oversized badge.
- Reject any heatmap with no usable measure when a prose cell is 60+ characters; render it as a roster instead.

## E. Typography and glyph audit

- Check that visible text uses only the two approved font families and that type levels are consistent.
- Record the minimum native and fit-to-viewport sizes for decision-critical body, table, and SVG text. Required result: at least 30 px native and 13 px at a 1280 px-wide fitted viewport; measure SVG labels at rendered size.
- Compare same-level peers. Required result: maximum font-size ratio no greater than 1.20; no more than three content levels on a data page, excluding title and page chrome.
- Review key conclusions for professional wording and causal discipline: association, hypothesis, and causality must not be conflated.
- Search for excessive bold and per-element emergency font sizes.
- Inspect representative Chinese-heavy pages for warped, doubled, missing, or rasterized glyphs.
- Run `pdffonts` on every final PDF. Required result: every used font embedded.

## F. Internal-field and overflow audit

- Search visible HTML and extracted PDF text for `溢出链末页`, `overflow_of`, `data-pack`, debug/code labels, `<cite`, `cite index=`, tool tokens, and hidden explanatory fields.
- Check all pages for horizontal/vertical overflow, clipped text, black squares, and workshop/export chrome.
- Required result: zero visible internal fields and zero page overflow.

## G. PDF gate

- Export only after gates A–F pass in HTML.
- Verify PDF page count equals HTML slide count and every page is 16:9.
- Render representative final PDF pages to PNG: at minimum one key-data figure, one wide table, one dense table, one insight, and one known edge case per deck.
- Inspect the latest PNGs for alignment, font rendering, label collisions, clipping, and missing graphics.
- Verify project-name filenames, final folder placement, file size shown by the folder index, and HTTP 200 for the folder and every PDF.
- Do not publish while a temporary chunk directory, stale `deck.pdf`, or intermediate audit file remains in the final folder.
- Verify the superseded HTML/PDF revision remains accessible from project history and its recorded checksums still match before replacing current-version files.

For long-form module PDFs, replace the 16:9 slide-count check with these mandatory gates:

- Count top-level semantic modules and require PDF page count to match exactly.
- Verify every module begins and ends on the same PDF page; required result: zero split, clipped, duplicated, or blank modules.
- Render and inspect every page, not only representative pages. Check the complete bottom edge of tables, SVGs, captions, legends, and notes.
- Record the minimum whole-module fit scale. A page that passes only by violating the typography floor fails the audit and must be internally reflowed before export.

## Required audit summary

Report at least: total pages, formal figures, roster tables, wide/dense table counts, overflow count, internal-field count, embedded-font status, PDF page counts, and final URLs. Any non-zero failure blocks delivery.
