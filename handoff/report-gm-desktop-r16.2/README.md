# ForecastMaster GM Desktop R16.2 — compact, source-aware review

This is a separate report-only replacement for R16.1. The receiving operator
confirmed that R16.1 opens, the one-time reporting setup completed, the native
refresh succeeded without stage errors, and model refresh completed. Numeric
Core Oral and Paed SIP rows subsequently appeared. Those are receiving facts;
R16.2 Desktop rendering and company reconciliation still require the checks in
`OPEN FIRST.txt`. No cloud report or company source data was changed here.

## What changes

- Growth drivers and Forecast tiers use two searchable multi-select dropdowns.
  Select all / Clear all operate on the search results. A driver tick controls
  its tiers; partial selection is indicated. Clear all stays empty.
- Choices come from the preferred ADS files for the selected Affiliate/cycle,
  or explicit custom files. The source priority remains Plan ADS, ADS, then the
  highest numbered ADS. Older ADS revisions cannot introduce unavailable tiers.
  Drivers with no ADS source are excluded from the selected total and named in
  expandable Source details. Missing selected-cycle cohorts and ambiguous ADS
  candidates remain visible problems; they never become a partial complete total.
- Driver/tier identity follows its source name, not feed row position. New
  revisions or a different row order cannot silently move a saved selection to
  another sector. An old index-based R16.1 selection is reset to available scope
  with an explanatory Source details notice. An explicit empty selection remains
  empty. The new delivered PBIP starts with fresh state.
- Scope comes before the headline. The headline shows one labelled summary
  period, Plan, and Overcall/Undercall against the selected trend, with amount
  and percentage together. All selected periods remain in the executive table.
  The repeated driver movements and FY + YTG shortcut/captions are hidden.
- The table starts with drivers. Drivers + sectors permits the existing drill
  view; the graph can retain its own presentation of the same included scope.
  Ranking controls hide when there is only one comparable row.
- IMS/Market does not display irrelevant Channel/Sub-channel controls. They
  reappear for Ex-factory with the existing choices preserved. Affiliate, cycle,
  Units/Value, visible month calendars and currency plan rates remain available.
- S&OP uses the same compact scope. Off channels occupy smaller rows; active
  contexts retain their bridge order, aligned subchannels and measure spacing.
- Both new native pages are 1440 x 810 with FitToPage and a matching visual.
  One visual viewport owns vertical content scrolling. Search menus scroll only
  while open; wide summaries retain their useful horizontal scrollbar. Arbitrary
  Power BI zoom settings can still add a separate application canvas scrollbar.

## Missing-history evidence and numerical safeguards

The operator's read-only check for Market Value, Sep 2025–Aug 2026, found all
12 numeric months for Vegan. Vegan 2K had only 11 or 8 complete months across the
returned source revisions, with 1 or 4 missing cells. This explains why selecting
that tier can preserve a Plan total while withholding a complete 12M benchmark.
Removing a sector changes Plan legitimately; a benchmark must use exactly that
same remaining scope. R16.2 shows an expandable history diagnostic naming the
sector, measure, window and missing-month count. No sales figures or company
revision IDs are stored in this public handoff.

There is no history imputation, shorter-window fallback or source repair. The
numeric read/cutoff/fit/parts/point/demand/sop routines remain byte-identical to
R16.1. Complete named FY/YTD/YTG periods, weighted Share, numeric zero, missing
FX, and separate IMS/EF cutoffs retain their rules. Actual months stay unchanged;
trend variance applies to forecast months, so an actual-only YTD has zero
variance. These are existing business semantics, not a new definition of growth.

The existing R16.1 date and transport safeguards remain: interpret zoned host
values before taking the calendar month, count exact aggregate-delivery repeats
once, and withhold conflicts or partial deliveries. All earlier packages and
company rollback files remain preserved.

## Local validation and remaining gates

`VALIDATION-*.json` contain explicitly synthetic evidence. The packaged visual
was tested in headless Edge, including two ADS drivers among five raw drivers,
500 tiers across ten drivers, search/bulk actions, partial selection, empty scope,
stable identities after feed reorder, source priority, incomplete training data,
Units/Value/FX, Share, refresh invalidation and segmented transport. The selector
stays below 160px at the tested desktop width for both four and 500 tiers. The
only open-page vertical content scroller is the visual viewport. Local choices
request no further model fetch after the complete feed is loaded.

TypeScript and Power BI packaging lint pass. The packaging tool still reports
optional feature recommendations, including high contrast, localization and
cross-visual selection; these are not claimed supported or qualified here.
Synthetic timings do not establish company-laptop speed or model-loading time.
Eleven generated project files validate against public Microsoft schemas. Three
visual containers preserve source schema 2.14.0, whose public URL returns 404;
native Desktop validation remains necessary.

The original thin PBIX is read only. `prepare_project.py` creates a NEW PBIP/PBIR,
retains the existing live model and feed expressions, removes Review meeting,
and preserves all Refresh Demand files byte for byte. Company-bound output and
its source backup are outside this public repository. This is a generated PBIP
candidate, not a claimed Desktop-saved PBIX. No company publication occurred.

The reporting setup and GM-RULES are unchanged. The operator already completed
setup and native/model refresh: do not repeat them for this report-only update.
Internal Demand review / Explore in S&OP navigation carries scope and plan rates.
Native Power BI page tabs have independent visual sessions. Plan rates remain
review-session inputs with no business rate prefilled. Future non-UK currencies
require qualified base metadata; this candidate does not invent currency maps.

GitNexus impact probes were ACTIONABLE_PARTIAL / UNKNOWN. One sources probe
stopped on a quick-graph extraction state-change sentinel. Direct source tracing,
canonical BR-005 and bridge-rule lookup, preservation checks and focused numeric/
packaged-browser tests supplement those incomplete graph results. No graph-safe
or zero-impact conclusion is made. The final change-scope gate failed closed
with incomplete analysis; detect_changes was UNAVAILABLE with
AUTHORITY_DRIFT_BLOCKS_CONCLUSION. These are unresolved graph gates, not a pass.
Application source and workbooks remain
untouched. Receiving company totals, initial load/interaction speed, native
rendering and eventual published-button operation remain separate gates.

## Reproduce

From Visual, install the existing package lock with npm ci --ignore-scripts.
From this folder:

```text
python3 build_visual.py
Visual/node_modules/.bin/tsc -p Visual --noEmit
Visual/node_modules/.bin/tsc Visual/src/live.ts --target es2022 --module commonjs --skipLibCheck --outDir local-test/math
node check-math.cjs
node check-selection-math.cjs
node check-scope.cjs
```

Run node_modules/.bin/pbiviz package from Visual. Then from this folder:

```text
python3 build_fixture.py
node check-package.cjs
node check-layout.cjs
python3 prepare_project.py <private-source.pbix> <new-private-output-folder>
python3 check_project.py <private-source.pbix> <private-output-folder>
```

The two browser scripts use the installed Windows Edge/Playwright runtime;
adapt the runtime path on other hosts. `check-reader.cjs` also needs preserved
R16 live.ts compiled into local-test/r16-before. Build fixtures and browser
captures are ignored and synthetic. Never commit a company report, source
metadata, screenshots or business amounts to this public repository.
