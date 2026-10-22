# ForecastMaster GM Review R16.5 — monthly hover values

The receiving operator noticed tooltip amounts changing during tiny movements
between month points. Both R16.4 chart handlers interpolated values along the
connecting line while rounding the displayed month. Those intermediate amounts
were not monthly observations. R16.5 corrects hover in Demand and S&OP only.
R16.4 and all earlier delivered files remain unchanged.

The nearest month determines the tooltip, vertical guide and point markers.
Moving within that month's half-way boundaries keeps the same monthly values;
crossing a boundary selects the adjacent month. The tooltip reads the existing
monthly series point, including the selected month's trend benchmark and weighted
Share. Currency formatting and Units/Value follow the existing selection. Blank
points are never interpolated or replaced with zero. When no selected series has
a point for that month, the tooltip says No data for this month. A valid month
beside a gap, numeric zero, the final month and a one-month view remain usable.
Click-to-pin and zoom-coordinate conversion are retained. The drawn connecting
lines, numerical series, totals, periods, source selection and model are unchanged.

R16.4's native 1440 x 2400 canvas/FitToWidth, shared summary periods, headline
matrix and hierarchy ordering carry forward without source changes. Native zoom
and drag acceptance still need the work-laptop checks described in its preserved
README. This tooltip correction does not establish those receiving gates.

## Evidence

The same synthetic feed reproduces the changing-value defect in the preserved
R16.4 package and verifies its absence in the R16.5 package. Monthly hover tests
cover both modes at 50%, 80% and 100%, exact actual/forecast/monthly trend values,
USD plan-rate conversion, weighted Share, snap boundaries, pinned hover, zero,
missing observations, adjacent valid points and single/final month windows.
There are no script errors or new model fetches from hover or resize. Viewport
regression now requires exact tooltip equality at each zoom, replacing the old
interpolation tolerance. Aggregate/selection, package/cache and FX regressions
pass. TypeScript and package lint/build pass; optional features are unqualified.

The full R16.4 numeric engine, source helpers, layout, viewport, drag/order,
review adapter, setup and rules are byte-preserved, alongside every R16.4 tracked
file. The new monthly_hover.py changes only both hover-handler bodies during the
existing reproducible build; exact source anchors fail closed on drift. Ten
available Microsoft project schemas validate; two retained 2.14.0 visualContainer
URLs are unavailable. GitNexus impact remains partial/UNKNOWN (drawPlot has two
candidates); final scope analysis is incomplete. Direct tracing and focused tests
supplement that evidence; no zero-impact conclusion is made.

Company-bound output stays outside this public repository. The source PBIX is
read-only. The separate private PBIP retains the original connection/feed, native
Refresh Demand and byte-identical rollback source. No company model, Fabric item
or Service report was changed or published. Actual native rendering, company
reconciliation, zoom/drag and measured speed remain receiving checks. Do not
repeat the already successful reporting setup/model rebuild for this update.

## Reproduce

Use the existing lock/dependencies from Visual, then:

```text
python3 build_visual.py
Visual/node_modules/.bin/tsc -p Visual --noEmit
Visual/node_modules/.bin/tsc Visual/src/live.ts Visual/src/review-order.ts --target es2022 --module commonjs --skipLibCheck --outDir local-test/math
node check-math.cjs
node check-aggregate.cjs
node check-selection-math.cjs
node check-preservation.cjs
```

Run node_modules/.bin/pbiviz package from Visual; run python3 build_fixture.py.
With Windows Edge/Playwright, run check-monthly-hover.cjs, check-package.cjs and
check-viewport.cjs. The hover regression also uses the preserved R16.4 local
fixture, built with its build_fixture.py if absent. Runtime paths are local to
the test laptop. The earlier regression scripts remain available unchanged.

```text
python3 prepare_project.py <private-source.pbix> <new-private-output-folder>
python3 check_project.py <private-source.pbix> <private-output-folder>
```

OPEN FIRST.txt contains the receiving steps. No setup rerun is needed.
