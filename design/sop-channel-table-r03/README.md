# Second page R03 — channel columns and lean lines

Open [index.html](index.html). This follows the user's rough sketch: two straight
button columns in one selector on the left, a thin line graph on the right and
the summary table directly beneath that graph. All figures are synthetic.

- Channel totals and the Community IMS build-up choices sit in the left column.
  Real subchannels sit in the right column, labelled Community or Contracts.
  The grouping does not reclassify Market, share or PI as source channels.
- Click any button once on, again off. Parents select only their own total.
  The graph, legend and table share the same selected measures. Share and
  reconciliation choices are tucked under one expandable heading.
- Search preserves channel context. Select matches adds the actual matches,
  not a context-only parent. Clear all gives an empty review.
- The graph uses thin solid actuals and dashed forecasts. There is no bar view;
  old bar-mode state is normalized to lines. Percentages retain a separate graph.
- Periods, month calendars, Units/Value and driver/sector scope stay above the
  two columns. The table retains FY/YTD/YTG and monthly modes. Hiding the
  selector preserves selections. Narrow screens stack the selector and review.

R01, R02 and the approved first-page R11 are preserved. No live Power BI or
application source changes were made. The prior
[Power BI feasibility note](../sop-side-panel-r02/powerbi-feasibility.md) still
applies; this remains a design proposal.

`check-sop.cjs` covers the two-column arrangement, clicks and keyboard toggles,
matching-only selection, forced line mode, parent context, hover/touch details,
responsive text and layout, light/dark rendering and retained scope/period
behavior. `validation.json` records 58 reconciliation comparisons and 385
raw/formatted cells matching preserved R01 across five scenarios. These are
synthetic local checks, not measured company Power BI performance.

Run with Node.js and Playwright (Windows uses Microsoft Edge):

```bash
node check-sop.cjs
```

`page.fragment.html` is editable source. `build.py` uses the pinned MIT-licensed
D3 copy in the preserved R01 vendor folder to prepare `review.fragment.html`.
`index.html` is the prepared standalone preview. `preservation.json` records
earlier-version hashes and unchanged calculation/fixture definitions. Review of
R03 and later live source/freshness/performance qualification remain pending.
