# Currency plan review R15 — both HTML pages

Open [index.html](index.html). **Plan rates** is always visible beside the page
header, including in Selling units view. The panel lists only source currencies
and their USD equivalents, such as **1 GBP = [rate] USD**. Choose Value to show
the local-currency/USD display control.

## Corrected business rule

The user's latest instruction replaces R14's annual Affiliate-specific editor:

- There is no plan-year selection, country label or Affiliate-specific rate key.
  Store one current plan rate per source currency: `{GBP: ..., EUR: ...}`.
- Discover the unique currency list from base Affiliate/currency metadata,
  independently of the current selection. The panel lists all source currencies,
  with one input per non-USD currency. USD already equals USD at rate 1.
- Multiple selected Affiliates default Value to USD, including multiple
  Affiliates sharing one currency. Mixed-currency local totals are unavailable;
  conversion to USD is required. An unchanged single-currency scope can still
  choose its local currency. Returning from Units to Value with multiple
  Affiliates defaults Value to USD again.
- Convert each currency's contributions using its own rate, then sum the USD
  amounts. Do not add GBP/EUR raw amounts or multiply their combined total by
  one currency's rate. Any missing required currency rate makes the complete
  USD total unavailable, avoiding a misleading partial total.
- Both pages share the currency display and currency-keyed rates. The header,
  graph and summary label USD as **USD · plan rate**, without an FX year.
  Actuals, forecasts, monetary trends, absolute variances and run rates retain
  the reporting conversion. Current single-affiliate business percentages and
  units remain independent of FX. Numeric zero FX remains numeric zero; missing,
  invalid or Boolean FX remains unavailable. No business rate is prefilled.
- Apply commits the local preview edit. Cancel, Close, Escape or clicking
  outside discards the draft. Pressing Enter in a rate input applies it.

## Scope and saved return point

**Before currency-only rates — Plan-rate Review R14** is saved at
`../checkpoints/before-currency-plan-review-r15.json`. All 31 R14 files and all
earlier saved designs remain byte-preserved. Open R14 from `../index.html` to
return to the preceding paired design, without a Git reset.

The actual illustrative base still contains UK/GBP only. Do not invent visible
Affiliates/currencies. The shared conversion model accepts source metadata,
deduplicates currency inputs, defaults multi-Affiliate Value to USD and converts
currency-tagged contributions before summation. The two current page adapters
submit their existing GBP observations to that model. New real Affiliate data,
per-Affiliate sources, currency-tagged monetary records and common cross-page
binding must be supplied during implementation; the fixture models are not live
multi-Affiliate report sources. The retained pages' independent illustrative
numbers do not establish cross-page numerical reconciliation.

## Validation

`check-connected.cjs` checks retained shared selection, source metadata,
calendars, local choices, Hide/Show, line emphasis, responsive light/dark layout
and 1,320 older-baseline numerical observations. `check-currency-fx.cjs` checks
the always-visible rate button, no year/country fields, shared edits, USD amounts,
absolute variances, run rates, percentage preservation, invalid/missing/zero
rates and restored currency-only state. It separately constructs isolated GBP,
EUR and USD plumbing fixtures to check multi-Affiliate defaults, currency
deduplication, conversion before summing, missing-rate completeness and mixed
local-total rejection. Those fixtures are never added to the visible UI.

See `validation.json`, `currency-validation.json` and `preservation.json` for
recorded evidence. Screenshot/check rates are explicit artificial inputs, not
official rates. The shipping default has no entered rate. Build using
`python3 build.py`, render the fragment using the installed visualization
renderer, then run both `.cjs` checks with Playwright.

Official rate storage/editing permissions, live multi-Affiliate source binding,
cross-page reconciliation, refresh/cache qualification and measured Power BI
performance remain unexecuted implementation work. Power BI, Fabric,
application source and workbooks are unchanged.
