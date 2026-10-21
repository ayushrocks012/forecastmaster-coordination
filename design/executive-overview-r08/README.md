# R08 — Executive Overview

**Open [index.html](index.html) in Edge or Chrome.** This is the new proposal,
using the same illustrative values and source-selection rules as R07.
The Power BI report and production packages have not been changed.

The preceding design is saved as **R07 — Driver and Sector Review**.
Open [the saved R07](../executive-review-r07/index.html) at any time, or use
[the design chooser](../index.html) to compare both versions. Its files are
unchanged; the named Git tag is `design-driver-sector-r07`. The checkpoint
record is [here](../checkpoints/driver-and-sector-review-r07.json).

## What to compare

1. **Executive position:** the plan and variance appear near the top, with the
   driver movements that offset each other. These recalculate with the shared
   scope and chart trend benchmark. There is a distinct observation for each
   selected plan cohort and measure. It explicitly uses the first displayed
   summary period when more than one period is selected.
2. **Data context:** actuals cutoff, YTG month boundaries and selected plan-source
   coverage appear together. The refresh timestamp is explicitly a sample
   timestamp, not a company refresh claim. Missing sources remain visible and
   prevent a complete total.
3. **Clear control roles:** Review scope chooses included drivers/sectors;
   Chart grouping and Table row layout change presentation. Driver-only,
   sector-only, Both and combined chart options are retained.
4. **Period context:** FY/YTG column groups show their month boundaries. The
   selected periods are shaded on the monthly graph; all chart observations
   and the chosen month range remain available. Both charts explicitly state
   that their vertical scales are independent. Combined-total charts have direct
   plan/trend endpoint labels at suitable widths.
5. **Variance review:** numbers remain in the standard table, with signed bars
   added to absolute-variance cells. Ranking uses an explicit 6M/12M/24M window
   and the first displayed summary period. In Both mode, sectors stay under
   their driver; sector-only mode ranks sectors across drivers.

The graph and table continue to share data selection and have independent
presentation controls. All 6M/12M/24M table columns, source choices, source search,
ADS override/restore and Matching files at the bottom are retained. There is no
monthly detail table or ADS approval workflow.

## Preview checks

The JSON receipts record local synthetic browser checks, not live Power BI
performance or company-data qualification:

- `validation-executive.json`: observation/table agreement, context dates,
  source coverage, period shading, signed bars, explicit ranking, distinct
  measure/cohort values, responsive layout and no external data queries.
- `validation-hierarchy.json`: retained parent/child selection, totals,
  variance arithmetic, weighted share aggregation and Both views.
- `validation-ads.json`: retained ADS precedence, numeric suffix ranking,
  source override/restore and missing/ambiguous candidate handling.

With Node.js and Playwright available, run `node check-executive.cjs`,
`node check-hierarchy.cjs` and `node check-ads-default.cjs` from this folder.
`PLAYWRIGHT_MODULE` can point to an existing installed module. Viewing the
preview requires none of those developer checks. The standalone renderer may
load static icon/tooltip libraries; application values are embedded sample data.

## Returning to R07

For design review, simply open the preserved R07 file; no rollback of the
repository is needed. If the user chooses R07 as the working design, future
edits can start from that saved source. Do not reset the repository, remove
other handoffs or replace the Power BI report to switch prototype designs.

**Pending:** user review and choice of design, then separately authorised
production implementation and company validation.
