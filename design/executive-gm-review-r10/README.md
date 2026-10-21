# R10 — GM Review

Open [index.html](index.html) in Edge or Chrome. This is the next HTML-only
proposal using illustrative data. R07, R08 and the numeric R09 remain unchanged
and available from [the design chooser](../index.html). The named R07 baseline
is still `design-driver-sector-r07`.

## Review flow

- Review period sits beside Demand cycle, above the executive position. It
  controls the overview and table together. The FY/YTG shortcut retains other
  selected periods.
- The graph follows the selected review periods by default, retaining at least
  twelve months of relevant prior history and ending at the latest selected
  period's end. Chart dates can extend this range. Editing dates switches to
  custom mode; Follow review period restores automatic alignment.
- The overview retains all selected period totals, signed gaps and offsetting
  driver movements. Monthly chart values are distinguished from period totals.
- One searchable driver/sector hierarchy owns shared scope. Parent checkboxes,
  partial selection, Select all and Clear all remain available. Graph and table
  presentation choices operate independently on that same scope.
- The table starts with driver totals. Expand a driver to show its selected
  sectors without changing scope or amounts. Sectors gives flat rows across
  drivers; Both shows all driver subtotals and their selected sectors.
- Row names stay frozen during horizontal FY/YTG scrolling. Driver rows have
  stronger subtotal formatting. Variance headers distinguish Units, pounds
  and percentage points; mixed measures identify units in their Measure field.
- Ranking explicitly chooses a selected review period and a 6M/12M/24M trend.
  Largest gaps first sorts by variance magnitude within each plan/cycle/measure,
  retaining parent-child grouping in driver views.
- Partial scope is labelled Selected total / Selected plan. Source coverage,
  actuals cutoff and the explicitly illustrative completed-refresh timestamp
  remain visible. Missing ADS does not become a complete numeric total.
- Matching files remains at the bottom, including ADS precedence, source
  details, manual override and restore. There are no variance bars, monthly
  detail table or approval controls.

## Verification

`check-gm-review.cjs` exercises period placement, aligned/custom chart dates,
row expansion, flat sectors, presentation independence, partial selection,
ranking, frozen row names, units, responsive layouts and empty states. It
compares every raw and formatted numeric table cell with preserved R09 across
seven scenarios, including weighted shares, multiple cycles and ex-factory.
It saves complete light/dark screenshots and `validation-gm-review.json`.

`check-ads-default.cjs` retains the independent ADS-priority, ambiguity,
missing-source, override and restoration checks and saves `validation-ads.json`.

Run with Node.js and Playwright available:

```bash
node check-gm-review.cjs
node check-ads-default.cjs
```

`PLAYWRIGHT_MODULE` can select an installed Playwright package. The check uses
Microsoft Edge on Windows and Playwright Chromium elsewhere. Node/Playwright
are developer verification tools; they are not required to open the design.

The local GitNexus CLI was unavailable and its read-only quick graph did not
resolve embedded HTML functions. This is unknown graph coverage, not proof of
zero impact. Its subsequent change-scope gate also returned incomplete analysis.
Exact source tracing, preserved arithmetic-function hashes and numeric
before/after checks bound this change to a new prototype; no production source
was modified. These checks do not claim a passing full graph gate.

## Speed and future implementation acceptance

The HTML uses local illustrative data and retained data/trend caches. Its receipt
records warm render timings and confirms no requests during those interactions.
The target is under 200 ms for warm selections. Those measurements describe
this synthetic prototype; Power BI performance is unmeasured.

After design approval, the separate Power BI implementation must demonstrate
cycle-data loading, local warm scope/measure/presentation changes, freshness
after completed refresh and invalidation of old cached data. Measure realistic
data volumes and visible response time, preserving the current saved report
and native refresh button. This proposal does not install any of that work.

Live Power BI changes remain paused pending explicit approval.
