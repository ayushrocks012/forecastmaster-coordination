# ForecastMaster GM Review R16.4

This separate report-only candidate follows the operator's R16.3 feedback about
native zoom, summary-period placement, headline clarity and S&OP ordering.
R16.3 and every earlier version remain byte-preserved. The calculation engine,
source selection, transport, model feed, setup and reporting rules are unchanged.
No company report has been published. Native Desktop acceptance remains pending.

## Native page zoom

The previous 1440 x 810 page contained a short, scrolling custom-visual viewport.
Zoom scaled that viewport and its contents together, exposing roughly the same
portion. R16.4 uses a 1440 x 2400 native report canvas and matching visual, opening
at FitToWidth. Standard Power BI page zoom can therefore expose more content as
the canvas shrinks; FitToPage fits the entire taller canvas and makes text smaller.
A small surrounding Desktop editing margin is expected. No internal zoom toolbar
has been added. Microsoft's page-view and viewport guidance is available at:

- https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-report-display-settings
- https://learn.microsoft.com/en-us/power-bi/developer/visuals/custom-visuals-resize-optimization-guidelines

Both default views fit within the taller canvas in the synthetic fixture. Native
page scrolling handles that normal layout. Expanded sector charts/tables can
exceed any fixed native page height; one safety content scrollbar remains for
that overflow. Open dropdowns and wide matrices also retain necessary scrolling.
Browser geometry tests simulate native canvas sizes and verify content exposure,
hover coordinates and unchanged cached state with zero new fetches. They cannot
establish how the receiving Desktop or published Service renderer behaves.

## One selection row and a clearer summary

Both views now show Growth drivers, Forecast tiers and Review summary period
beside one another under the same header. Period choices have search and filtered
Select all / Clear all. They follow Review months' available years and carry
across the internal Demand/S&OP navigation. Clearing stays empty. Both views retain
full FY/YTD/YTG windows and exact H1/H2 windows; calendars do not clip a named FY.

The Demand headline uses a standard matrix: one column for every selected period,
with Plan and the graph's selected trend comparison underneath. Actuals-only
periods say Actuals only; their lower executive-table variance columns are omitted.
Classification checks each period's exact months against the saved source cutoff:
a past FY can be actuals-only while a future year's YTD is forecast. Mixed periods
retain comparisons. No underlying amount or trend formula changes.

The lower Executive summary has one header with its scope caption and Hide button.
Table rows sits left and Trend comparisons right on one toolbar. The old lower
period picker and shortcut captions no longer occupy space.

## S&OP hierarchy ordering

Hold and drag existing Channel, Sub-channel or Measure buttons. Channels move
among channels; subchannels stay within their channel; measures stay within their
subchannel. Alt+Up/Down provides a keyboard alternative. Reset order restores the
grouped bridge hierarchy. All Contracts contexts are together in that default,
with source order retained within each parent. The neutral source catalogue is
unchanged. Table rows and chart/legend ordering follow the same saved permutation.
Selection, business parentage and numeric values remain unchanged. Escape cancels
a drag; ordinary clicks still toggle inclusion. Order persists with review state.

## Validation and boundaries

VALIDATION-*.json records synthetic local evidence. Tests cover the new searchable
shared periods, calendar narrowing, empty selection, actual-only classification,
all headline periods, compact table controls, real pointer hold/drag at all three
levels, rejected cross-parent moves, keyboard/cancellation, reset, saved-order
restore and invariant displayed amounts/selection. Existing aggregate/detail,
500-tier scope, FX/Share, complete calendars, decoder/date and refresh-cache checks
remain in force. TypeScript and package lint pass. Optional packaging features
are not claimed qualified. Native drag, native zoom, company reconciliation,
measured company speed and publication remain receiving gates.

R16.3 live.ts, scope helpers, files.ts, compact_adapters.py, setup and rules are
byte-preserved. Ten project files validate against available Microsoft schemas;
two retained visualContainer 2.14.0 schema URLs are unavailable. Refresh Demand's
four source definition files and the original PBIX rollback bytes are preserved.
The existing connection and report-extension feed expressions are retained.
GitNexus impact probes were partial/UNKNOWN and the final scope gate fails closed
on incomplete analysis; direct tracing and focused tests supplement that result.
No graph-safe or zero-impact conclusion is made.

The successful company reporting setup and native/model rebuild do not need to
be repeated for this report-only update. Company-bound projects, source IDs,
figures and screenshots stay outside this public repository. The PBIX input is
read-only; generation creates a new PBIP rather than modifying its binary.

## Reproduce

Install the existing lock with npm ci --ignore-scripts from Visual. Then run:

```text
python3 build_visual.py
Visual/node_modules/.bin/tsc -p Visual --noEmit
Visual/node_modules/.bin/tsc Visual/src/live.ts Visual/src/review-order.ts --target es2022 --module commonjs --skipLibCheck --outDir local-test/math
node check-math.cjs
node check-aggregate.cjs
node check-selection-math.cjs
node check-scope.cjs
node check-order.cjs
node check-preservation.cjs
```

Run node_modules/.bin/pbiviz package from Visual, then python3 build_fixture.py.
Run check-package.cjs, check-layout.cjs, check-review.cjs, check-viewport.cjs and
check-native-canvas.cjs with Windows Edge/Playwright (adapt local runtime paths).
check-reader.cjs additionally needs preserved R16 live.ts compiled into
local-test/r16-before. Fixtures and browser captures stay ignored and synthetic.

```text
python3 prepare_project.py <private-source.pbix> <new-private-output-folder>
python3 check_project.py <private-source.pbix> <private-output-folder>
```

OPEN FIRST.txt gives the receiving checks. Preserve all earlier projects.
