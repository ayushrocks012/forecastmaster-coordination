# R11 — Month Range Review

Open [index.html](index.html). This is the HTML-only revision following the
user's correction to R10. Earlier designs remain unchanged.

- The top retains Demand cycle, Channel, Sub channel, Section and Measure.
- The From/To month calendars are always visible beside the country/cycle
  heading. They control the graph's visible months, initially Jan 2025–Dec 2027.
- FY/YTG and other named periods belong to the executive-summary controls.
  They continue to drive its period columns and the executive overview.
- Changing summary periods or cycles does not reset the chosen chart months.
  Changing chart months does not change summary periods or their totals.
- Chart date range and summary period are labelled separately above the graph.
  Summary-period shading remains a visual guide inside the selected chart range.
- Expandable driver totals, flat sectors, Both views, shared scope, numeric
  variances, independent presentation choices and ADS defaults remain intact.

`check-gm-review.cjs` verifies control placement and calendar independence,
graph points after calendar changes, reversed-range handling and retained R10
interactions. It also verifies 819 raw/formatted cells against R09 across seven
numeric scenarios and responsive light/dark rendering. `check-ads-default.cjs`
verifies source precedence, manual overrides, missing ADS and ambiguity.

Run both checks with Node.js and Playwright; Windows uses Microsoft Edge:

```bash
node check-gm-review.cjs
node check-ads-default.cjs
```

The receipts and complete screenshots are saved alongside the source.
`preservation.json` binds the source to unchanged calculation/source-policy
function hashes and records preserved earlier-version bytes. The prior
GitNexus HTML coverage limitation remains; no full graph gate is claimed.

Timings describe synthetic local interactions only. Power BI implementation,
production performance and refresh-cache invalidation remain pending design
approval. No live Power BI items were changed.
