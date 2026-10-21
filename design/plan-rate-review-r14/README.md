# Plan-rate review R14 — Demand review and S&OP

Open [index.html](index.html), choose **Value** in either page's Display control,
then use **Currency: GBP / USD** and **Plan rates** beside the header. Navigation
retains the shared review scope, currency and plan-rate basis. This is an offline
HTML proposal using the existing illustrative figures; Power BI is unchanged.

## Saved version and return path

**Before plan rates — Connected GM Review R13** is recorded in
`../checkpoints/before-plan-rate-review-r14.json`. All 21 files in the paired
R13 package remain byte-preserved. Open `../connected-gm-review-r13/index.html`
from the design chooser to return to both preceding pages. Earlier saved
versions remain available; no Git reset or report replacement is needed.

## Plan-rate behavior

- Value reveals a compact currency selector and a Plan rates button in each
  page's header. Selling units hides these controls without losing the selected
  currency or rates. Existing broad filters, month calendars, source selection,
  Channel/Sub-channel/Measure gates and Hide/Show remain in place.
- The panel has one selected **plan year**, and editable **USD per one local
  currency** rates keyed by Affiliate / local currency / plan year. The current
  sample has only United Kingdom / GBP; no extra affiliates or business rates
  are invented. The sample's available plan years follow its 2024–2029 horizon.
- The user explicitly chose **one selected plan-year rate for the whole review**.
  For example, selecting the 2026 plan rate applies that rate to every historical
  and forecast Value observation, regardless of its observation year. This is
  distinct from choosing an observation's own calendar-year rate.
- One shared owner holds the currency, selected plan year and all entered annual
  rates for both pages. Apply rates commits the panel's edits locally; Cancel,
  Close, Escape or clicking outside discards uncommitted edits. Switching plan
  years within the panel retains drafts until Apply or dismissal. No input
  writes to a company rate table, workbook, model or report.
- Raw fixture amounts and caches remain GBP/units. USD reporting multiplies
  monetary amounts by the selected rate exactly once. This includes actuals,
  forecasts, fitted monetary trends, total plans, absolute variances and monthly
  run rates. Axes, hover details, executive amounts and tables label the currency;
  contexts explicitly show **USD · [selected year] plan rate**.
- Units, share, business growth, variance percentages, business-period windows
  and ranking order remain independent of FX. Growth and variance percentages
  use local-currency observations, including when USD amounts are unavailable
  or the numeric FX rate is zero. Source amount/ratio/trend calculations are
  retained beneath the reporting conversion.
- No rate is prefilled. Missing or invalid FX leaves USD monetary amounts
  unavailable and shows **Plan rate required**. A numeric zero is preserved as
  monetary zero, following the existing bridge convention. Negative, Boolean,
  nonnumeric and nonfinite rates are rejected. Blank edits remove a stored rate.
- The combined host-state snapshot includes the active page, both page states
  and shared FX state. Initial rendering and restored snapshots do not save.

## Business basis

Read-only references in Smart Demand Manager: `docs/workbooks/sop_summary_contract.md`
and `docs/business_rules/BR-018_channel_bridge_prototype.md#r08-selected-view-sop`.
They define USD-per-GBP conversion, independent units/business growth/share,
unavailable missing FX and valid numeric zero FX. This proposal adds the user's
affiliate/year key and explicit single-selected-plan-year rule; it does not edit
those application contracts or copy workbook contents into Coordination.

## Checks and practical limits

`check-connected.cjs` retains the preceding scope/navigation/calendar/visibility
checks and 1,320 comparisons with the older saved page baselines.
`check-plan-fx.cjs` compares Units/GBP directly with R13, then checks USD amounts,
trends, absolute variances and run rates against the same observations at explicit
artificial test rates. It covers prior/current/future years, multiple stored
annual rates, missing/zero/invalid rates, percentage independence, both editors,
Apply/Cancel/Escape, monthly mode, state restoration and narrow light/dark layouts.
The fixture rates used by checks/screenshots are illustrative test inputs, not
default or official business rates. See both validation JSON files and
`preservation.json` for the recorded results and saved-file hashes.

Both pages retain R13's independent illustrative numeric models. Shared FX and
source-selection metadata do not establish numerical reconciliation between
those different models. Actual affiliate/currency metadata, an authoritative
plan-rate store and its write/persistence permissions, common source binding,
cross-page reconciliation, refresh invalidation and measured Power BI response
times remain live-implementation work. No Power BI, Fabric, application source,
workbook or official exchange-rate data was changed.

Build with `python3 build.py`, render `review.fragment.html` with the installed
visualization renderer and run both `.cjs` checks using Playwright. The complete
fragment bundles pinned D3 and stays below 1 MB.
