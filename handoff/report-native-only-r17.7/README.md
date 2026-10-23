# Native-only R17.7 TEST

[Company-laptop steps](OPEN%20FIRST%20-%20R17.7.txt) start with one new guarded
ForecastMaster_GM_Setup cell, then one existing-TEST refresh and the new PBIP.
Production R16.6 and all prior packages retain their bytes.

## Receiving evidence and intended result

The R17.6 screenshots show both summaries loading and expanded variance columns.
They establish rendering of those states, not numerical reconciliation or a
complete successful update/refresh receipt. The operator removed some headers
to save space and then found the bare selected values ambiguous. Graph legends
repeat a long cycle/scenario prefix; the saved-files table omits ingestion time
and uses a table's Ctrl selection rather than a checkbox selector.

Operator-reported timings, in milliseconds:

| Visual | DAX | Total |
|---|---:|---:|
| Monthly graph | 26190 | 28287 |
| Review Summary | 17367 | 18979 |
| Executive Summary | 4742 | 6322 |

The timing reply did not name its view; screenshots show Sectors. These are
individual visual durations, not additive whole-page timing. Their relative
size makes DAX a concrete bottleneck. It does not by itself separate formula
evaluation, Direct Lake column loading, storage scans or capacity contention.

## Native interaction improvements

Compact 64px dropdowns retain readable labels and pending-state headers with
explicit 2px padding. Redundant section heading text is removed. The graph/view
and table-trend controls stay labelled; graph/review and Executive trend choices
remain independent. Start/End are still monthly and Section/Measure separate.

Native SeriesLabel starts with scope and line kind, moving cycle/scenario suffixes
later. Native end-of-line labels and a right legend are configured, with the
existing actual/forecast/trend styles. Dense native labels can still collide;
Focus mode and scope selection are available. No arbitrary series cap or Top N
silently drops data. No custom visual or script renderer is added.

Classic native Basic slicer checkboxes, search and non-Ctrl selection replace
table-row selection as the file chooser. ImportedAtUTC exposes the existing
timestamp parser's result, not NOW(), file modified time or publication status.
FileChoiceLabel includes a readable UTC timestamp and revision identity; it is
sorted by ImportedAtUTC newest first. Unavailable import time remains explicit.
The separate audit table shows that timestamp and both actual cutoffs.

Automatic ADS remains default. Selected files is now exposed as a native mode.
The selected native-file IDs are intersected with the original file/country/
cycle context; the old source algorithm, unique cohort/tie/coverage guards and
automatic ADS ranking remain. Manual alternatives are grouped by saved scenario
in matrices; they are not added into one plan or grand total. Choosing multiple
ambiguous versions of the same driver/cycle/scenario remains unavailable.
Scenario-to-mode already had a model relationship: it is verified and reused,
with no new relationship or bidirectional path.

Two native ApplyAllSlicers action buttons batch all page choices. Their presence
defers redraw until Apply, so choosing five files does not issue five complete
report refreshes. Headers retain pending indicators. In Desktop edit mode only
the action button requires Ctrl+click; file checkboxes do not. Service reading
mode uses a normal button click. The UI behavior remains a receiving gate.

## Performance changes and correctness boundary

The existing N Trend Monthly recomputes its regression training for future
points. N Benchmark also invoked it inside its month iterator. R17.7 introduces
two hidden scalar coefficient measures with the same history, missing-month
test and least-squares arithmetic. Axis filters are removed for coefficient
evaluation; N Benchmark holds mean/slope outside the future-month iterator.
The native engine can reuse those invariant coefficient contexts across points.

N Plan avoids the denominator branch for non-ratios. N Variance % holds plan and
benchmark once. The monthly numerator/denominator project only Sector, Amount
and MissingCells before GROUPBY, preserving duplicate rows and the exact
per-sector bad-cell exclusion. Storage/source filters, valid-zero behavior,
FX, country/cycle/driver coverage, full-year/YTD/YTG/H1/H2 masks, earliest cutoff,
mixed-fit cutoff rejection and weighted share denominators remain.

The graph's external N Line Visible visual measure filter is removed; the exact
same admission check instead wraps N Chart Monthly. This avoids that external
value-filter constraint path without losing its view/mode/cycle/window checks.
The copied query confirming redundant stages was for R17.5's summary, not this
graph; R17.7 graph query/timing verification remains a receiving gate.

Fifteen existing expressions change: six performance expressions, eight
source-choice adapters (two overlap the performance expressions), and two
scenario display guards plus the graph-admission wrapper. Two scalar fit measures are added: 51 measures total,
24 helper tables unchanged in count. Only native file/line helpers gain three
metadata columns. Original source tables, relationships, roles, source mode,
connections, dynamic formats and refresh worker are preserved.

No physical Fabric/Delta rewrite or aggregation cache is installed without a
measured reason. Model-query optimization and batching address observed work
first. If comparable warm report queries remain slow, the next investigation
must separate Direct Lake loading, scan/cardinality and formula costs before
choosing a TEST-only import/aggregation design. Do not run VACUUM, purge historical
revisions, increase memory limits or seek tenant-admin changes as a speed fix.

## Before-write numerical guard

The one-cell update first validates known R17.6 definitions and TEST identity.
SemPy evaluate_dax uses read-only connections and virtual DEFINE MEASURE
overrides. Before any model write it compares 72 old/candidate values: plan,
benchmark, variance % and a December trend point across Market/Ex-factory/Share,
6M/12M/24M and current/next FY for one available ADS driver. Blanks and zero
remain distinct; incomplete/all-blank results, failed evaluation/compile or
mismatches refuse the update. No company amount is printed or stored. Its
original-first timings have cache-order bias and are not report speed proof.

Only after passing does it verify private full UTF-8 backups, check concurrency
and cloud mapping, update once without purge, and compare complete readback.
Identical DAX line representations are tolerated for measure/format text and
five explicitly named calculated helpers only. No other differences disappear.
Ambiguous post-write state stops further action; do not rerun or refresh.

This guard depends on existing read-only semantic-query access on the company
laptop. No credential, tenant setting or IT dependency is added. If access is
unavailable the guard refuses a model write; send that result instead of bypassing
the comparison. No company query or update ran on this host.

## Verification

Local tests cover native geometry/labels/selection/batching contracts, source
and format preservation, mocked guarded updates, read-only comparison refusal,
and 3600 independent regression-algebra scenarios with missing/zero/negative
histories and weighted denominators. Both projects pass Microsoft PBIR schemas.
These are not local DAX execution or native UI proof. A bounded backend probe
found no available task-owned synthetic engine among three saved workspace
endpoints; no user model was modified. Company before-write numerical checks,
metadata processing, native rendering/file selection/export and comparable
warm/cold performance remain receiving gates.

References: [native line series labels](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-line-chart),
[Apply all slicers](https://learn.microsoft.com/en-us/power-bi/create-reports/buttons-apply-all-clear-all-slicers),
[virtual DAX measures](https://learn.microsoft.com/en-us/dax/dax-queries),
[SemPy evaluate_dax](https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric?view=semantic-link-python),
[native authoring slicer properties](https://raw.githubusercontent.com/microsoft/skills-for-fabric/main/skills/powerbi-report-cli/references/authoring/slicers.md).
