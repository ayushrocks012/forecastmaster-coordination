# R09 — Executive Period Review

Open [index.html](index.html) in Edge or Chrome. This builds on R08's executive
proposal using illustrative data. R07 and R08 remain unchanged and available
through [the design chooser](../index.html). The named R07 baseline is still
`design-driver-sector-r07`.

## New review improvements

- **Compare 2026 FY + YTG** adds those periods without clearing other selected
  periods. The table adds column groups as before.
- Every selected period now has its own executive overview, including period
  dates, total plan, net variance and driver movements. FY and YTG can be
  compared side by side; different measures, plans and cycles remain separate.
- The overview explicitly says overcall or undercall while retaining signed
  numbers and percentages. Direction is not an approval or performance rating.
- Each graph states the actual-history dates used to fit the chosen 6M, 12M
  or 24M trend and the month when its forecast begins.
- In Both graph mode, each driver also has a numeric FY/YTG variance caption.
  This supports comparison alongside the independently labelled volume scales.

The shared scope, Both hierarchy, original chart horizon, standard table values,
ADS source-selection rules and source details remain available. The monthly
detail table and approval workflow remain absent. The displayed refresh time
is explicitly sample metadata; this is not a production performance result.

## Pending request

The user asked to remove the small variance bars. That change has not been
made: the current session's global rule requires a direct message starting
`CONFIDENTIALITY OPT-IN:` before an action that reduces displayed information.
The assistant requested that opt-in and continued these independent changes.
R09 must not be described as having completed bar removal.

## Checks

`validation-period-review.json` records the new comparisons, history windows,
period/cohort/measure separation, table agreement and responsive layout.
`validation-hierarchy.json` and `validation-ads.json` record retained hierarchy,
arithmetic and ADS-source regression checks. These use synthetic sample data.

With Node.js, Playwright and its Chromium browser available, run:

```bash
node check-period-review.cjs
node check-hierarchy.cjs
node check-ads-default.cjs
```

`PLAYWRIGHT_MODULE` can point to an existing installed module. Those optional
developer checks are not needed to view the preview. Static icon/tooltip
libraries may be loaded by the renderer; no company data queries are made.

Live Power BI changes remain paused pending the user's final design choice.
