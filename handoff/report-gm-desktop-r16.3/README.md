# ForecastMaster GM Review R16.3 — aggregate totals, cascade and zoom

The receiving operator opened R16.2 and reported four linked defects: strict
sector completeness suppressed driver history/variance, Forecast tiers still
listed other drivers, host zoom did not scale the content, and the two pages'
calendars/filter/status positions differed. This separate report-only candidate
addresses those requests. R16.2 and every earlier package remain unchanged.
No company source data, reporting rules, model definition or Service report was
changed. R16.3 native Desktop acceptance remains pending.

## Display totals follow the bridge

The application-owned BR-018, V08 operator source and subtotal policy, documents
SUM_AVAILABLE_V1: display totals use available values while missing details stay
unavailable. The enforcing source is channel_bridge/operator_formulas.py
(available_total) and sector_summary.py (sum recipes). This later display policy
supersedes the historical complete-member display rule. The operator explicitly
requested that behavior for this GM report on 22 October 2026.

R16.2 had incorrectly carried its strict leaf completeness rule into every
aggregate. R16.3 sums the available numeric members for each selected monthly
scope, then fits the 6M/12M/24M trend to that aggregated monthly series. A driver
or combined selection can therefore have valid history and variance when an
individual tier lacks an observation. It does not sum per-tier trend fits or
remove a chosen tier wholesale from every month. The selected Plan, chart,
headline, summary, run rate and S&OP totals use the same inclusion rule.

Single-tier detail still returns unavailable for its own missing observations.
An entirely unreported month also remains unavailable in this report: there is
no qualified source zero to invent. All required period/training months must
exist, numeric zero stays valid, ratios use paired available numerator and
denominator components, and a zero denominator remains undefined. Missing or
ambiguous source cohorts remain blocking. Different actual cutoffs in one
aggregate trend are not silently blended. These display totals do not qualify
source/export/publication completeness or fill missing leaf forecasts.

The history diagnostic now checks the scopes actually displayed. A total is not
warned merely because one undisplayed sector has a gap. A sector drill view can
still explain that sector's unavailable comparison. Actual months are unchanged;
trend variance applies after the relevant saved IMS/EF cutoff, so actual-only
YTD variance remains zero.

## Driver-to-tier cascade

The source-aware driver list is unchanged: preferred Plan ADS, ADS, then highest
numbered ADS per Affiliate/cycle/driver, or explicit custom sources. Forecast
tiers now list only the selected drivers' tiers. Driver scope is saved separately
from child ticks. Clearing tiers leaves the chosen driver and its tier options
available; selecting a driver adds its tiers, removing it removes those children.
Search and filtered Select all / Clear all work at both levels. Internal page
navigation carries both parent and child scope. Stable name-based identities
survive feed order changes; legacy positional state retains its migration guard.
The compact selector stays the same height with four and 500 test tiers.

## Host zoom and matching headers

The visual now consumes VisualUpdateOptions.viewport on every update and scales
one fixed 1440px logical stage. Resize/ResizeEnd updates without dataViews preserve
the cached application, selections, data and DOM. There is no model requery or
state-persist roundtrip for a zoom change. Chart coordinates use logical sizes;
hover positions are transformed from physical pointer coordinates. This follows
Microsoft's viewport/resize-only guidance:
https://learn.microsoft.com/en-us/power-bi/developer/visuals/custom-visuals-resize-optimization-guidelines

The GM Review native page retains 1440 x 810 and FitToPage. Fit to page fits that report
canvas; long report content and tables still use one vertical content scrollbar.
It does not shrink all dynamic table rows into one unreadable screenshot.
Native Power BI resize/fit remains a receiving gate; the local Edge host simulates
50%, 80%, 100% and about 103% viewports, including updates without dataViews.

The two views now share the same header geometry: Review months and Plan status,
ADS/source/cutoff information, Source details, then five aligned filter positions.
Affiliate and demand cycle keep their columns; Display keeps the fifth. S&OP
leaves the Section/Measure positions blank. Its Channel/Sub-channel/Measure choices
remain in the bridge selector. Header and scope coordinates match in Units and
Value tests. Existing control nodes are moved, preserving handlers and values.

## One review page, two views

The operator questioned the duplicate native S&OP page on 22 October 2026.
This report now has GM Review and Refresh Demand as its only native pages.
Demand review and Explore in S&OP / Back to Demand review stay inside the same
review instance, preserving selections and avoiding a second data load for a
duplicate page. This is a design decision for this existing custom visual,
not a universal rule that all Power BI reports should have a single page.
Microsoft supports both page navigation and saved-view navigation:
https://learn.microsoft.com/en-us/power-bi/create-reports/button-navigators
Earlier three-page projects remain rollback options.

## Validation and delivery boundary

VALIDATION-*.json are synthetic local evidence. Tests cover aggregate versus leaf
missingness, total regression over available monthly history, whole missing months,
source ambiguity, complete calendar windows, zero/FX, weighted Share, source order,
refresh invalidation, segmented transport, 500-tier scale, parent/child selection,
matching page geometry and hover values under host zoom. TypeScript and Power BI
packaging lint pass. Optional packaging recommendations (high contrast, localization,
cross-visual interactions, etc.) are not claimed qualified.

Read, cutoff, leaf fit/parts/point, date/transport decoding, source selection helpers,
GM-RULES and setup remain byte-preserved against R16.2. The aggregate demand/S&OP
routines and diagnostics intentionally change to the requested display policy.
Ten project files validate against public Microsoft schemas. Two source
visualContainer 2.14.0 URLs return 404, so native Desktop validation is still needed.
GitNexus impact probes remain partial/UNKNOWN; demand was ambiguous in the provisional
graph. Bounded direct tracing and numeric/packaged-browser tests supplement those
incomplete results. The final change-scope gate failed closed with incomplete
analysis; detect_changes returned UNAVAILABLE / AUTHORITY_DRIFT_BLOCKS_CONCLUSION.
No graph-safe or zero-impact conclusion is made.

The private generated PBIP retains the existing connection/feed expressions and
byte-preserves Refresh Demand plus the original thin PBIX rollback copy. Do not
commit the company-bound project, screenshots, identifiers or business figures to
this public repository. The input PBIX is read only, never patched/re-zipped.

The operator already completed the reporting setup and native/model refresh.
Do not repeat those steps for this report-only update. Plan rates remain blank
review-session inputs until supplied by the reviewer. The report has one native GM Review page with both Demand and S&OP modes in
one visual instance, plus the preserved native Refresh Demand page. This removes
the duplicated S&OP native page and its independent selection state. Initial model load, actual company reconciliation, native zoom,
company speed and published-button behavior remain separate receiving checks.
No company publication was performed.

## Reproduce

Install the existing lock with npm ci --ignore-scripts from Visual. From this folder:

```text
python3 build_visual.py
Visual/node_modules/.bin/tsc -p Visual --noEmit
Visual/node_modules/.bin/tsc Visual/src/live.ts --target es2022 --module commonjs --skipLibCheck --outDir local-test/math
node check-math.cjs
node check-aggregate.cjs
node check-selection-math.cjs
node check-scope.cjs
node check-preservation.cjs
```

Run node_modules/.bin/pbiviz package from Visual, then python3 build_fixture.py.
Run check-package.cjs, check-layout.cjs and check-viewport.cjs with the installed
Windows Edge/Playwright runtime (adapt its local path on other hosts).
check-reader.cjs additionally needs preserved R16 live.ts compiled into
local-test/r16-before. Browser captures/fixtures stay ignored and synthetic.

```text
python3 prepare_project.py <private-source.pbix> <new-private-output-folder>
python3 check_project.py <private-source.pbix> <private-output-folder>
```

OPEN FIRST.txt provides the receiving steps. Preserve every earlier version.
