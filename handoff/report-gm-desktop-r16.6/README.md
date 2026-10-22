# ForecastMaster GM Review R16.6 — reconciled Share and compact table

The operator found individual-sector shares plausible but the selected total
incorrect. Both aggregation routes filtered numerator/denominator to paired
numeric members. The amount rows used independent available-member totals, so
missing Abbott could silently remove valid Market from Share's denominator.
R16.6 fixes that mismatch in Demand and S&OP while preserving R16.5 and all older
packages. No company source/model/report has been modified or published here.

## Share follows the displayed amount totals

For the same scope/calendar, aggregate Share divides the independently available
Abbott amount total by the independently available Market amount total. It never
averages sector or monthly percentages. This implements the existing BR-005
ratio-of-summed-amounts rule with BR-018 SUM_AVAILABLE_V1 display aggregation.
A missing numerator no longer deletes a valid denominator, or vice versa.

Required period/training months and source uniqueness still apply. A completely
unreported month is not filled. Single-sector missing observations stay missing;
a numeric zero denominator stays undefined, and numeric zero numerator is valid.
Source/reader/leaf-fit functions and standalone amount totals are preserved.
Aggregate Share trends fit the corrected monthly ratios; amounts/Share use the
same monthly scope in charts, headline and summary.

Known mixed-currency Value Shares convert both sides through the same configured
plan-rate basis. Missing rates/unknown currencies or a zero common denominator
stay unavailable. A single known currency remains currency-neutral, retaining
its existing independence from FX inputs. No affiliate-to-currency guesses were
added; actual multi-affiliate receiving qualification remains separate.

## Dash versus numeric zero

The user clarified that the reported year-formatting difference meant a dash
versus $0. Those are different calculation states, not year-specific formats.
A dash is unavailable (required input missing or calculation undefined); $0 is
a numeric zero after the normal calculation/display conversion. Missing history
must not be turned into zero to resemble a later forecast. The S&OP cell tooltip
now explains unavailable results and explicitly labels numeric zero, using native browser title hints. Neither the
underlying observation nor its unavailable flag is changed.

## Compact Demand executive table

The user also requested removing repeated date subtitles and two-line sector
labels. Period headings now show their short names only; the exact calendar
range remains in the header tooltip. Sector-only rows show Sector – Growth driver
on one line, with a full-label tooltip if truncated. Hierarchy view lists the
driver once above its sectors, without appending it to every child. Partial-scope
counts move to the row tooltip. Native browser title hints expose moved dates and full labels. Smaller vertical padding reduces row height.
Driver expansion, sorting, all numeric cells and required calendar windows remain.

The synthetic before/after check reduces sector row height from about 52px to
29px and header height from about 115px to 97px while preserving 80 numeric cells.
Those are local measurements, not a receiving Desktop performance guarantee.

## Bounded calculation review

The local review covers all 18 displayed S&OP measures, Units and Value, Demand
source reconciliation, exact FY/YTD/YTG/H1/H2 calendars, separate IMS/EF cutoffs,
run-rate eligibility/division, same-calendar prior-year growth, signed channel
amounts, publishing leaves counted once, strict sector detail and missing/zero
states. It checks 1,728 numeric/rendered results against an independent synthetic
bridge-identity oracle. A further 720 randomized comparisons check scalar/Share
aggregation with asymmetric missing observations, with mixed-rate/cache tests.
The old Share defect is reproduced against the preserved R16.5 engine.

Existing numeric/selection, package/cache/FX, monthly-hover and hierarchy controls
also pass their local regressions. Missing/zero tooltips and actual/future period
cases are checked explicitly. This is a report runtime review against synthetic
observations, not an exhaustive workbook/formula audit or actual company-source
reconciliation. The work laptop must verify the affected scope against the bridge.

TypeScript and package lint/build pass. Ten available Microsoft schemas validate;
two retained visualContainer 2.14.0 schema URLs remain unavailable. GitNexus impact
is partial/UNKNOWN, including ambiguous symbols and a transient quick-graph lock
error; final scope analysis remains incomplete. Direct tracing and focused tests
supplement that evidence; no zero-impact conclusion is claimed.

The full 56-file R16.5 handoff remains byte-preserved. The new changes are the
aggregate ratio/FX population, availability tooltip and compact table rendering.
Source selection/transport, leaf calculations, setup/rules, viewport, drag/order,
monthly hover and the original model/feed connection remain unchanged. The
private PBIP preserves native Refresh Demand and the read-only original PBIX.
No setup/model refresh is needed. Native rendering/zoom/drag, company figures,
measured speed and publication remain separate receiving checks.

## Reproduce

Use the locked Visual dependencies, then build and type-check as in R16.5.
Compile live.ts into local-test/math and the preserved R16.5 live.ts into
local-test/r16-5-before. Run check-ratios.cjs, check-math.cjs,
check-aggregate.cjs, check-selection-math.cjs and check-preservation.cjs.

Package with node_modules/.bin/pbiviz package from Visual, then run
python3 build_fixture.py. With Windows Edge/Playwright, run
check-calculations.cjs, check-compact-summary.cjs, check-package.cjs,
check-monthly-hover.cjs and check-review.cjs. The before/after tests also use the
preserved R16.5/R16.4 ignored local fixtures. Adapt runtime paths on another host.

```text
python3 prepare_project.py <private-source.pbix> <new-private-output-folder>
python3 check_project.py <private-source.pbix> <private-output-folder>
```

OPEN FIRST.txt gives the receiving steps. Keep all previous versions.
